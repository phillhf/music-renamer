#!/bin/bash
# Baut dist/music-renamer_<Version>_<Architektur>.deb (Fenster) und music-renamer-cli_... (Befehlszeile).
# Das Programm läuft nur auf Systemen mit mindestens der glibc des Build-Rechners.
# Aufruf aus dem Projektordner:  bash installer/build_deb.sh
set -euo pipefail
cd "$(dirname "$0")/.."

version=$(python -c "import musicrenamer; print(musicrenamer.__version__)")
arch=$(dpkg --print-architecture)
echo "Baue Music Renamer $version fuer $arch"

extra=()
recommends=""
if [ -f tools/fpcalc ]; then
    extra=(--add-binary "$PWD/tools/fpcalc:.")
else
    recommends="libchromaprint-tools"
    echo "tools/fpcalc fehlt, die Klangerkennung kommt aus libchromaprint-tools" >&2
fi

freeze() {
    python -m PyInstaller --noconfirm --distpath build/linux --workpath build/pyinstaller --specpath build \
        ${extra[@]+"${extra[@]}"} "$@"
}
freeze --name music-renamer --collect-all tkinterdnd2 app.py
freeze --name music-renamer-cli --exclude-module tkinter --exclude-module tkinterdnd2 cli_app.py

package() {  # Paketname, Depends, Recommends, Kurzbeschreibung; legt Zusatzdateien vorher nach build/deb/<Paket>
    local name=$1 depends=$2 recommends=$3 summary=$4
    local root="build/deb/$name"
    mkdir -p "$root/DEBIAN" "$root/opt" "$root/usr/bin" "$root/usr/share/doc/$name"
    cp -R "build/linux/$name" "$root/opt/$name"
    ln -s "/opt/$name/$name" "$root/usr/bin/$name"
    cat > "$root/usr/share/doc/$name/copyright" <<EOF
Music Renamer, https://github.com/phillhf/music-renamer
Lizenz: GPL-3.0-or-later, Volltext in /usr/share/common-licenses/GPL-3
EOF
    {
        echo "Package: $name"
        echo "Version: $version"
        echo "Architecture: $arch"
        echo "Maintainer: phillhf <181326255+phillhf@users.noreply.github.com>"
        echo "Installed-Size: $(du -sk "$root" | cut -f1)"
        echo "Depends: $depends"
        [ -z "$recommends" ] || echo "Recommends: $recommends"
        echo "Section: sound"
        echo "Priority: optional"
        echo "Homepage: https://github.com/phillhf/music-renamer"
        echo "Description: $summary"
        echo " Sortiert Dubletten aus, ergaenzt Metadaten, Cover und Songtexte und"
        echo " benennt Dateien einheitlich um."
    } > "$root/DEBIAN/control"
    chmod -R u=rwX,go=rX "$root"
    dpkg-deb --root-owner-group -Zxz --build "$root" "dist/${name}_${version}_${arch}.deb"
    (cd dist && sha256sum "${name}_${version}_${arch}.deb" > "${name}_${version}_${arch}.deb.sha256")
}

rm -rf build/deb
mkdir -p dist

desktop=build/deb/music-renamer/usr/share
mkdir -p "$desktop/applications" "$desktop/icons/hicolor/256x256/apps"
cp installer/app_256.png "$desktop/icons/hicolor/256x256/apps/music-renamer.png"
cat > "$desktop/applications/music-renamer.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Music Renamer
Comment=Musiksammlung aufräumen
Exec=music-renamer
Icon=music-renamer
Terminal=false
Categories=AudioVideo;Audio;
StartupWMClass=Music-renamer
EOF

package music-renamer "ca-certificates, xdg-utils, fonts-dejavu-core" \
    "${recommends:+$recommends, }pkexec | policykit-1" "Musiksammlung aufraeumen"
package music-renamer-cli "ca-certificates" "$recommends" "Musiksammlung aufraeumen, Befehlszeile"
ls -lh dist/*.deb
