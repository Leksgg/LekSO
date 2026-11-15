#!/usr/bin/env bash
# Prueba del panel: una IA pide, el panel aprueba con la tecla a, la IA escribe, el panel deshace con u.
set -u
cd "$(dirname "$0")"
T=$(mktemp -d); export HOME="$T/casa" XDG_RUNTIME_DIR="$T/run" TERM=xterm; mkdir -p "$HOME/proy" "$XDG_RUNTIME_DIR"; chmod 700 "$XDG_RUNTIME_DIR"
echo original > "$HOME/proy/a.txt"
python3 lekso_ia.py servir > "$T/log" 2>&1 & PID=$!
for i in $(seq 50); do [ -S "$XDG_RUNTIME_DIR/lekso-control.sock" ] && break; sleep 0.1; done
P=$(python3 lekso_ia.py ia pedir "ordenar proyecto" "$HOME/proy:rw" | python3 -c 'import sys,json;print(json.load(sys.stdin)["pid"])')
python3 - "$P" <<'EOF'
import os, pty, sys, time, select
pid, fd = pty.fork()
if pid == 0:
    os.execvp("python3", ["python3", "panel.py"])
def leer(t=1.2):
    fin = time.time() + t; b = b""
    while time.time() < fin:
        if select.select([fd], [], [], 0.1)[0]:
            try: b += os.read(fd, 65536)
            except OSError: break
    return b
leer(); os.write(fd, b"a"); leer(1.5)
EOF
TAREA=$(python3 lekso_ia.py ia estado "$P" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tarea",""))')
[ -n "$TAREA" ] && echo "ok   el panel aprobó la petición ($TAREA)" || echo "FALLA no se aprobó"
python3 lekso_ia.py ia escribir "$TAREA" "$HOME/proy/a.txt" cambiado > /dev/null
python3 - <<'EOF'
import os, pty, time, select
pid, fd = pty.fork()
if pid == 0:
    os.execvp("python3", ["python3", "panel.py"])
def leer(t=1.2):
    fin = time.time() + t; b = b""
    while time.time() < fin:
        if select.select([fd], [], [], 0.1)[0]:
            try: b += os.read(fd, 65536)
            except OSError: break
    return b
leer(); os.write(fd, b"u"); leer(1.5); os.write(fd, b"q"); leer(0.5)
EOF
[ "$(cat "$HOME/proy/a.txt")" = original ] && echo "ok   el panel deshizo la escritura" || echo "FALLA no se deshizo"
kill $PID 2>/dev/null; rm -rf "$T"
