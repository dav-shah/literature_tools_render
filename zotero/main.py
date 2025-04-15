from fastapi import APIRouter, Query
import requests

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

@router.post("/create_collection")
def create_collection(user_id: str, api_key: str, name: str):
    url = f"{ZOTERO_API_BASE}/users/{user_id}/collections"
    headers = {
        "Zotero-API-Key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "name": name
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    return {
        "message": "Collection created successfully.",
        "collection_name": name,
        "collection_key": response.json()["successful"]["0"]["key"]
    }

@router.post("/add")
def add_item(
    user_id: str,
    api_key: str,
    title: str,
    authors: str,
    publication_year: str,
    collection_name: str = "LitReviewGPT"
):
    # Find or create the collection
    collections_url = f"{ZOTERO_API_BASE}/users/{user_id}/collections"
    headers = {"Zotero-API-Key": api_key}
    collections_resp = requests.get(collections_url, headers=headers)
    collections_resp.raise_for_status()

    collections = collections_resp.json()
    collection_key = None
    for c in collections:
        if c["data"]["name"] == collection_name:
            collection_key = c["data"]["key"]
            break

    if not collection_key:
        create_resp = requests.post(
            collections_url,
            headers={**headers, "Content-Type": "application/json"},
            json={"name": collection_name}
        )
        create_resp.raise_for_status()
        collection_key = create_resp.json()["successful"]["0"]["key"]

    # Add the item
    items_url = f"{ZOTERO_API_BASE}/users/{user_id}/items"
    item_payload = [{
        "itemType": "journalArticle",
        "title": title,
        "creators": [{"creatorType": "author", "lastName": name.strip(), "firstName": ""} for name in authors.split(",")],
        "date": publication_year,
        "collections": [collection_key]
    }]
    item_resp = requests.post(
        items_url,
        headers={**headers, "Content-Type": "application/json"},
        json=item_payload
    )
    item_resp.raise_for_status()

    return {
        "message": "Item added successfully.",
        "title": title,
        "authors": authors,
        "publication_year": publication_year,
        "collection": collection_name
    }
