# Release erstellen

Die Installer werden automatisch von GitHub gebaut (Windows, Linux, macOS), weil man
sie nicht auf einem anderen System erzeugen kann.

1. Version in `katiecad/manifest.py` (`VERSION`) prüfen und committen.
2. Tag setzen und hochladen:
   `git tag v1.0.4 && git push origin v1.0.4`
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
