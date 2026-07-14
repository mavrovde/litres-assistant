; Inno Setup script for the BookVault Windows desktop app.
;
; Compiles the PyInstaller onedir output (packaging\windows\dist\BookVault\)
; into a single Setup.exe installer. Installs to Program Files, creates a Start
; menu entry (+ an optional desktop shortcut), and can launch the app when done.
; Chromium is fetched on first run, so the installer stays small (~80-120 MB).
;
; Build (from packaging\windows\, after the PyInstaller build):
;   iscc /DAppVersion=1.2.3 BookVault.iss
; The version is supplied by CI via /DAppVersion=; a dev default is used locally.

#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif

[Setup]
; Stable AppId GUID -- identifies the app across upgrades/uninstalls. Keep fixed.
AppId={{9E5B1B4E-BF00-4C21-9A11-1B00C4A9A7E4}
AppName=BookVault
AppVersion={#AppVersion}
AppPublisher=Sergii Mavrov
DefaultDirName={autopf}\BookVault
DefaultGroupName=BookVault
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\BookVault.exe
OutputDir=dist
OutputBaseFilename=BookVault-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
; SetupIconFile=BookVault.ico     ; optional

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The whole PyInstaller onedir folder (BookVault.exe + _internal\).
Source: "dist\BookVault\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\BookVault";           Filename: "{app}\BookVault.exe"
Name: "{group}\Uninstall BookVault"; Filename: "{uninstallexe}"
Name: "{autodesktop}\BookVault";     Filename: "{app}\BookVault.exe"; Tasks: desktopicon

[Run]
; Offer to launch the app when the wizard finishes.
Filename: "{app}\BookVault.exe"; Description: "{cm:LaunchProgram,BookVault}"; \
  Flags: nowait postinstall skipifsilent
