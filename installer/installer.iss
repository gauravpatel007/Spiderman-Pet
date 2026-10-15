; 🕷️ Spider-Buddy — Inno Setup Installer Script
; Windows Native Desktop Companion Installer

#define MyAppName "Spider-Buddy"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SpiderBuddy Team"
#define MyAppURL "https://github.com/spiderbuddy/spiderbuddy"
#define MyAppExeName "SpiderBuddy.exe"

[Setup]
; AppId uniquely identifies this application.
AppId={{5F7A9B32-8D41-4E62-9B71-9A52C06B22A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Per-user install does not require administrative elevation
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=SpiderBuddy_Setup_v{#MyAppVersion}
SetupIconFile=..\assets\icons\spider.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Launch Spider-Buddy automatically when Windows starts"; GroupDescription: "Windows Integration:"

[Files]
Source: "..\dist\SpiderBuddy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Registry]
; Register for Windows user startup if selected
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "SpiderBuddy"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: startupicon; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
