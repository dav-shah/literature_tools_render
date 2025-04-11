from fastapi import FastAPI
from pubmed.main import router as pubmed_router
from zotero.main import router as zotero_router

app = FastAPI(
    title="Literature Tools API",
    version="1.0.0",
    description="Search PubMed and manage Zotero from a unified assistant.",
    servers=[{"url": "https://literature-tools-render.onrender.com"}]
)

app.include_router(pubmed_router, prefix="/pubmed")
app.include_router(zotero_router, prefix="/zotero")
