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
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=yes
DisableWelcomePage=yes
DisableDirPage=no
UsePreviousAppDir=yes
UninstallDisplayIcon={app}\VSL Clinic.exe
OutputDir={#InstallerOutput}
OutputBaseFilename=VSL-Clinic-Setup-{#AppVersion}
Compression=lzma2/normal
SolidCompression=yes
LZMANumBlockThreads=2
LZMABlockSize=262144
DiskSpanning=no
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
LicenseFile=..\licenses\multimodal100\AV-HuBERT-LICENSE.txt

[Languages]
Name: "vietnamese"; MessagesFile: "Vietnamese.isl"

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\VSL Clinic"; Filename: "{app}\VSL Clinic.exe"; WorkingDir: "{app}"; Parameters: "--user-data-dir=""{localappdata}\VSL Clinic\UserData"""
Name: "{autoprograms}\VSL Clinic"; Filename: "{app}\VSL Clinic.exe"; WorkingDir: "{app}"; Parameters: "--user-data-dir=""{localappdata}\VSL Clinic\UserData"""

[Run]
Filename: "{app}\VSL Clinic.exe"; Parameters: "--user-data-dir=""{localappdata}\VSL Clinic\UserData"""; Description: "Mở VSL Clinic"; Flags: nowait postinstall skipifsilent

[Code]
function NextButtonClick(CurPageID: Integer): Boolean;
var Target: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    Target := RemoveBackslashUnlessRoot(WizardDirValue);
    if FileExists(Target + '\package.json') or
       (Pos('\app\0.4.1', Lowercase(Target)) > 0) then
    begin
      MsgBox('Chọn một thư mục cài đặt riêng, không dùng thư mục source hoặc bản lưu 0.4.1.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;
