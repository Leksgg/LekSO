#!/usr/bin/env bash
# Convierte un Debian 13 mínimo en la base de LeksSO: escritorio, audio y aislamiento.
# Se puede ejecutar varias veces sin romper nada. Debe correr como root.
#
# Uso:
#   sudo ./scripts/provision-base.sh [usuario]
#
# Incluye escritorio por zonas, permisor de IA con su panel, caja, dispositivos, red e iconos.
# No incluye: controlador de NVIDIA (se instala con confirmación desde Ajustes → Actualizaciones), Ollama ni las aplicaciones (Brave, Steam, Obsidian...):
# esas se instalan después con `leksso-apps`.
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

# Equipos instalados con el nombre antiguo («lekso»): mover sus datos antes de instalar
bash "$(dirname "${BASH_SOURCE[0]}")/migrar-nombre.sh" "$USUARIO" || true
HOME_USR="$(getent passwd "$USUARIO" | cut -d: -f6)"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Paquetes por capa. Todos existen en Debian 13 (trixie); winetricks necesita la sección contrib.
ESCRITORIO=(labwc sway swaybg waybar foot kitty fuzzel grim pcmanfm-qt qt6-wayland qt6-svg-plugins qt6ct xwayland fonts-font-awesome seatd xdg-desktop-portal-wlr micro imv zathura zathura-pdf-poppler mpv vlc xarchiver udisks2 udiskie gvfs gvfs-backends polkitd ntfs-3g exfatprogs usbutils v4l-utils bluez pavucontrol-qt swaylock wl-clipboard mako-notifier libnotify-bin swayidle brightnessctl slurp cliphist wdisplays blueman cups fonts-noto-color-emoji fonts-liberation ffmpegthumbnailer power-profiles-daemon playerctl wlr-randr network-manager streamdeck-ui python3-pyside6.qtwidgets python3-pyside6.qtgui python3-pyside6.qtcore python3-pyside6.qtsvg)
AUDIO=(pipewire pipewire-pulse wireplumber)
AISLAMIENTO=(bubblewrap firejail python3-seccomp)
HERRAMIENTAS=(git curl btop lm-sensors python3 bc pciutils mokutil fwupd)
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
apt-get update || echo "Sin conexión: se usan los paquetes locales disponibles."
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
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/waybar" "$HOME_USR/.config/qt6ct/colors" "$HOME_USR/.config/leksso"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/waybar/config.jsonc" "$HOME_USR/.config/waybar/config.jsonc"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/waybar/style.css" "$HOME_USR/.config/waybar/style.css"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/qt6ct/colors/leksso.conf" "$HOME_USR/.config/qt6ct/colors/leksso.conf"
sed "s|@HOME@|$HOME_USR|g" "$RAIZ/config/qt6ct/qt6ct.conf" > "$HOME_USR/.config/qt6ct/qt6ct.conf"
chown -R "$USUARIO:$USUARIO" "$HOME_USR/.config"

# Iconos de tipos de archivo (tema propio, hereda de Adwaita).
install -d /usr/share/icons
cp -r "$RAIZ/config/iconos/LeksSO" /usr/share/icons/
gtk-update-icon-cache -f /usr/share/icons/LeksSO 2>/dev/null || true
grep -q '^QT_QPA_PLATFORMTHEME=' /etc/environment 2>/dev/null || echo 'QT_QPA_PLATFORMTHEME=qt6ct' >> /etc/environment

# Permisor de IA, panel, gestor de modelos y caja (en /usr/local, solo lectura para el usuario).
install -d -m 0755 /usr/local/lib/leksso-ia
install -m 0644 "$RAIZ"/leksso-ia/nucleo.py "$RAIZ"/leksso-ia/permisor.py "$RAIZ"/leksso-ia/modelo.py "$RAIZ"/leksso-ia/equipo.py "$RAIZ"/leksso-ia/asistentes.py "$RAIZ"/leksso-ia/leksso_admin.py \
  "$RAIZ"/leksso-ia/panel.py "$RAIZ"/leksso-ia/leksso_ia.py "$RAIZ"/leksso-ia/mcp_permisor.py /usr/local/lib/leksso-ia/
