"""Piezas comunes de las ventanas propias de LekSO (menú de aplicaciones, energía...)."""
import os

ESTILO = """
QWidget { background: #10151b; color: #dfe6ee; font-size: 14px; }
QLabel#titulo { font-size: 16px; font-weight: bold; color: #4cc3e0; }
QLabel#nota { color: #8a98a8; font-size: 12px; }
QLineEdit { background: #1c2530; border: 1px solid #2a3644; padding: 8px 10px; color: #dfe6ee; }
QLineEdit:focus { border: 1px solid #4cc3e0; }
QPushButton#cerrar { background: transparent; color: #8a98a8; border: none; font-size: 20px; padding: 2px 12px; }
QPushButton#cerrar:hover { background: #3a1d1d; color: #f08a82; }
QPushButton#accion { background: #1c2530; border: 1px solid #2a3644; padding: 12px 14px; text-align: left; }
QPushButton#accion:hover { background: #16384a; border: 1px solid #4cc3e0; }
QPushButton#accion:disabled { color: #5a6877; background: #141b23; }
QPushButton#peligro { background: #1c2530; border: 1px solid #2a3644; padding: 12px 14px; text-align: left; }
QPushButton#peligro:hover { background: #3a1d1d; border: 1px solid #f08a82; }
QListWidget { background: #10151b; border: none; outline: none; }
QListWidget::item { padding: 8px 10px; border: none; }
QListWidget::item:hover { background: #1c2530; }
QListWidget::item:selected { background: #16384a; color: #dfe6ee; }
QMessageBox { background: #10151b; }
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
