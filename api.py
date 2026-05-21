from http.client import HTTPException
import sys
from urllib.request import Request
sys.path.append("agents")
sys.path.append("data")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pipeline import run
import os

if not os.path.exists("data/tickets.faiss"):
    print("Building FAISS index...")
    from data.build_index import build_index
    build_index()


app = FastAPI(title="Delivery Control Tower API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

from agents.writer_agent import (
    create_ticket, update_assignee, 
    set_due_date, add_comment, get_account_id
)

_pending_approvals = {}

@app.post("/api/approve")
async def approve_actions(req: dict):
    run_id = req.get("run_id")
    approved_indices = req.get("approved_indices", [])
    
    if run_id not in _pending_approvals:
        return {"error": "No pending actions found for this run_id"}
    
    pending = _pending_approvals[run_id]
    results = []
    
    for i in approved_indices:
        if i >= len(pending):
            continue
        action = pending[i]
        action_type = action["action_type"]
        
        if action_type == "create_ticket":
            account_id = get_account_id(action.get("assignee", "")) if action.get("assignee") else None
            result = create_ticket(
                summary=action["summary"],
                description=action["description"],
                priority=action.get("priority", "Medium"),
                assignee_account_id=account_id
            )
        elif action_type == "update_assignee":
            account_id = get_account_id(action["assignee"])
            result = update_assignee(action["ticket_id"], account_id)
        elif action_type == "set_due_date":
            result = set_due_date(action["ticket_id"], action["due_date"])
        elif action_type == "add_comment":
            result = add_comment(action["ticket_id"], action["comment"])
        else:
            result = {"success": False, "message": f"Unknown action type: {action_type}"}
        
        results.append({"action": action, "result": result})
    
    del _pending_approvals[run_id]
    return {"results": results}

@app.post("/api/query")
async def query(req: QueryRequest):
    result = run(req.query)
    
    # Store pending actions if write path
    if result.get("path") == "write" and result.get("pending_actions"):
        import uuid
        run_id = str(uuid.uuid4())
        _pending_approvals[run_id] = result["pending_actions"]
        result["run_id"] = run_id
    
    return result

# Fix the root route
@app.api_route("/", methods=["GET", "HEAD"])
async def serve_frontend(request: Request):
    if request.method == "HEAD":
        return HTMLResponse(content="", status_code=200)
    return FileResponse("index.html")

@app.get("/")
async def serve_frontend():
    return FileResponse("dct_frontend.html")

@app.post("/api/refresh")
async def refresh_jira():
    try:
        from data.tickets import get_all_tickets
        from agents.retrieval_agent import rebuild_index
        tickets = get_all_tickets()
        rebuild_index(tickets)
        return {"status": "ok", "ticket_count": len(tickets)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}  # don't use HTTPException

@app.get("/api/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)