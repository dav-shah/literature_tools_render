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
    url = f"https://api.zotero.org/users/{user_id}/collections"
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
def add_item(
    user_id: str,
    api_key: str,
    title: str,
    authors: str,
    publication_year: str,
    collection_name: str = "LitReviewGPT"
):
    # Step 1: Get collections to find or create the target collection
    collections_url = f"https://api.zotero.org/users/{user_id}/collections"
    headers = {
        "Zotero-API-Key": api_key,
        "Zotero-API-Version": "3"
    }
    collections_resp = requests.get(collections_url, headers=headers)
    collections_resp.raise_for_status()

    collections = collections_resp.json()
    collection_key = None
    for c in collections:
        if c["data"]["name"] == collection_name:
            collection_key = c["data"]["key"]
            break

    # Step 2: If not found, create the collection
    if not collection_key:
        create_resp = requests.post(
            collections_url,
            headers={**headers, "Content-Type": "application/json"},
            json=[
                {"data": {"name": collection_name}}
            ]
        )
        create_resp.raise_for_status()
        collection_key = list(create_resp.json()["successful"].values())[0]["key"]

    # Step 3: Build the item payload
    items_url = f"https://api.zotero.org/users/{user_id}/items"
    item_payload = [
        {
            "data": {
                "itemType": "journalArticle",
                "title": title,
                "creators": [
                    {"creatorType": "author", "lastName": name.strip(), "firstName": ""}
                    for name in authors.split(",")
                ],
                "date": publication_year,
                "collections": [collection_key]
            }
        }
    ]
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
