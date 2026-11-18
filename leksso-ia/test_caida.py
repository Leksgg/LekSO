"""Corte brusco: se mata el permisor (SIGKILL) con muchas escrituras en vuelo y se comprueba que
no quedan temporales, que el registro sigue siendo válido y que al volver se puede deshacer.
Uso: PYTHONPATH=. python3 test_caida.py"""
import os as _os
_os.environ["LEKSSO_SIN_AVISOS"] = "1"   # sin notificaciones de escritorio durante las pruebas
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

tmp = Path(tempfile.mkdtemp(prefix="leksso-caida-"))
casa, run = tmp / "casa", tmp / "run"
(casa / "proy").mkdir(parents=True)
run.mkdir(mode=0o700)
env = {**os.environ, "HOME": str(casa), "XDG_RUNTIME_DIR": str(run)}
aqui = Path(__file__).parent


def lanzar():
    p = subprocess.Popen([sys.executable, str(aqui / "permisor.py")], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        if (run / "leksso-control.sock").exists() and (run / "leksso-ia.sock").exists():
            time.sleep(0.2)
            return p
        time.sleep(0.1)
    raise SystemExit("el permisor no arrancó")


def hablar(sock, msg):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(10)
        s.connect(str(run / sock))
        s.sendall((json.dumps(msg) + "\n").encode())
        return json.loads(s.makefile().readline())


fallos = []
p = lanzar()
r = hablar("leksso-ia.sock", {"op": "pedir", "titulo": "caida", "carpetas": {str(casa / "proy"): "rw"}})
hablar("leksso-control.sock", {"op": "aprobar", "pid": r["pid"]})
tarea = hablar("leksso-ia.sock", {"op": "estado", "pid": r["pid"]})["tarea"]
(casa / "proy" / "g.txt").write_text("original")


def escribir(k):
    try:
        hablar("leksso-ia.sock", {"op": "escribir", "tarea": tarea, "ruta": str(casa / "proy" / "g.txt"),
                                  "texto": ("x" * 300000) + str(k)})
    except Exception:
        pass


hs = [threading.Thread(target=escribir, args=(k,)) for k in range(150)]
[h.start() for h in hs]
time.sleep(0.15)
os.kill(p.pid, signal.SIGKILL)
p.wait()
[h.join() for h in hs]

huerfanos = [x.name for x in (casa / "proy").iterdir() if x.name.startswith(".leksso-tmp")]
contenido = (casa / "proy" / "g.txt").read_text()
if huerfanos:
    print(f"AVISO: {len(huerfanos)} temporales huérfanos tras el corte (se limpian al volver)")
if not (contenido == "original" or contenido.startswith("x" * 300000)):
    fallos.append("g.txt quedó a medias (ni original ni una escritura completa)")
malas = 0
for linea in (casa / ".leksso" / "registro.jsonl").read_text().splitlines():
    try:
        json.loads(linea)
    except ValueError:
        malas += 1
if malas > 1:                           # como mucho la última línea puede quedar cortada
    fallos.append(f"{malas} líneas de registro corruptas")

for f in (run).glob("*.sock"):
    f.unlink()
p = lanzar()
# La tarea ya no existe en memoria tras el reinicio: el registro firmado debe bastar para deshacer.
r = hablar("leksso-control.sock", {"op": "deshacer_tarea", "tarea": tarea, "forzar": True})
print(f"{r.get('n')} escrituras deshechas tras reiniciar el permisor")
if not r.get("ok") or r.get("n", 0) < 1:
    fallos.append(f"no se pudo deshacer tras el reinicio: {r}")
if (casa / "proy" / "g.txt").read_text() != "original":
    fallos.append("tras deshacer, g.txt no volvió al original")
p.kill()
shutil.rmtree(tmp, ignore_errors=True)
if fallos:
    print("FALLOS:\n- " + "\n- ".join(fallos))
    sys.exit(1)
print("sin fallos")
