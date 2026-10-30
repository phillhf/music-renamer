; Wird in GitHub Actions gebaut: iscc /DAppVersion=1.2.3 installer\mp3-organizer.iss
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{7C1E2F64-6B0A-4D38-9E52-3F0B7D41A9C6}
AppName=MP3 Organizer
AppVersion={#AppVersion}
AppPublisher=phillhf
AppPublisherURL=https://github.com/phillhf/mp3-organizer
DefaultDirName={autopf}\MP3 Organizer
DefaultGroupName=MP3 Organizer
DisableProgramGroupPage=yes
; Ohne Adminrechte, damit Updates ohne Rückfrage durchlaufen
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=MP3-Organizer-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\MP3Organizer.exe
LicenseFile=..\LICENSE

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Verknüpfung auf dem Desktop"; Flags: unchecked

[Files]
Source: "..\dist\MP3Organizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MP3 Organizer"; Filename: "{app}\MP3Organizer.exe"
Name: "{autodesktop}\MP3 Organizer"; Filename: "{app}\MP3Organizer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MP3Organizer.exe"; Description: "MP3 Organizer starten"; Flags: nowait postinstall skipifsilent
; Beim stillen Update startet die neue Version von selbst
Filename: "{app}\MP3Organizer.exe"; Flags: nowait; Check: WizardSilent
