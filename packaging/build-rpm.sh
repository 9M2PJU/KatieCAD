#!/bin/bash
# Build an RPM for KatieCAD using rpmbuild.
# Usage: ./packaging/build-rpm.sh [version] [output-dir]
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-$(python3 -c 'from katiecad_manifest import VERSION; print(VERSION)')}"
OUTDIR="${2:-dist}"
SPEC="packaging/rpm/katiecad.spec"
TOPDIR="$(mktemp -d)"
trap 'rm -rf "$TOPDIR"' EXIT

mkdir -p "$TOPDIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS} "$OUTDIR"

# Keep spec version in sync with manifest.
sed -i -E "s/^Version:\s+.*/Version:        ${VERSION}/" "$SPEC"

# Stage a source tarball named as %autosetup expects.
STAGE_TMP="$(mktemp -d)"
PKGROOT="$STAGE_TMP/katiecad-$VERSION"
mkdir -p "$PKGROOT"
cp KatieCAD.py katiecad_*.py requirements.txt LICENSE README.md KatieCAD.png "$PKGROOT/"
cp -r packaging "$PKGROOT/"
tar -czf "$TOPDIR/SOURCES/katiecad-$VERSION.tar.gz" -C "$STAGE_TMP" "katiecad-$VERSION"
rm -rf "$STAGE_TMP"
cp "$SPEC" "$TOPDIR/SPECS/"

rpmbuild --define "_topdir $TOPDIR" -bb "$TOPDIR/SPECS/katiecad.spec"

find "$TOPDIR/RPMS" -name "*.rpm" -exec cp -v {} "$OUTDIR/" \;
echo "--- dist/ ---"
ls -la "$OUTDIR"
