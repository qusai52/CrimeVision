import os
import requests

def capabilities():
    return {
        "rtdetr": {"configured": False, "note": "Configure RT-DETR weights and inference runtime."},
        "clip": {"configured": False, "note": "Configure CLIP model and inference runtime."},
        "blip": {"configured": False, "note": "Configure BLIP/BLIP-2 model and inference runtime."},
        "whisper": {"configured": False, "note": "Install/configure Whisper model and audio dependencies."},
        "groq": {"configured": bool(os.getenv("GROQ_API_KEY")), "note": "Ready" if os.getenv("GROQ_API_KEY") else "Set GROQ_API_KEY in backend/.env."}
    }

def groq_answer(question, context):
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return "Groq is not configured. Add GROQ_API_KEY to backend/.env to enable evidence-grounded AI chat. No AI answer was generated."
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    prompt = (
        "You are CrimeVision AI, an evidence-analysis assistant. Use only supplied case context. "
        "Clearly distinguish recorded facts from hypotheses, cite evidence IDs when available, "
        "state when information is missing, and never present conclusions as legally definitive.\n\n"
        f"CASE CONTEXT:\n{context[:18000]}\n\nQUESTION:\n{question}"
    )
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
