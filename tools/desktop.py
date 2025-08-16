import pyautogui, time
pyautogui.FAILSAFE = True

def move_click(x:int, y:int):
    pyautogui.moveTo(x, y, duration=0.15)
    pyautogui.click()
    return f"Clicked at ({x},{y})"

def type_text(text:str):
    pyautogui.typewrite(text, interval=0.02)
    return "Typed on desktop."
