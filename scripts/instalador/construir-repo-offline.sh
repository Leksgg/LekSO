#!/usr/bin/env bash
# Construye el repositorio local de paquetes que lleva el USB de instalación, para instalar LeksSO SIN internet.
#
# Qué hace: crea un Debian 13 mínimo en una carpeta (debootstrap), calcula todo lo que necesita LeksSO encima
# de ese sistema base y descarga solo esos paquetes (los de Debian, con las firmas de Debian comprobadas por apt).
# Deja una carpeta con los .deb y un índice (Packages.gz) que el instalador usa como fuente de apt local.
#
# Uso (en un Debian 13 con internet, como root): construir-repo-offline.sh SALIDA [RAIZ_REPO_LEKSSO]
#   SALIDA            carpeta donde quedará el repositorio (por ejemplo /var/tmp/leksso-offline)
#   RAIZ_REPO_LEKSSO   copia del repositorio de LeksSO de la que leer las listas de paquetes (por defecto, la de este script)
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Ejecuta como root." >&2; exit 1; }
SALIDA="${1:?Indica la carpeta de salida}"
RAIZ="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
MIRROR="${LEKSSO_MIRROR:-http://deb.debian.org/debian}"
# Carpeta de trabajo nueva y privada (no una ruta predecible que otra cuenta pueda preparar de antemano).
BASE="$(mktemp -d /var/tmp/leksso-base.XXXXXXXX)"
chmod 0755 "$BASE"

apt-get install -y -qq debootstrap dpkg-dev >/dev/null

# 1. Las listas de paquetes salen del propio script de instalación (una sola fuente de verdad).
LISTA="$(bash -c '
  set -e
  eval "$(sed -n "/^ESCRITORIO=(/,/^COMPATIBILIDAD=(/p" "'"$RAIZ"'/scripts/provision-base.sh")"
  printf "%s\n" "${ESCRITORIO[@]}" "${AUDIO[@]}" "${AISLAMIENTO[@]}" "${HERRAMIENTAS[@]}" "${RED[@]}" "${GRAFICA[@]}" "${COMPATIBILIDAD[@]}" "${HYPERV[@]}"
')"
# Lo que instalan después el endurecimiento y el bloque de firmware, y lo que necesita el instalador.
EXTRA="nftables unattended-upgrades isenkram-cli intel-microcode amd64-microcode thermald
firmware-iwlwifi firmware-sof-signed firmware-intel-misc firmware-intel-graphics firmware-amd-graphics
firmware-realtek firmware-atheros firmware-mediatek firmware-misc-nonfree firmware-brcm80211
lxqt-policykit cloud-guest-utils parted smartmontools gparted gnome-disk-utility
git openssh-client openssh-server ca-certificates python3 sudo locales
clevis clevis-luks clevis-tpm2 clevis-initramfs tpm2-tools
os-prober ntfs-3g"
TODOS="$(printf '%s\n%s\n' "$LISTA" "$EXTRA" | tr ' ' '\n' | sed '/^$/d' | sort -u | tr '\n' ' ')"
echo "Paquetes pedidos: $(echo "$TODOS" | wc -w)"

# 2. Sistema base mínimo, para saber qué falta encima de él.
echo "Creando el sistema base (debootstrap)…"
# (la carpeta acaba de crearse vacía: no se borra ni se vuelve a crear por nombre)
debootstrap --variant=minbase --components=main,contrib,non-free-firmware trixie "$BASE" "$MIRROR" >/dev/null
cat > "$BASE/etc/apt/sources.list" <<EOF
deb $MIRROR trixie main contrib non-free-firmware
deb http://security.debian.org/debian-security trixie-security main contrib non-free-firmware
EOF

# 3. Descargar (sin instalar) todo el cierre de dependencias.
mkdir -p "$SALIDA"
rm -f "$SALIDA"/*.deb
mkdir -p "$BASE/var/cache/leksso-descargas"
mount --bind "$SALIDA" "$BASE/var/cache/leksso-descargas"
trap 'umount "$BASE/var/cache/leksso-descargas" 2>/dev/null || true; rm -rf "$BASE"' EXIT
chroot "$BASE" apt-get update -qq
# shellcheck disable=SC2086
chroot "$BASE" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends --download-only \
  -o Dir::Cache::archives=/var/cache/leksso-descargas $TODOS
rm -f "$SALIDA/lock"; rm -rf "$SALIDA/partial"

# 4. Índice del repositorio local.
( cd "$SALIDA" && dpkg-scanpackages --multiversion . /dev/null 2>/dev/null | gzip -9 > Packages.gz )
echo
echo "Repositorio listo en $SALIDA: $(ls "$SALIDA"/*.deb | wc -l) paquetes, $(du -sh "$SALIDA" | cut -f1)."
