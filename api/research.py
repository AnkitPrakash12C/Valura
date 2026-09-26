# from typing import Optional, List, Dict, Any
# from fastapi import FastAPI
# from fastapi.responses import FileResponse
# from pydantic import BaseModel
# from api.agent import run_agent, run_code_sandbox, explain_code_error
#
# app = FastAPI()
#
#
# class AgentRequest(BaseModel):
#     action: Optional[str] = "solve"
#     task: Optional[str] = ""
#     language: Optional[str] = "Python"
#     code: Optional[str] = ""
#     reference_code: Optional[str] = ""
#     error_details: Optional[str] = ""
#     sample_cases: Optional[List[Dict[str, Any]]] = None
#
#
# @app.get("/")
# def serve_home():
#     return FileResponse("public/index.html")
#
#
# @app.get("/style.css")
# def serve_css():
#     return FileResponse("public/style.css", media_type="text/css")
#
#
# @app.post("/api/research")
# def handle_request(req: AgentRequest):
#     try:
#         if req.action == "run_code":
#             result = run_code_sandbox(req.language, req.code, req.sample_cases)
#             mistake_analysis = None
#
#             # Automatically diagnose the mistake if the user's edited code fails or errors
#             if result.get("has_error") or not result.get("all_passed"):
#                 if result.get("has_error"):
#                     failure_info = f"Compiler/Runtime Error:\n{result.get('raw_output', '')}"
#                 else:
#                     failed_list = [
#                         f"Case {c['id']}: Input ({c['input']}) -> Expected {c['expected']}, but got Actual {c['actual']}"
#                         for c in result.get("cases", []) if not c.get("passed")
#                     ]
#                     failure_info = "Failed Test Cases:\n" + "\n".join(failed_list)
#
#                 mistake_analysis = explain_code_error(
#                     req.task,
#                     req.language,
#                     req.code,
#                     failure_info,
#                     req.reference_code
#                 )
#
#             return {
#                 "status": "success",
#                 "test_results": result,
#                 "mistake_analysis": mistake_analysis
#             }
#
#         if req.action == "explain_error":
#             explanation = explain_code_error(
#                 req.task, req.language, req.code, req.error_details, req.reference_code
#             )
#             if "error" in explanation:
#                 return {"status": "error", "message": explanation["error"]}
#             return {"status": "success", "explanation": explanation}
#
#         result = run_agent(req.task, req.language)
#         if "error" in result:
#             return {"status": "error", "message": result["error"]}
#         return {"status": "success", "data": result}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}

from typing import Optional, List, Dict, Any
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from api.agent import run_agent, run_code_sandbox, explain_code_error

app = FastAPI()


class AgentRequest(BaseModel):
    action: Optional[str] = "solve"
    task: Optional[str] = ""
    language: Optional[str] = "Python"
    code: Optional[str] = ""
    reference_code: Optional[str] = ""
    error_details: Optional[str] = ""
    sample_cases: Optional[List[Dict[str, Any]]] = None


@app.get("/")
def serve_home():
    return FileResponse("public/index.html")


@app.get("/style.css")
def serve_css():
    return FileResponse("public/style.css", media_type="text/css")


@app.post("/api/research")
@app.post("/api/research.py")
@app.post("/research")
@app.post("/")
def handle_request(req: AgentRequest):
    try:
        if req.action == "run_code":
            result = run_code_sandbox(req.language, req.code, req.sample_cases)
            mistake_analysis = None

            if result.get("has_error") or not result.get("all_passed"):
                if result.get("has_error"):
                    failure_info = f"Compiler/Runtime Error:\n{result.get('raw_output', '')}"
                else:
                    failed_list = [
                        f"Case {c['id']}: Input ({c['input']}) -> Expected {c['expected']}, but got Actual {c['actual']}"
                        for c in result.get("cases", []) if not c.get("passed")
                    ]
                    failure_info = "Failed Test Cases:\n" + "\n".join(failed_list)

                mistake_analysis = explain_code_error(
                    req.task,
                    req.language,
                    req.code,
                    failure_info,
                    req.reference_code
                )

            return {
                "status": "success",
                "test_results": result,
                "mistake_analysis": mistake_analysis
            }

        if req.action == "explain_error":
            explanation = explain_code_error(
                req.task, req.language, req.code, req.error_details, req.reference_code
            )
            if "error" in explanation:
                return {"status": "error", "message": explanation["error"]}
            return {"status": "success", "explanation": explanation}

        result = run_agent(req.task, req.language)
        if "error" in result:
            return {"status": "error", "message": result["error"]}
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e) or "Unexpected backend error"}