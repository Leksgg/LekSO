#!/usr/bin/env bash
# Publica una versión de LekSO: etiqueta firmada y subida. Solo para quien mantiene el repositorio.
#
# Uso: scripts/publicar-version.sh 0.1.1-alpha
#
# Comprueba antes de publicar:
#   - que VERSION dice lo mismo,
#   - que CHANGELOG.md tiene una sección con esa versión,
#   - que no hay cambios sin subir,
#   - que la etiqueta no existe ya.
# La etiqueta se firma con la clave indicada en LEKSO_CLAVE_FIRMA (por defecto ~/.ssh/lekso_release).
# Los equipos solo instalan versiones firmadas con la clave de config/allowed_signers.
set -euo pipefail

V="${1:-}"
if ! [[ "$V" =~ ^[0-9]+\.[0-9]+\.[0-9]+-(alpha|beta|rc)$ ]]; then
  echo "Uso: $0 X.Y.Z-alpha   (también -beta o -rc)" >&2
  exit 2
fi
CLAVE="${LEKSO_CLAVE_FIRMA:-$HOME/.ssh/lekso_release}"
[ -f "$CLAVE" ] || { echo "No encuentro la clave de firma: $CLAVE" >&2; exit 1; }
cd "$(dirname "$0")/.."

[ "$(tr -d '[:space:]' < VERSION)" = "$V" ] || { echo "VERSION no dice $V" >&2; exit 1; }
BONITA="$(echo "$V" | sed -E 's/^([0-9.]+)-alpha$/Alpha \1/; s/^([0-9.]+)-beta$/Beta \1/; s/^([0-9.]+)-rc$/RC \1/')"
grep -qE "^## .*(${V}|${BONITA})" CHANGELOG.md || { echo "CHANGELOG.md no tiene una sección «## $BONITA»" >&2; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "Hay cambios sin subir: haz commit antes." >&2; exit 1; }
git rev-parse "v$V" >/dev/null 2>&1 && { echo "La etiqueta v$V ya existe." >&2; exit 1; }

git -c gpg.format=ssh -c user.signingkey="$CLAVE" tag -s "v$V" -m "LekSO $BONITA"
git -c gpg.ssh.allowedSignersFile=config/allowed_signers tag -v "v$V"
git push origin main "v$V"
echo "Publicada: LekSO $BONITA (v$V)"
