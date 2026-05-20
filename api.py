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


# Fix the root route
@app.api_route("/", methods=["GET", "HEAD"])
async def serve_frontend(request: Request):
    if request.method == "HEAD":
        return HTMLResponse(content="", status_code=200)
    return FileResponse("index.html")

@app.get("/")
async def serve_frontend():
    return FileResponse("dct_frontend.html")

@app.post("/api/query")
async def query(req: QueryRequest):
    result = run(req.query)
    return result

@app.get("/api/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)