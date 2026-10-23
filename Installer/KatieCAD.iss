; Inno Setup script - Windows installer for KatieCAD
; Build:  iscc /DAppVersion=1.0.0 installer\KatieCAD.iss
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6F3B8E1A-4C2D-4F6B-9A57-0A1B2C3D4E5F}
AppName=KatieCAD
AppVersion={#AppVersion}
AppPublisher=KatieCAD
DefaultDirName={autopf}\KatieCAD
DefaultGroupName=KatieCAD
UninstallDisplayIcon={app}\KatieCAD.exe
OutputDir=..\release
OutputBaseFilename=KatieCAD-{#AppVersion}-Windows-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
SetupIconFile=..\KatieCAD.ico
LicenseFile=..\LICENSE

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "..\dist\KatieCAD\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\KatieCAD"; Filename: "{app}\KatieCAD.exe"
Name: "{autodesktop}\KatieCAD"; Filename: "{app}\KatieCAD.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\KatieCAD.exe"; Description: "{cm:LaunchProgram,KatieCAD}"; Flags: nowait postinstall skipifsilent
