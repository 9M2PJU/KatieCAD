# Creating a Release

The installers are built automatically by GitHub (for Windows, Linux, and macOS), as they
cannot be generated on a different system.

1. Check and commit the version number in `katiecad/manifest.py` (`VERSION`).
2. Create and push a tag:
`git tag v1.0.2 && git push origin v1.0.2`
(Alternatively, via GitHub: Actions > Release > Run workflow – select "Build" only, not "Release").
3. After approximately 10–15 minutes, the following files will be available under *Releases*
or *Actions > Artifacts*:
- `KatieCAD-<Version>-Windows-Setup.exe` (installer, created with Inno Setup)
- `KatieCAD-<Version>-macOS.dmg` (drag the application into the "Applications" folder)
- `KatieCAD-<Version>-Linux-amd64.deb` and `KatieCAD-<Version>-Linux.tar.gz`

Notes
- The applications are not digitally signed: on Windows, "SmartScreen" may appear (select "More info" >
"Run anyway"); on macOS, you may need to right-click the app and select "Open" the first time you run it.
- The logo is sourced from `KatieCAD.ico` and `KatieCAD.png` located in the repository's root directory. 
Both files must be present there. The `.icns` file for macOS is generated from the PNG during the build process.
- The Windows installer displays the MIT License (from the `LICENSE` file) for the user to accept before installation.
- The macOS build is designed for Apple Silicon (arm64).
