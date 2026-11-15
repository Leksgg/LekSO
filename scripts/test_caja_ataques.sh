#!/usr/bin/env bash
# Intenta salir de la caja de varias formas. Cada línea "ok" es un ataque que la caja frena.
# Ejecutar como usuario normal, en la VM o en el equipo: bash scripts/test_caja_ataques.sh
set -u
CAJA="$(dirname "$0")/caja.sh"
T=$(mktemp -d); export XDG_RUNTIME_DIR="$T/run"; mkdir -p "$XDG_RUNTIME_DIR" "$T/proy" "$T/secreto"; chmod 700 "$XDG_RUNTIME_DIR"
echo "CLAVE-PRIVADA" > "$T/secreto/id"; echo "dato" > "$T/proy/a.txt"
ln -s "$T/secreto/id" "$T/proy/enlace"                       # enlace hacia fuera dentro de la carpeta concedida
export SECRETO_API="sk-no-debe-verse"
python3 -c "import socket,os;s=socket.socket(socket.AF_UNIX);s.bind(os.environ['XDG_RUNTIME_DIR']+'/lekso-control.sock');s.listen()" &
PS=$!
python3 -m http.server 8765 --bind 127.0.0.1 >/dev/null 2>&1 & HS=$!
sleep 1
ok=0; mal=0
bien() { ok=$((ok+1)); echo "ok    $1"; }
falla() { mal=$((mal+1)); echo "FALLA $1"; }
# en(): ejecuta en la caja con la carpeta del proyecto en solo lectura
en() { bash "$CAJA" --ro "$T/proy" "$@"; }

[ -z "$(en -- sh -c 'env | grep -c SECRETO_API' | grep -v '^0$')" ] && bien "las variables de entorno no entran (claves de API)" || falla "la caja hereda variables de entorno"
en -- cat "$T/secreto/id" >/dev/null 2>&1 && falla "lee un archivo fuera de la caja por su ruta real" || bien "no ve archivos fuera de lo concedido"
[ "$(en -- cat /home/caja/proy/enlace 2>&1 | grep -c CLAVE)" = 0 ] && bien "un enlace hacia fuera no se sigue" || falla "enlace hacia fuera legible"
en -- sh -c "echo x > /home/caja/proy/n" >/dev/null 2>&1 && falla "escribe en una carpeta de solo lectura" || bien "no escribe en carpetas de solo lectura"
en -- touch /usr/x >/dev/null 2>&1 && falla "escribe en /usr" || bien "no escribe en /usr"
en -- touch /etc/x >/dev/null 2>&1 && falla "escribe en /etc" || bien "no escribe en /etc"
en -- cat /etc/shadow >/dev/null 2>&1 && falla "lee /etc/shadow" || bien "no lee /etc/shadow"
en -- python3 -c "import socket;socket.create_connection(('127.0.0.1',8765),2)" >/dev/null 2>&1 && falla "tiene red sin --red" || bien "sin red por defecto"
bash "$CAJA" --red -- python3 -c "import socket;socket.create_connection(('127.0.0.1',8765),2)" >/dev/null 2>&1 && bien "con --red sí hay red (control)" || bien "con --red: red aislada igualmente (loopback propio)"
for opc in "" "--gui --audio --gpu"; do
  en $opc -- sh -c "ls $XDG_RUNTIME_DIR/lekso-control.sock /run/user/$(id -u)/lekso-control.sock /run/user/$(id -u)/lekso-ia.sock" >/dev/null 2>&1 \
    && falla "el socket del permisor es visible (opciones: ${opc:-ninguna})" || bien "el socket del permisor no es visible (opciones: ${opc:-ninguna})"
done
[ "$(en -- sh -c 'ls /proc | grep -c "^[0-9]"')" -le 4 ] && bien "no ve los procesos del sistema" || falla "ve procesos ajenos"
[ -z "$(en -- ls /home | grep -v '^caja$')" ] && bien "solo existe /home/caja" || falla "ve otras carpetas en /home"
en -- ls /dev/dri >/dev/null 2>&1 && falla "ve la GPU sin --gpu" || bien "sin GPU por defecto"
en -- sh -c 'ls /proc/1/root/home | grep -v "^caja$" | head -1' 2>/dev/null | grep -q . && falla "se sale por /proc/1/root" || bien "/proc/1/root no lleva al sistema real"
en -- unshare -r true >/dev/null 2>&1 && echo "info  la caja permite crear espacios de usuario anidados (mitigar con seccomp)" || bien "no se crean espacios de usuario anidados"
if python3 -c "import seccomp" 2>/dev/null; then
  en --estricta -- unshare -r true >/dev/null 2>&1 && falla "--estricta permite espacios de usuario" || bien "--estricta: sin espacios de usuario anidados"
  en --estricta -- python3 -c "import ctypes;l=ctypes.CDLL(None,use_errno=True);import sys;sys.exit(0 if l.ptrace(0,0,0,0)==-1 else 1)" >/dev/null 2>&1 && bien "--estricta: ptrace denegado" || falla "--estricta: ptrace permitido"
  [ "$(en --estricta -- sh -c "echo funciona")" = funciona ] && bien "--estricta: los programas normales siguen funcionando" || falla "--estricta rompe programas normales"
else echo "info  sin python3-seccomp: se omite --estricta"; fi
en -- python3 -c "import os;os.setuid(0)" >/dev/null 2>&1 && bien "(info) setuid(0) no cambia nada fuera de su espacio" || bien "setuid(0) denegado"
if command -v script >/dev/null; then
  script -qec "bash $CAJA -- python3 -c \"import fcntl,termios;fcntl.ioctl(0,termios.TIOCSTI,b'x')\"" /dev/null >/dev/null 2>&1 \
    && falla "inyecta teclas en la terminal (TIOCSTI)" || bien "no puede inyectar teclas en la terminal"
fi
kill $PS $HS 2>/dev/null; rm -rf "$T"
echo; echo "$ok bien, $mal mal"; [ "$mal" = 0 ]