printf '#!/bin/sh\nexec python3 /usr/local/lib/leksso-ia/leksso_ia.py "$@"\n' > /usr/local/bin/leksso-ia
install -m 0755 "$RAIZ/scripts/caja.sh" /usr/local/bin/caja
install -m 0755 "$RAIZ/scripts/leksso-claude.sh" /usr/local/bin/leksso-claude
install -m 0755 "$RAIZ/scripts/leksso-codex.sh" /usr/local/bin/leksso-codex
install -m 0755 "$RAIZ/config/bin/leksso-asistente" /usr/local/bin/leksso-asistente
install -m 0755 "$RAIZ/config/bin/leksso-asistentes" /usr/local/bin/leksso-asistentes
# Permisos de los asistentes: archivo del administrador. En una instalación nueva, todos apagados y en «solo archivos».
# Si el usuario ya había elegido uno con la versión anterior, se conserva activo (solo archivos).
install -d -m 0755 /etc/leksso
if [ ! -f /etc/leksso/asistentes.json ]; then
  ANTERIOR="$(cat "$HOME_USR/.config/leksso/asistente" 2>/dev/null || true)"
  python3 - "$USUARIO" "$ANTERIOR" <<'PY'
import sys
sys.path.insert(0, "/usr/local/lib/leksso-ia")
import asistentes
usuario, anterior = sys.argv[1], sys.argv[2].strip()
asistentes.guardar(usuario, {anterior: {"activo": True}} if anterior in asistentes.NOMBRES else {})
PY
fi
install -m 0644 "$RAIZ/config/systemd/leksso-admin.service" /etc/systemd/system/leksso-admin.service
systemctl enable leksso-admin.service >/dev/null 2>&1 || true
if [ -d /run/systemd/system ]; then systemctl daemon-reload; systemctl restart leksso-admin.service || true; fi
# Asistentes de IA: vienen instalados pero INACTIVOS; cada usuario elige cuál activa (leksso-asistente).
# Necesitan conexión: sin red se omiten y se instalan después, al elegirlos.
if apt-get install -y --no-install-recommends nodejs npm; then
  for paquete in @anthropic-ai/claude-code @openai/codex; do
    npm install -g "$paquete" >/dev/null 2>&1 || echo "AVISO: no se pudo instalar $paquete (¿sin conexión?). Se instalará al elegirlo."
  done
else
  echo "AVISO: sin Node (¿sin conexión?): los asistentes de IA se instalarán al elegirlos."
fi
install -m 0644 "$RAIZ/scripts/seccomp-estricta.py" /usr/local/lib/leksso-ia/seccomp-estricta.py
chmod 0755 /usr/local/bin/leksso-ia
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/foot"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/foot/foot.ini" "$HOME_USR/.config/foot/foot.ini"
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/kitty"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/kitty/kitty.conf" "$HOME_USR/.config/kitty/kitty.conf"
# Explorador: árbol de carpetas y barra de ruta con botones.
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/pcmanfm-qt/default"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/pcmanfm-qt/settings.conf" "$HOME_USR/.config/pcmanfm-qt/default/settings.conf"
# Red: NetworkManager gestiona las interfaces (estado y redes disponibles en la barra).
if [ -f /etc/network/interfaces ] && grep -qE '^(allow-hotplug|auto|iface) (e|w)' /etc/network/interfaces; then
  cp -n /etc/network/interfaces /etc/network/interfaces.leksso-antes
  sed -i -E 's/^(allow-hotplug|auto) (e|w)/# /; s/^iface (e|w)/#iface /' /etc/network/interfaces
  systemctl restart NetworkManager || true
fi

# Lanzador de aplicaciones con la paleta de LeksSO y sin entradas técnicas.
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/fuzzel" "$HOME_USR/.local/share/applications"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/fuzzel/fuzzel.ini" "$HOME_USR/.config/fuzzel/fuzzel.ini"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ"/config/applications-ocultas/*.desktop "$HOME_USR/.local/share/applications/"

# Notificaciones y pantalla de bloqueo con la paleta de LeksSO.
install -d /usr/share/leksso
python3 "$RAIZ/scripts/generar-pantalla-bloqueo.py" /usr/share/leksso/bloqueo.png || true
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/mako" "$HOME_USR/.config/swaylock"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/mako/config" "$HOME_USR/.config/mako/config"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/swaylock/config" "$HOME_USR/.config/swaylock/config"

