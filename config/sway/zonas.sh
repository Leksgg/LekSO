#!/bin/sh
# Monta las zonas de LeksSO: explorador | centro (pestañas) + terminal | panel de IA.
# Las apps que abra el usuario van siempre a la zona central.
# Uso: lekso-zonas              monta las zonas al iniciar la sesión
#      lekso-zonas --restaurar  vuelve a la vista por defecto sin cerrar las apps del usuario
#      lekso-zonas --plegar     pliega o despliega la columna de carpetas (más sitio para la app)

# Si se lanzó sin el socket de sway (p. ej. desde una barra reiniciada a mano), lo busca.
if [ -z "${SWAYSOCK:-}" ]; then
  SWAYSOCK="$(ls "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"/sway-ipc.*.sock 2>/dev/null | tail -1)"; export SWAYSOCK
fi

PLEGADO="${XDG_RUNTIME_DIR:-/tmp}/lekso-carpetas.plegado"

# Espera a que exista una ventana que cumpla el criterio y le pone una marca.
marcar() {
  i=0
  while [ $i -lt 40 ]; do
    swaymsg "[$1] mark --add $2" 2>/dev/null | grep -q '"success": true' && return 0
    i=$((i + 1)); sleep 0.25
  done
  return 1
}

restaurar_previo() {
  # Aparta todas las ventanas a un espacio de trabajo auxiliar (el 9) y cierra las de zona.
  swaymsg '[app_id=".*"] move container to workspace number 9' >/dev/null 2>&1
  swaymsg '[class=".*"] move container to workspace number 9' >/dev/null 2>&1
  swaymsg '[app_id="^lekso-"] kill' >/dev/null 2>&1
  swaymsg '[con_mark="explorador"] kill' >/dev/null 2>&1
  sleep 1
}

montar() {
  swaymsg 'workspace number 1; layout splith' >/dev/null
  rm -f "$PLEGADO"
  # Archivos de LeksSO: «Carpetas» a la izquierda y el contenido de la carpeta en el centro (lo que se ve
  # cuando no hay ninguna app abierta). Si no arrancara, se vuelve al explorador clásico y a un centro vacío.
  swaymsg exec lekso-archivos >/dev/null
  if marcar 'app_id="lekso-archivos" title="^Carpetas$"' explorador && marcar 'app_id="lekso-archivos" title="^Archivos"' centro; then
    swaymsg '[con_mark="explorador"] move left; [con_mark="explorador"] move left' >/dev/null
  else
    swaymsg exec pcmanfm-qt >/dev/null
    marcar 'app_id="pcmanfm-qt" workspace="1"' explorador
    swaymsg exec "lekso-term -T \"Operativa usuario\" --app-id lekso-centro -e sh -c 'clear; printf \"\n  Aquí se abre la app que estés usando.\n\"; exec sleep infinity'" >/dev/null
    marcar 'app_id="lekso-centro"' centro
  fi
  swaymsg exec "lekso-term -T \"Panel de la IA\" --app-id lekso-ia -e python3 /usr/local/lib/lekso-ia/panel.py" >/dev/null
  marcar 'app_id="lekso-ia"' panel-ia

  # Terminal debajo del centro
  swaymsg '[con_mark="centro"] focus; splitv' >/dev/null
  swaymsg exec "lekso-term -T Terminal --app-id lekso-terminal" >/dev/null
  marcar 'app_id="lekso-terminal"' terminal
  # La columna central (centro + terminal) lleva su marca: sirve para devolver las carpetas a su sitio al desplegar
  swaymsg '[con_mark="terminal"] focus; focus parent; mark --add columna' >/dev/null
  # El centro pasa a ser un grupo de pestañas
  swaymsg '[con_mark="centro"] focus; splith; layout tabbed' >/dev/null

  # La zona de la derecha pasa a ser un grupo de pestañas: panel de la IA y asistente
  swaymsg '[con_mark="panel-ia"] focus; splith; layout tabbed' >/dev/null

  # Proporciones
  swaymsg '[con_mark="explorador"] resize set width 22 ppt' >/dev/null
  swaymsg '[con_mark="panel-ia"] resize set width 26 ppt' >/dev/null
  swaymsg '[con_mark="terminal"] resize set height 26 ppt' >/dev/null

  # A partir de ahora, todo lo que abra el usuario va al centro (la regla se añade una sola vez)
  marca="${XDG_RUNTIME_DIR:-/tmp}/lekso-zonas.regla"
  if [ ! -e "$marca" ]; then
    swaymsg 'for_window [app_id="^(?!lekso-).*"] move container to mark centro' >/dev/null
    : > "$marca"
  fi
  swaymsg '[con_mark="centro"] focus' >/dev/null
}

plegar() {
  if [ -e "$PLEGADO" ]; then
    # vuelve del escondite como ventana normal, se coloca junto a la columna central y pasa a su izquierda
    swaymsg '[con_mark="explorador"] scratchpad show' >/dev/null
    swaymsg '[con_mark="explorador"] floating disable' >/dev/null
    swaymsg '[con_mark="explorador"] move container to mark columna' >/dev/null
    swaymsg '[con_mark="explorador"] move left' >/dev/null
    swaymsg '[con_mark="explorador"] resize set width 22 ppt' >/dev/null
    rm -f "$PLEGADO"
  else
    swaymsg '[con_mark="explorador"] move scratchpad' >/dev/null && : > "$PLEGADO"
  fi
  # el sitio que se gana o se pierde es de la zona central: el panel de la IA conserva su ancho
  swaymsg '[con_mark="panel-ia"] resize set width 26 ppt' >/dev/null
  swaymsg '[con_mark="centro"] focus' >/dev/null 2>&1
}

if [ "${1:-}" = "--plegar" ]; then
  plegar
elif [ "${1:-}" = "--restaurar" ]; then
  restaurar_previo
  montar
  # Devuelve las apps del usuario a la zona central
  swaymsg '[workspace="9"] move container to mark centro' >/dev/null 2>&1
  swaymsg '[con_mark="centro"] focus' >/dev/null 2>&1
else
  montar
fi
