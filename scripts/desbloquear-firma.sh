#!/usr/bin/env bash
# Desbloquea la clave de firma de LekSO durante unas horas, para poder publicar versiones sin escribir la
# contraseña cada vez. La contraseña se escribe aquí, una vez, y no se guarda en ningún archivo:
# la clave queda cargada en un agente propio que se cierra solo al pasar el tiempo (o al reiniciar).
#
# Uso: scripts/desbloquear-firma.sh [horas]      (por defecto, 8)
# Cerrar antes de tiempo: scripts/desbloquear-firma.sh cerrar
set -euo pipefail

SOCK="${LEKSO_AGENTE:-$HOME/.ssh/lekso-agent.sock}"
CLAVE="${LEKSO_CLAVE_FIRMA:-$HOME/.ssh/lekso_release}"
[ -f "$CLAVE" ] || { echo "No encuentro la clave de firma: $CLAVE" >&2; exit 1; }

PIDF="$SOCK.pid"
if [ "${1:-}" = "cerrar" ]; then
  if [ -f "$PIDF" ]; then kill "$(cat "$PIDF")" >/dev/null 2>&1 || true; fi
  rm -f "$SOCK" "$PIDF"
  echo "Clave cerrada."
  exit 0
fi

HORAS="${1:-8}"
[[ "$HORAS" =~ ^[0-9]+$ ]] || { echo "Uso: $0 [horas|cerrar]" >&2; exit 2; }

# ¿Hay ya un agente vivo en ese socket? (ssh-add -l: 0 = con claves, 1 = vacío, 2 = no responde)
set +e
SSH_AUTH_SOCK="$SOCK" ssh-add -l >/dev/null 2>&1
ESTADO=$?
set -e
if [ "$ESTADO" -eq 2 ]; then
  rm -f "$SOCK"
  # ssh-agent imprime SSH_AGENT_PID=NNN; se guarda para poder cerrarlo después
  ssh-agent -a "$SOCK" -t "${HORAS}h" | sed -n 's/^SSH_AGENT_PID=\([0-9]*\);.*/\1/p' > "$PIDF"
fi
SSH_AUTH_SOCK="$SOCK" ssh-add -t "${HORAS}h" "$CLAVE"
echo "Clave de firma desbloqueada durante ${HORAS} h. Ya se pueden publicar versiones."
