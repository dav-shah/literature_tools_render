from fastapi import APIRouter, Query
import requests
import xml.etree.ElementTree as ET

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
def fetch_pubmed_details(pmids: list[str] = Query(...)):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    results = []

    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")
        title = article.findtext(".//ArticleTitle")
        abstract_parts = [
            (elem.attrib.get("Label", "") + ": " if elem.attrib.get("Label") else "") +
            (elem.text.strip() if elem.text else "")
            for elem in article.findall(".//AbstractText")
        ]
        abstract = "\n".join(abstract_parts).strip()

        journal = article.findtext(".//Journal/Title")
        volume = article.findtext(".//JournalIssue/Volume")
        issue = article.findtext(".//JournalIssue/Issue")
        pages = article.findtext(".//Pagination/MedlinePgn")
        pubdate = article.findtext(".//PubDate/Year") or article.findtext(".//PubDate/MedlineDate")

        doi = None
        for eid in article.findall(".//ELocationID"):
            if eid.attrib.get("EIdType") == "doi":
                doi = eid.text
                break

        authors = []
        for author in article.findall(".//Author"):
            last = author.findtext("LastName")
            first = author.findtext("ForeName")
            if last:
                authors.append(f"{first} {last}".strip())

        results.append({
            "pmid": pmid,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "journal": journal,
            "volume": volume,
            "issue": issue,
            "pages": pages,
            "pubdate": pubdate,
            "doi": doi,
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        })

    return results
