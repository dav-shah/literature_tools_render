from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pubmed.main import router as pubmed_router
from embase.main import router as embase_router
from zotero.main import router as zotero_router
from litsearch.main import router as litsearch_router
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Literature Tools API", version="1.0.0")

# Include routes
app.include_router(pubmed_router, prefix="/pubmed", tags=["PubMed"])
logger.info("Registered PubMed routes at /pubmed")
app.include_router(embase_router, prefix="/embase", tags=["Embase"])
logger.info("Registered Embase routes at /embase")
app.include_router(zotero_router, prefix="/zotero", tags=["Zotero"])
logger.info("Registered Zotero routes at /zotero")
app.include_router(litsearch_router, prefix="/litsearch", tags=["LitSearch"])  # NEW
logger.info("Registered LitSearch routes at /litsearch")

# Custom OpenAPI schema with 'servers' field and patched response for extract_chunks
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

    # Patch the extract_chunks_from_collection response schema
    path = "/zotero/extract_chunks_from_collection"
    method = "get"
    if path in openapi_schema["paths"]:
        openapi_schema["paths"][path][method]["responses"]["200"] = {
            "description": "Returns full-text sections extracted from each PDF",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "collection_name": {"type": "string"},
                            "results": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "key": {"type": "string"},
                                        "sections": {
                                            "type": "object",
                                            "additionalProperties": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            },
                            "skipped": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "key": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
logger.info("Custom OpenAPI schema set.")
