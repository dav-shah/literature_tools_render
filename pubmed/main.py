from fastapi import APIRouter, Query
import requests

router = APIRouter()

@router.get("/search", tags=["PubMed"], summary="Search PubMed", operation_id="searchPubMed")
def search_pubmed(query: str = Query(..., description="Search query for PubMed"),
                  retmax: int = Query(5, description="Maximum number of results to return")):
    """
    Searches PubMed using NCBI E-utilities and returns PMIDs.
    """
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    return {"pmids": data["esearchresult"].get("idlist", [])}
