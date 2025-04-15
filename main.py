from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pubmed.main import router as pubmed_router
from zotero.main import router as zotero_router

app = FastAPI(title="Literature Tools API", version="1.0.0")

# Include routes
app.include_router(pubmed_router, prefix="/pubmed", tags=["PubMed"])
app.include_router(zotero_router, prefix="/zotero", tags=["Zotero"])

# Custom OpenAPI schema with 'servers' field
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description="API to access PubMed and Zotero tools",
        routes=app.routes,
    )
    openapi_schema["servers"] = [
        {"url": "https://literature-tools-render.onrender.com"}
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
