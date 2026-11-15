#!/usr/bin/env bash
# Mide OBS grabando una escena fija y deja una línea CSV comparable con bench-obs.ps1 (Windows).
# Qué mide: fotogramas saltados por codificación, perdidos por render, retrasados, CPU y RAM
# medias de OBS y, si hay una NVIDIA, uso medio de GPU y del codificador (NVENC).
#
# Uso:  bench-obs.sh [SEGUNDOS] [COLECCION] [PERFIL]      (por defecto 120, "bench", "bench")
# Requisito: una colección de escenas y un perfil llamados igual en OBS, siempre los mismos
# en Windows y en LekSO (misma resolución, FPS, codificador y tasa de bits).
# Estado: sin probar con OBS real; la lectura del registro se probó con un registro de ejemplo.
set -euo pipefail
SEG="${1:-120}"; COL="${2:-bench}"; PER="${3:-bench}"
LOGS="${OBS_LOGS:-$HOME/.config/obs-studio/logs}"

parsear() {   # $1 = registro de OBS -> "saltados perdidos retrasados" (porcentaje de cada uno)
  local f="$1" s p r
  s=$(grep -oE 'skipped frames due to encoding lag: [0-9]+/[0-9]+ \([0-9.]+%\)' "$f" | tail -1 | grep -oE '[0-9.]+%' || echo 0%)
  p=$(grep -oE 'missed frames due to rendering lag: [0-9]+/[0-9]+ \([0-9.]+%\)' "$f" | tail -1 | grep -oE '[0-9.]+%' || echo 0%)
  r=$(grep -oE 'lagged frames due to rendering lag/stalls: [0-9]+/[0-9]+ \([0-9.]+%\)' "$f" | tail -1 | grep -oE '[0-9.]+%' || echo 0%)
  echo "${s:-0%} ${p:-0%} ${r:-0%}"
}
if [ "${1:-}" = "--parsear" ]; then parsear "$2"; exit 0; fi

command -v obs >/dev/null || { echo "OBS no está instalado" >&2; exit 1; }
ANTES=$(ls -t "$LOGS" 2>/dev/null | head -1 || true)
obs --collection "$COL" --profile "$PER" --startrecording --disable-shutdown-check >/dev/null 2>&1 &
PID=$!
sleep 15                                   # margen para que arranque y empiece a grabar
MUESTRAS=$((SEG / 2)); cpu=0; rss=0; gpu=0; enc=0
for _ in $(seq "$MUESTRAS"); do
  c=$(ps -o %cpu= -p "$PID" | tr -d ' '); r=$(ps -o rss= -p "$PID" | tr -d ' ')
  cpu=$(echo "$cpu + ${c:-0}" | bc -l); rss=$(echo "$rss + ${r:-0}" | bc -l)
  if command -v nvidia-smi >/dev/null; then
    g=$(nvidia-smi --query-gpu=utilization.gpu,utilization.encoder --format=csv,noheader,nounits | head -1)
    gpu=$(echo "$gpu + ${g%%,*}" | bc -l); enc=$(echo "$enc + ${g##*, }" | bc -l)
  fi
  sleep 2
done
kill -TERM "$PID" 2>/dev/null || true; wait "$PID" 2>/dev/null || true; sleep 2
LOG="$LOGS/$(ls -t "$LOGS" | head -1)"
[ "$(basename "$LOG")" = "$ANTES" ] && echo "AVISO: no hay registro nuevo de OBS" >&2
read -r SAL PER_ RET < <(parsear "$LOG")
printf 'sistema,segundos,cpu_media_pct,ram_media_mb,gpu_media_pct,nvenc_media_pct,saltados,perdidos,retrasados\n'
printf 'lekso,%s,%.1f,%.0f,%.1f,%.1f,%s,%s,%s\n' "$SEG" "$(echo "$cpu/$MUESTRAS" | bc -l)" \
  "$(echo "$rss/$MUESTRAS/1024" | bc -l)" "$(echo "$gpu/$MUESTRAS" | bc -l)" "$(echo "$enc/$MUESTRAS" | bc -l)" \
  "$SAL" "$PER_" "$RET"
