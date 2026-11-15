#!/usr/bin/env bash
# Convierte un Debian 13 mínimo en la base de LekSO: escritorio, audio y aislamiento.
# Se puede ejecutar varias veces sin romper nada. Debe correr como root.
#
# Uso:
#   sudo ./scripts/provision-base.sh [usuario]
#
# Incluye escritorio por zonas, permisor de IA con su panel, caja, dispositivos, red e iconos.
# No incluye: controlador de NVIDIA, Ollama ni las aplicaciones (Brave, Steam, Obsidian...):
# esas se instalan después con `lekso-apps`.
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
ESCRITORIO=(labwc sway swaybg waybar foot fuzzel grim pcmanfm-qt qt6-wayland qt6-svg-plugins qt6ct xwayland fonts-font-awesome seatd xdg-desktop-portal-wlr micro imv zathura zathura-pdf-poppler mpv xarchiver udisks2 udiskie gvfs gvfs-backends polkitd ntfs-3g exfatprogs usbutils v4l-utils bluez pavucontrol-qt swaylock network-manager streamdeck-ui python3-pyside6.qtwidgets python3-pyside6.qtgui python3-pyside6.qtcore python3-pyside6.qtsvg)
AUDIO=(pipewire pipewire-pulse wireplumber)
AISLAMIENTO=(bubblewrap firejail python3-seccomp)
HERRAMIENTAS=(git curl btop lm-sensors python3 bc)
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
# En una máquina virtual de Hyper-V, resolución grande (en un equipo real se usa la nativa).
if [ "$(systemd-detect-virt 2>/dev/null || true)" = "microsoft" ]; then
  echo "output * resolution 1920x1080" > "$HOME_USR/.config/sway/local.conf"
  chown "$USUARIO:$USUARIO" "$HOME_USR/.config/sway/local.conf"
fi

# Barra superior, tema de las aplicaciones Qt y estado de la IA.
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/waybar" "$HOME_USR/.config/qt6ct/colors" "$HOME_USR/.config/lekso"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/waybar/config.jsonc" "$HOME_USR/.config/waybar/config.jsonc"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/waybar/style.css" "$HOME_USR/.config/waybar/style.css"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/qt6ct/colors/lekso.conf" "$HOME_USR/.config/qt6ct/colors/lekso.conf"
sed "s|@HOME@|$HOME_USR|g" "$RAIZ/config/qt6ct/qt6ct.conf" > "$HOME_USR/.config/qt6ct/qt6ct.conf"
chown -R "$USUARIO:$USUARIO" "$HOME_USR/.config"

# Iconos de tipos de archivo (tema propio, hereda de Adwaita).
install -d /usr/share/icons
cp -r "$RAIZ/config/iconos/LekSO" /usr/share/icons/
gtk-update-icon-cache -f /usr/share/icons/LekSO 2>/dev/null || true
grep -q '^QT_QPA_PLATFORMTHEME=' /etc/environment 2>/dev/null || echo 'QT_QPA_PLATFORMTHEME=qt6ct' >> /etc/environment

# Permisor de IA, panel, gestor de modelos y caja (en /usr/local, solo lectura para el usuario).
install -d -m 0755 /usr/local/lib/lekso-ia
install -m 0644 "$RAIZ"/lekso-ia/nucleo.py "$RAIZ"/lekso-ia/permisor.py "$RAIZ"/lekso-ia/modelo.py \
  "$RAIZ"/lekso-ia/panel.py "$RAIZ"/lekso-ia/lekso_ia.py /usr/local/lib/lekso-ia/
printf '#!/bin/sh\nexec python3 /usr/local/lib/lekso-ia/lekso_ia.py "$@"\n' > /usr/local/bin/lekso-ia
install -m 0755 "$RAIZ/scripts/caja.sh" /usr/local/bin/caja
install -m 0644 "$RAIZ/scripts/seccomp-estricta.py" /usr/local/lib/lekso-ia/seccomp-estricta.py
chmod 0755 /usr/local/bin/lekso-ia
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/foot"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/foot/foot.ini" "$HOME_USR/.config/foot/foot.ini"
# Explorador: árbol de carpetas y barra de ruta con botones.
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/pcmanfm-qt/default"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/pcmanfm-qt/settings.conf" "$HOME_USR/.config/pcmanfm-qt/default/settings.conf"
# Red: NetworkManager gestiona las interfaces (estado y redes disponibles en la barra).
if [ -f /etc/network/interfaces ] && grep -qE '^(allow-hotplug|auto|iface) (e|w)' /etc/network/interfaces; then
  cp -n /etc/network/interfaces /etc/network/interfaces.lekso-antes
  sed -i -E 's/^(allow-hotplug|auto) (e|w)/# /; s/^iface (e|w)/#iface /' /etc/network/interfaces
  systemctl restart NetworkManager || true
