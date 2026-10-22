#!/bin/bash
# Build all KatieCAD installers: .deb, .rpm, .AppImage
# Usage: ./packaging/build-all.sh [version]
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="${1:-$(python3 -c 'from katiecad_manifest import VERSION; print(VERSION)')}"
chmod +x packaging/build-*.sh
./packaging/build-deb.sh "$VERSION" dist
./packaging/build-rpm.sh "$VERSION" dist
./packaging/build-appimage.sh "$VERSION" dist
echo "=== All artifacts ==="
ls -la dist/
