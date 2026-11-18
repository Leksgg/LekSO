"""Piezas comunes de las ventanas propias de LeksSO (menú de aplicaciones, energía...)."""
import json
import os
import re

# ---- tema de color ----------------------------------------------------------------------------
# Los colores de abajo son los del tema BASE (Marea). Si el usuario eligió otro (leksso-tema), cada color
# se cambia por el del mismo papel en el tema activo, al abrir la ventana.
BASE = "marea"
_AQUI = os.path.dirname(os.path.abspath(__file__))
_CARPETAS = ("/usr/local/share/leksso/temas", os.path.join(_AQUI, "..", "tema"))
_HEX = re.compile(r"(?<![0-9A-Za-z])[0-9A-Fa-f]{6,8}(?![0-9A-Za-z])")


def tema_activo():
    try:
        nombre = open(os.path.expanduser("~/.config/leksso/tema"), encoding="utf-8").read().strip()
    except OSError:
        return BASE
    return nombre if nombre.isalnum() else BASE


def tokens(nombre):
    """Colores de un tema por papel ({'bg': '021012', ...}) o {} si no existe."""
    for carpeta in _CARPETAS:
        try:
            datos = json.load(open(os.path.join(carpeta, nombre + ".json"), encoding="utf-8"))
            return {k: v.lstrip("#").lower() for k, v in datos["colores"].items()}
        except (OSError, ValueError, KeyError):
            continue
    return {}


def mapa_de_colores(desde, hasta):
    a, b = tokens(desde), tokens(hasta)
    return {a[k]: b[k] for k in a if k in b}


def recolorear(texto, mapa):
    """Cambia cada color de `texto` según `mapa` (hex sin # → hex sin #). Vale con o sin almohadilla y en
    formato de 8 cifras: ARGB de Qt (ffRRGGBB) o RGBA con el alfa al final (RRGGBBaa)."""
    def cambia(m):
        s, minus = m.group(0), m.group(0).lower()
        if len(s) == 6:
            return mapa.get(minus, s)
        if len(s) == 8:
            if minus[:2] == "ff" and minus[2:] in mapa:
                return "ff" + mapa[minus[2:]]
            if minus[:6] in mapa:
                return mapa[minus[:6]] + minus[6:]
        return s
    return _HEX.sub(cambia, texto)


def pintar(texto):
    """Pasa una hoja de estilo escrita con los colores base a los del tema activo."""
    activo = tema_activo()
    if activo == BASE:
        return texto
    return recolorear(texto, mapa_de_colores(BASE, activo))


ESTILO = """
QWidget { background: #021012; color: #e3edef; font-size: 14px; }
QLabel#titulo { font-size: 16px; font-weight: bold; color: #00c4bf; }
QLabel#nota { color: #94a1a3; font-size: 12px; }
QLineEdit { background: #112123; border: 1px solid #25393c; padding: 8px 10px; color: #e3edef; }
QLineEdit:focus { border: 1px solid #00c4bf; }
QPushButton#cerrar { background: transparent; color: #94a1a3; border: none; font-size: 20px; padding: 2px 12px; }
QPushButton#cerrar:hover { background: #3f1a13; color: #ff735a; }
QPushButton#accion { background: #112123; border: 1px solid #25393c; padding: 12px 14px; text-align: left; }
QPushButton#accion:hover { background: #003635; border: 1px solid #00c4bf; }
QPushButton#accion:disabled { color: #667576; background: #051416; }
QPushButton#peligro { background: #112123; border: 1px solid #25393c; padding: 12px 14px; text-align: left; }
QPushButton#peligro:hover { background: #3f1a13; border: 1px solid #ff735a; }
QListWidget { background: #021012; border: none; outline: none; }
QListWidget::item { padding: 8px 10px; border: none; }
QListWidget::item:hover { background: #112123; }
QListWidget::item:selected { background: #003635; color: #e3edef; }
QMessageBox { background: #021012; }
"""
ESTILO_BASE = ESTILO  # sin recolorear: para volver a pintar una ventana abierta al cambiar de tema
ESTILO = pintar(ESTILO)


def alternar(nombre):
    """Si ya hay una ventana abierta de este programa, la cierra (el botón actúa de interruptor)
    y devuelve True. Si no, se registra y devuelve False."""
    ruta = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), f"{nombre}.pid")
    try:
        pid = int(open(ruta).read())
        os.kill(pid, 0)
        if nombre in open(f"/proc/{pid}/cmdline").read():
            os.kill(pid, 15)
            return True
    except (OSError, ValueError):
        pass
    with open(ruta, "w") as f:
        f.write(str(os.getpid()))
    return False
