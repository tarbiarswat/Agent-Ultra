import tkinter as tk

class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Agent")
        self.root.attributes("-topmost", True)
        self.root.geometry("520x70+40+40")
        self.label = tk.Label(self.root, text="Idle", font=("Segoe UI", 11), justify="left")
        self.label.pack(padx=10, pady=10)
        self.root.update()

    def set_text(self, msg:str):
        self.label.config(text=msg[:250])
        self.root.update_idletasks()
        self.root.update()

overlay = None
def get_overlay():
    global overlay
    if overlay is None: overlay = Overlay()
    return overlay
