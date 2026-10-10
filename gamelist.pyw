"""
Game list - a tiny terminal-looking game launcher for Windows.
Only shows games you add yourself.

Keys:
  Up / Down   move
  Shift+Up / Shift+Down   move the selected game higher / lower in the list
  Enter       launch
  A           add an .exe / .bat / .cmd
  /           search / filter games
  T           cycle color themes
  Delete      remove the selected game from the list
  U           undo the last removal (within 5 seconds)
  Q / Esc     quit

Saved as .pyw so double-clicking it opens only this window (no cmd/PowerShell).
"""
import ctypes
import json
import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import filedialog

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "GameList")
DATA_FILE = os.path.join(APP_DIR, "games.json")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

THEMES = [
    {"name": "Classic White", "bg": "#0c0c0c", "fg": "#ffffff", "dim": "#9a9a9a"},
    {"name": "Amber CRT",     "bg": "#120c04", "fg": "#ffb000", "dim": "#9c6b00"},
    {"name": "Matrix Green",  "bg": "#020f02", "fg": "#00ff66", "dim": "#008a36"},
    {"name": "Cyber Blue",    "bg": "#040814", "fg": "#00d2fc", "dim": "#3a738f"},
]

FONT = ("Consolas", 13)


def load_games():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def save_games(items):
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2)
    except Exception as e:
        print(f"Error saving games: {e}")


def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {"theme_index": 0}


def save_config(config):
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")


