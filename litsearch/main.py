from fastapi import APIRouter
from fastapi import Query
from clients.pubmed_client import search_pubmed, fetch_pubmed_details
from clients.embase_client import search_embase
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/search")
def multi_database_search(query: str, databases: list[str] = Query(default=["pubmed"]), retmax: int = 10):
    logger.info(f"Received search query: '{query}' | Databases: {databases}")
    all_results = []

    if "pubmed" in databases:
        pmids = search_pubmed(query, retmax)
        results = fetch_pubmed_details(pmids)
        logger.info(f"PubMed returned {len(results)} results.")
        all_results.extend(results)

    if "embase" in databases:
        embase_results = search_embase(query, count=retmax)
        logger.info(f"Embase returned {len(embase_results)} results.")
        all_results.extend(embase_results)

    logger.info(f"Total combined results: {len(all_results)}")
    return {
        "count": len(all_results),
        "results": all_results
    }