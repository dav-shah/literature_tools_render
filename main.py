from fastapi import FastAPI
from pubmed.main import router as pubmed_router

app = FastAPI(
    title="Minimal PubMed API",
    version="1.0.0",
    description="Search PubMed using a simplified API for GPT integration.",
    servers=[{"url": "https://literature-tools-render.onrender.com"}]
)

app.include_router(pubmed_router, prefix="/pubmed")

@app.get("/")
def read_root():
    return {"status": "OK", "message": "Minimal PubMed API is running"}
