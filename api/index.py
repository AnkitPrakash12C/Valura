from fastapi import FastAPI
from pydantic import BaseModel
from api.agent import run_agent

app = FastAPI()

class TaskRequest(BaseModel):
    task: str

@app.post("/api/research")
def research(req: TaskRequest):
    try:
        # Trigger the LangGraph agent workflow
        result = run_agent(req.task)
        return {"status": "success", "output": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}