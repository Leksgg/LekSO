#!/usr/bin/env bash
# Ejecuta un programa dentro de una caja (Bubblewrap) donde solo ve lo que se le concede.
# Sin red (o con red PROPIA vía pasta si se pide --red), sin acceso a tu carpeta personal y con el sistema en solo lectura.
#
# Uso:
#   caja.sh [--rw CARPETA]... [--ro CARPETA]... [--env VAR=VALOR]... [--red] [--gui] [--audio] [--gpu]
#           [--wine PREFIJO] -- programa [argumentos]
#   --gui: ventana en el escritorio (Wayland y Xwayland). --audio: PipeWire/Pulse. --gpu: /dev/dri.
#   --ia: caja para una IA local; solo ve el socket del permisor (leksso-ia.sock) y pide permiso para todo.
#   --ia-nube: igual para una IA en la nube (usa el canal «nube», que siempre pregunta); necesita --red.
#   --estricta: filtro seccomp para programas NO fiables (sin espacios de usuario, mount, ptrace, bpf...).
#               No sirve para Steam ni los juegos, que los necesitan.
#
# Ejemplos:
#   caja.sh --rw ~/trabajo -- ls /home/caja
#   caja.sh --wine ~/.wine-juego --ro ~/Descargas -- wine setup.exe
#
# Cada carpeta concedida aparece dentro de la caja en /home/caja/<nombre>.
# En Wine, la unidad Z: solo ve la caja, no tu sistema real.
set -euo pipefail

RW=(); RO=(); ENV=(); RED=0; PREFIJO=""; GUI=0; AUDIO=0; GPU=0; ESTRICTA=0; IA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --ia)      [ -z "$IA" ] || { echo "Usa --ia o --ia-nube, no los dos" >&2; exit 2; }; IA="leksso-ia.sock"; shift ;;
    --ia-nube) [ -z "$IA" ] || { echo "Usa --ia o --ia-nube, no los dos" >&2; exit 2; }; IA="leksso-ia-nube.sock"; shift ;;
    --ia-asistente) [ -z "$IA" ] || { echo "Usa una sola opción --ia" >&2; exit 2; }
               case "$2" in ""|*[!a-z]*) echo "Nombre de asistente no válido: $2" >&2; exit 2 ;; esac
               IA="leksso-ia-$2.sock"; shift 2 ;;
    --gui)   GUI=1; shift ;;
    --audio) AUDIO=1; shift ;;
    --gpu)   GPU=1; shift ;;
    --estricta) ESTRICTA=1; shift ;;
    --rw)   RW+=("$(realpath "$2")"); shift 2 ;;
    --ro)   RO+=("$(realpath "$2")"); shift 2 ;;
    --env)  case "${2%%=*}" in ""|[0-9]*|*[!A-Za-z0-9_]*) echo "Nombre de variable no válido: $2" >&2; exit 2 ;; esac
            ENV+=(--setenv "${2%%=*}" "${2#*=}"); shift 2 ;;
    --red)  RED=1; shift ;;
    --wine) PREFIJO="$(realpath -m "$2")"; shift 2 ;;
    --)     shift; break ;;
    *)      echo "Opción desconocida: $1" >&2; exit 2 ;;
  esac
