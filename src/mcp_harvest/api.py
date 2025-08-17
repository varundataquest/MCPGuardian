from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Response, Request
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from mcp_harvest.storage.io import read_servers_csv
from mcp_harvest.query import search
from mcp_harvest.features import kmeans_clusters, plot_clusters_to_bytes, top_terms_per_cluster
from harvest.discovery.run import discover as run_discover
from harvest.recommend.run import recommend as run_recommend
from mcp_harvest.ranking import rank_servers
import pandas as pd
import math


app = FastAPI(title="mcp-registry-harvester")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/query")
def query(q: str, runtime: Optional[str] = None, top: int = 10):
    df = read_servers_csv()
    if df.empty:
        return []
    recs = rank_servers(df, q, top=top, runtime=runtime)
    def _clean_rec(rec: dict) -> dict:
        cleaned = {}
        for k, v in rec.items():
            if v is None:
                cleaned[k] = None
            elif isinstance(v, float) and math.isnan(v):
                cleaned[k] = None
            elif pd.isna(v):
                cleaned[k] = None
            else:
                cleaned[k] = v
        return cleaned
    return [_clean_rec(r) for r in recs]


@app.get("/server/{server_id}")
def server_detail(server_id: str):
    df = read_servers_csv()
    row = df[df["server_id"] == server_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Server not found")
    rec = row.iloc[0].to_dict()
    for k, v in list(rec.items()):
        if v is None:
            rec[k] = None
        elif isinstance(v, float) and math.isnan(v):
            rec[k] = None
        elif pd.isna(v):
            rec[k] = None
    return rec


@app.get("/discover")
async def api_discover(q: str, k: int = 20):
    results = await run_discover(q, limit=max(100, k * 5))
    return {"query": q, "results": results[:k]}


class RecommendRequest(BaseModel):
    desc: str
    top: int = 10


@app.post("/recommend")
def api_recommend(req: RecommendRequest):
    return run_recommend(req.desc, top_k=req.top)


@app.get("/recommend/page")
def recommend_page(request: Request, desc: Optional[str] = None, top: int = 10):
    results = []
    if desc:
        results = run_recommend(desc, top_k=top).get("results", [])
    return templates.TemplateResponse("recommend.html", {"request": request, "desc": desc or "", "top": top, "results": results})


# HTML pages
@app.get("/")
def home(request: Request, q: Optional[str] = None, runtime: Optional[str] = None, top: int = 10):
    df = read_servers_csv()
    items = []
    if q:
        idx_scores = search(df, q, top=top, require_runtime=runtime)
        items = [df.iloc[i].to_dict() | {"_score": s} for i, s in idx_scores]
    return templates.TemplateResponse("index.html", {"request": request, "q": q or "", "runtime": runtime or "", "results": items})


@app.get("/servers/{server_id}")
def server_page(request: Request, server_id: str):
    df = read_servers_csv()
    row = df[df["server_id"] == server_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Server not found")
    return templates.TemplateResponse("server.html", {"request": request, "server": row.iloc[0].to_dict()})


@app.get("/clusters/page")
def clusters_page(request: Request, k: int = 12):
    df = read_servers_csv()
    result = kmeans_clusters(df, k=k)
    labels = result["labels"]
    terms = top_terms_per_cluster(df, labels)
    labels_py = [int(x) for x in labels]
    terms_list = [
        {"cluster": int(k), "terms": [str(t) for t in v], "size": labels_py.count(int(k))}
        for k, v in terms.items()
    ]
    return templates.TemplateResponse("clusters.html", {"request": request, "k": k, "clusters": terms_list})


@app.get("/clusters")
def clusters(k: int = 12):
    df = read_servers_csv()
    result = kmeans_clusters(df, k=k)
    labels = result["labels"]
    terms = top_terms_per_cluster(df, labels)
    labels_py = [int(x) for x in labels]
    terms_py = {int(k): [str(t) for t in v] for k, v in terms.items()}
    return {"labels": labels_py, "top_terms": terms_py}


@app.get("/clusters/plot")
def clusters_plot(k: int = 12):
    df = read_servers_csv()
    result = kmeans_clusters(df, k=k)
    png_bytes = plot_clusters_to_bytes(df, result["labels"])
    return Response(content=png_bytes, media_type="image/png")


@app.get("/discover/page")
async def discover_page(request: Request, q: Optional[str] = None, k: int = 20):
    results = []
    if q:
        results = (await run_discover(q, limit=max(100, k * 5)))[:k]
    return templates.TemplateResponse("discover.html", {"request": request, "q": q or "", "k": k, "results": results})


