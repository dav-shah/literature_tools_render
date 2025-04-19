from dotenv import load_dotenv
import os
import requests

load_dotenv()

API_KEY = os.getenv("ELSEVIER_API_KEY")
assert API_KEY, "API key not found!"

url = "https://api.elsevier.com/content/search/scopus"
params = {
    "query": "TITLE-ABS-KEY(spinal metastasis AND radiomics)",
    "count": 5
}
headers = {
    "X-ELS-APIKey": API_KEY,
    "Accept": "application/json"
}

response = requests.get(url, headers=headers, params=params)
print(response.status_code)
print(response.json())