# Versión y actualizaciones: la versión instalada, la clave con la que se comprueban las versiones nuevas
# y la comprobación diaria. La clave instalada solo cambia con una versión ya firmada por la anterior.
install -m 0755 "$RAIZ/scripts/leksso-actualizar.py" /usr/local/bin/leksso-actualizar
install -d -m 0755 /etc/leksso /var/lib/leksso /etc/issue.d
install -m 0644 "$RAIZ/config/allowed_signers" /etc/leksso/allowed_signers
install -m 0644 "$RAIZ/VERSION" /etc/leksso-release
echo "LeksSO $(leksso-actualizar version | sed 's/^LeksSO //')" > /etc/issue.d/20-leksso.issue
install -m 0644 "$RAIZ"/config/systemd/leksso-actualizar.service "$RAIZ"/config/systemd/leksso-actualizar.timer /etc/systemd/user/
systemctl --global enable leksso-actualizar.timer >/dev/null 2>&1 || true

# Controladores y firmware: a los 3 minutos de arrancar y una vez al día, el sistema (como root) actualiza solo
# el microcódigo y el firmware de Debian y avisa del resto (NVIDIA, firmware de dispositivos), que se instalan
# con un clic en Ajustes → Actualizaciones. Ver scripts/leksso_hardware.py.
install -d -m 0755 /usr/local/lib/leksso
install -m 0644 "$RAIZ/scripts/leksso_hardware.py" /usr/local/lib/leksso/leksso_hardware.py
install -m 0644 "$RAIZ"/config/systemd/leksso-hardware.service "$RAIZ"/config/systemd/leksso-hardware.timer /etc/systemd/system/
systemctl daemon-reload >/dev/null 2>&1 || true
systemctl enable leksso-hardware.timer >/dev/null 2>&1 || true

# Stream Deck: se inicia al conectarlo (el acceso a USB lo da la regla del paquete).
install -m 0644 "$RAIZ/config/systemd/leksso-streamdeck.service" "$RAIZ/config/systemd/leksso-permisor.service" /etc/systemd/user/
install -m 0644 "$RAIZ/config/udev/70-leksso-streamdeck.rules" /etc/udev/rules.d/
udevadm control --reload 2>/dev/null || true

# Firmware y microcódigo según el hardware real (Wi-Fi, sonido, gráficos...). En una máquina virtual no hace falta
# (LEKSSO_HARDWARE=1 lo fuerza). isenkram detecta qué dispositivos hay y qué paquete de firmware necesitan.
if [ "$(systemd-detect-virt 2>/dev/null || echo none)" = "none" ] || [ "${LEKSSO_HARDWARE:-}" = "1" ]; then
  apt-get install -y --no-install-recommends isenkram-cli || true
  isenkram-autoinstall-firmware || true
  case "$(sed -n 's/^vendor_id[[:space:]]*:[[:space:]]*//p' /proc/cpuinfo | head -1)" in
    GenuineIntel)   # portátiles Intel: Wi-Fi, sonido (SOF), gráficos, microcódigo y control térmico
      apt-get install -y --no-install-recommends intel-microcode thermald firmware-iwlwifi firmware-sof-signed         firmware-intel-misc firmware-intel-graphics || true ;;
    AuthenticAMD)
      apt-get install -y --no-install-recommends amd64-microcode firmware-amd-graphics || true ;;
  esac
fi

