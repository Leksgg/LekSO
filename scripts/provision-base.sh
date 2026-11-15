#!/usr/bin/env bash
# Convierte un Debian 13 mínimo en la base de LekSO: escritorio, audio y aislamiento.
# Se puede ejecutar varias veces sin romper nada. Debe correr como root.
#
# Uso:
#   sudo ./scripts/provision-base.sh [usuario]
#
# No incluye todavía: controlador de NVIDIA, Steam, Brave, Ollama ni el panel de IA.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Ejecuta como root: sudo $0 [usuario]" >&2
  exit 1
fi

USUARIO="${1:-${SUDO_USER:-}}"
if [ -z "$USUARIO" ] || ! id "$USUARIO" >/dev/null 2>&1; then
  echo "Indica un usuario existente: sudo $0 <usuario>" >&2
  exit 1
fi
HOME_USR="$(getent passwd "$USUARIO" | cut -d: -f6)"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Paquetes por capa. Todos existen en Debian 13 (trixie); winetricks necesita la sección contrib.
ESCRITORIO=(sway swaybg waybar foot fuzzel grim pcmanfm-qt qt6-wayland xwayland fonts-font-awesome seatd xdg-desktop-portal-wlr)
AUDIO=(pipewire pipewire-pulse wireplumber)
AISLAMIENTO=(bubblewrap firejail)
HERRAMIENTAS=(git curl btop lm-sensors)
GRAFICA=(mesa-vulkan-drivers)
HYPERV=(hyperv-daemons)       # solo útil dentro de una máquina virtual de Hyper-V
COMPATIBILIDAD=(wine winetricks)

# winetricks (y más adelante Steam) están en la sección contrib, que el instalador no activa.
# Cubre tanto /etc/apt/sources.list como el formato nuevo en /etc/apt/sources.list.d/*.sources.
if [ -f /etc/apt/sources.list ]; then
  sed -i -E '/^deb(-src)? /{/ contrib( |$)/!s/ main( |$)/ main contrib\1/}' /etc/apt/sources.list
fi
for f in /etc/apt/sources.list.d/*.sources; do
  [ -e "$f" ] || continue
  sed -i -E '/^Components:/{/contrib/!s/ main( |$)/ main contrib\1/}' "$f"
done

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  "${ESCRITORIO[@]}" "${AUDIO[@]}" "${AISLAMIENTO[@]}" \
  "${HERRAMIENTAS[@]}" "${GRAFICA[@]}" "${COMPATIBILIDAD[@]}"

# Herramientas de invitado solo si estamos en Hyper-V.
if [ "$(systemd-detect-virt 2>/dev/null || true)" = "microsoft" ]; then
  apt-get install -y --no-install-recommends "${HYPERV[@]}"
  # El cursor por hardware suele fallar en la pantalla virtual de Hyper-V.
  grep -q '^WLR_NO_HARDWARE_CURSORS=' /etc/environment 2>/dev/null || echo 'WLR_NO_HARDWARE_CURSORS=1' >> /etc/environment
fi

# El usuario necesita estos grupos para que el compositor acceda a pantalla y teclado.
usermod -aG video,input,render "$USUARIO" 2>/dev/null || true
systemctl enable --now seatd 2>/dev/null || true
usermod -aG seatd "$USUARIO" 2>/dev/null || true

# Configuración del escritorio.
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/sway"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/sway/config" "$HOME_USR/.config/sway/config"

echo
echo "Listo. Cierra la sesión y vuelve a entrar, y arranca el escritorio con: sway"
