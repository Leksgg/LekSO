#!/usr/bin/env bash
# Estado de la IA para la barra superior (waybar). Devuelve JSON.
# Reposo: no hay modelo cargado en memoria. Activa: hay un modelo cargado en Ollama.
if ! command -v ollama >/dev/null 2>&1; then
  echo '{"text":"IA · sin instalar","class":"sin-instalar","tooltip":"Ollama no está instalado"}'
  exit 0
fi
cargado="$(ollama ps 2>/dev/null | tail -n +2 | awk 'NR==1 {print $1}')"
if [ -n "$cargado" ]; then
  echo "{\"text\":\"IA · activa\",\"class\":\"activa\",\"tooltip\":\"Modelo cargado: $cargado\"}"
else
  echo '{"text":"IA · reposo","class":"reposo","tooltip":"Ningún modelo cargado: no consume memoria"}'
fi
