import sys
sys.path.append("agents")
sys.path.append("data")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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