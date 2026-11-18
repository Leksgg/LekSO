#!/bin/sh
# Lo ejecuta el instalador de Debian justo antes de particionar (partman/early_command).
# Genera la receta de particiones para el disco que se elija:
#   - EFI (arranque), /boot sin cifrar, y el resto dentro de un volumen cifrado (LUKS) con LVM:
#       - swap de 1,2 veces la RAM (mínimo 2 GB, máximo 32 GB): hace falta para hibernar
#       - el sistema (/) con todo lo demás
RAM_KB="$(awk '/MemTotal/ {print $2}' /proc/meminfo)"
SWAP_MB=$(( RAM_KB / 1024 * 12 / 10 ))
[ "$SWAP_MB" -lt 2048 ] && SWAP_MB=2048
[ "$SWAP_MB" -gt 32768 ] && SWAP_MB=32768

cat > /tmp/leksso-receta <<'EOF'
leksso :: \
  1 1 1 free \
     $iflabel{ gpt } \
     $reusemethod{ } \
     method{ biosgrub } \
  . \
  538 538 538 free \
     $iflabel{ gpt } \
     $reusemethod{ } \
     method{ efi } \
     format{ } \
  . \
  1024 1024 1024 ext4 \
     $primary{ } \
     $bootable{ } \
     method{ format } \
     format{ } \
     use_filesystem{ } \
     filesystem{ ext4 } \
     mountpoint{ /boot } \
  . \
  8000 20000 1000000000 ext4 \
     $lvmok{ } \
     in_vg{ leksso } \
     lv_name{ raiz } \
     method{ format } \
     format{ } \
     use_filesystem{ } \
     filesystem{ ext4 } \
     mountpoint{ / } \
  . \
  SWAP_MB SWAP_MB SWAP_MB linux-swap \
     $lvmok{ } \
     in_vg{ leksso } \
     lv_name{ swap } \
     method{ swap } \
     format{ } \
  .
EOF
sed -i "s/SWAP_MB/$SWAP_MB/g" /tmp/leksso-receta

debconf-set partman-auto/expert_recipe_file /tmp/leksso-receta
debconf-set partman-auto/choose_recipe leksso
