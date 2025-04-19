from fastapi import APIRouter
from clients.pubmed_client import search_pubmed, fetch_pubmed_details
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/search")
def multi_database_search(query: str, databases: list[str] = ["pubmed"], retmax: int = 10):
    logger.info(f"Received search query: '{query}' | Databases: {databases}")
    all_results = []

    if "pubmed" in databases:
        pmids = search_pubmed(query, retmax)
        results = fetch_pubmed_details(pmids)
        logger.info(f"PubMed returned {len(results)} results.")
        all_results.extend(results)

    # Add more databases here later

    logger.info(f"Total combined results: {len(all_results)}")
    return {
        "count": len(all_results),
        "results": all_results
    }