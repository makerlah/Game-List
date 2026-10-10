# Lightweight-Game-Launcher
A tiny terminal-style game launcher for Windows. Add your own game .exe files, name them, reorder them with the Shift + Arrow keys, and launch them from one simple list.

## Features

- Terminal look: black background, white text, no mouse needed
- Add any `.exe` and give it your own name
- Reorder games however you like
- Confirmation prompts before adding or removing a game
- Undo a removal within 5 seconds
- Your list is saved automatically

## Controls

| Key | Action |
| --- | --- |
| Up / Down | Move through the list |
| Shift + Up / Down | Move the selected game higher / lower |
| Enter | Launch the selected game |
| A | Add a game (asks to confirm with Y/N, then pick the `.exe` and type a name) |
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

Your game list is stored in `%APPDATA%\GameList\games.json`. Delete that file to reset the list.

Made with help from [Claude](https://claude.ai).

## License

MIT. See [LICENSE](LICENSE).
