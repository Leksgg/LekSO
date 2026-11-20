#!/bin/sh
# Pantalla propia de LeksSO para elegir el disco, dentro del instalador de Debian (se ejecuta justo antes de particionar).
#
# Por qué: la pregunta de Debian solo enseña «SCSI1 (0,0,0) (sda) - 68.7 GB Msft Virtual Disk», sin decir qué contiene cada
# disco, con el orden cambiando de un arranque a otro y con el pendrive de instalación en la lista. Aquí:
#   - se lista cada disco con modelo, tamaño, tipo (NVMe, SSD, disco duro, USB) y qué contiene (Windows, Linux...);
#   - NO aparece el medio de instalación;
#   - el disco preseleccionado es el NVMe/SSD interno, si lo hay;
#   - para continuar hay que ESCRIBIR «BORRAR» (dejarlo vacío vuelve a la lista).
# El disco elegido se pasa a partman (partman-auto/disk), que ya no pregunta por él.
. /usr/share/debconf/confmodule
db_version 2.0 || true

# Plantillas de las dos preguntas (el instalador no las trae; se cargan aquí).
cat > /tmp/leksso-disco.templates <<'EOF'
Template: leksso/disco
Type: select
Choices: ${CHOICES}
Description: ¿En qué disco instalo LeksSO?
 Elige UNO. Se BORRARÁ por completo todo lo que tenga.
 .
 Mira bien el modelo y el tamaño. El pendrive de instalación no sale en la lista.

Template: leksso/borrar
Type: string
Description: Escribe BORRAR para confirmar
 Vas a BORRAR este disco por completo:
 .
 ${DISCO}
 .
 Para continuar, escribe BORRAR y pulsa Intro.
 Para elegir otro disco, déjalo vacío y pulsa Intro.
EOF
debconf-loadtemplate leksso /tmp/leksso-disco.templates 2>/dev/null || exit 0   # si no se puede, sigue con la pregunta normal de Debian

# El disco del medio de instalación (para no ofrecerlo): el que contiene /cdrom
ORIGEN=""
CD="$(grep ' /cdrom ' /proc/mounts 2>/dev/null | head -1 | cut -d' ' -f1)"
if [ -n "$CD" ]; then
  b="$(basename "$CD")"
  if [ -d "/sys/block/$b" ]; then ORIGEN="$b"
  elif [ -e "/sys/class/block/$b" ]; then ORIGEN="$(basename "$(readlink -f "/sys/class/block/$b/..")")"; fi
fi

lista_discos() {   # imprime: nombre|descripcion
  for d in /sys/block/*; do
    n="$(basename "$d")"
    case "$n" in loop*|ram*|sr*|fd*|zram*|md*|dm-*|nbd*) continue ;; esac
    [ "$n" = "$ORIGEN" ] && continue
    [ -b "/dev/$n" ] || continue
    sect="$(cat "$d/size" 2>/dev/null)"; [ "${sect:-0}" -gt 0 ] || continue
    gb=$(( sect / 2097152 ))
    modelo="$(cat "$d/device/model" 2>/dev/null | sed 's/  */ /g; s/ *$//')"
    [ -n "$modelo" ] || modelo="disco"
    case "$n" in
      nvme*) tipo="NVMe" ;;
      *) if readlink -f "$d" | grep -q usb; then tipo="USB"
         elif [ "$(cat "$d/queue/rotational" 2>/dev/null)" = 1 ]; then tipo="disco duro"
         else tipo="SSD"; fi ;;
    esac
    tiene=""
    for p in "$d/$n"*; do
      [ -e "$p" ] || continue
      t="$(blkid -o value -s TYPE "/dev/$(basename "$p")" 2>/dev/null)"
      case "$t" in
        ntfs) tiene="$tiene Windows" ;;
        ext2|ext3|ext4|btrfs|xfs) tiene="$tiene Linux" ;;
        crypto_LUKS) tiene="$tiene cifrado" ;;
        vfat|exfat) tiene="$tiene FAT" ;;
      esac
    done
    tiene="$(printf '%s\n' $tiene | sort -u | tr '\n' ' ' | sed 's/ *$//; s/ / + /g')"
    if [ -n "$tiene" ]; then cont="contiene $tiene"; else cont="vacio"; fi
    echo "$n|$n: $modelo - $gb GB $tipo - $cont"
  done
}

TODOS="$(lista_discos)"
[ -n "$TODOS" ] || exit 0

# Preseleccion: el primero NVMe; si no, el primer SSD; si no, el primero.
PRE="$(echo "$TODOS" | grep ' NVMe - ' | head -1 | cut -d'|' -f2)"
[ -n "$PRE" ] || PRE="$(echo "$TODOS" | grep ' SSD - ' | head -1 | cut -d'|' -f2)"
[ -n "$PRE" ] || PRE="$(echo "$TODOS" | head -1 | cut -d'|' -f2)"

OPCIONES="$(echo "$TODOS" | cut -d'|' -f2 | sed 's/,/;/g' | tr '\n' '#' | sed 's/#$//; s/#/, /g')"

while :; do
  db_subst leksso/disco CHOICES "$OPCIONES"
  db_set leksso/disco "$PRE"
  db_input critical leksso/disco || true
  db_go || exit 0
  db_get leksso/disco
  ELEGIDO="$RET"
  DISCO="${ELEGIDO%%:*}"
  [ -b "/dev/$DISCO" ] || continue
  db_subst leksso/borrar DISCO "$ELEGIDO"
  db_set leksso/borrar ""
  db_input critical leksso/borrar || true
  db_go || exit 0
  db_get leksso/borrar
  RESP="$(echo "$RET" | tr 'a-z' 'A-Z' | tr -d ' ')"
  if [ "$RESP" = "BORRAR" ]; then
    debconf-set partman-auto/disk "/dev/$DISCO"
    echo "disco elegido: /dev/$DISCO ($ELEGIDO)" > /tmp/leksso-disco.log
    break
  fi
  PRE="$ELEGIDO"
done
exit 0
