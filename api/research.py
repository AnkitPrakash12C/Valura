from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from api.agent import run_agent

app = FastAPI()

class TaskRequest(BaseModel):
    task: str

@app.get("/")
def serve_home():
    return FileResponse("public/index.html")

@app.post("/api/research")
def research(req: TaskRequest):
    try:
        result = run_agent(req.task)
        return {"status": "success", "output": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}