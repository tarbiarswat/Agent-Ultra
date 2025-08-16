# app/graph.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import requests, json, re, os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL = os.getenv("AGENT_MODEL", "llama3.1:8b")

@dataclass
class Step:
    thought: str
    action: str
    args: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None

@dataclass
class AgentState:
    goal: str
    steps: List[Step] = field(default_factory=list)
    done: bool = False

SYSTEM = (
    "You are a local automation agent. "
    "IMPORTANT: Respond with **only** a single JSON object, no prose, no code fences. "
    "The JSON MUST have exactly these keys: thought (string), action (string), args (object). "
    "Available actions: open_url(url), click(text_or_selector), type(text), wait(seconds), read_page(). "
    "Keep args minimal and valid."
)

def _extract_json(text: str) -> Dict[str, Any]:
    if not text:
        raise ValueError("Empty LLM response")
    # If there are code fences, pick inside them
    if "```" in text:
        parts = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
        if parts:
            return json.loads(parts[0])
    # Otherwise find first {...} block
    m = re.search(r"\{.*\}", text, flags=re.S)
    if m:
        return json.loads(m.group(0))
    # Last chance: try direct loads
    return json.loads(text)

def call_ollama(messages, model: str = MODEL) -> str:
    # Force non-streaming so we always get a single JSON payload back
    payload = {"model": model, "messages": messages, "stream": False, "options": {"temperature": 0.2}}
    r = requests.post(OLLAMA_URL, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    # Some servers return {"message":{"content": "..."}}
    return data.get("message", {}).get("content", "")

def next_step(goal: str, history: List[Dict[str, str]]) -> Step:
    messages = [{"role": "system", "content": SYSTEM}]
    messages += history
    messages.append({"role": "user", "content": f"Goal: {goal}\nReturn only JSON."})

    raw = call_ollama(messages)
    try:
        obj = _extract_json(raw)
    except Exception:
        # Ask the model to repair by returning pure JSON for the same intent
        repair = call_ollama(
            [
                {"role": "system", "content": "Return a valid JSON object only. No prose. Keys: thought, action, args."},
                {"role": "user", "content": raw or "(previous response empty)"},
            ]
        )
        obj = _extract_json(repair)

    # Minimal validation / defaults
    thought = str(obj.get("thought", "")).strip()
    action = str(obj.get("action", "")).strip()
    args = obj.get("args", {}) or {}
    if not action:
        # safe fallback to avoid crashing
        action, args = "read_page", {}

    return Step(thought=thought, action=action, args=args)
