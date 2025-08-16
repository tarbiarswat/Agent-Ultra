# app/graph.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import requests, json, os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL = os.getenv("AGENT_MODEL", "llama3.1:8b")

@dataclass
class Step:
    thought: str
    action: str
    args: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None

@dataclass
class AgentState:
    goal: str
    steps: List[Step] = field(default_factory=list)
    done: bool = False

SYSTEM = (
    "You are a local automation agent.\n"
    "Respond with ONE and ONLY ONE JSON object (no prose, no code fences).\n"
    'Schema: {"thought": string, "action": string, "args": object}.\n'
    "Allowed actions: open_url(url), click(text_or_selector), type(text), wait(seconds), read_page(), finish().\n"
    "Rules: Do exactly ONE action per reply. Never repeat the same action+args twice in a row. "
    "Use finish() ONLY when the user goal is satisfied. Prefer read_page() after navigation.\n"
)

def _first_json(text:str) -> Dict[str,Any]:
    if not text: raise ValueError("Empty LLM response")
    start = text.find("{")
    if start < 0: raise ValueError("No JSON object found")
    depth = 0; in_str=False; esc=False
    for i,ch in enumerate(text[start:], start):
        if in_str:
            if esc: esc=False
            elif ch=="\\": esc=True
            elif ch=='"': in_str=False
            continue
        if ch=='"': in_str=True
        elif ch=='{': depth+=1
        elif ch=='}':
            depth-=1
            if depth==0:
                return json.loads(text[start:i+1])
    raise ValueError("Unbalanced JSON")

def call_ollama(messages, model: str = MODEL) -> str:
    payload = {"model": model, "messages": messages, "stream": False, "options": {"temperature": 0.0}}
    r = requests.post(OLLAMA_URL, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data.get("message", {}).get("content", "")

def next_step(goal: str, history: List[Dict[str,str]]) -> Step:
    messages = [{"role":"system","content":SYSTEM}]
    messages += history
    messages.append({"role":"user","content":f"USER GOAL: {goal}\nReturn only one JSON object for your next single action."})

    raw = call_ollama(messages)
    # print raw for debugging if you want
    # print("\n[LLM RAW OUTPUT]\n", raw, "\n")
    try:
        obj = _first_json(raw)
    except Exception:
        repair = call_ollama(
            [{"role":"system","content":"Return ONLY one JSON object. No prose."},
             {"role":"user","content":raw or "(empty)"}]
        )
        obj = _first_json(repair)

    thought = str(obj.get("thought","")).strip()
    action = str(obj.get("action","")).strip()
    args   = obj.get("args",{}) or {}

    if action not in {"open_url","click","type","wait","read_page","finish"}:
        action, args = "read_page", {}

    return Step(thought=thought, action=action, args=args)
