import time
import json
import logging
from datetime import datetime
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from database import execute_query
from validator import validate_sql
from sql_generator import decompose, generate, fix

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOG_FILE = "logs/query_logs.json"
MAX_RETRIES = 3

class AgentState(TypedDict):
    question: str
    decomposition: Optional[dict]
    sql: Optional[str]
    result: Optional[list]
    error: Optional[str]
    retry_count: int
    status: str
    summary: Optional[str]

def log_execution(entry: dict):
    try:
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []

    logs.append(entry)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2, default=str)

def decompose_node(state: AgentState) -> AgentState:
    logger.info(f"[NODE: DECOMPOSE] Question: {state['question']}")

    try:
        decomposition = decompose(state["question"])

        return {
            **state,
            "decomposition": decomposition,
            "error": None
        }

    except Exception as e:
        logger.error(f"[NODE: DECOMPOSE] Failed: {e}")

        return {
            **state,
            "decomposition": None,
            "error": str(e),
            "status": "failed",
            "summary": "Failed to understand the question."
        }

def generate_node(state: AgentState) -> AgentState:
    logger.info(f"[NODE: GENERATE] Decomposition: {state['decomposition']}")

    if state.get("status") == "failed":
        return state

    try:
        sql = generate(state["decomposition"])

        return {
            **state,
            "sql": sql,
            "error": None
        }

    except Exception as e:
        logger.error(f"[NODE: GENERATE] Failed: {e}")

        return {
            **state,
            "sql": None,
            "error": str(e),
            "status": "failed",
            "summary": "Failed to generate SQL query."
        }

def execute_node(state: AgentState) -> AgentState:
    logger.info(f"[NODE: EXECUTE] Attempt {state['retry_count'] + 1}")

    if state.get("status") == "failed":
        return state

    try:
        clean_sql = validate_sql(state["sql"])
        logger.info(f"[NODE: EXECUTE] Validated SQL: {clean_sql}")

        start = time.time()
        result = execute_query(clean_sql)
        elapsed = round(time.time() - start, 3)

        logger.info(
            f"[NODE: EXECUTE] Success. Rows: {len(result)}. Time: {elapsed}s"
        )

        summary = build_summary(state["question"], result)

        return {
            **state,
            "sql": clean_sql,
            "result": result,
            "error": None,
            "status": "success",
            "summary": summary
        }

    except ValueError as e:
        logger.error(f"[NODE: EXECUTE] Validation error: {e}")

        return {
            **state,
            "error": str(e),
            "status": "failed",
            "summary": "Query blocked by safety validator."
        }

    except Exception as e:
        logger.warning(f"[NODE: EXECUTE] Execution error: {e}")

        return {
            **state,
            "error": str(e),
            "retry_count": state["retry_count"] + 1,
            "status": "retrying"
        }

def fix_node(state: AgentState) -> AgentState:
    logger.info(f"[NODE: FIX] Fixing SQL. Attempt {state['retry_count']}")

    try:
        fixed_sql = fix(state["sql"], state["error"])
        logger.info(f"[NODE: FIX] Fixed SQL: {fixed_sql}")

        return {
            **state,
            "sql": fixed_sql,
            "error": None,
            "status": "retrying"
        }

    except Exception as e:
        logger.error(f"[NODE: FIX] Fix failed: {e}")

        return {
            **state,
            "error": str(e),
            "status": "failed",
            "summary": "Failed to fix SQL query."
        }

def should_retry(state: AgentState) -> str:

    if state["status"] == "success":
        logger.info("[EDGE] Execution successful. Going to END.")
        return "end"

    if state["status"] == "failed":
        logger.info("[EDGE] Fatal failure. Going to END.")
        return "end"

    if (
        state["status"] == "retrying"
        and state["retry_count"] < MAX_RETRIES
    ):
        logger.info(
            f"[EDGE] Retry {state['retry_count']}/{MAX_RETRIES}. Going to FIX."
        )
        return "fix"

    logger.info("[EDGE] Max retries exhausted. Going to END.")
    return "end"

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("decompose", decompose_node)
    graph.add_node("generate", generate_node)
    graph.add_node("execute", execute_node)
    graph.add_node("fix", fix_node)

    graph.set_entry_point("decompose")

    graph.add_edge("decompose", "generate")
    graph.add_edge("generate", "execute")
    graph.add_edge("fix", "execute")

    graph.add_conditional_edges(
        "execute",
        should_retry,
        {
            "fix": "fix",
            "end": END
        }
    )

    return graph.compile()

agent = build_graph()

def build_summary(question: str, result: list) -> str:
    
    if not result:
        return "No results found for your question."

    row_count = len(result)

    if row_count == 1:
        
        if len(result[0]) == 1:
            value = list(result[0].values())[0]
            return f"The answer to your question is: {value}"
        
        else:
            values = ", ".join(f"{k}: {v}" for k, v in result[0].items())
            return f"Result: {values}"

    return f"Found {row_count} records matching your query."

def run_pipeline(
    question: str,
    max_retries: int = MAX_RETRIES
) -> dict:

    logger.info(f"[PIPELINE] Starting for question: {question}")

    pipeline_start = time.time()

    initial_state = AgentState(
        question=question,
        decomposition=None,
        sql=None,
        result=None,
        error=None,
        retry_count=0,
        status="running",
        summary=None
    )

    try:
        final_state = agent.invoke(initial_state)

    except Exception as e:
        logger.error(f"[PIPELINE] Graph execution failed: {e}")

        final_state = {
            **initial_state,
            "status": "failed",
            "error": str(e),
            "summary": "Pipeline encountered an unexpected error."
        }

    total_time = round(time.time() - pipeline_start, 3)

    logger.info(
        f"[PIPELINE] Completed in {total_time}s. "
        f"Status: {final_state['status']}"
    )

    log_execution({
        "timestamp": datetime.now(),
        "question": question,
        "decomposition": final_state.get("decomposition"),
        "sql": final_state.get("sql"),
        "status": final_state.get("status"),
        "retries": final_state.get("retry_count", 0),
        "total_time": total_time,
        "error": final_state.get("error"),
        "result_preview": (final_state.get("result") or [])[:5]
    })

    return {
    "sql": final_state.get("sql"),
    "result": final_state.get("result"),
    "summary": final_state.get("summary", "No summary available."),
    "status": final_state.get("status"),
    "error": final_state.get("error"),
    "decomposition": final_state.get("decomposition")  # ← ADD THIS
}