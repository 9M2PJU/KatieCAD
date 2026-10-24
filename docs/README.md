# Release erstellen

Die Installer werden automatisch von GitHub gebaut (Windows, Linux, macOS), weil man
sie nicht auf einem anderen System erzeugen kann.

1. Version in `katiecad/manifest.py` (`VERSION`) prüfen und committen.
2. Tag setzen und hochladen:
   `git tag v1.0.1 && git push origin v1.0.1`
   (oder auf GitHub: Actions > Release > Run workflow – dann nur Build, kein Release).
3. Nach ca. 10-15 Minuten liegen unter *Releases* bzw. *Actions > Artefakte*:
   - `KatieCAD-<Version>-Windows-Setup.exe` (Installer, Inno Setup)
   - `KatieCAD-<Version>-macOS.dmg` (Programm in „Programme“ ziehen)
   - `KatieCAD-<Version>-Linux-amd64.deb` und `KatieCAD-<Version>-Linux.tar.gz`

Hinweise
- Die Programme sind nicht signiert: Windows zeigt „SmartScreen“ (Weitere Informationen >
  Trotzdem ausführen), macOS verlangt Rechtsklick > Öffnen beim ersten Start.
- Das Logo kommt aus `KatieCAD.ico` und `KatieCAD.png` im Hauptordner des Repos.
  Beide Dateien müssen dort liegen. Die `.icns`-Datei für den Mac wird beim Bauen aus der PNG erzeugt.
- Der Windows-Installer zeigt vor der Installation die MIT-Lizenz (Datei `LICENSE`) zur Zustimmung.
- Der macOS-Build ist für Apple Silicon (arm64).


# Creating a Release

The installers are built automatically by GitHub (for Windows, Linux, and macOS), as they
cannot be generated on a different system.

1. Check and commit the version number in `katiecad/manifest.py` (`VERSION`).
2. Create and push a tag:
`git tag v1.0.1 && git push origin v1.0.1`
(Alternatively, via GitHub: Actions > Release > Run workflow – select "Build" only, not "Release").
3. After approximately 10–15 minutes, the following files will be available under *Releases* or *Actions > Artifacts*:
- `KatieCAD-<Version>-Windows-Setup.exe` (installer, created with Inno Setup)
- `KatieCAD-<Version>-macOS.dmg` (drag the application into the "Applications" folder)
- `KatieCAD-<Version>-Linux-amd64.deb` and `KatieCAD-<Version>-Linux.tar.gz`

Notes
- The applications are not digitally signed: on Windows, "SmartScreen" may appear (select "More info" > "Run anyway"); on macOS, you may need to right-click the app and select "Open" the first time you launch it.
- The logo is sourced from `KatieCAD.ico` and `KatieCAD.png` located in the repository's root directory. 
Both files must be present there. The `.icns` file for macOS is generated from the PNG during the build process.
- The Windows installer displays the MIT License (from the `LICENSE` file) for the user to accept before installation.
- The macOS build is designed for Apple Silicon (arm64).
