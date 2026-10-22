#!/bin/bash
# Build a .deb for KatieCAD (Architecture: all, Python app).
# Usage: ./packaging/build-deb.sh [version] [output-dir]
# Defaults: version from katiecad_manifest.py, output to dist/
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-$(python3 -c 'from katiecad_manifest import VERSION; print(VERSION)')}"
OUTDIR="${2:-dist}"
PKGNAME="katiecad"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

echo "Building ${PKGNAME}_${VERSION}_all.deb ..."

# --- payload ---------------------------------------------------------------
mkdir -p "$STAGE/DEBIAN"
mkdir -p "$STAGE/usr/share/katiecad"
mkdir -p "$STAGE/usr/bin"
mkdir -p "$STAGE/usr/share/applications"
mkdir -p "$STAGE/usr/share/pixmaps"
mkdir -p "$STAGE/usr/share/icons/hicolor/512x512/apps"
mkdir -p "$STAGE/usr/share/doc/katiecad"
mkdir -p "$STAGE/usr/share/metainfo"

for f in KatieCAD.py katiecad_*.py requirements.txt LICENSE README.md; do
    cp "$f" "$STAGE/usr/share/katiecad/"
done
cp packaging/katiecad "$STAGE/usr/bin/katiecad"
chmod 0755 "$STAGE/usr/bin/katiecad" "$STAGE/usr/share/katiecad/KatieCAD.py"
cp packaging/katiecad.desktop "$STAGE/usr/share/applications/katiecad.desktop"
cp KatieCAD.png "$STAGE/usr/share/pixmaps/katiecad.png"
cp KatieCAD.png "$STAGE/usr/share/icons/hicolor/512x512/apps/katiecad.png"
cp packaging/katiecad.appdata.xml "$STAGE/usr/share/metainfo/katiecad.appdata.xml"
cp LICENSE "$STAGE/usr/share/doc/katiecad/copyright"
chmod 0644 "$STAGE/usr/share/applications/katiecad.desktop"

# --- control ---------------------------------------------------------------
cat > "$STAGE/DEBIAN/control" <<EOF
Package: katiecad
Version: ${VERSION}
Section: graphics
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-tk, python3-pil | python3-pillow, python3-ezdxf
Recommends: python3-pip
Suggests: oda-file-converter | libredwg
Maintainer: KatieCAD Contributors <https://github.com/Merecete/KatieCAD>
Homepage: https://github.com/Merecete/KatieCAD
Description: Lightweight CAD drawing tool (Python/Tkinter)
 KatieCAD is a lightweight 2D CAD drawing tool built with Python and
 Tkinter, featuring drawing, editing and dimensioning tools, layers,
 layout view with viewports, and DXF import/export via ezdxf plus
 DWG import support.
 .
 Install python3-ezdwg from PyPI for extended DWG import:
   pip install --break-system-packages ezdwg
EOF

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
# Warn if optional DWG helper is missing; never fail the install.
if ! python3 -c "import ezdwg" 2>/dev/null; then
    echo "KatieCAD: optional DWG support missing. Install it with:"
    echo "  pip install --break-system-packages ezdwg"
fi
# Refresh desktop/icon caches when available.
command -v update-desktop-database >/dev/null && update-desktop-database -q || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
exit 0
EOF
chmod 0755 "$STAGE/DEBIAN/postinst"

# --- build -----------------------------------------------------------------
mkdir -p "$OUTDIR"
dpkg-deb --build "$STAGE" "$OUTDIR/${PKGNAME}_${VERSION}_all.deb"
echo "Built: $OUTDIR/${PKGNAME}_${VERSION}_all.deb"
dpkg-deb -c "$OUTDIR/${PKGNAME}_${VERSION}_all.deb"
