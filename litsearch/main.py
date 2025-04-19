from fastapi import APIRouter
from fastapi import Query
from clients.pubmed_client import search_pubmed, fetch_pubmed_details
from clients.embase_client import search_scopus, search_sciencedirect
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
        pubmed_results = fetch_pubmed_details(pmids)
        logger.info(f"PubMed returned {len(pubmed_results)} results.")
        all_results.extend(pubmed_results)

    if "scopus" in databases:
        scopus_results = search_scopus(query, count=retmax)
        logger.info(f"Scopus returned {len(scopus_results)} results.")
        all_results.extend(scopus_results)

    if "sciencedirect" in databases:
        sd_results = search_sciencedirect(query, count=retmax)
        logger.info(f"ScienceDirect returned {len(sd_results)} results.")
        all_results.extend(sd_results)

    logger.info(f"Total combined results: {len(all_results)}")
    return {
        "count": len(all_results),
        "results": all_results
    }