# Literature Tools API

This repo includes two FastAPI services:

- `/pubmed` routes to interact with the NCBI PubMed API
- `/zotero` routes to manage Zotero collections and items

## Deployment
Use [Render.com](https://render.com) or any other cloud service. Start with:

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 10000
```
