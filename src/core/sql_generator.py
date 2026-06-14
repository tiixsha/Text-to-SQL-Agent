import os
import json
import time
import logging
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from src.prompts.templates import DECOMPOSE_PROMPT, GENERATE_PROMPT, FIX_PROMPT

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)

decompose_template = PromptTemplate(
    input_variables=["question"],
    template=DECOMPOSE_PROMPT
)

generate_template = PromptTemplate(
    input_variables=["decomposition"],
    template=GENERATE_PROMPT
)

fix_template = PromptTemplate(
    input_variables=["sql", "error"],
    template=FIX_PROMPT
)

decompose_chain = decompose_template | llm
generate_chain = generate_template | llm
fix_chain = fix_template | llm


def decompose(question: str) -> dict:
   
    logger.info(f"[DECOMPOSE] Question: {question}")

    start_time = time.time()
    response = decompose_chain.invoke({"question": question})
    elapsed = round(time.time() - start_time, 3)

    raw = response.content.strip()
    logger.info(f"[DECOMPOSE] Raw response: {raw}")
    logger.info(f"[DECOMPOSE] Time taken: {elapsed}s")

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        decomposition = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"[DECOMPOSE] Failed to parse JSON: {e}")
        raise ValueError(f"Gemini returned invalid JSON: {raw}")

    logger.info(f"[DECOMPOSE] Parsed: {decomposition}")
    return decomposition


def generate(decomposition: dict) -> str:
   
    logger.info(f"[GENERATE] Decomposition: {decomposition}")

    start_time = time.time()
    response = generate_chain.invoke({
        "decomposition": json.dumps(decomposition, indent=2)
    })
    elapsed = round(time.time() - start_time, 3)

    sql = response.content.strip()
    logger.info(f"[GENERATE] Generated SQL: {sql}")
    logger.info(f"[GENERATE] Time taken: {elapsed}s")

    if sql.startswith("```"):
        sql = sql.split("```")[1]
        if sql.startswith("sql"):
            sql = sql[3:]
    sql = sql.strip()

    return sql


def fix(sql: str, error: str) -> str:
    
    logger.info(f"[FIX] Failed SQL: {sql}")
    logger.info(f"[FIX] Error: {error}")

    start_time = time.time()
    response = fix_chain.invoke({
        "sql": sql,
        "error": error
    })
    elapsed = round(time.time() - start_time, 3)

    fixed_sql = response.content.strip()
    logger.info(f"[FIX] Fixed SQL: {fixed_sql}")
    logger.info(f"[FIX] Time taken: {elapsed}s")

    if fixed_sql.startswith("```"):
        fixed_sql = fixed_sql.split("```")[1]
        if fixed_sql.startswith("sql"):
            fixed_sql = fixed_sql[3:]
    fixed_sql = fixed_sql.strip()

    return fixed_sql