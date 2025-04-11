from fastapi import APIRouter, Query, HTTPException
import requests
import urllib.parse
import logging

router = APIRouter()
ZOTERO_API = "https://api.zotero.org"

@router.get("/collections")
def get_collections(user_id: str = Query(...), api_key: str = Query(...)):
    encoded_key = urllib.parse.quote(api_key, safe='')
    url = f"{ZOTERO_API}/users/{user_id}/collections?key={encoded_key}"
    logging.warning(f"Calling Zotero Collections URL: {url}")
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

@router.get("/items")
def get_items(user_id: str = Query(...), api_key: str = Query(...)):
    encoded_key = urllib.parse.quote(api_key, safe='')
    url = f"{ZOTERO_API}/users/{user_id}/items?key={encoded_key}"
    logging.warning(f"Calling Zotero Items URL: {url}")
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

@router.post("/create_collection")
def create_collection(user_id: str = Query(...), api_key: str = Query(...), name: str = Query(...)):
    encoded_key = urllib.parse.quote(api_key, safe='')
    url = f"{ZOTERO_API}/users/{user_id}/collections?key={encoded_key}"
    headers = {"Content-Type": "application/json"}
    payload = [{"name": name}]
    logging.warning(f"Creating Zotero Collection: {name} at {url}")
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

@router.post("/add")
def add_item(user_id: str = Query(...), api_key: str = Query(...), title: str = Query(...),
             authors: str = Query(...), publication_year: str = Query(...),
             collection_name: str = Query("LitReviewGPT")):
    encoded_key = urllib.parse.quote(api_key, safe='')
    collections_url = f"{ZOTERO_API}/users/{user_id}/collections?key={encoded_key}"
    logging.warning(f"Checking collections at: {collections_url}")
    collections_resp = requests.get(collections_url)
    collections_resp.raise_for_status()
    collections = collections_resp.json()

    collection_key = None
    for c in collections:
        if c['data']['name'].lower() == collection_name.lower():
            collection_key = c['data']['key']
            break

    if not collection_key:
        logging.warning(f"Creating new collection: {collection_name}")
        create_resp = requests.post(collections_url, headers={"Content-Type": "application/json"}, json=[{"name": collection_name}])
        create_resp.raise_for_status()
        collection_key = create_resp.json()['successful']['0']['key']

    items_url = f"{ZOTERO_API}/users/{user_id}/items?key={encoded_key}"
    payload = [{
        "itemType": "journalArticle",
        "title": title,
        "creators": [{"creatorType": "author", "firstName": name.split()[0], "lastName": name.split()[-1]} for name in authors.split(",")],
        "date": publication_year,
        "collections": [collection_key]
    }]
    headers = {"Content-Type": "application/json"}
    logging.warning(f"Adding item '{title}' to collection key {collection_key} at URL: {items_url}")
    response = requests.post(items_url, headers=headers, json=payload)
    if response.status_code not in [200, 201, 204]:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return {"status": "success", "collection_key": collection_key, "item_response": response.json()}