class App:
    def __init__(self, root):
        self.root = root
        root.title("games")
        root.geometry("1920x1080")

        self.config = load_config()
        self.theme_idx = self.config.get("theme_index", 0)
        if self.theme_idx >= len(THEMES):
            self.theme_idx = 0

        theme = THEMES[self.theme_idx]
        self.bg = theme["bg"]
        self.fg = theme["fg"]
        self.dim = theme["dim"]

        root.configure(bg=self.bg)

        self.text = tk.Text(
            root, bg=self.bg, fg=self.fg, font=FONT, insertbackground=self.fg, bd=0,
            highlightthickness=0, padx=14, pady=10, cursor="arrow", wrap="none",
        )
        self.text.pack(fill="both", expand=True)
        
        self.apply_theme_tags()

        self.games = load_games()
        self.sel = 0
        self.mode = "list"
        self.confirm_action = None
        self.confirm_text = ""
        self.pending_exe = None
        self.buffer = ""
        self.cursor = 0         
        self.status = ""
        self.status_job = None
        self.undo_item = None  
        
        self.search_query = ""

        root.bind("<Key>", self.on_key)
        self.draw()

    def apply_theme_tags(self):
        theme = THEMES[self.theme_idx]
        self.bg = theme["bg"]
        self.fg = theme["fg"]
        self.dim = theme["dim"]
        
        self.root.configure(bg=self.bg)
        self.text.configure(bg=self.bg, fg=self.fg, insertbackground=self.fg)
        self.text.tag_configure("sel", background=self.fg, foreground=self.bg)
        self.text.tag_configure("dim", foreground=self.dim)

    def get_active_list(self):
        games = self.games
        if self.search_query:
            games = [g for g in games if self.search_query.lower() in str(g.get("name", "")).lower()]
        return games

    def draw(self):
        t = self.text
        t.configure(state="normal")
        t.delete("1.0", "end")
        
        theme_name = THEMES[self.theme_idx]["name"]
        t.insert("end", f"Games  ({theme_name} Theme)\n")
        
        display_games = self.get_active_list()
        sel_line = 2
        
        if not display_games:
            if self.search_query:
                t.insert("end", f"(no games match '{self.search_query}')\n", "dim")
            else:
                t.insert("end", "(empty - press A to add an exe)\n", "dim")
        
        for i, g in enumerate(display_games):
            name = str(g.get("name", "Unknown"))
            if len(name) > 42:
                name = name[:39] + "..."
                
            last_played = g.get("last_played")
            last_str = f"Last: {last_played}" if last_played else "Last: Never"
            
            # Wide gap (45 spaces) for the name column before Last Played
            line = f"{'>' if i == self.sel else ' '} {name:<45} {last_str}\n"
            if i == self.sel:
                sel_line = 2 + i
                t.insert("end", line, "sel")
            else:
                t.insert("end", line)
                
        t.insert("end", "\n")
        t.insert("end", "[up/down] move  [/] search  [t] theme  [enter] launch  [a] add  [del] remove  [q] quit\n", "dim")
        
        if self.mode == "name":
            exe_name = os.path.basename(self.pending_exe) if self.pending_exe else ""
            t.insert("end", f"name for {exe_name} (blank = '{os.path.splitext(exe_name)[0]}', esc cancels): {self.buffer[:self.cursor]}")
            at = self.buffer[self.cursor:self.cursor + 1] or " "
            t.insert("end", at, "sel")
            t.insert("end", f"{self.buffer[self.cursor + 1:]}\n")
        elif self.mode == "search":
            t.insert("end", f"search: {self.search_query}_ (esc to clear/exit)\n")
        elif self.mode == "confirm":
            t.insert("end", f"{self.confirm_text}\n")
        else:
            t.insert("end", f"{self.status}\n", "dim")
            
        try:
            t.see(f"{sel_line}.0")
        except Exception:
            pass
        t.configure(state="disabled")

    def on_key(self, e):
        if self.mode == "confirm":
            k = e.keysym.lower()
            if k == "y":
                action = self.confirm_action
                self.mode, self.confirm_action = "list", None
                if action:
                    action()
            elif k == "n":
                self.mode, self.confirm_action = "list", None
                self.set_status("cancelled")
            self.draw()
            return
        
        if self.mode == "name":
            return self.key_name(e)
            
        if self.mode == "search":
            return self.key_search(e)

        k = e.keysym
        shift = bool(e.state & 0x1)
        display_games = self.get_active_list()

        if k == "Up" and display_games:
            if shift:
                self.move(-1)
            else:
                self.sel = (self.sel - 1) % len(display_games)
        elif k == "Down" and display_games:
            if shift:
                self.move(1)
            else:
                self.sel = (self.sel + 1) % len(display_games)
        elif k == "Return":
            self.launch()
        elif k == "slash" or k == "bar" or e.char == "/":
            self.mode = "search"
        elif k.lower() == "t":
            self.theme_idx = (self.theme_idx + 1) % len(THEMES)
            self.apply_theme_tags()
            self.config["theme_index"] = self.theme_idx
            save_config(self.config)
            self.set_status(f"Theme: {THEMES[self.theme_idx]['name']}")
        elif k.lower() == "u":
            self.undo_remove()
        elif k.lower() == "a":
            self.ask("Are you sure you want to add a game? (y/n)", self.add_exe)
            return
        elif k == "Delete":
            if display_games and 0 <= self.sel < len(display_games):
                name = display_games[self.sel].get("name", "this game")
                self.ask(f"Are you sure you want to remove '{name}'? (y/n)", self.remove)
            return
        elif k.lower() == "q" or k == "Escape":
            if self.search_query:
                self.search_query = ""
            else:
                self.root.destroy()
                return
        self.draw()

    def key_search(self, e):
        if e.keysym == "Escape":
            self.mode = "list"
            self.search_query = ""
            self.sel = 0
        elif e.keysym == "Return":
            self.mode = "list"
        elif e.keysym == "BackSpace":
            self.search_query = self.search_query[:-1]
        elif e.char and e.char.isprintable():
            self.search_query += e.char
        self.sel = 0
        self.draw()

    def key_name(self, e):
        if e.keysym == "Return":
            default = os.path.splitext(os.path.basename(self.pending_exe))[0] if self.pending_exe else "game"
            name = self.buffer.strip() or default
            items = load_games()
            items.append({"name": name, "path": self.pending_exe, "last_played": None})
            save_games(items)
            self.mode, self.pending_exe, self.buffer, self.cursor = "list", None, "", 0
            self.games = load_games()
            self.set_status(f"added '{name}'")
        elif e.keysym == "Escape":
            self.mode, self.pending_exe, self.buffer, self.cursor = "list", None, "", 0
            self.set_status("cancelled")
        elif e.keysym == "BackSpace":
            if self.cursor > 0:
                self.buffer = self.buffer[:self.cursor - 1] + self.buffer[self.cursor:]
                self.cursor -= 1
        elif e.keysym == "Delete":
            self.buffer = self.buffer[:self.cursor] + self.buffer[self.cursor + 1:]
        elif e.keysym == "Left":
            self.cursor = max(0, self.cursor - 1)
        elif e.keysym == "Right":
            self.cursor = min(len(self.buffer), self.cursor + 1)
        elif e.keysym == "Home":
            self.cursor = 0
        elif e.keysym == "End":
            self.cursor = len(self.buffer)
        elif e.char and e.char.isprintable():
            self.buffer = self.buffer[:self.cursor] + e.char + self.buffer[self.cursor:]
            self.cursor += len(e.char)
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
        self.sel = min(idx, max(0, len(items) - 1))
        self.set_status(f"restored '{g.get('name', 'game')}'")

    def ask(self, text, action):
        self.mode = "confirm"
        self.confirm_text = text
        self.confirm_action = action
        self.draw()

    def add_exe(self):
        path = filedialog.askopenfilename(
            title="Pick the game's .exe or .bat",
            filetypes=[("Games", "*.exe *.bat *.cmd"), ("Executables", "*.exe"),
                       ("Batch files", "*.bat *.cmd"), ("All files", "*.*")],
        )
        if path:
            self.pending_exe = os.path.normpath(path)
            self.mode = "name"
            self.buffer = ""
            self.cursor = 0
        self.draw()

    def move(self, direction):
        display_games = self.get_active_list()
        if not display_games or not (0 <= self.sel < len(display_games)):
            return
        
        target_game = display_games[self.sel]
        actual_idx = next((i for i, g in enumerate(self.games) if g.get("path") == target_game.get("path") and g.get("name") == target_game.get("name")), -1)
        
        if actual_idx == -1:
            return

        j = actual_idx + direction
        if j < 0 or j >= len(self.games):
            return
            
        self.games[actual_idx], self.games[j] = self.games[j], self.games[actual_idx]
        save_games(self.games)
        self.sel = (self.sel + direction) % len(display_games)

    def remove(self):
        display_games = self.get_active_list()
        if not display_games or not (0 <= self.sel < len(display_games)):
            return
        g = display_games[self.sel]
        
        actual_idx = next((i for i, item in enumerate(self.games) if item.get("path") == g.get("path") and item.get("name") == g.get("name")), -1)
        if actual_idx == -1:
            return
            
        items = load_games()
        removed_item = items.pop(actual_idx)
        save_games(items)
        self.games = load_games()
        self.sel = min(self.sel, max(0, len(self.get_active_list()) - 1))
        self.set_status(f"removed '{g.get('name', 'game')}' - press U to undo")
        self.undo_item = (actual_idx, removed_item)

    def launch(self):
        display_games = self.get_active_list()
        if not display_games or not (0 <= self.sel < len(display_games)):
            return
        g = display_games[self.sel]
        path = g.get("path")
        name = g.get("name", "game")
        
        if not path or not os.path.exists(path):
            self.set_status(f"Error: Executable not found at path.")
            return

        try:
            folder = os.path.dirname(path) or None
            if path.lower().endswith((".bat", ".cmd")):
                subprocess.Popen(["cmd", "/c", path], cwd=folder,
                             creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen([path], cwd=folder)
            
            timestamp_str = time.strftime("%Y-%m-%d %H:%M")
            items = load_games()
            for item in items:
                if item.get("path") == path and item.get("name") == name:
                    item["last_played"] = timestamp_str
                    break
            save_games(items)
            self.games = load_games()
            
            self.set_status(f"launching {name}...")
            self.draw()
            
        except Exception as ex:
            self.set_status(f"failed to launch: {ex}")


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if __name__ == "__main__":
    if not is_admin():
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1
            )
        except Exception as e:
            print(f"Failed to elevate privileges: {e}")
        sys.exit(0)

    root = tk.Tk()
    App(root)
    root.mainloop()
