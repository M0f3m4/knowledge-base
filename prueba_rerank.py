import os
import requests
from dotenv import load_dotenv

load_dotenv()

VOYAGE_KEY = os.getenv("VOYAGE_API_KEY")
print(f"Key: {VOYAGE_KEY[:10]}...")

r = requests.post(
    "https://ai.mongodb.com/v1/rerank",
    headers={"Authorization": f"Bearer {VOYAGE_KEY}", "Content-Type": "application/json"},
    json={
        "query": "RFC del acreditado formato personas morales",
        "documents": ["El RFC debe tener 13 caracteres", "El municipio se extrae del código de localidad"],
        "model": "rerank-2.5"
    }
)
print(f"Status: {r.status_code}")
print(r.json())