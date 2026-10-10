"""
Game list - a tiny terminal-looking game launcher for Windows.
Only shows games you add yourself.

Keys:
  Up / Down   move
  Shift+Up / Shift+Down   move the selected game higher / lower in the list
  Enter       launch
  A           add an .exe / .bat / .cmd
  /           search / filter games
  P           toggle playtime sorting (on/off)
  T           cycle color themes
  Delete      remove the selected game from the list
  U           undo the last removal (within 5 seconds)
  Q / Esc     quit

Saved as .pyw so double-clicking it opens only this window (no cmd/PowerShell).
"""
import json
import os
import subprocess
import threading
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
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_games(items):
    os.makedirs(APP_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"theme_index": 0}


def save_config(config):
    os.makedirs(APP_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


class App:
    def __init__(self, root):
        self.root = root
        root.title("games")
        root.geometry("880x540")

        # Load configurations and themes
        self.config = load_config()
        self.theme_idx = self.config.get("theme_index", 0)
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
        self.mode = "list"      # "list", "name", "confirm", or "search"
        self.confirm_action = None
        self.confirm_text = ""
        self.pending_exe = None
        self.buffer = ""
        self.cursor = 0         
        self.status = ""
        self.status_job = None
        self.undo_item = None  
        
        self.search_query = ""
        self.sort_by_playtime = False

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
            games = [g for g in games if self.search_query.lower() in g["name"].lower()]
        
        if self.sort_by_playtime:
            games = sorted(games, key=lambda x: x.get("playtime", 0), reverse=True)
        return games

    def draw(self):
        t = self.text
        t.configure(state="normal")
        t.delete("1.0", "end")
        
        sort_indicator = " [Sorted by Playtime]" if self.sort_by_playtime else ""
        theme_name = THEMES[self.theme_idx]["name"]
        t.insert("end", f"Games:{sort_indicator}  ({theme_name} Theme)\n")
        
        display_games = self.get_active_list()
        sel_line = 2
        
        if not display_games:
            if self.search_query:
                t.insert("end", f"(no games match '{self.search_query}')\n", "dim")
            else:
                t.insert("end", "(empty - press A to add an exe)\n", "dim")
        
        for i, g in enumerate(display_games):
            pt = g.get("playtime", 0)
            if pt >= 60:
                time_str = f"[{pt // 60}h {pt % 60}m]"
            else:
                time_str = f"[{pt}m]"
            
            last_played = g.get("last_played")
            last_str = f"Last: {last_played}" if last_played else "Never played"
            
            line = f"{'>' if i == self.sel else ' '} {g['name']:<25} {time_str:<10} ({last_str})\n"
            if i == self.sel:
                sel_line = 2 + i
                t.insert("end", line, "sel")
            else:
                t.insert("end", line)
                
        t.insert("end", "\n")
        t.insert("end", "[up/down] move  [/] search  [p] sort  [t] theme  [enter] launch  [a] add  [del] remove  [q] quit\n", "dim")
        
        if self.mode == "name":
            exe_name = os.path.basename(self.pending_exe)
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
            if shift and not self.sort_by_playtime:
                self.move(-1)
            else:
                self.sel = (self.sel - 1) % len(display_games)
        elif k == "Down" and display_games:
            if shift and not self.sort_by_playtime:
                self.move(1)
            else:
                self.sel = (self.sel + 1) % len(display_games)
        elif k == "Return":
            self.launch()
        elif k == "slash" or k == "bar" or e.char == "/":
            self.mode = "search"
        elif k.lower() == "p":
            self.sort_by_playtime = not self.sort_by_playtime
            self.sel = 0
            self.set_status(f"Playtime sorting: {'ON' if self.sort_by_playtime else 'OFF'}")
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
            if display_games:
                name = display_games[self.sel]["name"]
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
            default = os.path.splitext(os.path.basename(self.pending_exe))[0]
            name = self.buffer.strip() or default
            items = load_games()
            items.append({"name": name, "path": self.pending_exe, "playtime": 0, "last_played": None})
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
        self.sel = min(idx, len(items) - 1)
        self.set_status(f"restored '{g['name']}'")

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
        if not display_games or self.sort_by_playtime:
            return
        
        target_game = display_games[self.sel]
        actual_idx = next(i for i, g in enumerate(self.games) if g["path"] == target_game["path"] and g["name"] == target_game["name"])
        
        j = actual_idx + direction
        if j < 0 or j >= len(self.games):
            return
            
        self.games[actual_idx], self.games[j] = self.games[j], self.games[actual_idx]
        save_games(self.games)
        self.sel = (self.sel + direction) % len(display_games)

    def remove(self):
        display_games = self.get_active_list()
        if not display_games:
            return
        g = display_games[self.sel]
        
        actual_idx = next(i for i, item in enumerate(self.games) if item["path"] == g["path"] and item["name"] == g["name"])
        
        save_games([m for i, m in enumerate(load_games()) if i != actual_idx])
        self.games = load_games()
        self.sel = min(self.sel, max(0, len(self.get_active_list()) - 1))
        self.set_status(f"removed '{g['name']}' - press U to undo")
        self.undo_item = (actual_idx, g)

    def launch(self):
        display_games = self.get_active_list()
        if not display_games:
            return
        g = display_games[self.sel]
        try:
            folder = os.path.dirname(g["path"]) or None
            if g["path"].lower().endswith((".bat", ".cmd")):
                proc = subprocess.Popen(["cmd", "/c", g["path"]], cwd=folder,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                proc = subprocess.Popen([g["path"]], cwd=folder)
            
            self.set_status(f"launching {g['name']}...")
            threading.Thread(target=self.track_playtime, args=(g, proc), daemon=True).start()
            
        except Exception as ex:
            self.set_status(f"failed to launch: {ex}")

    def track_playtime(self, game_ref, process):
        start_time = time.time()
        process.wait()  
        duration_minutes = int((time.time() - start_time) / 60)
        timestamp_str = time.strftime("%Y-%m-%d %H:%M")
        
        if duration_minutes >= 0:
            items = load_games()
            for item in items:
                if item.get("path") == game_ref.get("path") and item.get("name") == game_ref.get("name"):
                    item["playtime"] = item.get("playtime", 0) + duration_minutes
                    item["last_played"] = timestamp_str
                    break
            save_games(items)
            self.root.after(0, lambda: self.update_after_play(game_ref['name'], duration_minutes))

    def update_after_play(self, name, duration):
        self.games = load_games()
        self.set_status(f"Finished playing '{name}' (+{duration}m)")
        self.draw()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
