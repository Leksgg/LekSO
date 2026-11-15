#!/usr/bin/env bash
# La IA dentro de su caja (--ia): solo llega a tus archivos a través del permisor.
# Ejecutar como usuario normal: bash scripts/test_caja_ia.sh
set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"; CAJA="$AQUI/caja.sh"; IA="$AQUI/../lekso-ia"
T=$(mktemp -d); export HOME="$T/casa" XDG_RUNTIME_DIR="$T/run"
mkdir -p "$HOME/proy" "$HOME/privado" "$XDG_RUNTIME_DIR"; chmod 700 "$XDG_RUNTIME_DIR"
echo "hola" > "$HOME/proy/a.txt"; echo "CLAVE" > "$HOME/privado/secreto.txt"
python3 "$IA/lekso_ia.py" servir > "$T/log" 2>&1 & PID=$!
for i in $(seq 50); do [ -S "$XDG_RUNTIME_DIR/lekso-control.sock" ] && [ -S "$XDG_RUNTIME_DIR/lekso-ia-nube.sock" ] && break; sleep 0.1; done
ok=0; mal=0
bien() { ok=$((ok+1)); echo "ok    $1"; }
falla() { mal=$((mal+1)); echo "FALLA $1"; }
LIA='python3 /home/caja/lekso-ia/lekso_ia.py'
caja_ia() { bash "$CAJA" "$@"; }                         # caja_ia --ia -- programa
dentro() { caja_ia --ia --ro "$IA" -- "$@"; }
campo() { python3 -c "import sys,json;print(json.load(sys.stdin).get('$1',''))"; }

PIDP=$(dentro sh -c "$LIA ia pedir ordenar $HOME/proy:rw" | campo pid)
[ -n "$PIDP" ] && bien "la IA, desde su caja, llega al permisor y pide permiso" || falla "la IA no llega al permisor"
echo s | python3 "$IA/lekso_ia.py" aprobar "$PIDP" >/dev/null
TAREA=$(dentro sh -c "$LIA ia estado $PIDP" | campo tarea)
[ -n "$TAREA" ] && bien "tras aprobar fuera de la caja, la IA recibe su tarea" || falla "sin tarea"

dentro sh -c "$LIA ia leer $TAREA $HOME/proy/a.txt" | grep -q hola && bien "lee un archivo concedido a través del permisor" || falla "no lee por el permisor"
dentro cat "$HOME/proy/a.txt" >/dev/null 2>&1 && falla "la IA lee el archivo directamente" || bien "no puede leer el archivo directamente: su ruta real no existe en la caja"
dentro sh -c "$LIA ia leer $TAREA $HOME/privado/secreto.txt" | grep -q "fuera del alcance" && bien "lo no concedido lo rechaza el permisor" || falla "lee fuera del alcance"
dentro sh -c "$LIA ia escribir $TAREA $HOME/proy/n.txt nuevo" >/dev/null; [ "$(cat "$HOME/proy/n.txt" 2>/dev/null)" = nuevo ] && bien "escribe dentro de lo concedido" || falla "no escribe"
dentro sh -c "$LIA pendientes" >/dev/null 2>&1 && falla "la IA llega al socket de control" || bien "el socket de control no existe dentro de la caja"
dentro sh -c "ls \$XDG_RUNTIME_DIR" | grep -q control && falla "el control es visible" || bien "dentro solo hay el socket de su canal"
dentro sh -c "ls \$XDG_RUNTIME_DIR/lekso-ia-nube.sock" >/dev/null 2>&1 && falla "una IA local ve el canal nube" || bien "una IA local no ve el canal de la nube"
dentro sh -c "$LIA ia aprobar $PIDP" | grep -q "desconocida" && bien "no existe operación de aprobar en el canal de la IA" || falla "la IA puede aprobar"
dentro sh -c "env | grep -c HOME=/home/caja" | grep -q 1 && bien "la IA no hereda el entorno del usuario" || falla "entorno heredado"

# canal nube: aunque la carpeta esté recordada, siempre pregunta
echo s | python3 "$IA/lekso_ia.py" aprobar "$(dentro sh -c "$LIA ia pedir otra $HOME/proy:r" | campo pid)" -r >/dev/null 2>&1
caja_ia --ia-nube --ro "$IA" -- sh -c "$LIA ia pedir nube $HOME/proy:r" | grep -q pendiente && bien "una IA en la nube siempre pregunta, aunque la carpeta esté recordada" || falla "la nube se aprobó sola"
caja_ia --ia-nube --ro "$IA" -- sh -c "ls \$XDG_RUNTIME_DIR/lekso-ia.sock" >/dev/null 2>&1 && falla "una IA en la nube ve el canal local" || bien "una IA en la nube no ve el canal local"
caja_ia --ia --ia-nube -- true >/dev/null 2>&1 && falla "se aceptan los dos canales a la vez" || bien "no se mezclan canales"
kill "$PID" 2>/dev/null; rm -f "$XDG_RUNTIME_DIR"/*.sock
caja_ia --ia -- true >/dev/null 2>&1 && falla "arranca sin permisor" || bien "sin permisor en marcha, --ia se niega a arrancar"
rm -rf "$T"
echo; echo "$ok bien, $mal mal"; [ "$mal" = 0 ]
