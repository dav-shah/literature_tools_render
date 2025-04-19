import requests
import xml.etree.ElementTree as ET
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PUBMED_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

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
    logger.info(f"PubMed search: query='{query}', retmax={retmax}, results={len(id_list)}")
    return id_list

def fetch_pubmed_details(pmids: list[str]):
    url = f"{PUBMED_EUTILS_BASE}/efetch.fcgi"
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
        abstract = "\n".join([
            (elem.attrib.get("Label", "") + ": " if elem.attrib.get("Label") else "") + (elem.text or "")
            for elem in article.findall(".//AbstractText")
        ]).strip()

        authors = [
            f"{a.findtext('ForeName')} {a.findtext('LastName')}".strip()
            for a in article.findall(".//Author") if a.findtext("LastName")
        ]

        results.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        })

    logger.info(f"Fetched details for PMIDs: {pmids} | Parsed {len(results)} articles")
    return results