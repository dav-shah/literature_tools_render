from fastapi import APIRouter, Query
import requests
from typing import List

router = APIRouter()
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

@router.get("/search")
def search_pubmed(query: str = Query(...), retmax: int = 10):
    response = requests.get(f"{NCBI_BASE}/esearch.fcgi", params={
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax
    })
    response.raise_for_status()
    return response.json()

@router.get("/summary")
def get_summary(pmids: List[str] = Query(...)):
    response = requests.get(f"{NCBI_BASE}/esummary.fcgi", params={
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json"
    })
    response.raise_for_status()
    return response.json()

@router.get("/fetch")
def fetch_abstract(pmids: List[str] = Query(...)):
    response = requests.get(f"{NCBI_BASE}/efetch.fcgi", params={
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml"
    })
    response.raise_for_status()
    return response.text
