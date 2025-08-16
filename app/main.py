# app/main.py
import json
from app.graph import AgentState, next_step, Step
from tools.browser import BrowserTool
from ui.overlay import get_overlay

ACTIONS = {
  "open_url": lambda b, **k: b.open_url(k["url"]),
  "click":    lambda b, **k: b.click(k["text_or_selector"]),
  "type":     lambda b, **k: b.type(k["text"]),
  "wait":     lambda b, **k: b.wait(k.get("seconds",1)),
  "read_page":lambda b, **k: b.read_page(),
}

def run(goal:str) -> AgentState:
    state = AgentState(goal=goal)
    browser = BrowserTool()
    ol = get_overlay()
    messages = []  # chat history for the LLM

    last_signature = None
    repeat_budget = 2  # how many repeats allowed before we override
    max_steps = 12

    try:
        for _ in range(max_steps):
            step: Step = next_step(state.goal, messages)

            # repetition guard
            signature = (step.action, json.dumps(step.args, sort_keys=True))
            if signature == last_signature:
                repeat_budget -= 1
                if repeat_budget <= 0:
                    # force a progress-making action
                    step.action, step.args = ("read_page", {})
                    repeat_budget = 2
            else:
                repeat_budget = 2

            # overlay
            ol.set_text(f"Thinking: {step.thought}\nDoing: {step.action} {step.args}")

            if step.action == "finish":
                state.done = True
                state.steps.append(step)
                messages.append({"role":"assistant","content":json.dumps({"thought":step.thought,"action":"finish","args":{}})})
                messages.append({"role":"user","content":"Observation: finished acknowledged."})
                break

            # execute tool
            tool_fn = ACTIONS.get(step.action)
            if not tool_fn:
                result = {"status":"error","message":f"Unknown action {step.action}"}
            else:
                try:
                    result = tool_fn(browser, **step.args)
                except Exception as e:
                    result = {"status":"error","message":str(e)}

            step.result = result
            state.steps.append(step)

            # ReAct-style feedback to the model
            messages.append({"role":"assistant","content":json.dumps({"thought":step.thought,"action":step.action,"args":step.args})})
            messages.append({"role":"user","content":f"Observation: {json.dumps(result)}"})

            last_signature = signature

            # fast stop if the page clearly loaded and goal mentions 'read'
            if step.action == "read_page" and "Done" in state.goal:
                messages.append({"role":"user","content":"You can now call finish()."})
        return state
    finally:
        ol.set_text("Done.")
        # keep browser open for inspection
