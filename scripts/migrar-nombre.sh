#!/usr/bin/env bash
# Pasa un equipo instalado como «lekso» al nombre «leksso» (LekSO → LeksSO). Se puede repetir sin romper nada.
# Lo llama provision-base.sh al principio de cada instalación o actualización; solo actúa si queda algo del nombre antiguo.
# Uso: migrar-nombre.sh <usuario>            al principio: mueve datos y para lo antiguo
#      migrar-nombre.sh <usuario> limpiar    al final, ya instalado lo nuevo: borra los programas con el nombre antiguo
#      (así, si la instalación falla a medias, el equipo conserva un actualizador para volver atrás)
set -uo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Ejecuta como root." >&2; exit 1; }
USUARIO="${1:-${SUDO_USER:-}}"
HOME_USR="$(getent passwd "$USUARIO" 2>/dev/null | cut -d: -f6)"

hecho=0
# el enlace de compatibilidad de una migración anterior ya no hace falta (se crea de nuevo más abajo si toca)
[ -L /var/lib/lekso ] && rm -f /var/lib/lekso
# mueve un archivo o carpeta al nombre nuevo; si ya existe el nuevo, el antiguo no pisa nada
mover() { # origen destino
  [ -e "$1" ] || [ -L "$1" ] || return 0
  if [ -e "$2" ]; then rm -rf "$1"; else mkdir -p "$(dirname "$2")"; mv "$1" "$2"; fi
  hecho=1
}

# 1. Servicios y temporizadores: parar y quitar los antiguos (los nuevos los activa provision-base.sh)
if [ -d /run/systemd/system ]; then
  for u in lekso-admin.service lekso-permisor.service lekso-hardware.service lekso-hardware.timer lekso-streamdeck.service; do
    systemctl disable --now "$u" >/dev/null 2>&1 || true
  done
  systemctl --global disable lekso-actualizar.timer >/dev/null 2>&1 || true
fi

# 2. Datos del sistema
mover /etc/lekso /etc/leksso
mover /var/lib/lekso /var/lib/leksso
mover /usr/share/lekso /usr/share/leksso
mover /etc/lekso-release /etc/leksso-release
mover /usr/local/lib/lekso /usr/local/lib/leksso
mover /var/log/lekso-postinstalar.log /var/log/leksso-postinstalar.log

# 3. Solo al final: programas y ficheros sueltos con el nombre antiguo (provision-base.sh ya instaló los nuevos)
if [ "${2:-}" = limpiar ]; then
for f in /etc/systemd/system/lekso-* /etc/systemd/user/lekso-* /usr/lib/systemd/user/lekso-* /usr/lib/systemd/system/lekso-* /usr/local/bin/lekso-* /usr/local/lib/lekso-ia /usr/local/lib/lekso-ui /usr/share/applications/lekso-*.desktop \
         /etc/sudoers.d/lekso-* /etc/ssh/sshd_config.d/lekso.conf /etc/apt/apt.conf.d/99lekso-sin-recomendados \
         /etc/apt/sources.list.d/lekso-offline.list /usr/share/icons/LekSO /etc/udev/rules.d/70-lekso-streamdeck.rules; do
  [ -e "$f" ] || [ -L "$f" ] || continue
  rm -rf "$f"; hecho=1
done
  [ -d /run/systemd/system ] && systemctl daemon-reload >/dev/null 2>&1
fi

# 4. Datos del usuario
if [ -n "$HOME_USR" ] && [ -d "$HOME_USR" ]; then
  mover "$HOME_USR/.config/lekso" "$HOME_USR/.config/leksso"
  mover "$HOME_USR/.cache/lekso" "$HOME_USR/.cache/leksso"
  mover "$HOME_USR/.local/share/lekso" "$HOME_USR/.local/share/leksso"
  for f in "$HOME_USR"/.local/share/applications/lekso-*.desktop "$HOME_USR/.local/share/themes/LekSO"; do
    [ -e "$f" ] && { rm -rf "$f"; hecho=1; }
  done
  chown -R "$USUARIO": "$HOME_USR/.config/leksso" "$HOME_USR/.cache/leksso" "$HOME_USR/.local/share/leksso" 2>/dev/null || true
fi

# 5. Compatibilidad durante UNA actualización: el actualizador antiguo, al terminar de instalar, todavía escribe en las
#    rutas viejas. /var/lib/lekso apunta a la nueva; /etc/lekso-release lo adopta el actualizador nuevo la próxima vez.
if [ "$hecho" -eq 1 ] && [ ! -e /var/lib/lekso ]; then ln -s /var/lib/leksso /var/lib/lekso; fi
[ "$hecho" -eq 1 ] && echo "Migrado del nombre «lekso» a «leksso»."
exit 0
