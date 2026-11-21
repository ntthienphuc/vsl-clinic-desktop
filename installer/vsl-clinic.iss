; One offline installer; all runtimes and models come from the verified payload.
#ifndef AppVersion
  #error AppVersion must be supplied by tools/build_installer.py
#endif
#ifndef PayloadDir
  #error PayloadDir must be supplied by tools/build_installer.py
#endif
#ifndef InstallerOutput
  #error InstallerOutput must be supplied by tools/build_installer.py
#endif

[Setup]
AppId=vn.vsl.clinic.desktop.installer
AppName=VSL Clinic
AppVersion={#AppVersion}
AppPublisher=VSL Clinic
DefaultDirName={localappdata}\Programs\VSL Clinic
DefaultGroupName=VSL Clinic
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
; The Windows AVX2 feature flag used below is available from build 19041.
MinVersion=10.0.19041
DisableProgramGroupPage=yes
DisableWelcomePage=yes
DisableDirPage=no
UsePreviousAppDir=yes
UninstallDisplayIcon={app}\VSL Clinic.exe
OutputDir={#InstallerOutput}
OutputBaseFilename=VSL-Clinic-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
MergeDuplicateFiles=yes
LZMANumBlockThreads=4
LZMABlockSize=262144
DiskSpanning=no
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
; Legal texts stay with the installed payload and in Tai_lieu as a separate
; Word document. Setup R2 has no license acceptance or information-only page.
VersionInfoDescription=VSL Clinic Setup R3

[Languages]
Name: "vietnamese"; MessagesFile: "Vietnamese.isl"

[Files]
; CPU is always included so GPU installations can recover from unavailable drivers.
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Excludes: "resources\multimodal-runtime\*"; Flags: ignoreversion recursesubdirs createallsubdirs
#include GpuFiles

[InstallDelete]
; Private versioned runtimes are replaced on upgrade, including old CUDA DLLs.
; Original models and rollback installers remain in the project baselines.
; UserData is outside {app}; never delete it or unrelated application folders.
Type: files; Name: "{app}\resources\frontend\ui-assets\*"
Type: files; Name: "{app}\LOCAL_PATCH.json"
Type: files; Name: "{app}\LOCAL_PATCH_GIT_SYNC.json"
Type: files; Name: "{app}\LOCAL_PATCH.md"
Type: filesandordirs; Name: "{app}\resources\multimodal-runtime"
Type: filesandordirs; Name: "{app}\resources\multimodal-runtime-cpu"
Type: filesandordirs; Name: "{app}\resources\engine"
; Replace app-owned assets/modules in full: no stale voice takes, historical
; model files or Python caches survive upgrade. [Files] restores all inputs;
; UserData and original research/source folders remain outside this tree.
Type: filesandordirs; Name: "{app}\resources\assets"
Type: filesandordirs; Name: "{app}\resources\multimodal"
Type: files; Name: "{app}\debug.log"

[Icons]
Name: "{autodesktop}\VSL Clinic"; Filename: "{app}\VSL Clinic.exe"; WorkingDir: "{app}"; Parameters: "--user-data-dir=""{localappdata}\VSL Clinic\UserData"""
Name: "{autoprograms}\VSL Clinic"; Filename: "{app}\VSL Clinic.exe"; WorkingDir: "{app}"; Parameters: "--user-data-dir=""{localappdata}\VSL Clinic\UserData"""

[UninstallDelete]
Type: files; Name: "{app}\runtime-preference.json"

[Run]
Filename: "{app}\VSL Clinic.exe"; Parameters: "--user-data-dir=""{localappdata}\VSL Clinic\UserData"""; Description: "Mở VSL Clinic"; Flags: nowait postinstall skipifsilent

[Code]
type
  TDeviceText = array[0..127] of Char;
  TDisplayDevice = record
    Size: Cardinal;
    DeviceName: array[0..31] of Char;
    DeviceString: TDeviceText;
    StateFlags: Cardinal;
    DeviceID: TDeviceText;
    DeviceKey: TDeviceText;
  end;

var
  ComputePage: TInputOptionWizardPage;
  DetectedGPU: Boolean;

function EnumDisplayDevices(Device: Cardinal; Index: Cardinal;
  var DisplayDevice: TDisplayDevice; Flags: Cardinal): Boolean;
  external 'EnumDisplayDevicesW@user32.dll stdcall';

function DeviceText(Value: TDeviceText): String;
var I: Integer;
begin
  Result := '';
  for I := 0 to 127 do
  begin
    if Value[I] = #0 then Exit;
    Result := Result + Value[I];
  end;
end;

function HasNvidiaGPU(): Boolean;
var
  Device: TDisplayDevice;
  Index: Cardinal;
begin
  Result := False;
  Index := 0;
  Device.Size := SizeOf(Device);
  while EnumDisplayDevices(0, Index, Device, 0) do
  begin
    if (Pos('VEN_10DE', Uppercase(DeviceText(Device.DeviceID))) > 0) or
       (Pos('NVIDIA', Uppercase(DeviceText(Device.DeviceString))) > 0) then
    begin
      Result := True;
      Exit;
    end;
    Index := Index + 1;
    Device.Size := SizeOf(Device);
  end;
end;

function InstallGPU(): Boolean;
begin
  Result := ComputePage.SelectedValueIndex = 0;
end;

procedure InitializeWizard();
var
  RequestedMode: String;
begin
  DetectedGPU := HasNvidiaGPU();
  ComputePage := CreateInputOptionPage(wpSelectDir,
    'Chọn cách chạy VSL Clinic',
    'Cài đầy đủ trên máy, không cần Python hoặc tải thêm model.',
    'GPU phù hợp với máy có card NVIDIA. CPU dùng ít dung lượng hơn và chạy được khi không có card NVIDIA.',
    True, False);
  ComputePage.Add('GPU NVIDIA — ưu tiên card đồ họa, có CPU dự phòng');
  ComputePage.Add('CPU — tiết kiệm dung lượng, không cần card NVIDIA');
  if DetectedGPU then
  begin
    ComputePage.SelectedValueIndex := 0;
    ComputePage.SubCaptionLabel.Caption := 'Đã phát hiện NVIDIA. GPU được chọn sẵn; bạn có thể đổi sang CPU.';
  end
  else
  begin
    ComputePage.SelectedValueIndex := 1;
    ComputePage.SubCaptionLabel.Caption := 'Chưa phát hiện NVIDIA. CPU được chọn sẵn cho máy này.';
  end;
  RequestedMode := Lowercase(ExpandConstant('{param:COMPUTE|}'));
  if RequestedMode = 'cpu' then ComputePage.SelectedValueIndex := 1;
  if RequestedMode = 'gpu' then ComputePage.SelectedValueIndex := 0;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Mode: String;
begin
  if CurStep = ssPostInstall then
  begin
    if InstallGPU() then Mode := 'gpu' else Mode := 'cpu';
    if not SaveStringToFile(ExpandConstant('{app}\runtime-preference.json'),
      '{"schema":1,"compute":"' + Mode + '"}', False) then
      RaiseException('Không lưu được lựa chọn CPU/GPU. Hãy chạy lại bộ cài.');
    Log('VSL Clinic compute mode: ' + Mode);
  end;
end;

function IsProcessorFeaturePresent(Feature: Cardinal): Boolean;
  external 'IsProcessorFeaturePresent@kernel32.dll stdcall';

function InitializeSetup(): Boolean;
begin
  Result := IsProcessorFeaturePresent(40);
  if not Result then
    MsgBox('Bản này cần Windows 10 phiên bản 2004 trở lên hoặc Windows 11, máy 64-bit và CPU có AVX2. Bạn không cần cài Python.', mbError, MB_OK);
end;

function SafeInstallFolder(Target: String): Boolean;
var Entry: TFindRec;
begin
  Target := RemoveBackslashUnlessRoot(Target);
  Result := True;
  if not DirExists(Target) then Exit;
  if FileExists(Target + '\VSL Clinic.exe') and
     FileExists(Target + '\BUILD_RECEIPT.json') and
     FileExists(Target + '\unins000.exe') and
     not DirExists(Target + '\.git') and not FileExists(Target + '\package.json') then Exit;
  if FindFirst(Target + '\*', Entry) then
  try
    repeat
      if (Entry.Name <> '.') and (Entry.Name <> '..') then
      begin
        Result := False;
        Break;
      end;
    until not FindNext(Entry);
  finally
    FindClose(Entry);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if not SafeInstallFolder(WizardDirValue) then
    Result := 'Hãy chọn thư mục trống hoặc thư mục đã cài VSL Clinic.';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var Target: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    Target := RemoveBackslashUnlessRoot(WizardDirValue);
    if not SafeInstallFolder(Target) then
    begin
      MsgBox('Hãy chọn thư mục trống hoặc thư mục đã cài VSL Clinic.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;
