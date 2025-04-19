from fastapi import APIRouter, Query
import requests
import xml.etree.ElementTree as ET
import logging
from clients.pubmed_client import search_pubmed, fetch_pubmed_details

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

PUBMED_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

@router.get("/search")
def search_pubmed_endpoint(query: str, retmax: int = 10):
    id_list = search_pubmed(query, retmax)
    results = [{"pmid": pmid, "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"} for pmid in id_list]
    logger.info(f"Search query: {query} | Returned {len(results)} PMIDs")
    return results

@router.get("/summary")
def get_summary(pmids: list[str] = Query(...)):
    url = f"{PUBMED_EUTILS_BASE}/esummary.fcgi"
    params = {
        "db": "pubmed",
        "retmode": "json",
        "id": ",".join(pmids)
    }
    response = requests.get(url, params=params)
    response.raise_for_status()

    summaries = []
    result = response.json()["result"]
    for pmid in pmids:
        if pmid in result:
            doc = result[pmid]
            summaries.append({
                "pmid": pmid,
                "title": doc.get("title"),
                "authors": ", ".join([a["name"] for a in doc.get("authors", [])]),
                "source": doc.get("source"),
                "pubdate": doc.get("pubdate"),
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            })
    logger.info(f"Summarizing PMIDs: {pmids} | Returned {len(summaries)} summaries")
    return summaries

@router.get("/fetch")
def fetch_pubmed_details_endpoint(pmids: list[str] = Query(...)):
    results = fetch_pubmed_details(pmids)
    logger.info(f"Fetched details for PMIDs: {pmids} | Returned {len(results)} articles")
    return results