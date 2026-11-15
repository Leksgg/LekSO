#!/usr/bin/env bash
# Prueba de extremo a extremo del permisor con sockets reales y una casa aislada.
set -u
cd "$(dirname "$0")"
T=$(mktemp -d); export HOME="$T/casa" XDG_RUNTIME_DIR="$T/run"; mkdir -p "$HOME/proy" "$XDG_RUNTIME_DIR"; chmod 700 "$XDG_RUNTIME_DIR"
echo "clave" > "$HOME/secreto.txt"; echo original > "$HOME/proy/a.txt"
python3 lekso_ia.py servir > "$T/log" 2>&1 & PID=$!
for i in $(seq 50); do [ -S "$XDG_RUNTIME_DIR/lekso-control.sock" ] && break; sleep 0.1; done
ok=0; mal=0
chk() { if [ "$1" = "$2" ]; then ok=$((ok+1)); echo "ok   $3"; else mal=$((mal+1)); echo "FALLA $3 (esperado '$2', salió '$1')"; fi; }
L() { python3 lekso_ia.py "$@"; }
PID_P=$(L ia pedir "editar proyecto" "$HOME/proy:rwd" | python3 -c 'import sys,json;print(json.load(sys.stdin)["pid"])')
chk "$(L ia estado "$PID_P" | grep -c pendiente)" 1 "la petición queda pendiente"
echo s | L aprobar "$PID_P" -r > /dev/null
TAREA=$(L ia estado "$PID_P" | python3 -c 'import sys,json;print(json.load(sys.stdin)["tarea"])')
chk "$(L ia leer "$TAREA" "$HOME/proy/a.txt" | grep -c original)" 1 "lee dentro del alcance"
chk "$(L ia leer "$TAREA" "$HOME/secreto.txt" | grep -c 'fuera del alcance')" 1 "rechaza fuera del alcance"
L ia escribir "$TAREA" "$HOME/proy/a.txt" "cambiado" > /dev/null
chk "$(cat "$HOME/proy/a.txt")" cambiado "escribe"
L ia borrar "$TAREA" "$HOME/proy/a.txt" > /dev/null
chk "$(ls "$HOME/proy" | wc -l)" 0 "borra a la papelera"
chk "$(ls "$HOME/.local/share/Trash/files" | wc -l)" 1 "está en la papelera estándar"
L deshacer-tarea "$TAREA" > /dev/null
chk "$(cat "$HOME/proy/a.txt")" original "deshacer tarea restaura todo"
# la IA no puede aprobar: el socket de control es otro y no se le da
chk "$(L ia aprobar x 2>&1 | grep -c 'desconocida')" 1 "la IA no tiene operación de aprobar"
# carpeta recordada: segunda petición se aprueba sola
chk "$(L ia pedir "otra" "$HOME/proy:rw" | grep -c aprobada)" 1 "carpeta recordada se aprueba sola"
# pero nunca con permisos mayores que los recordados ni con nube
chk "$(L ia pedir "nube" "$HOME/proy:rw" | grep -c aprobada)" 1 "(control) local ok"
chk "$(L ia --nube pedir "n" "$HOME/proy:rw" | grep -c pendiente)" 1 "por el canal nube siempre pregunta"
chk "$(stat -c %a "$XDG_RUNTIME_DIR/lekso-control.sock")" 600 "socket de control 0600"
echo; echo "registro:"; L registro 8
kill $PID 2>/dev/null; rm -rf "$T"
echo; echo "$ok bien, $mal mal"; [ "$mal" = 0 ]
