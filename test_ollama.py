import requests, json

MODEL = "llama3.1:8b"
URL = "http://localhost:11434/api/chat"

payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "Say 'hello' and 2+3."}],
    "stream": True
}

try:
    with requests.post(URL, json=payload, stream=True, timeout=120) as r:
        r.raise_for_status()
        full = []
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            obj = json.loads(line)
            # Each obj has keys like: {"message": {"content": "..."}, "done": false, ...}
            if "message" in obj and "content" in obj["message"]:
                full.append(obj["message"]["content"])
            if obj.get("done"):
                break
        print("OK ✅\n", "".join(full))
except Exception as e:
    print("FAILED ❌", e)
