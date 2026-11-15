#!/bin/sh
# Se ejecuta DENTRO del sistema recién instalado (en el instalador, con chroot), sin necesidad de red.
# Instala LekSO con el instalador firmado: la versión sale del paquete del USB y se comprueba su firma.
set -e
PAQ=/opt/lekso-instalacion
export DEBIAN_FRONTEND=noninteractive

# 1. Los paquetes de Debian que necesita LekSO están en el USB: se usan como fuente de apt local.
echo "deb [trusted=yes] file:$PAQ/offline ./" > /etc/apt/sources.list.d/lekso-offline.list
apt-get update -qq 2>/dev/null || true      # si los espejos de red fallan por no haber conexión, no importa

# 2. Para quién se instala: el primer usuario que creó el instalador.
USUARIO="$(getent passwd 1000 | cut -d: -f1)"
[ -n "$USUARIO" ] || { echo "No encuentro el usuario creado por el instalador." >&2; exit 1; }

# 3. Solo para las imágenes de prueba (llevan un archivo PRUEBA): acceso por SSH para poder revisar la instalación.
if [ -f "$PAQ/PRUEBA" ]; then
  apt-get install -y -qq openssh-server sudo >/dev/null
  install -d -m 0700 -o "$USUARIO" -g "$USUARIO" "/home/$USUARIO/.ssh"
  install -m 0600 -o "$USUARIO" -g "$USUARIO" "$PAQ/PRUEBA" "/home/$USUARIO/.ssh/authorized_keys"
  echo "$USUARIO ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/$USUARIO"; chmod 440 "/etc/sudoers.d/$USUARIO"
fi

# 4. LekSO, con la comprobación de firma del instalador.
VERSION="$(cat "$PAQ/VERSION_TAG")"
SUDO_USER="$USUARIO" bash "$PAQ/instalar.sh" --origen "$PAQ/lekso.bundle" --version "$VERSION" --si

# 5. Fuentes de apt normales para el sistema ya instalado (las actualizaciones de Debian irán por red) y limpieza.
rm -f /etc/apt/sources.list.d/lekso-offline.list
cat > /etc/apt/sources.list <<'EOF'
deb http://deb.debian.org/debian trixie main contrib non-free-firmware
deb http://deb.debian.org/debian trixie-updates main contrib non-free-firmware
deb http://security.debian.org/debian-security trixie-security main contrib non-free-firmware
EOF
rm -rf "$PAQ/offline"
echo "LekSO instalado."
