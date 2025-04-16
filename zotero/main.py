from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import requests
import xml.etree.ElementTree as ET
from io import BytesIO
import fitz  # PyMuPDF
import re
import sys

router = APIRouter()
ZOTERO_API_BASE = "https://api.zotero.org"

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

@router.get("/extract_chunks_from_collection")
def extract_chunks_from_collection(user_id: str, api_key: str, collection_name: str, limit_items: int = 1, start_index: int = 0):
    try:
        headers = {
            "Zotero-API-Key": api_key,
            "Zotero-API-Version": "3"
        }

        section_pattern = re.compile(r"^(abstract|introduction|background|methods|materials and methods|results|findings|discussion|conclusion|references)\b", re.IGNORECASE)

        collections_url = f"{ZOTERO_API_BASE}/users/{user_id}/collections"
        collections_resp = requests.get(collections_url, headers=headers)
        collections_resp.raise_for_status()
        collections = collections_resp.json()
        collection_key = next((c["data"]["key"] for c in collections if c["data"]["name"] == collection_name), None)
        if not collection_key:
            return {"error": f"Collection '{collection_name}' not found."}

        items_url = f"{ZOTERO_API_BASE}/users/{user_id}/collections/{collection_key}/items"
        items_resp = requests.get(items_url, headers=headers)
        items_resp.raise_for_status()
        items = items_resp.json()

        extracted_chunks = []
        skipped = []

        for item in items[start_index:start_index + limit_items]:
            item_data = item["data"]
            if item_data.get("itemType") in ["attachment", "note", "link"]:
                continue

            item_key = item_data["key"]
            log(f"Processing item: {item_data.get('title')} ({item_key})")

            try:
                children_url = f"{ZOTERO_API_BASE}/users/{user_id}/items/{item_key}/children"
                children_resp = requests.get(children_url, headers=headers)
                children_resp.raise_for_status()
                children = children_resp.json()

                pdf = next(
                    (c for c in children
                     if c.get("data", {}).get("itemType") == "attachment" and
                        c.get("data", {}).get("contentType") == "application/pdf"),
                    None
                )

                if pdf:
                    pdf_key = pdf["data"]["key"]
                    log(f"Found PDF attachment: {pdf_key} for item {item_key}")
                    pdf_url = f"{ZOTERO_API_BASE}/users/{user_id}/items/{pdf_key}/file"
                    pdf_resp = requests.get(pdf_url, headers=headers, stream=True)
                    if pdf_resp.status_code == 200:
                        doc = fitz.open(stream=pdf_resp.content, filetype="pdf")
                        full_text = "\n".join(page.get_text() for page in doc)
                        # TEMPORARY: return a raw text snippet for testing
                        extracted_chunks.append({
                            "title": item_data.get("title"),
                            "key": item_key,
                            "full_text_snippet": full_text[:2000]  # safely trimmed for plugin response limits
                        })
                        continue  # skip chunking logic for now

                        sections = {}
                        current_section = "Unknown"
                        buffer = []

                        for line in full_text.splitlines():
                            match = section_pattern.match(line.strip())
                            if match:
                                if buffer:
                                    sections.setdefault(current_section, []).append(" ".join(buffer).strip())
                                    buffer = []
                                current_section = match.group(1).title()
                            else:
                                buffer.append(line)

                        if buffer:
                            sections.setdefault(current_section, []).append(" ".join(buffer).strip())

                        log(f"Extracted sections: {list(sections.keys())} from {item_key}")
                        extracted_chunks.append({
                            "title": item_data.get("title"),
                            "key": item_key,
                            "sections": sections
                        })
                    else:
                        log(f"Failed to download PDF for {item_key}")
                        skipped.append({"key": item_key, "reason": "PDF download failed"})
                else:
                    log(f"No PDF attachment found for {item_key}")
                    skipped.append({"key": item_key, "reason": "No PDF attachment"})

            except Exception as e:
                log(f"Error processing item {item_key}: {str(e)}")
                skipped.append({"key": item_key, "reason": str(e)})

        return {
            "collection_name": collection_name,
            "results": extracted_chunks,
            "skipped": skipped
        }

    except Exception as e:
        log(f"FATAL error in extract_chunks_from_collection: {str(e)}")
        return {
            "error": "Extraction failed",
            "detail": str(e)
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

@router.get("/debug_pdf_text")
def debug_pdf_text(user_id: str, api_key: str, pdf_key: str):
    import fitz
    from io import BytesIO

    headers = {
        "Zotero-API-Key": api_key,
        "Zotero-API-Version": "3"
    }

    try:
        # Download the PDF
        pdf_url = f"https://api.zotero.org/users/{user_id}/items/{pdf_key}/file"
        resp = requests.get(pdf_url, headers=headers, stream=True)
        resp.raise_for_status()

        # Load PDF and extract text
        doc = fitz.open(stream=BytesIO(resp.content), filetype="pdf")
        output = []

        for i, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            output.append({
                "page": i,
                "text_snippet": text[:1000] if text else "[No text found]"
            })

        return {
            "page_count": len(doc),
            "pages": output
        }

    except Exception as e:
        return {"error": str(e)}
