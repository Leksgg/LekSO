#!/usr/bin/env bash
# Firma una imagen de instalación de LeksSO: crea IMAGEN.sha256 e IMAGEN.sha256.sig con la clave de versiones.
# Uso: firmar-imagen.sh IMAGEN.iso      (con el agente de firma desbloqueado: scripts/desbloquear-firma.sh)
set -euo pipefail
ISO="${1:?Uso: $0 IMAGEN.iso}"
CLAVE="${LEKSO_CLAVE_FIRMA:-$HOME/.ssh/lekso_release}"
SOCK="${LEKSO_AGENTE:-$HOME/.ssh/lekso-agent.sock}"
FIRMA="$CLAVE"
if [ -S "$SOCK" ] && SSH_AUTH_SOCK="$SOCK" ssh-add -l >/dev/null 2>&1; then export SSH_AUTH_SOCK="$SOCK"; FIRMA="$CLAVE.pub"; fi
( cd "$(dirname "$ISO")" && sha256sum "$(basename "$ISO")" ) > "$ISO.sha256"
rm -f "$ISO.sha256.sig"
ssh-keygen -Y sign -f "$FIRMA" -n file "$ISO.sha256" >/dev/null
mv "$ISO.sha256.sig" "$ISO.sha256.sig" 2>/dev/null || true
echo "Firmada: $ISO.sha256 y $ISO.sha256.sig"
