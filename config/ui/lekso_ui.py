"""Piezas comunes de las ventanas propias de LeksSO (menú de aplicaciones, energía...)."""
import os

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
