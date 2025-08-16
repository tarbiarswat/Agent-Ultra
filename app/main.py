import json, time
from app.graph import AgentState, next_step
from tools.browser import BrowserTool
from ui.overlay import get_overlay

ACTIONS = {
  "open_url": lambda b, **k: b.open_url(k["url"]),
  "click":    lambda b, **k: b.click(k["text_or_selector"]),
  "type":     lambda b, **k: b.type(k["text"]),
  "wait":     lambda b, **k: b.wait(k.get("seconds",1)),
  "read_page":lambda b, **k: b.read_page(),
}

def run(goal:str):
    state = AgentState(goal=goal)
    browser = BrowserTool()
    ol = get_overlay()
    history = []

    try:
        for _ in range(20):  # cap steps
            step = next_step(state.goal, history)
            ol.set_text(f"Thinking: {step.thought}\nDoing: {step.action} {step.args}")
            action_fn = ACTIONS.get(step.action)
            if not action_fn:
                step.result = f"Unknown action {step.action}"
            else:
                step.result = action_fn(browser, **step.args)
            state.steps.append(step)
            history.append({"role":"assistant","content":json.dumps({
                "thought": step.thought, "action": step.action, "args": step.args, "result": step.result
            })})
            # simple stopping condition
            if "done" in (step.thought.lower() + step.result.lower()):
                break
        return state
    finally:
        ol.set_text("Done.")
        # keep browser open for inspection; close manually if you like

if __name__ == "__main__":
    # Example task: open a site, search, read page
    run("Open https://example.com, read the page, then say Done.")
