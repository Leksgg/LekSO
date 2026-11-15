#!/usr/bin/env python3
"""Gestor de modelos de LekSO sobre Ollama. Sin dependencias.

Estado normal: ningún modelo cargado, cero RAM. Se carga al pedirlo y se descarga
al terminar o tras la inactividad (OLLAMA_KEEP_ALIVE, 5 minutos por defecto).

  modelo.py estado            JSON para waybar (IA · sin instalar / reposo / activa)
  modelo.py ram               RAM libre y modelo cargado, en texto
  modelo.py lista             modelos instalados con su tamaño
  modelo.py cargar NOMBRE     avisa si no cabe en la RAM libre; carga si cabe (o con --forzar)
  modelo.py descargar         descarga ya el modelo de la memoria
"""
import json
import os
import shutil
import sys
import urllib.request

HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
URL = HOST if HOST.startswith("http") else "http://" + HOST
KEEP_ALIVE = os.environ.get("LEKSO_KEEP_ALIVE", "5m")
MARGEN = 1.5 * 1024 ** 3        # RAM que se deja libre para el sistema


def api(ruta, datos=None, espera=5):
    peticion = urllib.request.Request(URL + ruta, method="POST" if datos is not None else "GET",
                                      data=json.dumps(datos).encode() if datos is not None else None)
    with urllib.request.urlopen(peticion, timeout=espera) as r:
        return json.loads(r.read() or b"{}")


def ollama_instalado():
    return shutil.which("ollama") is not None


def ollama_responde():
    try:
        api("/api/version", espera=1)
        return True
    except OSError:
        return False


def ram():
    datos = {}
    for linea in open("/proc/meminfo"):
        k, v = linea.split(":")
        datos[k] = int(v.split()[0]) * 1024
    return datos["MemTotal"], datos["MemAvailable"]


def cargados():
    return api("/api/ps").get("models", []) if ollama_responde() else []


def instalados():
    return api("/api/tags").get("models", [])


def gb(b):
    return f"{b / 1024 ** 3:.1f} GB"


def estado_barra():
    if not ollama_instalado():
        return {"text": "IA · sin instalar", "class": "sin-instalar", "tooltip": "Ollama no está instalado"}
    c = cargados()
    if c:
        m = c[0]
        return {"text": "IA · activa", "class": "activa",
                "tooltip": f"Modelo cargado: {m['name']} ({gb(m.get('size', 0))} en memoria)"}
    return {"text": "IA · reposo", "class": "reposo", "tooltip": "Ningún modelo cargado: no consume memoria"}


def cargar(nombre, forzar=False):
    tam = next((m["size"] for m in instalados() if m["name"].split(":")[0] == nombre.split(":")[0]
                and (":" not in nombre or m["name"] == nombre)), None)
    if tam is None:
        return False, f"El modelo {nombre} no está instalado."
    _, libre = ram()
    if tam + MARGEN > libre and not forzar:
        return False, (f"{nombre} ocupa {gb(tam)} y solo hay {gb(libre)} libres "
                       f"(se dejan {gb(MARGEN)} al sistema). Usa --forzar si lo quieres igualmente.")
    api("/api/generate", {"model": nombre, "keep_alive": KEEP_ALIVE}, espera=300)
    return True, f"{nombre} cargado; se descarga solo tras {KEEP_ALIVE} sin usarse."


def descargar():
    c = cargados()
    for m in c:
        api("/api/generate", {"model": m["name"], "keep_alive": 0})
    return len(c)


def main(a):
    c = a[0] if a else "estado"
    if c == "estado":
        print(json.dumps(estado_barra(), ensure_ascii=False))
    elif c == "ram":
        total, libre = ram()
        print(f"RAM: {gb(total - libre)} usados de {gb(total)} ({gb(libre)} libres)")
        for m in cargados():
            print(f"Modelo cargado: {m['name']} ({gb(m.get('size', 0))})")
    elif c == "lista":
        for m in instalados():
            print(f"{m['name']}  {gb(m['size'])}")
    elif c == "cargar":
        ok, msg = cargar(a[1], "--forzar" in a)
        print(msg)
        sys.exit(0 if ok else 1)
    elif c == "descargar":
        print(f"{descargar()} modelo(s) descargado(s) de la memoria.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
