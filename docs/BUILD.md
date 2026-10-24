# Programm selbst bauen (Windows, Linux, macOS)

Gebaut wird **auf dem jeweiligen System** (Windows-Programm unter Windows usw.).
Voraussetzung: Python 3.10+ mit Tk (Windows/macOS: python.org-Installer; Linux:
`sudo apt install python3-tk python3-venv`) und das Repository von GitHub.

**Ohne Bauen** geht es immer: `pip install -r requirements.txt` und `python main.py`.
Dann liegen Symbole, Blöcke und Vorlagen einfach im Repo-Ordner.

## Wie kommen Symbolbibliothek, Rahmen, Vorlagen mit?
KatieCAD sucht `symbols/`, `title_blocks/`, `report_templates/` und `docs/` relativ zum
Programm. PyInstaller packt diese Ordner mit der Option `--add-data` neben das Programm
(bei Windows/Linux in den Ordner `_internal`, bei macOS ins App-Paket). Die Build-Skripte
unten machen das bereits. Eigene Blöcke legst du weiter im Block-Browser/Projektordner ab.

## Windows
0. `KatieCAD.ico` und `KatieCAD.png` müssen im Hauptordner des Repos liegen (ebenso `LICENSE`).
1. `installer\build_windows.bat` ausführen → `dist\KatieCAD\KatieCAD.exe`
2. Installer: Inno Setup installieren, `installer\KatieCAD.iss` öffnen, „Compile“
   (oder `iscc /DAppVersion=1.0.1 installer\KatieCAD.iss`) → `release\KatieCAD-1.0.1-Windows-Setup.exe`
   Das Skript nimmt den ganzen Ordner `dist\KatieCAD` mit, also auch alle Bibliotheken.

## Linux
1. `sh installer/build_unix.sh` → `dist/KatieCAD/KatieCAD`
2. Als Paket (Debian/Ubuntu): `installer/build_deb.sh 1.0.1` → `release/KatieCAD-1.0.1-Linux-amd64.deb`,
   installieren mit `sudo apt install ./release/KatieCAD-1.0.1-Linux-amd64.deb`
   (legt das Programm nach `/opt/katiecad`, Startmenü-Eintrag und Befehl `katiecad`).
   Alternativ den Ordner `dist/KatieCAD` kopieren, er ist ohne Installation lauffähig.

## macOS
1. `sh installer/build_unix.sh` → `dist/KatieCAD.app`
2. Disk-Image: `mkdir dmg && cp -R dist/KatieCAD.app dmg/ && ln -s /Applications dmg/Applications && hdiutil create -volname KatieCAD -srcfolder dmg -ov -format UDZO KatieCAD-1.0.1-macOS.dmg`
   Beim ersten Start: Rechtsklick auf die App > Öffnen (nicht signiert).

## Prüfen
Nach dem Bauen das Programm starten und im Block-Browser nachsehen, ob „Symbolbibliothek“
erscheint und unter Rahmen die Titelblock-Vorlagen auswählbar sind.
