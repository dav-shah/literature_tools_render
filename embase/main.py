from fastapi import APIRouter, Query
from clients.embase_client import search_embase, fetch_full_text_by_doi

router = APIRouter()

@router.get("/embase/search")
def embase_search(
    query: str,
    count: int = 10,
    start: int = 0  # pagination offset
):
    results = search_embase(query, count=count, start=start)
    return {"results": results}

@router.get("/fulltext_by_doi")
def get_full_text_by_doi(
    doi: str,
    para_start: int = 1,
    para_end: int = None
):
    return fetch_full_text_by_doi(doi, para_start=para_start, para_end=para_end)