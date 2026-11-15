#!/bin/sh
# Monta las zonas de LekSO: explorador | centro (pestañas) + terminal | panel de IA.
# Las apps que abra el usuario van siempre a la zona central.
# Uso: lekso-zonas              monta las zonas al iniciar la sesión
#      lekso-zonas --restaurar  vuelve a la vista por defecto sin cerrar las apps del usuario

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
  swaymsg exec pcmanfm-qt >/dev/null
  marcar 'app_id="pcmanfm-qt" workspace="1"' explorador
  swaymsg exec "foot -T \"Operativa usuario\" --app-id lekso-centro -e sh -c 'clear; printf \"\n  Operativa usuario\n\n  Aquí se abre la app que estés usando.\n  Una por vez, a pantalla completa de esta zona.\n\"; exec sleep infinity'" >/dev/null
  marcar 'app_id="lekso-centro"' centro
  swaymsg exec "foot -T \"Panel de la IA\" --app-id lekso-ia -e python3 /usr/local/lib/lekso-ia/panel.py" >/dev/null
  marcar 'app_id="lekso-ia"' panel-ia

  # Terminal debajo del centro
  swaymsg '[con_mark="centro"] focus; splitv' >/dev/null
  swaymsg exec "foot -T Terminal --app-id lekso-terminal" >/dev/null
  marcar 'app_id="lekso-terminal"' terminal
  # El centro pasa a ser un grupo de pestañas
  swaymsg '[con_mark="centro"] focus; splith; layout tabbed' >/dev/null

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

if [ "${1:-}" = "--restaurar" ]; then
  restaurar_previo
  montar
  # Devuelve las apps del usuario a la zona central
  swaymsg '[workspace="9"] move container to mark centro' >/dev/null 2>&1
  swaymsg '[con_mark="centro"] focus' >/dev/null 2>&1
else
  montar
fi
