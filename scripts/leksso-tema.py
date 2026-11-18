#!/usr/bin/env python3
"""Cambia el tema de color de todo el escritorio de LeksSO, sin reiniciar.

Los temas (Marea, Pizarra...) son archivos de colores por papel en /usr/local/share/leksso/temas. Aquí se
cambian, en la configuración del usuario, los colores del tema actual por los del nuevo (barra, terminal,
menús, avisos, bordes de ventana, bloqueo, colores de Qt) y se recarga lo que se puede recargar al momento.
Las ventanas propias (Archivos, Ajustes...) leen el tema activo cada vez que se abren.

Uso:
  leksso-tema listar            temas disponibles
  leksso-tema actual            el que está activo
  leksso-tema aplicar <tema>    cambia a ese tema
  leksso-tema reaplicar         vuelve a poner el tema elegido (lo usa la instalación tras copiar la configuración base)
"""
import os
import subprocess
import sys

sys.path.insert(0, "/usr/local/lib/leksso-ui")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "ui"))
from leksso_ui import BASE, _CARPETAS, mapa_de_colores, recolorear, tema_activo, tokens  # noqa: E402

CASA = os.path.expanduser("~")
ESTADO = os.path.join(CASA, ".config", "leksso", "tema")
# archivos del usuario que llevan colores (relativos a ~)
ARCHIVOS = [
    ".config/waybar/style.css", ".config/foot/foot.ini", ".config/kitty/kitty.conf", ".config/sway/config",
    ".config/mako/config", ".config/fuzzel/fuzzel.ini", ".config/swaylock/config",
    ".config/qt6ct/colors/leksso.conf", ".config/pcmanfm-qt/default/settings.conf",
    ".local/share/themes/LeksSO/openbox-3/themerc",
]


def disponibles():
    nombres = set()
    for carpeta in _CARPETAS:
        try:
            nombres |= {f[:-5] for f in os.listdir(carpeta) if f.endswith(".json") and f[:-5].isalnum()}
        except OSError:
            pass
    return sorted(nombres)


def recolorear_archivos(mapa):
    cambiados = 0
    for rel in ARCHIVOS:
        ruta = os.path.join(CASA, rel)
        try:
            texto = open(ruta, encoding="utf-8", newline="").read()
        except (OSError, UnicodeDecodeError):
            continue
        nuevo = recolorear(texto, mapa)
        if nuevo != texto:
            tmp = ruta + ".nuevo"
            open(tmp, "w", encoding="utf-8", newline="").write(nuevo)
            os.replace(tmp, ruta)
            cambiados += 1
    return cambiados


def recargar():
    ordenes = [["pkill", "-USR2", "waybar"], ["makoctl", "reload"], ["swaymsg", "reload"], ["labwc", "--reconfigure"]]
    for o in ordenes:
        try:
            subprocess.run(o, capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass


def guardar(nombre):
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    open(ESTADO, "w", encoding="utf-8").write(nombre + "\n")


def aplicar(destino, desde):
    if destino not in disponibles() or not tokens(destino):
        sys.exit(f"Tema desconocido: {destino}. Disponibles: {', '.join(disponibles())}")
    mapa = {} if desde == destino else mapa_de_colores(desde, destino)
    n = recolorear_archivos(mapa) if mapa else 0
    guardar(destino)
    if n:
        recargar()
    return n


def main(a):
    if not a or a[0] in ("-h", "--help"):
        sys.exit(__doc__)
    if a[0] == "listar":
        print("\n".join(disponibles()))
    elif a[0] == "actual":
        print(tema_activo())
    elif a[0] == "aplicar" and len(a) == 2:
        n = aplicar(a[1], tema_activo())
        print(f"Tema {a[1]} aplicado ({n} archivos). Las ventanas ya abiertas lo estrenan al abrirlas de nuevo.")
    elif a[0] == "reaplicar":
        # la instalación acaba de copiar la configuración base (colores de Marea): se vuelve a poner el tema elegido
        elegido = tema_activo()
        n = aplicar(elegido, BASE) if elegido != BASE else 0
        print(f"Tema {elegido} puesto de nuevo ({n} archivos).")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
