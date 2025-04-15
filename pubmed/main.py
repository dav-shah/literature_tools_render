from fastapi import APIRouter, Query
import requests

router = APIRouter()

PUBMED_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

@router.get("/search")
def search_pubmed(query: str, retmax: int = 10):
    url = f"{PUBMED_EUTILS_BASE}/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax
    }
    response = requests.get(url, params=params)
    response.raise_for_status()

    id_list = response.json()["esearchresult"]["idlist"]
    results = [
        {
            "pmid": pmid,
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        } for pmid in id_list
    ]
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
    return summaries

@router.get("/fetch")
def fetch_abstract(pmids: list[str] = Query(...)):
    url = f"{PUBMED_EUTILS_BASE}/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "text",
        "rettype": "abstract"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()

    # Split abstracts by PMID (assuming 1:1 return order)
    abstracts_text = response.text.strip().split("\n\n")
    results = []
    for pmid, abstract in zip(pmids, abstracts_text):
        results.append({
            "pmid": pmid,
            "abstract": abstract.strip(),
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        })
    return results
