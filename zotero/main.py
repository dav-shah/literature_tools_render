from fastapi import APIRouter, Query, Header
import requests

router = APIRouter()
ZOTERO_API = "https://api.zotero.org"

@router.get("/collections")
def get_collections(user_id: str = Query(...), api_key: str = Header(...)):
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
