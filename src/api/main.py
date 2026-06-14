from fastapi import FastAPI
from pydantic import BaseModel
from src.engine.executor import run_pipeline

app = FastAPI(
    title="Text-to-SQL Agent",
    description="AI-powered NL to SQL pipeline",
    version="1.0.0"
)

class QuestionRequest(BaseModel):
    question: str

class SQLResponse(BaseModel):
    sql: str | None = None
    result: list | None = None
    summary: str | None = None
    status: str
    error: str | None = None
    decomposition: dict | None = None  # ← ADD THIS

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Agent is running!"}

@app.post("/agent/sql", response_model=SQLResponse)
def run_agent(request: QuestionRequest):
    result = run_pipeline(request.question)
    if not result.get("summary"):
        result["summary"] = "No summary available."
    return result