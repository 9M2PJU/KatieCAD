#!/bin/bash
# Build a KatieCAD AppImage (x86_64).
# Layout: AppDir with app sources + pip-bundled pure-python deps
# (ezdxf, ezdwg, Pillow) in usr/lib/python3/site-packages.
# Host must still provide: python3 + python3-tk.
# Usage: ./packaging/build-appimage.sh [version] [output-dir]
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-$(python3 -c 'from katiecad_manifest import VERSION; print(VERSION)')}"
OUTDIR="${2:-dist}"
APPDIR="$(mktemp -d)/KatieCAD.AppDir"
mkdir -p "$APPDIR/usr/share/katiecad" \
         "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/lib/python3/site-packages" \
         "$OUTDIR"

echo "Staging AppDir at $APPDIR ..."

# --- app sources -----------------------------------------------------------
for f in KatieCAD.py katiecad_*.py requirements.txt LICENSE README.md; do
    cp "$f" "$APPDIR/usr/share/katiecad/"
done
cp KatieCAD.png "$APPDIR/katiecad.png"
cp KatieCAD.png "$APPDIR/.DirIcon"
cp packaging/katiecad.desktop "$APPDIR/katiecad.desktop"
cp packaging/katiecad.desktop "$APPDIR/usr/share/applications/katiecad.desktop"
cp packaging/katiecad.appdata.xml "$APPDIR/usr/share/katiecad/" 2>/dev/null || true

# --- bundled python deps ---------------------------------------------------
# Pin minimums from requirements.txt; install wheels for portability.
python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
python3 -m pip install --target "$APPDIR/usr/lib/python3/site-packages" \
    "ezdxf>=1.4" "ezdwg>=0.12" "Pillow>=10.0"

# Drop tests/caches to keep the image small.
find "$APPDIR/usr/lib/python3/site-packages" \
    \( -name "__pycache__" -o -name "*.dist-info" \) -prune -exec rm -rf {} + 2>/dev/null || true
python3 -m compileall -q "$APPDIR/usr/share/katiecad" || true

# --- AppRun ----------------------------------------------------------------
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
# KatieCAD AppImage entry point.
APPDIR="$(dirname "$(readlink -f "$0")")"
export PYTHONPATH="$APPDIR/usr/lib/python3/site-packages${PYTHONPATH:+:$PYTHONPATH}"
export APPDIR
if ! command -v python3 >/dev/null 2>&1; then
    echo "KatieCAD AppImage requires a system python3 with tkinter (python3-tk)." >&2
    exit 1
fi
exec python3 "$APPDIR/usr/share/katiecad/KatieCAD.py" "$@"
EOF
chmod 0755 "$APPDIR/AppRun"
chmod 0755 "$APPDIR/usr/share/katiecad/KatieCAD.py" || true

# --- build -----------------------------------------------------------------
ARCH=x86_64 appimagetool -n "$APPDIR" "$OUTDIR/KatieCAD-${VERSION}-x86_64.AppImage"
chmod +x "$OUTDIR/KatieCAD-${VERSION}-x86_64.AppImage"
ls -la "$OUTDIR"
