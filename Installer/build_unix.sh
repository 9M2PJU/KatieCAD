#!/bin/sh
# Local build for Linux and macOS (run inside the repository folder):
#   sh installer/build_unix.sh
set -e
cd "$(dirname "$0")/.."
python3 -m venv .venv-build
. .venv-build/bin/activate
pip install -r requirements.txt pyinstaller
python tools/make_icon.py
ICON=KatieCAD.png
[ "$(uname)" = "Darwin" ] && ICON=build/KatieCAD.icns
# --add-data "<folder>:<folder>" copies the data folders next to the program,
# so symbols, title blocks, report templates and docs are found.
DOCS=""; [ -d docs ] && DOCS="--add-data docs:docs"
pyinstaller --noconfirm $DOCS --windowed --name KatieCAD --icon "$ICON" \
  --collect-submodules katiecad --collect-submodules ezdxf \
  --add-data "symbols:symbols" --add-data "title_blocks:title_blocks" \
  --add-data "report_templates:report_templates" \
  --add-data "KatieCAD.ico:." --add-data "KatieCAD.png:." main.py
echo "Done: dist/KatieCAD (Linux) or dist/KatieCAD.app (macOS)"
