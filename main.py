from fastapi import FastAPI, Query
import requests
from typing import List, Optional

app = FastAPI()

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

@app.get("/search")
def search_pubmed(query: str = Query(..., description="Your PubMed search string"), 
                  retmax: int = 10):
    """Search PubMed and return a list of PMIDs"""
    response = requests.get(f"{NCBI_BASE}/esearch.fcgi", params={
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax
    })
    response.raise_for_status()
    return response.json()

@app.get("/summary")
def get_summary(pmids: List[str] = Query(..., description="List of PMIDs")):
    """Get summary details for a list of PMIDs"""
    response = requests.get(f"{NCBI_BASE}/esummary.fcgi", params={
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json"
    })
    response.raise_for_status()
    return response.json()

@app.get("/fetch")
def fetch_abstract(pmids: List[str] = Query(..., description="List of PMIDs")):
    """Fetch full article info (e.g. abstract) for PMIDs"""
    response = requests.get(f"{NCBI_BASE}/efetch.fcgi", params={
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml"
    })
    response.raise_for_status()
    return response.text
