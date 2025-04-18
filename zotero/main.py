from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import requests
import xml.etree.ElementTree as ET
from io import BytesIO
import fitz  # PyMuPDF
import re
import sys
from typing import Optional

router = APIRouter()
ZOTERO_API_BASE = "https://api.zotero.org"

SECTION_PATTERN = re.compile(
    r"^(abstract|introduction|background|methods|materials and methods|results|findings|discussion|conclusion|references)\b",
    re.IGNORECASE
)

def log(msg):
    print(msg, file=sys.stderr)

@router.get("/collections")
def get_collections(user_id: str, api_key: str):
    headers = {"Zotero-API-Key": api_key}
    url = f"{ZOTERO_API_BASE}/users/{user_id}/collections"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return [
        {"name": c["data"]["name"], "key": c["data"]["key"]}
        for c in response.json()
    ]

@router.get("/items_by_collection")
def get_items_by_collection(
    user_id: str,
    api_key: str,
    collection_name: str,
    limit: int = 100,
    start: int = 0
):
    headers = {"Zotero-API-Key": api_key}
    collections_url = f"{ZOTERO_API_BASE}/users/{user_id}/collections"
    collections_resp = requests.get(collections_url, headers=headers)
    collections_resp.raise_for_status()
    collections = collections_resp.json()
    collection_key = next((c["data"]["key"] for c in collections if c["data"]["name"] == collection_name), None)
    if not collection_key:
        return {"error": f"Collection '{collection_name}' not found."}

    items_url = f"{ZOTERO_API_BASE}/users/{user_id}/collections/{collection_key}/items"
    params = {"limit": limit, "start": start}
    items_resp = requests.get(items_url, headers=headers, params=params)
    items_resp.raise_for_status()

    return {
        "collection_name": collection_name,
        "collection_key": collection_key,
        "items": [
            {
                "title": item["data"].get("title"),
                "key": item["data"].get("key"),
                "authors": ", ".join(a.get("lastName", "") for a in item["data"].get("creators", [])),
                "publication_year": item["data"].get("date", "")[:4],
                "link": item["data"].get("url", "")
            }
            for item in items_resp.json()
            if item["data"].get("itemType") not in ["attachment", "note", "link"]
        ]
    }

SECTION_PATTERN = re.compile(
    r"^(abstract|introduction|background|methods|materials and methods|results|findings|discussion|conclusion|references)\b",
    re.IGNORECASE
)

def get_zotero_collections(user_id: str, api_key: str):
    headers = {"Zotero-API-Key": api_key}
    url = f"{ZOTERO_API_BASE}/users/{user_id}/collections"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def get_zotero_items(user_id: str, api_key: str, collection_key: str):
    headers = {"Zotero-API-Key": api_key}
    all_items = []
    start = 0
    limit = 100

    while True:
        url = f"{ZOTERO_API_BASE}/users/{user_id}/collections/{collection_key}/items"
        params = {"limit": limit, "start": start}
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_items.extend(batch)
        start += limit

    return all_items

def get_children(user_id: str, api_key: str, item_key: str):
    headers = {"Zotero-API-Key": api_key}
    url = f"{ZOTERO_API_BASE}/users/{user_id}/items/{item_key}/children"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

