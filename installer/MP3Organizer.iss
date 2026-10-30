; MP3 Organizer – grafisches Setup und Deinstallation (Inno Setup 6)
; Bauen: installer\build.ps1   (baut erst dist\MP3Organizer mit PyInstaller, dann dieses Setup)
;   oder direkt: ISCC.exe /DAppVersion=x.y.z installer\MP3Organizer.iss
;
; Ohne Administratorrechte. Datenbank, Protokolle und Berichte liegen unter %LOCALAPPDATA%\MP3 Organizer.
; Stilles Setup:  MP3-Organizer-Setup-x.y.z.exe /VERYSILENT [/DIR="D:\MP3 Organizer"] [/TASKS="desktopicon"]
;   [/RESTARTAPP=1 (MP3 Organizer nach dem Update wieder starten - so ruft es die Update-Funktion auf)]

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef DistDir
  #define DistDir "..\dist"
#endif

[Setup]
AppId={{7C1E2F64-6B0A-4D38-9E52-3F0B7D41A9C6}
AppName=MP3 Organizer
AppVersion={#AppVersion}
AppVerName=MP3 Organizer {#AppVersion}
AppPublisher=phillhf
AppPublisherURL=https://github.com/phillhf/mp3-organizer
AppSupportURL=https://github.com/phillhf/mp3-organizer/issues
AppUpdatesURL=https://github.com/phillhf/mp3-organizer/releases
VersionInfoVersion={#AppVersion}
VersionInfoDescription=MP3 Organizer Setup
DefaultDirName=C:\Tools\MP3 Organizer
AppendDefaultDirName=no
DirExistsWarning=no
UsePreviousAppDir=yes
UsePreviousTasks=yes
DisableProgramGroupPage=yes
DisableWelcomePage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#DistDir}
OutputBaseFilename=MP3-Organizer-Setup-{#AppVersion}
SetupIconFile=app.ico
WizardStyle=modern
LicenseFile=..\LICENSE
UninstallDisplayName=MP3 Organizer
UninstallDisplayIcon={app}\MP3Organizer.exe
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=auto

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Messages]
de.WelcomeLabel1=Willkommen bei MP3 Organizer
en.WelcomeLabel1=Welcome to MP3 Organizer

[CustomMessages]
de.Welcome=Dieses Setup installiert MP3 Organizer {#AppVersion}.%n%nMP3 Organizer räumt MP3-Sammlungen auf: Dubletten aussortieren, fehlende Metadaten wie Jahr und Genre ergänzen und Dateien einheitlich benennen.%n%nEs werden keine Administratorrechte benötigt.
en.Welcome=This setup installs MP3 Organizer {#AppVersion}.%n%nMP3 Organizer tidies up MP3 collections: it sorts out duplicates, fills in missing metadata such as year and genre, and gives files consistent names.%n%nNo administrator rights are required.
de.WelcomeUpdate=MP3 Organizer %1 ist bereits installiert in%n%2%n%nDas Setup aktualisiert auf Version {#AppVersion}. Einstellungen, Suchergebnisse und Berichte bleiben erhalten.
en.WelcomeUpdate=MP3 Organizer %1 is already installed in%n%2%n%nThis setup updates it to version {#AppVersion}. Settings, lookup results and reports are kept.
de.NewerInstalled=Installiert ist bereits die neuere Version %1.%n%nTrotzdem die ältere Version {#AppVersion} einspielen?
en.NewerInstalled=The newer version %1 is already installed.%n%nInstall the older version {#AppVersion} anyway?
de.BadDir=Bitte einen Unterordner auf einer lokalen Festplatte wählen, z. B. C:\Tools\MP3 Organizer.
en.BadDir=Please choose a subfolder on a local drive, e.g. C:\Tools\MP3 Organizer.
de.DesktopIcon=Verknüpfung auf dem Desktop anlegen
en.DesktopIcon=Create a desktop shortcut
de.Shortcuts=Zusätzliche Verknüpfungen:
en.Shortcuts=Additional shortcuts:
de.Uninstall=MP3 Organizer deinstallieren
en.Uninstall=Uninstall MP3 Organizer
de.LaunchNow=MP3 Organizer jetzt starten
en.LaunchNow=Start MP3 Organizer now
de.Finished=MP3 Organizer {#AppVersion} ist installiert.%n%nSo geht's los:%n  • Sammlung auswählen%n  • jeden Schritt zuerst mit „Vorschau“ prüfen%n  • dann mit „Ausführen“ anwenden%n%nGelöscht wird dabei nichts, und der letzte Schritt lässt sich zurücknehmen. Updates bietet MP3 Organizer beim Start automatisch an.
en.Finished=MP3 Organizer {#AppVersion} is installed.%n%nGetting started:%n  • choose your collection%n  • check each step with “Vorschau” (preview) first%n  • then apply it with “Ausführen” (run)%n%nNothing gets deleted, and the last step can be undone. MP3 Organizer offers updates automatically when it starts.
de.Operation=Vorgang:
en.Operation=Operation:
de.OpUpdate=Update von %1 auf {#AppVersion} (Einstellungen und Berichte bleiben erhalten)
en.OpUpdate=Update from %1 to {#AppVersion} (settings and reports are kept)
de.OpInstall=Neuinstallation von MP3 Organizer {#AppVersion}
en.OpInstall=New installation of MP3 Organizer {#AppVersion}
de.DeleteData=Sollen auch Einstellungen, gespeicherte Suchergebnisse, Berichte und Änderungsprotokolle gelöscht werden?%n%nOrdner: %1%n%nBei „Nein“ bleiben sie erhalten und werden bei einer Neuinstallation wieder verwendet. Ohne die Protokolle lassen sich bisherige Schritte nicht mehr rückgängig machen.%n%nDeine Musik und der Dubletten-Ordner werden in keinem Fall angefasst.
en.DeleteData=Should settings, saved lookup results, reports and change logs be deleted as well?%n%nFolder: %1%n%nIf you choose “No” they are kept and reused by a later reinstallation. Without the logs, earlier steps can no longer be undone.%n%nYour music and the duplicates folder are never touched.

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "{cm:Shortcuts}"

[InstallDelete]
; Ein Update ersetzt die komplette Python-Laufzeit – alte Dateien nicht liegen lassen
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#DistDir}\MP3Organizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\MP3 Organizer\MP3 Organizer"; Filename: "{app}\MP3Organizer.exe"; WorkingDir: "{app}"
Name: "{autoprograms}\MP3 Organizer\{cm:Uninstall}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\MP3 Organizer"; Filename: "{app}\MP3Organizer.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\MP3Organizer.exe"; WorkingDir: "{app}"; Description: "{cm:LaunchNow}"; Flags: postinstall nowait skipifsilent
; Nach einem Update ueber die eingebaute Update-Funktion MP3 Organizer wieder starten
Filename: "{app}\MP3Organizer.exe"; WorkingDir: "{app}"; Flags: nowait; Check: RestartAfterSilentUpdate

[UninstallDelete]
Type: dirifempty; Name: "{app}"

[Code]
var
  OldVersion, OldDir: String;

// Versionen wie 1.10.2 vergleichen: <0 aelter, 0 gleich, >0 neuer
function CompareVersion(A, B: String): Integer;
var
  PA, PB, NA, NB: Integer;
begin
  Result := 0;
  while (Result = 0) and ((A <> '') or (B <> '')) do
  begin
    PA := Pos('.', A); PB := Pos('.', B);
    if PA = 0 then begin NA := StrToIntDef(A, 0); A := ''; end else begin NA := StrToIntDef(Copy(A, 1, PA - 1), 0); A := Copy(A, PA + 1, Length(A)); end;
    if PB = 0 then begin NB := StrToIntDef(B, 0); B := ''; end else begin NB := StrToIntDef(Copy(B, 1, PB - 1), 0); B := Copy(B, PB + 1, Length(B)); end;
    Result := NA - NB;
  end;
end;

function UninstallKey(): String;
begin
  Result := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{7C1E2F64-6B0A-4D38-9E52-3F0B7D41A9C6}_is1';
end;

function IsUpdate(): Boolean;
begin
  Result := OldVersion <> '';
end;

// Vor dem Assistenten: vorhandene Installation erkennen
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not RegQueryStringValue(HKCU, UninstallKey(), 'DisplayVersion', OldVersion) then
    RegQueryStringValue(HKLM, UninstallKey(), 'DisplayVersion', OldVersion);
  if not RegQueryStringValue(HKCU, UninstallKey(), 'InstallLocation', OldDir) then
    RegQueryStringValue(HKLM, UninstallKey(), 'InstallLocation', OldDir);
  if IsUpdate() and (CompareVersion(OldVersion, '{#AppVersion}') > 0) and not WizardSilent() then
    Result := MsgBox(FmtMessage(CustomMessage('NewerInstalled'), [OldVersion]), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
end;

procedure InitializeWizard;
begin
  if IsUpdate() then
    WizardForm.WelcomeLabel2.Caption := FmtMessage(CustomMessage('WelcomeUpdate'), [OldVersion, RemoveBackslashUnlessRoot(OldDir)])
  else
    WizardForm.WelcomeLabel2.Caption := CustomMessage('Welcome');
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  // Bei einem Update bleibt der Ordner - nur bei einer Neuinstallation fragen
  Result := (PageID = wpSelectDir) and IsUpdate();
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  D: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    D := WizardForm.DirEdit.Text;
    if (Copy(D, 1, 2) = '\\') or (Length(D) <= 3) then
    begin
      MsgBox(CustomMessage('BadDir'), mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
begin
  Result := CustomMessage('Operation') + NewLine + Space;
  if IsUpdate() then
    Result := Result + FmtMessage(CustomMessage('OpUpdate'), [OldVersion])
  else
    Result := Result + CustomMessage('OpInstall');
  Result := Result + NewLine + NewLine + MemoDirInfo;
  if MemoTasksInfo <> '' then Result := Result + NewLine + NewLine + MemoTasksInfo;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
begin
  // Stilles Update aus dem Programm heraus: laufendes MP3 Organizer beenden, damit die Dateien ersetzt werden koennen.
  // (Interaktiv fragt Inno Setup selbst nach, ob laufende Programme geschlossen werden sollen.)
  if WizardSilent() then
  begin
    Sleep(1500);
    Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM MP3Organizer.exe', '', SW_HIDE, ewWaitUntilTerminated, Code);
    Sleep(500);
  end;
  Result := '';
end;

function RestartAfterSilentUpdate(): Boolean;
begin
  Result := WizardSilent() and (ExpandConstant('{param:RESTARTAPP|0}') = '1');
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
  begin
    WizardForm.FinishedLabel.Caption := CustomMessage('Finished');
    WizardForm.AdjustLabelHeight(WizardForm.FinishedLabel);
    WizardForm.RunList.Top := WizardForm.FinishedLabel.Top + WizardForm.FinishedLabel.Height + ScaleY(12);
  end;
end;

// ---- Deinstallation: Einstellungen und Protokolle auf Wunsch behalten
var
  DeleteData: Boolean;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  DeleteData := False;
  if not UninstallSilent() then
    DeleteData := MsgBox(FmtMessage(CustomMessage('DeleteData'), [ExpandConstant('{localappdata}\MP3 Organizer')]),
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep <> usPostUninstall then Exit;
  if DeleteData then
    DelTree(ExpandConstant('{localappdata}\MP3 Organizer'), True, True, True);
end;
