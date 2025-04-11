from fastapi import APIRouter, Query, Header, HTTPException
import requests

router = APIRouter()
ZOTERO_API = "https://api.zotero.org"

@router.get("/collections")
def get_collections(user_id: str = Query(...), api_key: str = Query(...)):
    url = f"{ZOTERO_API}/users/{user_id}/collections"
    headers = {"Zotero-API-Key": api_key}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

@router.get("/items")
def get_items(user_id: str = Query(...), api_key: str = Header(...)):
    url = f"{ZOTERO_API}/users/{user_id}/items"
    headers = {"Zotero-API-Key": api_key}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

@router.post("/add")
def add_item(user_id: str = Query(...), api_key: str = Header(...), title: str = Query(...), 
             authors: str = Query(...), publication_year: str = Query(...), 
             collection_name: str = Query("LitReviewGPT")):
    headers = {
        "Zotero-API-Key": api_key,
        "Content-Type": "application/json"
    }

    # Check for collection or create one
    collections_url = f"{ZOTERO_API}/users/{user_id}/collections"
    collections_resp = requests.get(collections_url, headers=headers)
    collections_resp.raise_for_status()
    collections = collections_resp.json()

    collection_key = None
    for c in collections:
        if c['data']['name'].lower() == collection_name.lower():
            collection_key = c['data']['key']
            break

    if not collection_key:
        create_resp = requests.post(collections_url, headers=headers, json=[{
            "name": collection_name
        }])
        create_resp.raise_for_status()
        collection_key = create_resp.json()['successful']['0']['key']

    # Add the item
    items_url = f"{ZOTERO_API}/users/{user_id}/items"
    payload = [{
        "itemType": "journalArticle",
        "title": title,
        "creators": [{"creatorType": "author", "firstName": name.split()[0], "lastName": name.split()[-1]} for name in authors.split(",")],
        "date": publication_year,
        "collections": [collection_key]
    }]

    response = requests.post(items_url, headers=headers, json=payload)
    if response.status_code not in [200, 201, 204]:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return {"status": "success", "collection_key": collection_key, "item_response": response.json()}