fi

# Lanzador de aplicaciones con la paleta de LekSO y sin entradas técnicas.
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/fuzzel" "$HOME_USR/.local/share/applications"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/fuzzel/fuzzel.ini" "$HOME_USR/.config/fuzzel/fuzzel.ini"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ"/config/applications-ocultas/*.desktop "$HOME_USR/.local/share/applications/"

# Stream Deck: se inicia al conectarlo (el acceso a USB lo da la regla del paquete).
install -m 0644 "$RAIZ/config/systemd/lekso-streamdeck.service" "$RAIZ/config/systemd/lekso-permisor.service" /etc/systemd/user/
install -m 0644 "$RAIZ/config/udev/70-lekso-streamdeck.rules" /etc/udev/rules.d/
udevadm control --reload 2>/dev/null || true

# Zonas del escritorio (sway) y alternativa labwc: ventanas con título y botones, barra de tareas en la barra superior.
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/labwc" "$HOME_USR/.local/share/themes"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/labwc/rc.xml" "$RAIZ/config/labwc/menu.xml" "$HOME_USR/.config/labwc/"
install -o "$USUARIO" -g "$USUARIO" -m 0755 "$RAIZ/config/labwc/autostart" "$HOME_USR/.config/labwc/autostart"
cp -r "$RAIZ/config/labwc/tema/LekSO" "$HOME_USR/.local/share/themes/"
chown -R "$USUARIO:$USUARIO" "$HOME_USR/.local/share/themes"
install -m 0755 "$RAIZ/config/sway/zonas.sh" /usr/local/bin/lekso-zonas
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/bash_profile" "$HOME_USR/.bash_profile"
# Escritorio con iconos: carpeta Escritorio y accesos.
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/user-dirs.dirs" "$HOME_USR/.config/user-dirs.dirs"
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/Escritorio"
install -o "$USUARIO" -g "$USUARIO" -m 0755 "$RAIZ"/config/escritorio/*.desktop "$HOME_USR/Escritorio/"

# Programas predeterminados por tipo de archivo (no pisa lo que el usuario ya haya elegido).
install -m 0755 "$RAIZ/config/bin/lekso-info" "$RAIZ/config/bin/lekso-wine" "$RAIZ/config/bin/lekso-menu" "$RAIZ/config/bin/lekso-energia" /usr/local/bin/
install -d /usr/local/lib/lekso-ui
install -m 0644 "$RAIZ/config/ui/lekso_ui.py" /usr/local/lib/lekso-ui/
install -m 0644 "$RAIZ"/config/applications/*.desktop /usr/share/applications/
install -m 0755 "$RAIZ/scripts/asociar-archivos.py" /usr/local/bin/lekso-asociar
install -m 0755 "$RAIZ/scripts/lekso-apps.py" /usr/local/bin/lekso-apps
sudo -u "$USUARIO" lekso-asociar

echo
# Todo lo que se creó en la carpeta personal es del usuario (los directorios intermedios los crea root).
chown -R "$USUARIO:$USUARIO" "$HOME_USR/.config" "$HOME_USR/.local" 2>/dev/null || true

# Teclado de la sesión según el del sistema (por defecto, español).
DISTRIB="$(. /etc/default/keyboard 2>/dev/null && echo "${XKBLAYOUT%%,*}")"
LOCAL="$HOME_USR/.config/sway/local.conf"
{ grep -sv 'xkb_layout' "$LOCAL" || true; echo "input type:keyboard xkb_layout ${DISTRIB:-es}"; } > "$LOCAL.nuevo"
mv "$LOCAL.nuevo" "$LOCAL"
chown "$USUARIO:$USUARIO" "$LOCAL"

# Cortafuegos, actualizaciones de seguridad y ajustes del núcleo (en Hyper-V deja el SSH abierto).
if [ "$(systemd-detect-virt 2>/dev/null || true)" = "microsoft" ]; then
  bash "$RAIZ/scripts/endurecer.sh" --ssh
else
  bash "$RAIZ/scripts/endurecer.sh"
fi

echo "Listo. Reinicia: al iniciar sesión en la primera consola arranca el escritorio de LekSO."
