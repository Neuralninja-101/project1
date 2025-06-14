from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict
import httpx
from bs4 import BeautifulSoup
from fastapi.middleware.cors import CORSMiddleware
import json
import re

AIPIPE_URL = "https://aipipe.org/openrouter/v1/chat/completions"
AIPIPE_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIzZjEwMDExNzdAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.6FuJgEJ9v8AukUuzZsBHMzUaYvtPfTfrN8qrMhiSgaI"

TDS_CONTENT_URL = "https://tds.s-anand.net/#/2025-01/"
DISCOURSE_URL = "https://discourse.onlinedegree.iitm.ac.in/c/courses/tds-kb/34"

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class QARequest(BaseModel):
    question: str
    image_url: Optional[str] = None

class QAResponse(BaseModel):
    answer: str
    links: List[Dict[str, str]]

async def fetch_page_text(url: str) -> str:
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, timeout=20.0)
            soup = BeautifulSoup(resp.text, "html.parser")
            return soup.get_text(separator="\n")[:4000]
    except Exception as e:
        return f"Failed to load {url}: {e}"

async def call_aipipe(messages):
    headers = {
        "Authorization": f"Bearer {AIPIPE_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-4o",
        "messages": messages
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(AIPIPE_URL, headers=headers, json=data)
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content']

@app.post("/api/", response_model=QAResponse)
async def answer_question(payload: QARequest):
    tds_text = await fetch_page_text(TDS_CONTENT_URL)
    discourse_text = await fetch_page_text(DISCOURSE_URL)

    user_content = [{"type": "text", "text": f"Question: {payload.question}\n\nTDS:\n{tds_text}\n\nForum:\n{discourse_text}"}]
    if payload.image_url:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": payload.image_url},
            "detail": "low"
        })

    # Main Answer
    messages_answer = [
        {"role": "system", "content": "You are a helpful TA for the TDS course at IITM. Use the context and image to answer the question concisely."},
        {"role": "user", "content": user_content}
    ]

    # Link Extractor Prompt
    messages_links = [
        {"role": "system", "content": "Extract the most relevant links from the context for the question below. Respond ONLY in JSON format as a list like: [{\"url\": \"<url>\", \"text\": \"<reason>\"}]. Do NOT add commentary."},
        {"role": "user", "content": f"Question: {payload.question}\n\nTDS:\n{tds_text}\n\nForum:\n{discourse_text}"}
    ]

    # Answer generation
    try:
        answer_text = await call_aipipe(messages_answer)
    except Exception as e:
        answer_text = f"Failed to generate answer: {e}"

    # Link extraction
    try:
        links_raw = await call_aipipe(messages_links)
        try:
            links_json = json.loads(links_raw)
        except:
            # Fallback: manually extract URLs using regex
            url_matches = re.findall(r'https?://[^\s")]+', links_raw)
            links_json = [{"url": url, "text": "Related to the question."} for url in url_matches[:3]]
    except Exception as e:
        links_json = []

    return {
        "answer": answer_text.strip(),
        "links": links_json
    }
