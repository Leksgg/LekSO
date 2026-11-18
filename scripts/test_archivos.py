"""Archivos de LeksSO: navegación y operaciones con archivos, sin pantalla (Qt en modo «offscreen»).
Incluye las barreras contra copiar o mover la raíz del disco y una carpeta dentro de sí misma.
Uso: python3 scripts/test_archivos.py   (en un equipo LeksSO: necesita PySide6 y gio)
"""
import importlib.machinery, importlib.util, os, sys, tempfile, shutil
os.environ["QT_QPA_PLATFORM"] = "offscreen"
_aqui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "bin", "leksso-archivos")
l = importlib.machinery.SourceFileLoader("arch", _aqui if os.path.exists(_aqui) else "/usr/local/bin/leksso-archivos")
m = importlib.util.module_from_spec(importlib.util.spec_from_loader("arch", l)); l.exec_module(m)
from PySide6 import QtWidgets, QtCore
app = QtWidgets.QApplication([])
e = m.Explorador()
e.v_arbol.show(); e.v_lista.show()
d = tempfile.mkdtemp(dir=os.path.expanduser("~"))
os.makedirs(d + "/a/sub"); open(d + "/a/uno.txt", "w").write("1"); os.makedirs(d + "/b")
def espera(ms=400):
    t = QtCore.QEventLoop(); QtCore.QTimer.singleShot(ms, t.quit); t.exec()
_mal = []
def ok(t, c):
    print(("OK  " if c else "MAL ") + t)
    if not c:
        _mal.append(t)
e.ir(d + "/a")
e.lista.selectAll(); e.copiar(False)                      # antes de que cargue: no debe colarse la raíz
ok("seleccionar todo sin cargar no coge la raíz", all(os.path.dirname(r) == d + "/a" for r in e.portapapeles[0]))
e.portapapeles = (["/"], False); e.ir(d + "/b"); e.pegar()
ok("pegar ignora la raíz", os.listdir(d + "/b") == [])
e.portapapeles = ([d + "/a"], False); e.ir(d + "/a/sub"); e.pegar()
ok("no copia una carpeta dentro de sí misma", os.listdir(d + "/a/sub") == [])
e.portapapeles = ([], False)
e.ir(d + "/a"); espera(2000)
ok("navega y pone título", e.v_lista.windowTitle() == "Archivos · a" and e.ruta == d + "/a")
ok("árbol sigue a la lista", e.m_arbol.filePath(e.arbol.currentIndex()) == d + "/a")
e.portapapeles = ([d + "/a/uno.txt", d + "/a/sub"], False); e.ir(d + "/b"); e.pegar(); espera()
ok("copia archivo y carpeta", os.path.isfile(d + "/b/uno.txt") and os.path.isdir(d + "/b/sub"))
e.portapapeles = ([d + "/a/uno.txt"], False); e.pegar()
ok("pegar no pisa: crea (2)", os.path.isfile(d + "/b/uno (2).txt") and open(d + "/b/uno.txt").read() == "1")
e.portapapeles = ([d + "/a/uno.txt"], True); e.ir(d); e.pegar()
ok("cortar mueve", os.path.isfile(d + "/uno.txt") and not os.path.exists(d + "/a/uno.txt"))
e.portapapeles = ([d + "/a"], True); e.ir(d + "/a/sub"); e.pegar()
ok("no mueve una carpeta dentro de sí misma", os.path.isdir(d + "/a/sub") and not os.path.exists(d + "/a/sub/a"))
e.ir(d); e.subir()
ok("subir", e.ruta == os.path.dirname(d))
e.ir("/root")
ok("carpeta sin permiso: no entra", e.ruta == os.path.dirname(d))
e.ir(d + "/b"); espera(2000)
i = e.m_lista.index(d + "/b/uno (2).txt"); e.lista.setCurrentIndex(i); e.lista.selectionModel().select(i, QtCore.QItemSelectionModel.ClearAndSelect)
e.seleccion = lambda: [d + "/b/uno (2).txt"]; e.a_papelera(); espera()
ok("a la papelera (recuperable)", not os.path.exists(d + "/b/uno (2).txt") and any("uno (2).txt" in x for x in os.listdir(os.path.expanduser("~/.local/share/Trash/files"))))
print("lugares:", [n for n, _ in m.lugares()[0]])
shutil.rmtree(d)
sys.exit(1 if _mal else 0)
