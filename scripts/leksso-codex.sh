#!/bin/sh
# Codex CLI dentro de la caja de IA en la nube, conectado al permisor de LeksSO.
#
# - Corre en `caja --ia-nube --red`: no ve tus archivos; su único camino a ellos es el permisor.
# - Sus herramientas propias (shell, editar) actúan solo dentro de la caja, sobre una carpeta vacía y suya:
#   no alcanzan tu equipo. Por eso se desactiva su sandbox interno, que no funciona anidado en la caja.
# - Su sesión y ajustes viven en una carpeta aparte (~/.leksso/codex), que es lo único que ve de tu usuario.
# Uso: leksso-codex [argumentos de codex]
if ! command -v codex >/dev/null 2>&1; then
  echo "Codex no está instalado todavía. Se instala ahora (necesita conexión y tu contraseña)."
  leksso-asistente instalar codex || exit 1
fi
CASA="${LEKSSO_CODEX_CASA:-$HOME/.leksso/codex}"
mkdir -p "$CASA" && chmod 700 "$CASA"
NOTA='Estás en LeksSO, dentro de una caja: tu carpeta (/home/caja) NO es la del usuario. Para tocar sus archivos usa solo las herramientas del servidor MCP «leksso», con rutas del equipo real. Cada acción pasa por el permisor, que pide permiso al usuario.'
exec caja --ia-asistente codex --red --rw "$CASA" \
  --env CODEX_HOME=/home/caja/codex \
  --env LEKSSO_HOME_REAL="$HOME" \
  -- codex --sandbox danger-full-access \
           -c 'mcp_servers.leksso.command="python3"' \
           -c 'mcp_servers.leksso.args=["/usr/local/lib/leksso-ia/mcp_permisor.py"]' \
           -c "developer_instructions='$NOTA'" "$@"
