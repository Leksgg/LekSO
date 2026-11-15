"""Ronda de estabilidad y rendimiento del núcleo del permisor, acorde a los límites de la VM.
Uso: PYTHONPATH=. python3 estres.py [N]   (N = operaciones secuenciales, por defecto 2000)
Nada pasa de ~300 MB de datos ni de 8 hilos. Devuelve error si algo falla."""
import os as _os
_os.environ["LEKSO_SIN_AVISOS"] = "1"   # sin notificaciones de escritorio durante las pruebas
import os
import resource
import shutil
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

from nucleo import Nucleo, Denegado

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
fallos = []


def medir(nombre, f):
    t = time.perf_counter()
    r = f()
    print(f"{nombre:<46} {time.perf_counter() - t:8.2f} s")
    return r


def rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


tmp = Path(tempfile.mkdtemp(prefix="lekso-estres-"))
casa, proy = tmp / "casa", tmp / "casa" / "proy"
proy.mkdir(parents=True)
n = Nucleo(casa)
t = n.conceder("estrés", {str(proy): "rwd"}, ttl=7200)
print(f"RAM del proceso al inicio: {rss_mb():.0f} MB\n")

# 1. escrituras secuenciales con latencia por operación
lat = []
def secuencial():
    for i in range(N):
        t0 = time.perf_counter()
        n.escribir(t, str(proy / f"f{i % 200}.txt"), "x" * 4096 + str(i))
        lat.append((time.perf_counter() - t0) * 1000)
medir(f"{N} escrituras de 4 KB (200 archivos, con versiones)", secuencial)
lat.sort()
print(f"   latencia mediana {statistics.median(lat):.2f} ms, p95 {lat[int(len(lat) * .95)]:.2f} ms, máx {lat[-1]:.1f} ms")

# 2. concurrencia: 8 hilos, archivos distintos y un archivo compartido
def hilo(k):
    try:
        for i in range(150):
            n.escribir(t, str(proy / f"h{k}-{i}.txt"), f"{k}-{i}")
            n.escribir(t, str(proy / "compartido.txt"), f"{k}-{i}")
            n.leer(t, str(proy / f"h{k}-{i}.txt"))
    except Exception as e:
        fallos.append(f"hilo {k}: {type(e).__name__}: {e}")
def concurrente():
    hs = [threading.Thread(target=hilo, args=(k,)) for k in range(8)]
    [h.start() for h in hs]
    [h.join() for h in hs]
medir("8 hilos x 150 (escribir x2 + leer), archivo compartido", concurrente)
huerfanos = [p for p in proy.iterdir() if p.name.startswith(".lekso-tmp")]
if huerfanos:
    fallos.append(f"{len(huerfanos)} temporales huérfanos")
if (proy / "compartido.txt").read_text().count("-") != 1:
    fallos.append("compartido.txt corrupto")

# 3. archivos grandes: coste de guardar la versión previa
for mb in (1, 100):
    (proy / f"g{mb}.bin").write_text("a" * (mb * 1024 * 1024))
    medir(f"reescribir archivo de {mb} MB (copia previa)", lambda: n.escribir(t, str(proy / f"g{mb}.bin"), "b" * (mb * 1024 * 1024)))

# 4. registro: tamaño, validez y arranque con registro grande
lineas = n.registro.read_text().splitlines()
print(f"\nregistro: {len(lineas)} líneas, {n.registro.stat().st_size / 1e6:.1f} MB")
import json
for l in lineas:
    try:
        json.loads(l)
    except ValueError:
        fallos.append("línea de registro corrupta")
        break
for _ in range(60):                      # lo que hace el panel: pedir el final cada segundo
    n.ultimas(60)
medir("60 lecturas del final del registro (panel)", lambda: [n.ultimas(60) for _ in range(60)])
medir("arranque leyendo el registro completo", lambda: Nucleo(casa))

# 5. deshacer toda la tarea
hechas = medir("deshacer toda la tarea", lambda: n.deshacer_tarea(t, forzar=True))
print(f"   {hechas} acciones deshechas")
print(f"\nversiones en disco: {sum(f.stat().st_size for f in (n.versiones).rglob('*') if f.is_file()) / 1e6:.0f} MB")
print(f"RAM máxima del proceso: {rss_mb():.0f} MB")
shutil.rmtree(tmp, ignore_errors=True)
if fallos:
    print("\nFALLOS:\n- " + "\n- ".join(fallos))
    sys.exit(1)
print("\nsin fallos")
