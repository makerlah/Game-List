"""
Game list - a tiny terminal-looking game launcher for Windows.
Only shows games you add yourself.

Keys:
  Up / Down   move
  Shift+Up / Shift+Down   move the selected game higher / lower in the list
  Enter       launch
  A           add an .exe (asks to confirm, then type a name for it)
  Delete      remove the selected game from the list (asks to confirm)
  U           undo the last removal (within 5 seconds)
  Q / Esc     quit

Saved as .pyw so double-clicking it opens only this window (no cmd/PowerShell).
"""
import json
import os
import subprocess
import tkinter as tk
from tkinter import filedialog

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "GameList")
DATA_FILE = os.path.join(APP_DIR, "games.json")

BG, FG, DIM = "#0c0c0c", "#ffffff", "#9a9a9a"
FONT = ("Consolas", 13)


def load_games():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            games = json.load(f)
    except Exception:
        games = []
    return games


def save_games(items):
    os.makedirs(APP_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)


class App:
    def __init__(self, root):
        self.root = root
        root.title("games")
        root.geometry("820x520")
        root.configure(bg=BG)

        self.text = tk.Text(
            root, bg=BG, fg=FG, font=FONT, insertbackground=FG, bd=0,
            highlightthickness=0, padx=14, pady=10, cursor="arrow", wrap="none",
        )
        self.text.pack(fill="both", expand=True)
        self.text.tag_configure("sel", background=FG, foreground=BG)
        self.text.tag_configure("dim", foreground=DIM)

        self.games = load_games()
        self.sel = 0
        self.mode = "list"      # "list", "name" or "confirm"
        self.confirm_action = None
        self.confirm_text = ""
        self.pending_exe = None
        self.buffer = ""
        self.status = ""
        self.status_job = None
        self.undo_item = None  # (index, game) of the last removed game

        root.bind("<Key>", self.on_key)
        self.draw()

    def draw(self):
        t = self.text
        t.configure(state="normal")
        t.delete("1.0", "end")
        t.insert("end", "Games:\n")
        sel_line = 2
        if not self.games:
            t.insert("end", "(empty - press A to add an exe)\n", "dim")
        for i, g in enumerate(self.games):
            line = f"{'>' if i == self.sel else ' '} {g['name']}\n"
            if i == self.sel:
                sel_line = 2 + i
                t.insert("end", line, "sel")
            else:
                t.insert("end", line)
        t.insert("end", "\n")
        t.insert("end", "[up/down] move  [shift+up/down] reorder  [enter] launch  [a] add  [del] remove  [q] quit\n", "dim")
        if self.mode == "name":
            exe_name = os.path.basename(self.pending_exe)
            t.insert("end", f"name for {exe_name} (blank = '{os.path.splitext(exe_name)[0]}', esc cancels): {self.buffer}_\n")
        elif self.mode == "confirm":
            t.insert("end", f"{self.confirm_text}\n")
        else:
            t.insert("end", f"{self.status}\n", "dim")
        t.see(f"{sel_line}.0")
        t.configure(state="disabled")

    def on_key(self, e):
        if self.mode == "confirm":
            k = e.keysym.lower()
            if k == "y":
                action = self.confirm_action
                self.mode, self.confirm_action = "list", None
                action()
            elif k == "n":
                self.mode, self.confirm_action = "list", None
                self.set_status("cancelled")
            else:
                return  # ignore every other key until y or n
            self.draw()
            return
        if self.mode == "name":
            return self.key_name(e)
        k = e.keysym
        shift = bool(e.state & 0x1)
        if k == "Up" and self.games:
            if shift:
                self.move(-1)
            else:
                self.sel = (self.sel - 1) % len(self.games)
        elif k == "Down" and self.games:
            if shift:
                self.move(1)
            else:
                self.sel = (self.sel + 1) % len(self.games)
        elif k == "Return":
            self.launch()
        elif k.lower() == "u":
            self.undo_remove()
        elif k.lower() == "a":
            self.ask("Are you sure you want to add a game? (y/n)", self.add_exe)
            return
        elif k == "Delete":
            if self.games:
                name = self.games[self.sel]["name"]
                self.ask(f"Are you sure you want to remove '{name}'? (y/n)", self.remove)
            return
        elif k.lower() == "q" or k == "Escape":
            self.root.destroy()
            return
        self.draw()

    def key_name(self, e):
        if e.keysym == "Return":
            default = os.path.splitext(os.path.basename(self.pending_exe))[0]
            name = self.buffer.strip() or default
            items = load_games()
            items.append({"name": name, "path": self.pending_exe})
            save_games(items)
            self.mode, self.pending_exe, self.buffer = "list", None, ""
            self.games = load_games()
            self.set_status(f"added '{name}'")
        elif e.keysym == "Escape":
            self.mode, self.pending_exe, self.buffer = "list", None, ""
            self.set_status("cancelled")
        elif e.keysym == "BackSpace":
            self.buffer = self.buffer[:-1]
        elif e.char and e.char.isprintable():
            self.buffer += e.char
        self.draw()

    def set_status(self, text, seconds=5):
        if self.status_job:
            self.root.after_cancel(self.status_job)
        self.status = text
        self.undo_item = None
        self.status_job = self.root.after(seconds * 1000, self.clear_status)

    def clear_status(self):
        self.status = ""
        self.status_job = None
        self.undo_item = None
        self.draw()

    def undo_remove(self):
        if not self.undo_item:
            return
        idx, g = self.undo_item
        items = load_games()
        items.insert(min(idx, len(items)), g)
        save_games(items)
        self.games = items
        self.sel = min(idx, len(items) - 1)
        self.set_status(f"restored '{g['name']}'")

    def ask(self, text, action):
        self.mode = "confirm"
        self.confirm_text = text
        self.confirm_action = action
        self.draw()

    def add_exe(self):
        path = filedialog.askopenfilename(
            title="Pick the game's .exe", filetypes=[("Executables", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self.pending_exe = os.path.normpath(path)
            self.mode = "name"
            self.buffer = ""
        self.draw()

    def move(self, direction):
        j = self.sel + direction
        if j < 0 or j >= len(self.games):
            return
        self.games[self.sel], self.games[j] = self.games[j], self.games[self.sel]
        save_games(self.games)
        self.sel = j

    def remove(self):
        if not self.games:
            return
        idx = self.sel
        g = self.games[idx]
        save_games([m for m in load_games() if not (m["name"] == g["name"] and m["path"] == g["path"])])
        self.games = load_games()
        self.sel = min(self.sel, max(0, len(self.games) - 1))
        self.set_status(f"removed '{g['name']}' - press U to undo")
        self.undo_item = (idx, g)  # after set_status, which clears any older undo

    def launch(self):
        if not self.games:
            return
        g = self.games[self.sel]
        try:
            subprocess.Popen([g["path"]], cwd=os.path.dirname(g["path"]) or None)
            self.set_status(f"launching {g['name']}...")
        except Exception as ex:
            self.set_status(f"failed to launch: {ex}")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
