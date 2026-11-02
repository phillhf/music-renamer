#!/bin/sh
# Installiert die Pakete aus /pakete in einem frischen System und prüft sie dort.
# Läuft im Container, siehe .github/workflows/release.yml
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
arch=$(dpkg --print-architecture)

# Zuerst die Befehlszeile allein: sie muss ohne Grafik auskommen
apt-get install -y -qq /pakete/music-renamer-cli_*"_$arch.deb" > /dev/null
if find /opt/music-renamer-cli | grep -E 'libtk|libtcl|libX11'; then
    echo "Grafikbibliotheken im Befehlszeilen-Paket" >&2
    exit 1
fi
if dpkg -s libx11-6 > /dev/null 2>&1 && [ "$arch" = amd64 ]; then
    echo "Befehlszeilen-Paket zieht Grafik nach" >&2
    exit 1
fi
music-renamer-cli --selftest
music-renamer-cli --help > /dev/null
mkdir -p /tmp/leer
music-renamer-cli umbenennen /tmp/leer
test -d "$HOME/.local/share/Music Renamer"

apt-get install -y -qq /pakete/music-renamer_*"_$arch.deb" xvfb xauth imagemagick > /dev/null
test -f /usr/share/applications/music-renamer.desktop
xvfb-run -a music-renamer --selftest
xvfb-run -a -s "-screen 0 1000x800x24" sh -c '
    music-renamer & pid=$!
    sleep 10
    import -window root "/pakete/fenster-linux-'"$arch"'.png"
    kill -0 "$pid"
    kill "$pid"
'
apt-get remove -y -qq music-renamer music-renamer-cli > /dev/null
test ! -e /opt/music-renamer/music-renamer
echo "Pakete in Ordnung"
