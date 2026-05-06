# Build Windows EXE with VS Code

This guide explains how to build a Windows executable (`.exe`) for the GUI app.

## 1. Copy Project to Windows
- Copy the project folder to a Windows machine.
- Example folder name: `Imatest analysis v2/`

## 2. Install Python (with Tkinter)
- Install Python 3.10 or later.
- During installation, enable:
  - `Add Python to PATH`
  - `tcl/tk and IDLE`

Verify installation:
```bash
python --version
python -c "import tkinter; print(tkinter.TkVersion)"
```

## 3. Open Project in VS Code
- In VS Code, use `File > Open Folder` and open this project.

## 4. Create Virtual Environment (Recommended)
```bash
python -m venv .venv
.venv\Scripts\activate
```

## 5. Install Dependencies
```bash
pip install -r requirements.txt
pip install pyinstaller
```

## 6. Run GUI Locally (Quick Check)
```bash
python gui.py
```

## 7. Build GUI EXE
Use either command below.

Option A (direct command):
```bash
pyinstaller --onefile --windowed --collect-submodules src --add-data "src;src" gui.py
```

Option B (spec file in repo):
```bash
pyinstaller gui.spec
```

## 8. Check Build Output
- Executable path:
  - `dist\gui.exe`

## 9. Distribution Notes
- In most cases, you can distribute `dist\gui.exe` directly.
- On first run, Windows Defender/SmartScreen may show a warning depending on environment and signing status.

---

## Optional: Build CLI EXE
If you also need the CLI executable:
```bash
pyinstaller --onefile main.py
```
Output:
- `dist\main.exe`