@router.get("/zotero/extract_chunks_from_collection")
def extract_chunks_from_collection(
    user_id: str,
    api_key: str,
    collection_name: str,
    limit_items: int = 1,
    start_index: int = 0,
    page_start: int = 1,
    page_end: int = None
):
    headers = {"Zotero-API-Key": api_key, "Zotero-API-Version": "3"}

    log(f"Fetching collections for user {user_id}")
    collections = get_zotero_collections(user_id, api_key)
    log(f"Found collections: {[c['data']['name'] for c in collections]}")
    collection_key = next(
        (c["data"]["key"] for c in collections if c["data"]["name"] == collection_name), None
    )
    if not collection_key:
        log(f"Collection '{collection_name}' not found.")
        return {"error": f"Collection '{collection_name}' not found."}

    log(f"Fetching items from collection key: {collection_key}")
    all_items = get_zotero_items(user_id, api_key, collection_key)
    log(f"Total items fetched: {len(all_items)}")
    for item in all_items:
        log(f"Item key: {item['data'].get('key')}, title: {item['data'].get('title')}, type: {item['data'].get('itemType')}, has parent: {bool(item['data'].get('parentItem'))}")
    journal_articles = [
        item for item in all_items
        if item["data"].get("itemType") == "journalArticle"
    ]
    log(f"Total journalArticles (regardless of parent status): {len(journal_articles)}")

    selected_articles = journal_articles[start_index:start_index + limit_items]
    log(f"Selected {len(selected_articles)} journalArticle items for extraction")

    results = []
    skipped = []

    for parent in selected_articles:
        item_key = parent["data"]["key"]
        item_title = parent["data"].get("title")
        log(f"Processing item: {item_title} (key: {item_key})")

        try:
            children = get_children(user_id, api_key, item_key)
            pdf = next((
                c for c in children
                if c.get("data", {}).get("itemType") == "attachment" and
                   c.get("data", {}).get("contentType") == "application/pdf"
            ), None)

            if not pdf:
                log(f"No PDF attachment found for item {item_key}")
                skipped.append({"key": item_key, "title": item_title, "reason": "No PDF attachment"})
                continue

            pdf_key = pdf["data"]["key"]
            pdf_url = f"{ZOTERO_API_BASE}/users/{user_id}/items/{pdf_key}/file"
            log(f"Downloading PDF from {pdf_url}")
            resp = requests.get(pdf_url, headers=headers, stream=True)
            resp.raise_for_status()

            doc = fitz.open(stream=BytesIO(resp.content), filetype="pdf")
            page_count = len(doc)
            log(f"PDF has {page_count} pages")

            page_start_clamped = max(1, page_start)
            page_end_clamped = min(page_end or page_count, page_count)

            full_text = "\n".join(
                doc[i - 1].get_text() for i in range(page_start_clamped, page_end_clamped + 1)
            )
            log(f"Extracted {len(full_text)} characters of text")

            results.append({
                "title": item_title,
                "key": item_key,
                "page_count": page_count,
                "page_range": [page_start_clamped, page_end_clamped],
                "text": full_text
            })

        except Exception as e:
            log(f"Error processing item {item_key}: {e}")
            skipped.append({"key": item_key, "title": item_title, "reason": str(e)})

    return {
        "collection_name": collection_name,
        "results": results,
        "skipped": skipped
    }

@router.post("/create_collection")
def create_collection(user_id: str, api_key: str, name: str):
    url = f"{ZOTERO_API_BASE}/users/{user_id}/collections"
    headers = {
        "Zotero-API-Key": api_key,
        "Zotero-API-Version": "3",
        "Content-Type": "application/json"
    }
    payload = [
        {
            "data": {
                "name": name
            }
        }
    ]
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    result = response.json()
    new_key = list(result.get("successful", {}).values())[0].get("key", "UNKNOWN")

    return {
        "message": "Collection created successfully.",
        "collection_name": name,
        "collection_key": new_key
    }

@router.post("/add")
def add_pubmed_article(
    user_id: str,
    api_key: str,
    pmid: str,
    collection_name: str = "LitReviewGPT"
):
    # Step 1: Fetch article metadata from PubMed
    efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml"
    }
    efetch_resp = requests.get(efetch_url, params=params)
    efetch_resp.raise_for_status()
    root = ET.fromstring(efetch_resp.content)
    article = root.find(".//PubmedArticle")
    
    # Basic fields
    title = article.findtext(".//ArticleTitle")
    abstract = " ".join(
        elem.text.strip() for elem in article.findall(".//AbstractText") if elem.text
    )
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
    link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

    # Authors
    creators = []
    for author in article.findall(".//Author"):
        last = author.findtext("LastName")
        first = author.findtext("ForeName")
        if last:
            creators.append({
                "creatorType": "author",
                "lastName": last,
                "firstName": first or ""
            })

    # Step 2: Ensure collection exists
    headers = {
        "Zotero-API-Key": api_key,
        "Zotero-API-Version": "3"
    }
    collections_url = f"{ZOTERO_API_BASE}/users/{user_id}/collections"
    collections_resp = requests.get(collections_url, headers=headers)
    collections_resp.raise_for_status()
    collections = collections_resp.json()
    collection_key = next((c["data"]["key"] for c in collections if c["data"]["name"] == collection_name), None)

    if not collection_key:
        create_resp = requests.post(
            collections_url,
            headers={**headers, "Content-Type": "application/json"},
            json=[{"data": {"name": collection_name}}]
        )
        create_resp.raise_for_status()
        collection_key = list(create_resp.json()["successful"].values())[0]["key"]

    # Step 3: Construct Zotero item
    item_payload = [
        {
            "data": {
                "itemType": "journalArticle",
                "title": title,
                "abstractNote": abstract,
                "creators": creators,
                "publicationTitle": journal,
                "volume": volume,
                "issue": issue,
                "pages": pages,
                "date": pubdate,
                "DOI": doi,
                "url": link,
                "collections": [collection_key]
            }
        }
    ]
    item_url = f"{ZOTERO_API_BASE}/users/{user_id}/items"
    item_resp = requests.post(
        item_url,
        headers={**headers, "Content-Type": "application/json"},
        json=item_payload
    )
    item_resp.raise_for_status()

    return {
        "message": "PubMed article added to Zotero successfully.",
        "pmid": pmid,
        "title": title,
        "doi": doi,
        "collection": collection_name
    }
