#!/usr/bin/env bash
# Construye la imagen de instalación de LekSO (ISO): el Debian oficial con firmware, más el paquete de LekSO.
#
# Uso: construir-iso.sh --iso DEBIAN.iso --offline CARPETA_REPO --version vX.Y.Z-alpha --salida LEKSO.iso [--prueba CLAVE_PUBLICA_SSH]
#   --iso      imagen oficial «netinst con firmware» de Debian 13 (ya comprobada con su suma de Debian)
#   --offline  repositorio local de paquetes (lo crea construir-repo-offline.sh)
#   --version  versión de LekSO que lleva, con su etiqueta firmada (v0.1.4-alpha)
#   --fase-pruebas  equipo real en pruebas: actualiza sin exigir firma y arranca con SSH en red local
#   --prueba   imagen de PRUEBAS: respuestas fijas (disco /dev/sda, claves de prueba) y acceso por SSH. NUNCA para uso real.
# Requiere: xorriso, git. Se ejecuta desde la raíz del repositorio de LekSO (que debe tener la etiqueta).
set -euo pipefail

ISO=""; OFFLINE=""; VERSION=""; SALIDA=""; PRUEBA=""; FASE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --iso) ISO="$2"; shift 2 ;; --offline) OFFLINE="$2"; shift 2 ;; --version) VERSION="$2"; shift 2 ;;
    --salida) SALIDA="$2"; shift 2 ;; --prueba) PRUEBA="$2"; shift 2 ;; --fase-pruebas) FASE=1; shift ;;
    *) echo "Opción desconocida: $1" >&2; exit 2 ;;
  esac
done
for v in ISO OFFLINE VERSION SALIDA; do [ -n "${!v}" ] || { echo "Falta --${v,,}" >&2; exit 2; }; done
[[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+-(alpha|beta|rc)$ ]] || { echo "Versión no válida: $VERSION" >&2; exit 2; }
[ -f "$ISO" ] && [ -f "$OFFLINE/Packages.gz" ] || { echo "No encuentro la ISO o el repositorio local." >&2; exit 1; }
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ"
git rev-parse -q --verify "refs/tags/$VERSION" >/dev/null || { echo "La etiqueta $VERSION no existe en este repositorio." >&2; exit 1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
PAQ="$TMP/lekso"; mkdir -p "$PAQ"

# 1. El paquete de LekSO: el repositorio con sus etiquetas (se verifica al instalar), el instalador de ESA versión
#    y los archivos de instalación automática.
git bundle create "$PAQ/lekso.bundle" --all >/dev/null 2>&1
git show "$VERSION:scripts/instalar.sh" > "$PAQ/instalar.sh"
git show "$VERSION:scripts/instalador/preseed.cfg" > "$PAQ/preseed.cfg"
git show "$VERSION:scripts/instalador/receta.sh" > "$PAQ/receta.sh"
git show "$VERSION:scripts/instalador/postinstalar.sh" > "$PAQ/postinstalar.sh"
printf '%s\n' "$VERSION" > "$PAQ/VERSION_TAG"
cp -r "$OFFLINE" "$PAQ/offline"
# La clave incrustada en instalar.sh debe ser exactamente la de config/allowed_signers de esa versión.
CLAVE_EN_SCRIPT="$(sed -n "s/^CLAVE_PUBLICA='\(.*\)'\$/\1/p" "$PAQ/instalar.sh")"
[ -n "$CLAVE_EN_SCRIPT" ] && [ "$CLAVE_EN_SCRIPT" = "$(git show "$VERSION:config/allowed_signers" | head -n1)" ] \
  || { echo "La clave incrustada en instalar.sh no coincide con config/allowed_signers." >&2; exit 1; }

# 1b. Fase de pruebas en equipos reales: sin exigir firma en las actualizaciones y con acceso remoto en red local.
if [ "$FASE" = 1 ]; then echo "fase de pruebas" > "$PAQ/FASE_PRUEBAS"; fi

# 2. Imagen de pruebas: respuestas fijas para poder instalar sin nadie delante.
if [ -n "$PRUEBA" ]; then
  printf '%s\n' "$PRUEBA" > "$PAQ/PRUEBA"
  cat >> "$PAQ/preseed.cfg" <<'EOF'

# ===== SOLO IMAGEN DE PRUEBAS =====
d-i partman-auto/disk string /dev/sda
d-i partman-crypto/passphrase password prueba
d-i partman-crypto/passphrase-again password prueba
d-i partman-crypto/weak_passphrase boolean true
d-i partman/confirm boolean true
d-i partman/confirm_nooverwrite boolean true
d-i partman/choose_partition select finish
d-i passwd/user-fullname string LekSO
d-i passwd/username string lekso
d-i passwd/user-password password Lks15
d-i passwd/user-password-again password Lks15
d-i user-setup/allow-password-weak boolean true
EOF
fi

# 3. Menú de arranque: una entrada nueva (la primera) que lanza la instalación de LekSO.
ORIGEN_GRUB="$TMP/grub.orig"
xorriso -osirrox on -indev "$ISO" -extract /boot/grub/grub.cfg "$ORIGEN_GRUB" >/dev/null 2>&1
ENTRADA="menuentry --hotkey=l 'Instalar LekSO (borra el disco que elijas)' {
    set background_color=black
    linux    /install.amd/vmlinuz auto=true priority=high file=/cdrom/lekso/preseed.cfg vga=788 --- quiet
    initrd   /install.amd/initrd.gz
}"
python3 - "$ORIGEN_GRUB" "$TMP/grub.cfg" "$ENTRADA" <<'PY'
import sys
orig = open(sys.argv[1], encoding="utf-8").read()
entrada = sys.argv[3]
# antes de la primera entrada del menú original; y que arranque ésta por defecto
i = orig.index("menuentry ")
nuevo = orig[:i] + entrada + "\n" + orig[i:]
nuevo = "set default=0\nset timeout=10\n" + nuevo
open(sys.argv[2], "w", encoding="utf-8").write(nuevo)
PY

# 4. La imagen: la original más el paquete y el menú nuevo (el arranque se conserva).
rm -f "$SALIDA"
xorriso -indev "$ISO" -outdev "$SALIDA" -map "$PAQ" /lekso -map "$TMP/grub.cfg" /boot/grub/grub.cfg -boot_image any replay 2>&1 \
  | grep -iE 'fail|error|written|wrote' || true
echo
ls -la "$SALIDA"
sha256sum "$SALIDA"
