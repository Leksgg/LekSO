#!/usr/bin/env bash
# Instala el servidor de TeamSpeak 3 en LeksSO (servicio apagado por defecto) y, si se indica, trae los datos de un
# servidor de Windows (base de datos, archivos subidos, claves de consulta).
#
# Uso: sudo leksso-ts3-instalar [--datos CARPETA_DEL_SERVIDOR_DE_WINDOWS]
#
# - Versión fijada (3.13.8) y su suma SHA-256: si lo descargado no coincide, no se instala nada. (El proveedor no publica
#   una suma aparte; esta es la de la descarga oficial por HTTPS del 2026-11-20.)
# - Corre como un usuario propio sin acceso al resto del equipo, sin red salvo lo que se abre con `leksso-ts3 on`.
# - Los datos de origen NO se tocan: se copian a un lugar de trabajo, se cierra el registro de la base de datos (WAL) y
#   se comprueba su integridad antes de usarlos.
set -euo pipefail
VERSION=3.13.8
SHA256=a3c4658e09892d3dbd8ea752d0de42dc7d111bf44d09721927f0f4782496eb2d
URL="https://files.teamspeak-services.com/releases/server/$VERSION/teamspeak3-server_linux_amd64-$VERSION.tar.bz2"
DESTINO=/opt/teamspeak3-server
DATOS=/var/lib/teamspeak3
LOGS=/var/log/teamspeak3

[ "$(id -u)" -eq 0 ] || { echo "Ejecuta con sudo: sudo $0" >&2; exit 1; }
ORIGEN=""
while [ $# -gt 0 ]; do
  case "$1" in
    --datos) ORIGEN="${2:?Indica la carpeta del servidor de Windows}"; shift 2 ;;
    *) echo "Uso: sudo $0 [--datos CARPETA]" >&2; exit 2 ;;
  esac
done
[ -z "$ORIGEN" ] || [ -f "$ORIGEN/ts3server.sqlitedb" ] || { echo "No encuentro ts3server.sqlitedb en $ORIGEN" >&2; exit 1; }

T="$(mktemp -d /var/tmp/leksso-ts3.XXXXXXXX)"; trap 'rm -rf "$T"' EXIT
echo "Descargando TeamSpeak $VERSION…"
curl -fsSL --proto '=https' -o "$T/ts3.tar.bz2" "$URL"
echo "$SHA256  $T/ts3.tar.bz2" | sha256sum -c - >/dev/null || { echo "ERROR: la suma SHA-256 no coincide; no se instala nada." >&2; exit 1; }
echo "Suma SHA-256 correcta."

id teamspeak >/dev/null 2>&1 || useradd --system --home-dir "$DATOS" --shell /usr/sbin/nologin --user-group teamspeak
rm -rf "$DESTINO.nuevo"; mkdir "$DESTINO.nuevo"
tar -xjf "$T/ts3.tar.bz2" -C "$DESTINO.nuevo" --strip-components=1
rm -rf "$DESTINO"; mv "$DESTINO.nuevo" "$DESTINO"
chown -R root:root "$DESTINO"; chmod -R go-w "$DESTINO"
install -d -m 0750 -o teamspeak -g teamspeak "$DATOS" "$LOGS"

if [ -n "$ORIGEN" ]; then
  echo "Preparando los datos de $ORIGEN (el origen no se modifica)…"
  mkdir "$T/datos"
  cp -a "$ORIGEN"/ts3server.sqlitedb* "$T/datos/"
  # la base de Windows estaba en modo WAL: lo escrito recientemente vive en el archivo -wal; se vuelca a la base principal
  python3 - "$T/datos/ts3server.sqlitedb" <<'PY'
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
ok = c.execute("PRAGMA integrity_check").fetchone()[0]
n = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('servers','channels','clients','groups','bans')")}
print("integridad:", ok, "| filas:", n)
sys.exit(0 if ok == "ok" else 1)
PY
  install -m 0640 -o teamspeak -g teamspeak "$T/datos/ts3server.sqlitedb" "$DATOS/ts3server.sqlitedb"
  [ -d "$ORIGEN/files" ] && cp -a "$ORIGEN/files" "$DATOS/files"
  for f in query_ip_allowlist.txt query_ip_denylist.txt licensekey.dat; do
    [ -f "$ORIGEN/$f" ] && install -m 0640 -o teamspeak -g teamspeak "$ORIGEN/$f" "$DATOS/$f"
  done
  [ -f "$ORIGEN/ssh_host_rsa_key" ] && install -m 0600 -o teamspeak -g teamspeak "$ORIGEN/ssh_host_rsa_key" "$DATOS/ssh_host_rsa_key"
  chown -R teamspeak:teamspeak "$DATOS"
fi
[ -f "$DATOS/query_ip_allowlist.txt" ] || printf '127.0.0.1\n::1\n' | install -m 0640 -o teamspeak -g teamspeak /dev/stdin "$DATOS/query_ip_allowlist.txt"
touch "$DATOS/.ts3server_license_accepted"; chown teamspeak:teamspeak "$DATOS/.ts3server_license_accepted"

cat > /etc/systemd/system/teamspeak3.service <<UNIT
[Unit]
Description=Servidor de TeamSpeak 3 (LeksSO, se enciende con «sudo leksso-ts3 on»)
After=network-online.target

[Service]
User=teamspeak
Group=teamspeak
WorkingDirectory=$DATOS
Environment=TS3SERVER_LICENSE=accept
Environment=LD_LIBRARY_PATH=$DESTINO:$DESTINO/redist
ExecStart=$DESTINO/ts3server dbplugin=ts3db_sqlite3 dbpluginparameter= dbsqlpath=$DESTINO/sql/ dbsqlcreatepath=create_sqlite/ logpath=$LOGS licensepath=$DATOS query_ip_allowlist=$DATOS/query_ip_allowlist.txt query_ip_denylist=$DATOS/query_ip_denylist.txt
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=$DATOS $LOGS
UNIT
systemctl daemon-reload
echo "Instalado en $DESTINO, datos en $DATOS. Servicio apagado: sudo leksso-ts3 on para encenderlo."
