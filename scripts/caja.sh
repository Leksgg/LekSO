#!/usr/bin/env bash
# Ejecuta un programa dentro de una caja (Bubblewrap) donde solo ve lo que se le concede.
# Sin red, sin acceso a tu carpeta personal y con el sistema en solo lectura.
#
# Uso:
#   caja.sh [--rw CARPETA]... [--ro CARPETA]... [--red] [--wine PREFIJO] -- programa [argumentos]
#
# Ejemplos:
#   caja.sh --rw ~/trabajo -- ls /home/caja
#   caja.sh --wine ~/.wine-juego --ro ~/Descargas -- wine setup.exe
#
# Cada carpeta concedida aparece dentro de la caja en /home/caja/<nombre>.
# En Wine, la unidad Z: solo ve la caja, no tu sistema real.
set -euo pipefail

RW=(); RO=(); RED=0; PREFIJO=""
while [ $# -gt 0 ]; do
  case "$1" in
    --rw)   RW+=("$(realpath "$2")"); shift 2 ;;
    --ro)   RO+=("$(realpath "$2")"); shift 2 ;;
    --red)  RED=1; shift ;;
    --wine) PREFIJO="$(realpath -m "$2")"; shift 2 ;;
    --)     shift; break ;;
    *)      echo "Opción desconocida: $1" >&2; exit 2 ;;
  esac
done
[ $# -gt 0 ] || { echo "Falta el programa. Uso: caja.sh [opciones] -- programa" >&2; exit 2; }

ARGS=(
  --ro-bind /usr /usr --symlink usr/bin /bin --symlink usr/lib /lib --symlink usr/lib64 /lib64
  --ro-bind /etc /etc --proc /proc --dev /dev --tmpfs /tmp --tmpfs /home
  --unshare-all --die-with-parent
)
[ "$RED" -eq 1 ] && ARGS+=(--share-net)

for d in "${RW[@]}"; do ARGS+=(--bind "$d" "/home/caja/$(basename "$d")"); done
for d in "${RO[@]}"; do ARGS+=(--ro-bind "$d" "/home/caja/$(basename "$d")"); done

if [ -n "$PREFIJO" ]; then
  mkdir -p "$PREFIJO"
  ARGS+=(--bind "$PREFIJO" "$PREFIJO" --setenv WINEPREFIX "$PREFIJO"
         --setenv WINEDEBUG -all --setenv WINEDLLOVERRIDES "mscoree,mshtml=")
fi

exec bwrap "${ARGS[@]}" "$@"
