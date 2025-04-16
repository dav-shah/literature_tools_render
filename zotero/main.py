from fastapi import APIRouter, Query
import requests
import xml.etree.ElementTree as ET

router = APIRouter()

ZOTERO_API_BASE = "https://api.zotero.org"

@router.get("/collections")
def get_collections(user_id: str, api_key: str):
    url = f"{ZOTERO_API_BASE}/users/{user_id}/collections"
    headers = {"Zotero-API-Key": api_key}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    collections = [
        {
            "name": c["data"]["name"],
            "key": c["data"]["key"]
        }
        for c in response.json()
    ]
    return collections

@router.get("/items")
def get_items(user_id: str, api_key: str):
    url = f"{ZOTERO_API_BASE}/users/{user_id}/items"
    headers = {"Zotero-API-Key": api_key}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    items = []
    for item in response.json():
        data = item["data"]
        items.append({
            "title": data.get("title"),
            "authors": ", ".join(a.get("lastName", "") for a in data.get("creators", [])),
            "publication_year": data.get("date", "")[:4],
            "link": data.get("url", "")
        })
    return items

@router.get("/items_by_collection")
def get_items_by_collection(
    user_id: str,
    api_key: str,
    collection_name: str,
    limit: int = 100,
    start: int = 0
):
    # Step 1: Get the collection key
    collections_url = f"{ZOTERO_API_BASE}/users/{user_id}/collections"
    headers = {"Zotero-API-Key": api_key}
    collections_resp = requests.get(collections_url, headers=headers)
    collections_resp.raise_for_status()

    collections = collections_resp.json()
    collection_key = next((c["data"]["key"] for c in collections if c["data"]["name"] == collection_name), None)
    if not collection_key:
        return {"error": f"Collection '{collection_name}' not found."}

    # Step 2: Fetch items with pagination
    items_url = f"{ZOTERO_API_BASE}/users/{user_id}/collections/{collection_key}/items"
    params = {"limit": limit, "start": start}
    items_resp = requests.get(items_url, headers=headers, params=params)
    items_resp.raise_for_status()

    items_data = []
    for item in items_resp.json():
        data = item["data"]
        items_data.append({
            "title": data.get("title"),
            "authors": ", ".join(a.get("lastName", "") for a in data.get("creators", [])),
            "publication_year": data.get("date", "")[:4],
            "link": data.get("url", "")
        })

    return {
        "collection_name": collection_name,
        "collection_key": collection_key,
        "items_returned": len(items_data),
        "items": items_data
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

from fastapi.responses import StreamingResponse
from io import BytesIO

@router.get("/pdf_download")
def download_pdf_from_zotero(user_id: str, api_key: str, item_key: str):
    headers = {
        "Zotero-API-Key": api_key,
        "Zotero-API-Version": "3"
    }

    # Step 1: Find attached PDF
    children_url = f"{ZOTERO_API_BASE}/users/{user_id}/items/{item_key}/children"
    children_resp = requests.get(children_url, headers=headers)
    children_resp.raise_for_status()

    attachment = next(
        (c for c in children_resp.json()
         if c.get("data", {}).get("itemType") == "attachment" and
            c.get("data", {}).get("contentType") == "application/pdf"),
        None
    )

    if not attachment:
        return {"error": "No PDF attachment found."}

    pdf_key = attachment["data"]["key"]

    # Step 2: Download PDF
    pdf_url = f"https://api.zotero.org/users/{user_id}/items/{pdf_key}/file"
    pdf_resp = requests.get(pdf_url, headers=headers, stream=True)
    if pdf_resp.status_code != 200:
        return {"error": "Failed to fetch PDF. Is Zotero storage enabled and are you logged in?"}

    return StreamingResponse(BytesIO(pdf_resp.content), media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename={pdf_key}.pdf"
    })

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
