# Lightweight-Game-Launcher
A tiny terminal-style game launcher for Windows. Add your own game .exe or .bat files, name them, search, sort by playtime, cycle retro themes, and launch them from one simple list.

## Features

- Terminal look with a built-in theme switcher (cycle through Classic White, Amber CRT, Matrix Green, and Cyber Blue using the T key).
- Add any `.exe`, `.bat` or `.cmd` and give it your own name.
- Edit names while typing with Left / Right / Home / End / Delete.
- Reorder games however you like (when playtime sorting is turned off).
- Real-time search/filtering by pressing `/`.
- Automatic background playtime tracking and cumulative duration display.
- "Last Played" timestamp recording for each game.
- Toggleable playtime sorting (`P` key).
- Confirmation prompts before adding or removing a game.
- Undo a removal within 5 seconds (`U` key).
- Your list and theme preferences are saved automatically.

## Controls

| Key | Action |
| --- | --- |
| Up / Down | Move through the list |
| Shift + Up / Down | Move the selected game higher / lower |
| Enter | Launch the selected game |
| A | Add a game (asks to confirm with Y/N, then pick the `.exe` or `.bat` and type a name) |
| / | Search / filter games in real-time |
| P | Toggle playtime sorting on or off |
| T | Cycle through color themes |
| Delete | Remove the selected game (asks to confirm with Y/N) |
| U | Undo the last removal (within 5 seconds) |
| Q / Esc | Quit |

## Download

Grab `Games.exe` from the [Releases](../../releases) page and run it. No installation needed.

Windows SmartScreen or your antivirus may warn about the file because it isn't code-signed. This is a common false positive with PyInstaller apps. Click **More info**, then **Run anyway**, or build it yourself from the source below.

## Run from source

Requires Python 3 (tkinter is included with the standard Windows installer).

Double-click `gamelist.pyw`. It opens only the app window, with no console.

## Build the exe yourself

With Python installed, put `build.bat` and `gamelist.pyw` in the same folder and double-click `build.bat`. The finished app will be at `dist\Games.exe`.

## Where your data is saved

Your files are stored in `%APPDATA%\GameList\`:
- `games.json` — Stores your game library, playtime counts, and last played timestamps.
- `config.json` — Saves your active color theme choice.

Made with help from [Claude](https://claude.ai) and AI collaboration.

## License

MIT. See [LICENSE](LICENSE).
