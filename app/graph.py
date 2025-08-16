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
    "Respond with ONE and ONLY ONE JSON object. No prose, no extra JSON blocks, no code fences.\n"
    'Schema: {"thought": string, "action": string, "args": object}. '
    "Available actions: open_url(url), click(text_or_selector), type(text), wait(seconds), read_page(). "
    "Perform exactly ONE action per reply."
)



def _extract_json(text: str) -> Dict[str, Any]:
    """
    Return the FIRST valid JSON object found in 'text' by scanning for a balanced
    {...} block. Works even if the model outputs multiple JSON objects concatenated
    with newlines or extra prose.
    """
    if not text:
        raise ValueError("Empty LLM response")

    import json

    # find first '{'
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found")

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        # not inside a string
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                segment = text[start:i + 1]
                return json.loads(segment)

    raise ValueError("Unbalanced JSON braces in LLM output")



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