# Zonas del escritorio (sway) y alternativa labwc: ventanas con título y botones, barra de tareas en la barra superior.
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/.config/labwc" "$HOME_USR/.local/share/themes"
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/labwc/rc.xml" "$RAIZ/config/labwc/menu.xml" "$HOME_USR/.config/labwc/"
install -o "$USUARIO" -g "$USUARIO" -m 0755 "$RAIZ/config/labwc/autostart" "$HOME_USR/.config/labwc/autostart"
cp -r "$RAIZ/config/labwc/tema/LeksSO" "$HOME_USR/.local/share/themes/"
chown -R "$USUARIO:$USUARIO" "$HOME_USR/.local/share/themes"
install -m 0755 "$RAIZ/config/sway/zonas.sh" /usr/local/bin/leksso-zonas
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/bash_profile" "$HOME_USR/.bash_profile"
# Escritorio con iconos: carpeta Escritorio y accesos.
install -o "$USUARIO" -g "$USUARIO" -m 0644 "$RAIZ/config/user-dirs.dirs" "$HOME_USR/.config/user-dirs.dirs"
install -d -o "$USUARIO" -g "$USUARIO" "$HOME_USR/Escritorio"
install -o "$USUARIO" -g "$USUARIO" -m 0755 "$RAIZ"/config/escritorio/*.desktop "$HOME_USR/Escritorio/"

# Programas predeterminados por tipo de archivo (no pisa lo que el usuario ya haya elegido).
install -m 0755 "$RAIZ/config/bin/leksso-info" "$RAIZ/config/bin/leksso-wine" "$RAIZ/config/bin/leksso-menu" "$RAIZ/config/bin/leksso-energia" "$RAIZ/config/bin/leksso-flotantes" "$RAIZ/config/bin/leksso-term" "$RAIZ/config/bin/leksso-medios" "$RAIZ/config/bin/leksso-captura" "$RAIZ/config/bin/leksso-reposo" "$RAIZ/config/bin/leksso-portapapeles" "$RAIZ/config/bin/leksso-ajustes" "$RAIZ/config/bin/leksso-redes" "$RAIZ/config/bin/leksso-actualizaciones" "$RAIZ/config/bin/leksso-panel-ia" "$RAIZ/config/bin/leksso-acceso-remoto" "$RAIZ/config/bin/leksso-archivos" "$RAIZ/config/bin/leksso-juego" "$RAIZ/config/bin/leksso-office-web" "$RAIZ/config/bin/leksso-secureboot" /usr/local/bin/
# Apagar y reiniciar no se quedan esperando a un servicio que no responde (por defecto serían hasta 2 minutos).
install -d /etc/systemd/system.conf.d /etc/systemd/user.conf.d /etc/systemd/system/user@.service.d /etc/systemd/user/mpris-proxy.service.d
printf '[Manager]
DefaultTimeoutStopSec=15s
' > /etc/systemd/system.conf.d/leksso-apagado.conf
printf '[Manager]
DefaultTimeoutStopSec=10s
' > /etc/systemd/user.conf.d/leksso-apagado.conf
printf '[Service]
TimeoutStopSec=20s
' > /etc/systemd/system/user@.service.d/leksso-apagado.conf
printf '[Service]
TimeoutStopSec=3s
' > /etc/systemd/user/mpris-proxy.service.d/leksso-apagado.conf
# Modo juego: perfiles de energía, GameMode y la parte de administrador (un solo ajuste, sin contraseña)
apt-get install -y --no-install-recommends power-profiles-daemon gamemode || echo "AVISO: sin power-profiles-daemon o gamemode (¿sin conexión?)"
install -m 0755 "$RAIZ/scripts/leksso-juego-raiz.sh" /usr/local/sbin/leksso-juego-raiz
printf '%%sudo ALL=(root) NOPASSWD: /usr/local/sbin/leksso-juego-raiz on, /usr/local/sbin/leksso-juego-raiz off
' > /etc/sudoers.d/leksso-juego
chmod 0440 /etc/sudoers.d/leksso-juego
visudo -cf /etc/sudoers.d/leksso-juego >/dev/null || rm -f /etc/sudoers.d/leksso-juego
install -d /usr/local/lib/leksso-ui
install -m 0644 "$RAIZ/config/ui/leksso_ui.py" /usr/local/lib/leksso-ui/
install -m 0644 "$RAIZ"/config/applications/*.desktop /usr/share/applications/
install -m 0755 "$RAIZ/scripts/asociar-archivos.py" /usr/local/bin/leksso-asociar
install -m 0755 "$RAIZ/scripts/leksso-apps.py" /usr/local/bin/leksso-apps
sudo -u "$USUARIO" leksso-asociar

# Temas de color: los archivos de colores por papel, el comando que los aplica y la ventana de Apariencia.
# La configuración base se acaba de copiar con los colores de Marea; si el usuario eligió otro tema, se vuelve a poner.
install -d -m 0755 /usr/local/share/leksso/temas
install -m 0644 "$RAIZ"/config/tema/*.json /usr/local/share/leksso/temas/
install -m 0755 "$RAIZ/scripts/leksso-tema.py" /usr/local/bin/leksso-tema
install -m 0755 "$RAIZ/config/bin/leksso-apariencia" /usr/local/bin/leksso-apariencia
sudo -u "$USUARIO" leksso-tema reaplicar || true
# La sesión abierta sigue con la configuración vieja (barra, atajos): se le pide que lea la nueva sin cerrar sesión.
sudo -u "$USUARIO" leksso-tema recargar || true

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

# Libera la caché de paquetes descargados (cientos de MB que no hacen falta).
apt-get clean

echo "Listo. Reinicia: al iniciar sesión en la primera consola arranca el escritorio de LeksSO."

# Ya instalado lo nuevo: borrar lo que quedó con el nombre antiguo
bash "$(dirname "${BASH_SOURCE[0]}")/migrar-nombre.sh" "$USUARIO" limpiar || true
