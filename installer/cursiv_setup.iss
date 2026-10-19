; ============================================================
; Cursiv v3.14-U73 — Signed field records
; Produces: installer\Output\Cursiv-Setup-3.14-U73.exe
;
; Single PyInstaller bundle: Cursiv.exe (GUI launcher with embedded chat
; panel, tray, guardian, feedback loops, and terminal/chat mode via -t).
; Patches applied: groovy/version.txt + pandas stub (fixes CLI crash).
; Bootstrap script installs Ollama + all pip packages post-install.
;
; Compile: iscc installer\cursiv_setup.iss
; ============================================================

#define AppName      "Cursiv"
#define AppVer       "3.14-U73"
#define AppPublisher "Joshua Winkler"
#define AppURL       "https://cursiv.winklers-llc.com"
#define SourceURL    "https://github.com/winklersllc2026-bit/Cursiv"
#define AppVerNum    StringChange(AppVer, "-U", ".")
#define AppExe       "Cursiv.exe"
#define AppID        "{{A7B1C2D3-E4F5-4A6B-9C7D-8E0F1A2B3C4D}}"

[Setup]
AppId={#AppID}
AppName={#AppName}
AppVersion={#AppVer}
AppVerName={#AppName} {#AppVer}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#SourceURL}/issues
AppUpdatesURL={#SourceURL}/releases
VersionInfoVersion={#AppVerNum}
VersionInfoProductVersion={#AppVerNum}
VersionInfoTextVersion={#AppVer}
VersionInfoProductTextVersion={#AppVer}
VersionInfoCompany={#AppPublisher}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} Setup: an offline AI assistant for field research
VersionInfoCopyright=Copyright (c) 2026 {#AppPublisher}. MIT License. Source: {#SourceURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
InfoBeforeFile=BEFORE-INSTALL.txt
InfoAfterFile=..\CHANGELOG.md
AppComments=A personal AI assistant that runs on your own computer. The local model answers first; online features are optional, and offline mode blocks every connection off this computer.
OutputDir=Output
OutputBaseFilename=Cursiv-Setup-3.14-U73
SetupIconFile=..\launcher\resources\icons\cursiv.ico
WizardSmallImageFile=..\launcher\resources\icons\cursiv_256.png
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExe}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";  Description: "{cm:CreateDesktopIcon}";                                                       GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart";    Description: "Start Cursiv when Windows starts";                                             GroupDescription: "Startup:"; Flags: unchecked

[Files]
; ── Main application (PyInstaller bundle: single Cursiv.exe) ─────────────────
; Includes groovy/version.txt and pandas stub patch — CLI no longer crashes.
Source: "..\dist\Cursiv\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Leftovers from older versions: the terminal-chat command and the old
; PowerShell setup scripts (the Setup window does that job now).
Type: files; Name: "{app}\cursiv.bat"
Type: filesandordirs; Name: "{app}\scripts"

[Icons]
; Start Menu
Name: "{group}\{#AppName}";            Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}";  Filename: "{uninstallexe}"

; Desktop shortcut — main launcher (optional)
Name: "{autodesktop}\{#AppName}";                  Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; Autostart (optional task) — HKCU so no admin needed
Root: HKCU; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#AppName}"; \
  ValueData: """{app}\{#AppExe}"" --tray"; \
  Flags: uninsdeletevalue; Tasks: autostart

; Older versions added the install folder to the user PATH (for the removed
; 'cursiv' terminal command). The uninstaller still removes that entry -- see
; RemoveFromUserPath.

[Run]
; Cursiv's own Setup window installs Ollama, a model and coding models with
; progress bars.

; Launch after install (the setup script also launches, but this is the checkbox option)
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent

; In-app update (launched by Cursiv with /SILENT /UPDATE=1): reopen Cursiv
; when the update finishes. Normal installs use the checkbox entry above.
Filename: "{app}\{#AppExe}"; Flags: nowait runasoriginaluser; Check: IsAppUpdate

[UninstallRun]
; Kill running instance before uninstall
Filename: "taskkill"; Parameters: "/f /im {#AppExe}"; \
  Flags: runhidden; RunOnceId: "KillCursiv"

[Code]
// True when Cursiv's in-app updater launched this installer (/UPDATE=1).
function IsAppUpdate: Boolean;
begin
  Result := ExpandConstant('{param:UPDATE|0}') = '1';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  // PATH is registered; new terminals will pick it up automatically
end;

// Removes only Param from the user PATH, leaving every other entry alone.
procedure RemoveFromUserPath(Param: string);
var
  OrigPath, Rest, Entry, NewPath: string;
  P: Integer;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', OrigPath) then
    exit;
  Rest := OrigPath + ';';
  NewPath := '';
  while Rest <> '' do
  begin
    P := Pos(';', Rest);
    Entry := Copy(Rest, 1, P - 1);
    Delete(Rest, 1, P);
    if (Entry <> '') and (CompareText(RemoveBackslashUnlessRoot(Entry), RemoveBackslashUnlessRoot(Param)) <> 0) then
    begin
      if NewPath <> '' then
        NewPath := NewPath + ';';
      NewPath := NewPath + Entry;
    end;
  end;
  if NewPath <> OrigPath then
    RegWriteExpandStringValue(HKCU, 'Environment', 'Path', NewPath);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RemoveFromUserPath(ExpandConstant('{app}'));
end;
