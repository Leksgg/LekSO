"""Estado del equipo para la IA: una foto de solo lectura (memoria, disco, CPU, carga, batería, temperatura
y los procesos que más consumen). No expone archivos, argumentos de procesos ni nada del usuario: solo cifras
y el nombre corto de cada proceso. Lo sirve el permisor (fuera de la caja); la IA no puede leer /proc por sí misma.
"""
import glob
import os
import shutil
import time


def _leer(ruta):
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _mb(kb):
    return round(kb / 1024)


def _memoria():
    d = {}
    for linea in _leer("/proc/meminfo").splitlines():
        k, _, v = linea.partition(":")
        try:
            d[k] = int(v.split()[0])
        except (ValueError, IndexError):
            pass
    total, libre = d.get("MemTotal", 0), d.get("MemAvailable", 0)
    st, sl = d.get("SwapTotal", 0), d.get("SwapFree", 0)
    return {"ram_total_mb": _mb(total), "ram_usada_mb": _mb(total - libre), "ram_disponible_mb": _mb(libre),
            "ram_usada_pct": round(100 * (total - libre) / total, 1) if total else None,
            "swap_total_mb": _mb(st), "swap_usada_mb": _mb(st - sl)}


def _tiempos_cpu():
    campos = _leer("/proc/stat").split("\n", 1)[0].split()[1:]
    v = [int(x) for x in campos] if campos else [0]
    inactivo = (v[3] + v[4]) if len(v) > 4 else 0
    return sum(v), inactivo


def _cpu(pausa=0.4):
    t1, i1 = _tiempos_cpu()
    time.sleep(pausa)
    t2, i2 = _tiempos_cpu()
    uso = round(100 * (1 - (i2 - i1) / (t2 - t1)), 1) if t2 > t1 else None
    modelo = ""
    for linea in _leer("/proc/cpuinfo").splitlines():
        if linea.startswith("model name"):
            modelo = linea.partition(":")[2].strip()
            break
    carga = _leer("/proc/loadavg").split()[:3]
    return {"modelo": modelo, "hilos": os.cpu_count(), "uso_pct": uso,
            "carga_1_5_15_min": [float(x) for x in carga] if len(carga) == 3 else None}


def _discos():
    vistos, salida = set(), []
    for linea in _leer("/proc/mounts").splitlines():
        p = linea.split()
        if len(p) < 3 or not p[0].startswith("/dev/") or p[2] in ("squashfs", "iso9660"):
            continue
        if p[0] in vistos:
            continue
        vistos.add(p[0])
        punto = p[1].replace("\\040", " ")
        try:
            u = shutil.disk_usage(punto)
        except OSError:
            continue
        gb = 1024 ** 3
        salida.append({"montado_en": punto, "total_gb": round(u.total / gb, 1), "usado_gb": round(u.used / gb, 1),
                       "libre_gb": round(u.free / gb, 1), "usado_pct": round(100 * u.used / u.total, 1) if u.total else None})
    return salida


def _procesos(n=8):
    filas = []
    for d in glob.glob("/proc/[0-9]*"):
        nombre, rss = "", 0
        for linea in _leer(d + "/status").splitlines():
            if linea.startswith("Name:"):
                nombre = linea.split(None, 1)[1].strip() if len(linea.split(None, 1)) > 1 else ""
            elif linea.startswith("VmRSS:"):
                try:
                    rss = int(linea.split()[1])
                except (ValueError, IndexError):
                    pass
        if rss:
            filas.append((rss, nombre))
    agrupado = {}
    for rss, nombre in filas:
        agrupado[nombre] = agrupado.get(nombre, 0) + rss
    orden = sorted(agrupado.items(), key=lambda x: -x[1])[:n]
    return {"total": len(filas), "mas_memoria": [{"proceso": k, "ram_mb": _mb(v)} for k, v in orden]}


def _bateria():
    for d in glob.glob("/sys/class/power_supply/BAT*"):
        try:
            return {"carga_pct": int(_leer(d + "/capacity").strip()), "estado": _leer(d + "/status").strip()}
        except ValueError:
            continue
    return None


def _temperaturas():
    salida = []
    for d in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
        try:
            salida.append({"zona": _leer(d + "/type").strip(), "grados": round(int(_leer(d + "/temp").strip()) / 1000, 1)})
        except ValueError:
            continue
    return salida[:8]


def estado():
    """Foto del equipo en este momento. Tarda medio segundo (mide el uso de CPU entre dos lecturas)."""
    try:
        encendido = round(float(_leer("/proc/uptime").split()[0]) / 3600, 1)
    except (ValueError, IndexError):
        encendido = None
    return {"ok": True, "sistema": "LeksSO " + _leer("/etc/leksso-release").strip(), "nucleo": os.uname().release,
            "encendido_horas": encendido, "memoria": _memoria(), "cpu": _cpu(), "discos": _discos(),
            "procesos": _procesos(), "bateria": _bateria(), "temperaturas": _temperaturas()}


if __name__ == "__main__":
    import json
    print(json.dumps(estado(), ensure_ascii=False, indent=1))
