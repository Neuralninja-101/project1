from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict
import base64
import httpx
import os
from dotenv import load_dotenv ## added

AIPIPE_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIzZjEwMDExNzdAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.6FuJgEJ9v8AukUuzZsBHMzUaYvtPfTfrN8qrMhiSgaI'
AIPIPE_URL = "https://aipipe.org/openrouter/v1/chat/completions"
IMAGE_FILE_PATH = "project-tds-virtual-ta-q1.webp" # File to temporarily save the image

app = FastAPI()

class QARequest(BaseModel):
    question: str
    image: Optional[str] = None

class QAResponse(BaseModel):
    answer: str
    links: List[Dict[str, str]]

@app.post("/api/", response_model=QAResponse)
def answer_question(payload: QARequest):
    if payload.image:
        try:
            with open(IMAGE_FILE_PATH, "wb") as f:
                f.write(base64.b64decode(payload.image))
        except Exception as e:
            return {"answer": f"Failed to decode image: {str(e)}", "links": []}

    # Replace this with your actual retrieval logic
    retrieved_context = "The relevant content from TDS course or Discourse goes here."

    # Build messages
    messages = [
        {"role": "system", "content": "You are a helpful TA for the TDS course at IITM."},
        {"role": "user", "content": f"{payload.question}\n\nContext:\n{retrieved_context}"}
    ]

    # Call AIPipe
    headers = {
        "Authorization": f"Bearer {AIPIPE_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo", 
        "messages": messages
    }

    response = httpx.post(AIPIPE_URL, headers=headers, json=data, timeout=60.0)
    response.raise_for_status()

    reply = response.json()['choices'][0]['message']['content']

    return {
        "answer": reply.strip(),
        "links": [
            {
                "url": "https://discourse.onlinedegree.iitm.ac.in/t/example-post",
                "text": "Relevant discussion link"
            }
        ]
    }