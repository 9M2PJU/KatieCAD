#!/bin/sh
# Builds a .deb package from the PyInstaller output (dist/KatieCAD).
# Usage: installer/build_deb.sh <version> [arch]
set -e
VER="$1"; ARCH="${2:-amd64}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG="$ROOT/build/deb/katiecad_${VER}_${ARCH}"
rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" "$PKG/opt/katiecad" "$PKG/usr/bin" \
         "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/256x256/apps"
cp -r "$ROOT/dist/KatieCAD/." "$PKG/opt/katiecad/"
ln -s /opt/katiecad/KatieCAD "$PKG/usr/bin/katiecad"
cp "$ROOT/assets/KatieCAD.png" "$PKG/usr/share/icons/hicolor/256x256/apps/katiecad.png"
cat > "$PKG/usr/share/applications/katiecad.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=KatieCAD
Comment=2D CAD and electrical CAD
Exec=/opt/katiecad/KatieCAD
Icon=katiecad
Terminal=false
Categories=Graphics;Engineering;
DESK
cat > "$PKG/DEBIAN/control" <<CTRL
Package: katiecad
Version: $VER
Section: graphics
Priority: optional
Architecture: $ARCH
Maintainer: KatieCAD
Description: 2D CAD growing into an electrical CAD
 Wires, devices, cross references, terminal plans and reports.
CTRL
mkdir -p "$ROOT/release"
dpkg-deb --build --root-owner-group "$PKG" "$ROOT/release/KatieCAD-${VER}-Linux-${ARCH}.deb"
