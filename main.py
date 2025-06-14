from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict
import httpx
from bs4 import BeautifulSoup

# AIPipe Setup
AIPIPE_URL = "https://aipipe.org/openrouter/v1/chat/completions"
AIPIPE_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIzZjEwMDExNzdAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.6FuJgEJ9v8AukUuzZsBHMzUaYvtPfTfrN8qrMhiSgaI"

# Scraping sources
TDS_CONTENT_URL = "https://tds.s-anand.net/#/2025-01/"
DISCOURSE_URL = "https://discourse.onlinedegree.iitm.ac.in/c/courses/tds-kb/34"

app = FastAPI()

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
            return soup.get_text(separator="\n")[:4000]  # Truncate for token limit
    except Exception as e:
        return f"Failed to load {url}: {e}"

@app.post("/api/", response_model=QAResponse)
async def answer_question(payload: QARequest):
    # Fetch and build relevant context
    tds_text = await fetch_page_text(TDS_CONTENT_URL)
    discourse_text = await fetch_page_text(DISCOURSE_URL)
    context_text = f"TDS Page:\n{tds_text}\n\nDiscussion Forum:\n{discourse_text}"

    # Build AIPipe-compatible message
    user_content = [{"type": "text", "text": f"{payload.question}\n\nContext:\n{context_text}"}]
    if payload.image_url:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": payload.image_url},
            "detail": "low"
        })

    messages = [
        {"role": "system", "content": "You are a helpful TA for the TDS course at IITM. Use provided context and images."},
        {"role": "user", "content": user_content}
    ]

    headers = {
        "Authorization": f"Bearer {AIPIPE_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-4o",
        "messages": messages
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(AIPIPE_URL, headers=headers, json=data)
            resp.raise_for_status()
            result = resp.json()
            answer = result['choices'][0]['message']['content']
            return {
                "answer": answer.strip(),
                "links": [
                    {"url": TDS_CONTENT_URL, "text": "TDS Content"},
                    {"url": DISCOURSE_URL, "text": "Discourse Forum"}
                ]
            }
    except Exception as e:
        return {"answer": f"Failed to generate answer: {str(e)}", "links": []}
