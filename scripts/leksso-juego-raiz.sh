#!/bin/sh
# Parte de administrador del modo juego. Solo acepta «on» u «off» y solo toca un ajuste del núcleo:
# la protección «split lock», que frena mucho a algunos juegos de Windows. Con «off» vuelve a su valor normal.
# Se permite sin contraseña (ver /etc/sudoers.d/leksso-juego) porque no hace nada más.
case "${1:-}" in
  on)  sysctl -q -w kernel.split_lock_mitigate=0 ;;
  off) sysctl -q -w kernel.split_lock_mitigate=1 ;;
  *)   echo "Uso: leksso-juego-raiz on|off" >&2; exit 2 ;;
esac
