#!/usr/bin/env bash
# Ejecuta un programa dentro de una caja (Bubblewrap) donde solo ve lo que se le concede.
# Sin red, sin acceso a tu carpeta personal y con el sistema en solo lectura.
#
# Uso:
#   caja.sh [--rw CARPETA]... [--ro CARPETA]... [--red] [--gui] [--audio] [--gpu]
#           [--wine PREFIJO] -- programa [argumentos]
#   --gui: ventana en el escritorio (Wayland y Xwayland). --audio: PipeWire/Pulse. --gpu: /dev/dri.
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

RW=(); RO=(); RED=0; PREFIJO=""; GUI=0; AUDIO=0; GPU=0; ESTRICTA=0
while [ $# -gt 0 ]; do
  case "$1" in
    --gui)   GUI=1; shift ;;
    --audio) AUDIO=1; shift ;;
    --gpu)   GPU=1; shift ;;
    --estricta) ESTRICTA=1; shift ;;
    --rw)   RW+=("$(realpath "$2")"); shift 2 ;;
    --ro)   RO+=("$(realpath "$2")"); shift 2 ;;
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
[ "$RED" -eq 1 ] && ARGS+=(--share-net)

# Pantalla, audio y GPU, solo si se piden. Dentro hay un /run/user/UID nuevo y vacío al que
# se añaden únicamente estos sockets. Los sockets del permisor de IA (lekso-ia.sock y
# lekso-control.sock) viven en el XDG_RUNTIME_DIR real y NUNCA se montan en la caja.
RT="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"; DENTRO="/run/user/$(id -u)"
if [ "$GUI" -eq 1 ] || [ "$AUDIO" -eq 1 ]; then ARGS+=(--tmpfs "$DENTRO" --setenv XDG_RUNTIME_DIR "$DENTRO"); fi
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

for d in "${RW[@]}"; do ARGS+=(--bind "$d" "/home/caja/$(basename "$d")"); done
for d in "${RO[@]}"; do ARGS+=(--ro-bind "$d" "/home/caja/$(basename "$d")"); done

if [ -n "$PREFIJO" ]; then
  mkdir -p "$PREFIJO"
  ARGS+=(--bind "$PREFIJO" "$PREFIJO" --setenv WINEPREFIX "$PREFIJO"
         --setenv WINEDEBUG -all --setenv WINEDLLOVERRIDES "mscoree,mshtml=")
fi

if [ "$ESTRICTA" -eq 1 ]; then
  SC="${LEKSO_SECCOMP:-/usr/local/lib/lekso-ia/seccomp-estricta.py}"
  [ -f "$SC" ] || SC="$(dirname "$(realpath "$0")")/seccomp-estricta.py"
  python3 -c "import seccomp" 2>/dev/null || { echo "Falta python3-seccomp para --estricta" >&2; exit 3; }
  exec 9< <(python3 "$SC")
  ARGS+=(--seccomp 9)
fi
exec bwrap "${ARGS[@]}" "$@"
