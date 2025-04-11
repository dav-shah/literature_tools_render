from fastapi import FastAPI
from pubmed.main import router as pubmed_router
from zotero.main import router as zotero_router

app = FastAPI()
app.include_router(pubmed_router, prefix="/pubmed")
app.include_router(zotero_router, prefix="/zotero")
