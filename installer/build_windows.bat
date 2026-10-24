@echo off
rem Local build for Windows (run inside the repository folder):  installer\build_windows.bat
cd /d "%~dp0\.."
python -m venv .venv-build
call .venv-build\Scripts\activate
pip install -r requirements.txt pyinstaller
set DOCS=
if exist docs set DOCS=--add-data "docs;docs"
pyinstaller --noconfirm --windowed --name KatieCAD --icon KatieCAD.ico ^
  --collect-submodules katiecad --collect-submodules ezdxf --collect-all ezdwg ^
  --add-data "symbols;symbols" --add-data "title_blocks;title_blocks" ^
  --add-data "report_templates;report_templates" %DOCS% ^
  --add-data "KatieCAD.ico;." --add-data "KatieCAD.png;." main.py
echo Done: dist\KatieCAD\KatieCAD.exe  (next: Inno Setup, see docs\BUILD.md)
