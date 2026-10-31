#!/bin/bash
# Baut dist/Music Renamer.app und dist/Music-Renamer-<Version>-macOS-<arm64|intel>.dmg.
# Laeuft nur auf einem Mac und baut fuer dessen Prozessor. tools/fpcalc ist optional.
# Aufruf aus dem Projektordner:  bash installer/build_mac.sh
set -euo pipefail
cd "$(dirname "$0")/.."

version=$(python -c "import musicrenamer; print(musicrenamer.__version__)")
arch=$([ "$(uname -m)" = arm64 ] && echo arm64 || echo intel)
echo "Baue Music Renamer $version fuer $arch"

extra=()
if [ -f tools/fpcalc ]; then
    extra=(--add-binary "$PWD/tools/fpcalc:.")
else
    echo "tools/fpcalc fehlt, Build ohne Klangerkennung" >&2
fi

# Die mitgelieferte Bash 3.2 lehnt ein leeres "${extra[@]}" unter set -u ab
python -m PyInstaller --noconfirm --windowed --name "Music Renamer" \
    --osx-bundle-identifier io.github.phillhf.musicrenamer \
    --icon "$PWD/installer/app.icns" --collect-all tkinterdnd2 ${extra[@]+"${extra[@]}"} \
    --distpath dist --workpath build/pyinstaller --specpath build app.py

app="dist/Music Renamer.app"
plutil -replace CFBundleShortVersionString -string "$version" "$app/Contents/Info.plist"
plutil -replace CFBundleVersion -string "$version" "$app/Contents/Info.plist"
# Die Aenderung macht die Signatur ungueltig; Apple Silicon startet nichts Unsigniertes
codesign --force --deep --sign - "$app"

stage=build/dmg
rm -rf "$stage"
mkdir -p "$stage"
cp -R "$app" "$stage/"
ln -s /Applications "$stage/Applications"

dmg="dist/Music-Renamer-$version-macOS-$arch.dmg"
hdiutil create -volname "Music Renamer" -srcfolder "$stage" -ov -format UDZO "$dmg"
(cd dist && shasum -a 256 "$(basename "$dmg")" > "$(basename "$dmg").sha256")
ls -lh "$dmg"
