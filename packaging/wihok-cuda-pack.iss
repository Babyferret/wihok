; The GPU add-on for NVIDIA cards. It holds every file of the CUDA build of Wihok that differs from
; the CPU build, so installing it over the CPU install turns that install into the CUDA build.
; It is not meant to be run by hand: the main installer downloads it, checks its SHA-256 and runs it
; silently with /DIR pointing at Wihok's folder. Build with packaging\build.ps1.

[Setup]
AppId={{3C8D7A41-6E52-4B9F-A1D0-7B2E94C5F6A3}
AppName=Wihok GPU support
AppVersion={#AppVersion}
AppPublisher=Wihok
CreateAppDir=yes
DefaultDirName={autopf}\Wihok
DirExistsWarning=no
DisableProgramGroupPage=yes
DisableReadyPage=yes
; Not listed in "Apps & features": the main uninstaller removes these files with the app.
Uninstallable=no
CreateUninstallRegKey=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#Generated}\wihok.ico
OutputDir={#OutDir}
OutputBaseFilename=Wihok-CUDA-Pack-{#AppVersion}

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#PackDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  // NVIDIA's license lets us ship its runtime libraries only inside an application, used only by that
  // application, and not as a stand-alone product. So this add-on installs only over an existing Wihok.
  Result := '';
  if not FileExists(ExpandConstant('{app}\Wihok.exe')) then
    Result := 'This add-on installs only over an existing Wihok installation. Run the Wihok installer instead.';
end;
