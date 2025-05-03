# proxy.py
import logging
import os
import time

import dotenv
import httpx
from aiolimiter import AsyncLimiter
from fastapi import FastAPI, Header, HTTPException, Request

dotenv.load_dotenv(override=True)

AZURE_ENDPOINT = os.environ[
    "AZURE_ENDPOINT"
]  # e.g. "https://<resource>.openai.azure.com"
AZURE_KEY = os.environ["AZURE_API_KEY"]
AZURE_DEPLOY = os.environ["AZURE_DEPLOYMENT"]  # your GPT‑4o deployment name
AZURE_API_VER = os.getenv("AZURE_API_VERSION")

# Example: 20 000 tokens/minute, 200 requests/minute
tpm_limiter = AsyncLimiter(max_rate=200_000, time_period=60)
rpm_limiter = AsyncLimiter(max_rate=400, time_period=60)

app = FastAPI()
log = logging.getLogger("proxy")
logging.basicConfig(level=logging.INFO)

# very simple auth layer
ALLOWED_KEYS = {"student_alice": "k1...", "student_bob": "k2..."}


def check_auth(proxy_key: str | None):
    if proxy_key is None or proxy_key not in ALLOWED_KEYS.values():
        print("Request proxy_api_key not existed:", proxy_key)
        raise HTTPException(401, "Invalid proxy API key")


@app.post("/v1/chat/completions")
async def chat_completions(
    req: Request, proxy_api_key: str | None = Header(None, alias="X-Proxy-Key")
):
    check_auth(proxy_api_key)
    payload = await req.json()

    # Optional guardrails
    if payload.get("max_tokens", 0) > 16000:
        raise HTTPException(400, "max_tokens capped at 1000")
    if payload.get("stream"):
        raise HTTPException(400, "Streaming disabled via proxy")

    prompt_tokens_est = len(payload["messages"]) * 200  # crude, adjust if you like

    async with tpm_limiter, rpm_limiter:
        async with httpx.AsyncClient(timeout=60) as client:
            url = (
                f"{AZURE_ENDPOINT}/openai/deployments/{AZURE_DEPLOY}"
                f"/chat/completions?api-version={AZURE_API_VER}"
            )
            headers = {"api-key": AZURE_KEY}
            t0 = time.time()
            r = await client.post(url, headers=headers, json=payload)
            t1 = time.time()

    # Log usage – prompt & completion tokens come back in Azure’s headers
    r_json = r.json()
    prompt_tokens = -1
    completion_tokens = -1
    if "usage" in r_json:
        prompt_tokens = r_json["usage"].get("prompt_tokens", 0)
        completion_tokens = r_json["usage"].get("completion_tokens", 0)
    log.info(
        "%s | %.1f ms | prompt=%s compl=%s",
        proxy_api_key,
        (t1 - t0) * 1e3,
        prompt_tokens,
        completion_tokens,
    )
    return r.json()


"""
curl -H "X-Proxy-Key: k1..." \
     -H "Content-Type: application/json" \
     http://localhost:8000/v1/chat/completions \
     -d '{
           "messages":[{"role":"user","content":"Hello"}],
           "model":"gpt-4o"
         }'
        
curl -H "X-Proxy-Key: k1..." \
     -H "Content-Type: application/json" \
     http://169.233.7.1:8000/v1/chat/completions \
     -d '{
           "messages":[{"role":"user","content":"Hello"}],
           "model":"gpt-4o"
         }'


client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    default_headers={"X-Proxy-Key": os.getenv("LOCAL_API_KEY")},
)
"""
