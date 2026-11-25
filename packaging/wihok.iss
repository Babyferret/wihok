; Wihok installer. Build with packaging\build.ps1, which passes these defines:
;   AppVersion, SourceDir (the CPU build), Generated (icon and images), OutDir,
;   CudaPackUrl, CudaPackSha256 (the optional GPU add-on for NVIDIA cards)
; The base install is the CPU build and runs on any computer (AMD, Intel, no GPU).
; On a computer with an NVIDIA driver the installer offers to download the GPU add-on and
; verifies its SHA-256 before running it.

[Setup]
AppId={{56DDD27F-3F1E-4D2B-B563-96F9AA8ABA04}
AppName=Wihok
AppVersion={#AppVersion}
AppPublisher=Wihok
; Per-user install by default, so no administrator prompt. The wizard can still ask for one.
DefaultDirName={autopf}\Wihok
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#Generated}\wihok.ico
WizardImageFile={#Generated}\wizard-164x314.bmp,{#Generated}\wizard-192x386.bmp,{#Generated}\wizard-246x459.bmp,{#Generated}\wizard-328x628.bmp
WizardSmallImageFile={#Generated}\wizard-small-55.bmp,{#Generated}\wizard-small-64.bmp,{#Generated}\wizard-small-83.bmp,{#Generated}\wizard-small-110.bmp
UninstallDisplayIcon={app}\Wihok.exe
OutputDir={#OutDir}
OutputBaseFilename=Wihok-Setup-{#AppVersion}
; English is the first language and the default; Thai is offered in the language dialog.
ShowLanguageDialog=yes
LanguageDetectionMethod=none
CloseApplications=yes
SetupMutex=WihokSetupMutex

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "th"; MessagesFile: "compiler:Languages\Thai.isl"

[CustomMessages]
en.CudaTask=Add GPU support for NVIDIA cards (downloads about 1.5 GB)
th.CudaTask=เพิ่มการรองรับการ์ดจอ NVIDIA (ดาวน์โหลดประมาณ 1.5 GB)
en.CudaGroup=Speed
th.CudaGroup=ความเร็ว
en.DesktopIcon=Create a desktop shortcut
th.DesktopIcon=สร้างทางลัดบนเดสก์ท็อป
en.CudaInstalling=Installing GPU support...
th.CudaInstalling=กำลังติดตั้งการรองรับการ์ดจอ...
en.CudaFailed=GPU support could not be installed. Wihok will still work, but only on the CPU, which is much slower. You can run this installer again to add GPU support.
th.CudaFailed=ติดตั้งการรองรับการ์ดจอไม่สำเร็จ วิหคยังใช้งานได้ แต่จะใช้ CPU ซึ่งช้ากว่ามาก เปิดตัวติดตั้งนี้อีกครั้งเพื่อเพิ่มการรองรับการ์ดจอได้
en.DownloadNoConnection=Could not connect to the download server. Check your internet connection and try again, or untick the GPU support option to install the CPU version only.
th.DownloadNoConnection=เชื่อมต่อเซิร์ฟเวอร์ดาวน์โหลดไม่ได้ ตรวจสอบอินเทอร์เน็ตแล้วลองใหม่ หรือเอาเครื่องหมายถูกออกจากตัวเลือกการรองรับการ์ดจอเพื่อติดตั้งเฉพาะรุ่น CPU
en.DownloadBadHash=The downloaded GPU support file did not match its checksum, so it was not used. Try again later, or untick the GPU support option to install the CPU version only.
th.DownloadBadHash=ไฟล์การรองรับการ์ดจอที่ดาวน์โหลดมาไม่ตรงกับค่าตรวจสอบ จึงไม่ถูกนำไปใช้ ลองใหม่ภายหลัง หรือเอาเครื่องหมายถูกออกจากตัวเลือกการรองรับการ์ดจอเพื่อติดตั้งเฉพาะรุ่น CPU
en.DownloadNotFound=The GPU support file was not found on the download server. Try again later, or untick the GPU support option to install the CPU version only.
th.DownloadNotFound=ไม่พบไฟล์การรองรับการ์ดจอบนเซิร์ฟเวอร์ดาวน์โหลด ลองใหม่ภายหลัง หรือเอาเครื่องหมายถูกออกจากตัวเลือกการรองรับการ์ดจอเพื่อติดตั้งเฉพาะรุ่น CPU
en.DownloadOther=The GPU support download failed (%1). Check your internet connection and try again, or untick the GPU support option to install the CPU version only.
th.DownloadOther=ดาวน์โหลดการรองรับการ์ดจอไม่สำเร็จ (%1) ตรวจสอบอินเทอร์เน็ตแล้วลองใหม่ หรือเอาเครื่องหมายถูกออกจากตัวเลือกการรองรับการ์ดจอเพื่อติดตั้งเฉพาะรุ่น CPU
en.BadFolder=Wihok must be installed in a folder named Wihok, for example C:\Users\You\AppData\Local\Programs\Wihok. This keeps uninstalling from ever touching other files.
th.BadFolder=ต้องติดตั้งวิหคในโฟลเดอร์ที่ชื่อ Wihok เช่น C:\Users\You\AppData\Local\Programs\Wihok เพื่อให้การถอนการติดตั้งไม่แตะไฟล์อื่นเลย
en.DeleteSettings=Also delete Wihok's saved settings (language and theme)?%n%nYour songs and the results in Music\Wihok are never deleted.
th.DeleteSettings=ลบการตั้งค่าที่วิหคบันทึกไว้ (ภาษาและธีม) ด้วยหรือไม่%n%nเพลงของคุณและผลลัพธ์ใน Music\Wihok จะไม่ถูกลบไม่ว่ากรณีใด

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; Flags: unchecked
Name: "cudapack"; Description: "{cm:CudaTask}"; GroupDescription: "{cm:CudaGroup}"; Check: HasNvidiaDriver

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Wihok"; Filename: "{app}\Wihok.exe"
Name: "{autodesktop}\Wihok"; Filename: "{app}\Wihok.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Wihok.exe"; Description: "{cm:LaunchProgram,Wihok}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; The GPU add-on is installed by a second installer, so Inno does not know its files. _internal is
; entirely ours (PyInstaller created it), so this removes exactly that folder and nothing else.
Type: filesandordirs; Name: "{app}\_internal"

[Code]
var
  DownloadPage: TDownloadWizardPage;

function HasNvidiaDriver: Boolean;
begin
  // nvcuda.dll is installed with the NVIDIA driver; AMD, Intel and no-GPU computers do not have it.
  Result := FileExists(ExpandConstant('{sys}\nvcuda.dll'));
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);
end;

// Inno reports every download failure as "Internal error: Worker thread terminated unexpectedly ...".
// Turn the cause inside it into a sentence a person can act on. The raw text goes to the log.
// 12002 timeout, 12007 name not found, 12029 cannot connect, 12030 connection dropped (WinINet codes).
function DownloadErrorText(const Raw: String): String;
var
  Msg: String;
begin
  Msg := Lowercase(Raw);
  if (Pos('hash', Msg) > 0) or (Pos('verification', Msg) > 0) then
    Result := CustomMessage('DownloadBadHash')
  else if (Pos('12029', Msg) > 0) or (Pos('12007', Msg) > 0) or (Pos('12002', Msg) > 0) or
          (Pos('12030', Msg) > 0) or (Pos('could not be established', Msg) > 0) or (Pos('timed out', Msg) > 0) then
    Result := CustomMessage('DownloadNoConnection')
  else if (Pos('404', Msg) > 0) or (Pos('not found', Msg) > 0) then
    Result := CustomMessage('DownloadNotFound')
  else
    Result := FmtMessage(CustomMessage('DownloadOther'), [Raw]);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Dir, Leaf: String;
begin
  Result := True;

  if CurPageID = wpSelectDir then
  begin
    // Always install into a folder named Wihok, never straight into a drive or a user folder.
    Dir := RemoveBackslashUnlessRoot(WizardDirValue);
    Leaf := ExtractFileName(Dir);
    if CompareText(Leaf, 'Wihok') <> 0 then
      WizardForm.DirEdit.Text := AddBackslash(Dir) + 'Wihok';
  end;

  if (CurPageID = wpReady) and WizardIsTaskSelected('cudapack') then
  begin
    DownloadPage.Clear;
    DownloadPage.Add('{#CudaPackUrl}', 'Wihok-CUDA-Pack.exe', '{#CudaPackSha256}');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
      except
        Log('GPU add-on download error: ' + GetExceptionMessage);
        if not DownloadPage.AbortedByUser then
          SuppressibleMsgBox(DownloadErrorText(GetExceptionMessage), mbCriticalError, MB_OK, IDOK);
        Result := False;
      end;
    finally
      DownloadPage.Hide;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  // A backstop: NextButtonClick already appends \Wihok (tested, also with /VERYSILENT /DIR=...),
  // so this should never fire. It guarantees we never install into any other folder name.
  Result := '';
  if CompareText(ExtractFileName(RemoveBackslashUnlessRoot(ExpandConstant('{app}'))), 'Wihok') <> 0 then
    Result := CustomMessage('BadFolder');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Pack: String;
begin
  // The download itself happens in NextButtonClick (wizard page and silent installs alike). If it fails or
  // the SHA-256 does not match, setup stops there, so by now the add-on is present and verified.
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('cudapack') then
  begin
    Pack := ExpandConstant('{tmp}\Wihok-CUDA-Pack.exe');
    WizardForm.StatusLabel.Caption := CustomMessage('CudaInstalling');
    if not (FileExists(Pack) and
            Exec(Pack, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /DIR="' + ExpandConstant('{app}') + '"',
                 '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0)) then
      SuppressibleMsgBox(CustomMessage('CudaFailed'), mbError, MB_OK, IDOK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
    if MsgBox(CustomMessage('DeleteSettings'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Wihok');
end;