done
[ $# -gt 0 ] || { echo "Falta el programa. Uso: caja.sh [opciones] -- programa" >&2; exit 2; }

# --clearenv: la caja NO hereda tus variables de entorno (claves de API, tokens, rutas).
# --new-session: sin terminal de control, para que nada dentro inyecte teclas en tu terminal (TIOCSTI).
# --cap-drop ALL: sin ninguna capacidad de Linux, ni siquiera dentro de su propio espacio.
ARGS=(
  --clearenv --setenv PATH /usr/local/bin:/usr/bin:/bin --setenv HOME /home/caja
  --setenv LANG "${LANG:-C.UTF-8}" --setenv TERM "${TERM:-xterm}"
  --ro-bind /usr /usr --symlink usr/bin /bin --symlink usr/lib /lib --symlink usr/lib64 /lib64
  --ro-bind /etc /etc --proc /proc --dev /dev --tmpfs /tmp --tmpfs /home --dir /home/caja
  --unshare-all --die-with-parent --new-session --cap-drop ALL
)
# Con --red la caja tiene su PROPIA red (pasta: sale a Internet, pero no ve los sockets locales ni los servicios
# en localhost del equipo). Compartir la red del equipo daría acceso a los sockets «abstractos» (por ejemplo el de
# instancia única de kitty) y a todo lo que escuche en 127.0.0.1. Sin pasta se avisa y se comparte, como antes.
PREFIJO_RED=()
if [ "$RED" -eq 1 ]; then
  ARGS+=(--share-net)                     # dentro de la red que prepara pasta (o la del equipo si no hay pasta)
  if [ "${LEKSSO_CAJA_RED_COMPARTIDA:-0}" = 1 ]; then
    echo "AVISO: la caja comparte la red del equipo (sockets locales y servicios en localhost incluidos)." >&2
  elif command -v pasta >/dev/null 2>&1; then
    PREFIJO_RED=(pasta --config-net --quiet -t none -u none -T none -U none --no-map-gw --)   # sin reenvío de puertos en ningún sentido
  else
    # Cerrada por defecto: sin pasta NO se arranca la caja con red (antes se compartía la del equipo en silencio).
    echo "ERROR: falta pasta (paquete passt): la caja con red no se arranca sin una red propia. Instálalo con «sudo apt install passt»." >&2
    echo "       (Solo si aceptas que la caja vea la red del equipo: LEKSSO_CAJA_RED_COMPARTIDA=1.)" >&2
    exit 5
  fi
fi

# Pantalla, audio y GPU, solo si se piden. Dentro hay un /run/user/UID nuevo y vacío al que
# se añaden únicamente estos sockets. Los sockets del permisor de IA (leksso-ia.sock y
# leksso-control.sock) viven en el XDG_RUNTIME_DIR real y NUNCA se montan en la caja.
RT="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"; DENTRO="/run/user/$(id -u)"
if [ "$GUI" -eq 1 ] || [ "$AUDIO" -eq 1 ] || [ -n "$IA" ]; then ARGS+=(--tmpfs "$DENTRO" --setenv XDG_RUNTIME_DIR "$DENTRO"); fi
# --ia / --ia-nube: la caja de una IA. Dentro entra SOLO el socket de su canal; el de control nunca.
# La IA no ve tus archivos: su único camino a ellos es pedir permiso al permisor.
if [ -n "$IA" ]; then
  [ -S "$RT/$IA" ] || { echo "El permisor no está en marcha (no existe $RT/$IA)" >&2; exit 4; }
  ARGS+=(--bind "$RT/$IA" "$DENTRO/$IA")
fi
if [ "$GUI" -eq 1 ]; then
  WL="${WAYLAND_DISPLAY:-wayland-1}"
  [ -S "$RT/$WL" ] && ARGS+=(--bind "$RT/$WL" "$DENTRO/$WL" --setenv WAYLAND_DISPLAY "$WL")
  if [ -d /tmp/.X11-unix ]; then      # Xwayland, que necesita Wine
    ARGS+=(--ro-bind /tmp/.X11-unix /tmp/.X11-unix --setenv DISPLAY "${DISPLAY:-:0}")
  fi
fi
if [ "$AUDIO" -eq 1 ]; then
  [ -S "$RT/pipewire-0" ] && ARGS+=(--bind "$RT/pipewire-0" "$DENTRO/pipewire-0")
  [ -S "$RT/pulse/native" ] && ARGS+=(--bind "$RT/pulse/native" "$DENTRO/pulse/native" --setenv PULSE_SERVER "unix:$DENTRO/pulse/native")
fi
[ "$GPU" -eq 1 ] && [ -d /dev/dri ] && ARGS+=(--dev-bind /dev/dri /dev/dri)

[ "${#ENV[@]}" -gt 0 ] && ARGS+=("${ENV[@]}")
for d in "${RW[@]}"; do ARGS+=(--bind "$d" "/home/caja/$(basename "$d")"); done
for d in "${RO[@]}"; do ARGS+=(--ro-bind "$d" "/home/caja/$(basename "$d")"); done

if [ -n "$PREFIJO" ]; then
  mkdir -p "$PREFIJO"
  ARGS+=(--bind "$PREFIJO" "$PREFIJO" --setenv WINEPREFIX "$PREFIJO"
         --setenv WINEDEBUG -all --setenv WINEDLLOVERRIDES "mscoree,mshtml=")
fi

if [ "$ESTRICTA" -eq 1 ]; then
  SC="${LEKSSO_SECCOMP:-/usr/local/lib/leksso-ia/seccomp-estricta.py}"
  [ -f "$SC" ] || SC="$(dirname "$(realpath "$0")")/seccomp-estricta.py"
  python3 -c "import seccomp" 2>/dev/null || { echo "Falta python3-seccomp para --estricta" >&2; exit 3; }
  ARGS+=(--seccomp 9)
  if [ "${#PREFIJO_RED[@]}" -gt 0 ]; then
    # pasta cierra los descriptores que hereda: el filtro se abre DENTRO, justo antes de lanzar bwrap, para que el
    # descriptor 9 llegue de verdad a bwrap (si no, bwrap fallaría y la caja no arrancaría: nunca sin filtro).
    exec "${PREFIJO_RED[@]}" bash -c 'exec 9< <(python3 "$1") || exit 1; shift; exec bwrap "$@"' _ "$SC" "${ARGS[@]}" "$@"
  fi
  exec 9< <(python3 "$SC")
fi
exec "${PREFIJO_RED[@]}" bwrap "${ARGS[@]}" "$@"
