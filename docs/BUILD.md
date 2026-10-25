# Building the Program Yourself (Windows, Linux, macOS)

The program must be built **on the respective operating system** (e.g., build the Windows version on Windows, etc.).
Prerequisites: Python 3.10+ with Tk (for Windows/macOS, use the installer from python.org; for Linux, run `sudo apt install python3-tk python3-venv`) and the repository from GitHub.

Alternatively, you can run it **without building**: simply execute `pip install -r requirements.txt` followed by `python main.py`.
In this case, symbols, blocks, and templates will remain directly within the repository folder.

## How are the symbol library, title blocks, and templates included?
KatieCAD looks for `symbols/`, `title_blocks/`, `report_templates/`, and `docs/` relative to the program's location. PyInstaller uses the `--add-data` option to bundle these folders alongside the program (placing them in an `_internal` folder on Windows/Linux, or within the app package on macOS). The build scripts provided below handle this automatically. You can continue to store your own custom blocks in the block browser or your project folder.

## Windows
0. Ensure `KatieCAD.ico`, `KatieCAD.png`, and `LICENSE` are located in the repository's root folder.
1. Run `installer\build_windows.bat` → this generates `dist\KatieCAD\KatieCAD.exe`.
2. For the installer: Install Inno Setup, open `installer\KatieCAD.iss`, and select "Compile"
(or run `iscc /DAppVersion=1.0.2 installer\KatieCAD.iss` from the command line) → this produces `release\KatieCAD-1.0.2-Windows-Setup.exe`.
The script includes the entire `dist\KatieCAD` folder, ensuring all necessary libraries are bundled. ## Linux
1. `sh installer/build_unix.sh` → `dist/KatieCAD/KatieCAD`
2. As a package (Debian/Ubuntu): `installer/build_deb.sh 1.0.2` → `release/KatieCAD-1.0.2-Linux-amd64.deb`,
install using `sudo apt install ./release/KatieCAD-1.0.2-Linux-amd64.deb`
(this places the program in `/opt/katiecad`, creates a start menu entry, and adds the `katiecad` command). 
Alternatively, you can simply copy the `dist/KatieCAD` folder; it is ready to run without installation.

## macOS
1. `sh installer/build_unix.sh` → `dist/KatieCAD.app`
2. Disk image: `mkdir dmg && cp -R dist/KatieCAD.app dmg/ && ln -s /Applications dmg/Applications && hdiutil create -volname KatieCAD -srcfolder dmg -ov -format UDZO KatieCAD-1.0.2-macOS.dmg`
Upon first launch: Right-click the app > Open (as it is unsigned).

## Verification
After building, launch the program and check the block browser to see if "Symbol Library"
appears, and verify that the title block templates can be selected under "Frames."
