# Baut dist\MusicRenamer (PyInstaller) und dist\Music-Renamer-Setup-<Version>.exe (Inno Setup 6).
# Die Version kommt ausschliesslich aus musicrenamer\__init__.py (__version__ = "x.y.z").
# Aufruf aus dem Projektordner:  powershell -ExecutionPolicy Bypass -File installer\build.ps1 [-SkipTests]

param([switch]$SkipTests)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$src = Get-Content "musicrenamer\__init__.py" -Raw
if ($src -notmatch '__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"') { throw "__version__ in musicrenamer\__init__.py nicht gefunden" }
$version = "$($Matches[1]).$($Matches[2]).$($Matches[3])"
$tuple = "($($Matches[1]), $($Matches[2]), $($Matches[3]), 0)"
Write-Host "Baue Music Renamer $version"

$python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

if (-not $SkipTests) {
    & $python -m unittest discover -s tests
    if ($LASTEXITCODE -ne 0) { throw "Tests fehlgeschlagen" }
}

# Versionsinfo fuer die Dateieigenschaften der EXE
New-Item -ItemType Directory -Force build | Out-Null
@"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=$tuple, prodvers=$tuple, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040704B0', [
      StringStruct('CompanyName', 'phillhf'),
      StringStruct('FileDescription', 'Music Renamer - Musiksammlung aufraeumen'),
      StringStruct('FileVersion', '$version'),
      StringStruct('InternalName', 'MusicRenamer'),
      StringStruct('LegalCopyright', 'GPL-3.0 - phillhf'),
      StringStruct('OriginalFilename', 'MusicRenamer.exe'),
      StringStruct('ProductName', 'Music Renamer'),
      StringStruct('ProductVersion', '$version')])]),
    VarFileInfo([VarStruct('Translation', [1031, 1200])])
  ]
)
"@ | Set-Content "build\version_info.txt" -Encoding utf8

# fpcalc ist optional: ohne es fehlt nur die Erkennung am Klang
$extra = @()
if (Test-Path "tools\fpcalc.exe") { $extra = @("--add-binary", "$root\tools\fpcalc.exe;.") }
else { Write-Warning "tools\fpcalc.exe fehlt, Build ohne Klangerkennung" }

& $python -m PyInstaller --noconfirm --windowed --name MusicRenamer `
    --icon "$root\installer\app.ico" --add-data "$root\installer\app.ico;." --collect-all tkinterdnd2 --version-file "$root\build\version_info.txt" `
    @extra --distpath dist --workpath build\pyinstaller --specpath build app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fehlgeschlagen" }

$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 nicht gefunden (winget install JRSoftware.InnoSetup)" }

& $iscc /Q "/DAppVersion=$version" installer\MusicRenamer.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup fehlgeschlagen" }

$setup = Get-Item "dist\Music-Renamer-Setup-$version.exe"
$hash = (Get-FileHash $setup -Algorithm SHA256).Hash.ToLower()
"$hash  $($setup.Name)" | Set-Content "$($setup.FullName).sha256" -NoNewline -Encoding ascii
Write-Host ("{0,-36} {1,6:N1} MB" -f $setup.Name, ($setup.Length / 1MB))
