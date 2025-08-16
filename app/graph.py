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
    "You are a local automation agent.\n"
    "Return **one and only one** JSON object. No prose, no extra objects, no code fences.\n"
    "JSON schema: {\"thought\": str, \"action\": str, \"args\": object}.\n"
    "Available actions: open_url(url), click(text_or_selector), type(text), wait(seconds), read_page().\n"
    "Do exactly one action per reply."
)


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Return the FIRST valid JSON object found in the text.
    Handles code fences and multiple concatenated JSON objects.
    """
    if not text:
        raise ValueError("Empty LLM response")

    # Prefer code-fenced JSON blocks
    import re, json
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    candidates = fenced if fenced else re.findall(r"\{.*?\}", text, flags=re.S)

    for cand in candidates:
        try:
            return json.loads(cand)
        except Exception:
            continue

    # Last chance: try direct loads (in case it's already clean)
    return json.loads(text)


def call_ollama(messages, model: str = MODEL) -> str:
    # Force non-streaming so we always get a single JSON payload back
    payload = {
    "model": model,
    "messages": messages,
    "stream": False,
    "options": {"temperature": 0.0}
    }

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
    print("\n[LLM RAW OUTPUT]\n", raw, "\n")

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
