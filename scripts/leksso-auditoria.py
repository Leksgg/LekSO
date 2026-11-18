#!/usr/bin/env python3
"""Registro de instalaciones de LeksSO: qué programas se han instalado, cómo y de dónde.

Se instala como /usr/local/bin/leksso-auditoria. Lo llaman, como root, los ganchos de apt (antes y después de cada
instalación) y un temporizador que vigila lo que aparece fuera de apt. La ventana Seguridad de Ajustes lo lee con sudo.

Qué es y qué no es
  - Es un REGISTRO de lo ocurrido. Cada línea lleva el origen con un nivel de certeza:
      confirmado   lo prueba quien lo hizo: el catálogo de LeksSO, las actualizaciones de LeksSO o de seguridad, la IA
                   (su grupo de control) o una sesión SSH (el proceso viene de sshd)
      inferido     se deduce del contexto (p. ej. «desde un terminal local»); un script o un programa podrían haberlo lanzado
      desconocido  no hay contexto, o apareció fuera de apt sin que nadie lo anotara
    Nunca se pone «usuario» por defecto: sin pruebas es «desconocido».
  - Es encadenado: cada línea incluye el hash de la anterior y el archivo es de solo añadir (chattr +a). Detecta
    ediciones a medias; NO impide que quien tenga permisos de administrador lo apague o lo borre (se ve en el sello).
  - La IA solo puede leerlo si el usuario lo aprueba en el panel; no puede tocarlo (permisor y servicio de administración).

Uso (root salvo estado y barra)
  leksso-auditoria listar [--ultimos N] [--no-confirmados]   registros en JSON
  leksso-auditoria verificar                                   comprueba la cadena y los sellos
  leksso-auditoria revisar N                                   marca la entrada N como revisada
  leksso-auditoria anotar --nombre X --modo M --origen O       lo usan los instaladores propios (npm, scripts)
  leksso-auditoria foto                                        busca programas nuevos fuera de apt (temporizador)
  leksso-auditoria gancho pre|post                             lo llama apt
  leksso-auditoria estado | barra                              resumen público (no hace falta ser root)
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import pwd
import re
import subprocess
import sys

VERSION = 1
PRUEBAS = os.geteuid() != 0         # las variables de prueba solo valen si NO eres root
RAIZ = os.environ.get("LEKSSO_AUDITORIA_RAIZ", "") if PRUEBAS else ""
DIR = RAIZ + "/var/lib/leksso-auditoria"
REGISTRO = DIR + "/instalaciones.jsonl"
FOTO = DIR + "/foto-fuera-de-apt.json"
ANCLA = DIR + "/ancla.json"
ANCLA2 = RAIZ + "/etc/leksso/auditoria.ancla"
PUBLICO = RAIZ + "/var/lib/leksso/seguridad-estado.json"
EFIMERO = RAIZ + "/run/leksso-auditoria"
CERROJO = DIR + "/cerrojo"
MAX_CADENA = 25


# ---------- contexto: quién lanzó la instalación ----------
def leer(ruta, binario=False):
    try:
        with open(ruta, "rb" if binario else "r", errors="replace" if not binario else None) as f:
            return f.read()
    except OSError:
        return b"" if binario else ""


def proceso(pid):
    """Datos de un proceso para clasificar; None si ya no existe."""
    stat = leer(f"/proc/{pid}/stat")
    if not stat:
        return None
    m = re.match(r"\d+ \((.*)\) \S (\d+)", stat)           # el nombre puede llevar espacios y paréntesis
    if not m:
        return None
    entorno = leer(f"/proc/{pid}/environ", binario=True).split(b"\0")
    ssh = next((e.decode("utf-8", "replace").split("=", 1)[1] for e in entorno if e.startswith(b"SSH_CONNECTION=")), None)
    sudo_usuario = next((e.decode("utf-8", "replace").split("=", 1)[1] for e in entorno if e.startswith(b"SUDO_USER=")), None)
    cmd = leer(f"/proc/{pid}/cmdline", binario=True).replace(b"\0", b" ").decode("utf-8", "replace").strip()
    return {"pid": pid, "ppid": int(m.group(2)), "comm": m.group(1), "cmd": cmd[:300],
            "cgroup": (leer(f"/proc/{pid}/cgroup").splitlines() or [""])[0], "ssh": ssh, "sudo_usuario": sudo_usuario}


def cadena_de_procesos(pid):
    cadena = []
    while pid > 1 and len(cadena) < MAX_CADENA:
        p = proceso(pid)
        if not p:
            break
        cadena.append(p)
        pid = p["ppid"]
    return cadena


def clasificar(cadena):
    """(modo, origen, nivel, detalle) a partir de la cadena de procesos (del más cercano al más lejano). Función pura."""
    comandos = " ".join(p.get("cmd", "") for p in cadena)
    cgrupos = " ".join(p.get("cgroup", "") for p in cadena)
    nombres = {p.get("comm", "") for p in cadena}
    apt = next((p["cmd"] for p in cadena if re.search(r"(^|/)(apt|apt-get|aptitude|dpkg)(\s|$)", p.get("cmd", ""))), "")
    detalle = {"comando": apt[:200]} if apt else {}
    sudo_u = next((p["sudo_usuario"] for p in cadena if p.get("sudo_usuario")), None)
    if sudo_u:
        detalle["usuario"] = sudo_u
    if "leksso-admin.service" in cgrupos or "leksso-permisor.service" in cgrupos:
        return "orden de la IA", "IA (permisor de LeksSO)", "confirmado", detalle
    if "leksso-actualizar" in comandos:
        return "actualización de LeksSO", "leksso-actualizar", "confirmado", detalle
    if "unattended-upgrade" in comandos or "apt-daily-upgrade" in cgrupos or "unattended-upgrades" in cgrupos:
        return "actualización automática de seguridad", "Debian (unattended-upgrades)", "confirmado", detalle
    if "leksso-apps" in comandos:
        return "catálogo de LeksSO (Aplicaciones)", "leksso-apps", "confirmado", detalle
    ssh = next((p["ssh"] for p in cadena if p.get("ssh")), None)
    if ssh or any(n.startswith("sshd") for n in nombres):
        ip = ssh.split()[0] if ssh else "?"
        detalle["ip_remota"] = ip
        return "sesión remota (ssh)", f"SSH desde {ip}", "confirmado", detalle
    if re.search(r"(curl|wget)[^|]*\|\s*(sudo\s+)?(ba)?sh", comandos):
        return "script descargado y ejecutado (curl | sh)", "script de Internet", "inferido", detalle
    if nombres & {"kitty", "foot", "login", "xterm", "gnome-terminal", "konsole", "alacritty", "leksso-term"} \
            or re.search(r"/(kitty|login)\b", comandos):
        return "terminal local", "terminal de este equipo", "inferido", detalle
    return "comando desconocido", "desconocido", "desconocido", detalle


# ---------- el registro encadenado ----------
def hash_de(prev, registro):
    cuerpo = json.dumps({k: v for k, v in registro.items() if k != "h"}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256((prev + cuerpo).encode("utf-8")).hexdigest()


def lineas():
    out = []
    for linea in leer(REGISTRO).splitlines():
        try:
            out.append(json.loads(linea))
        except ValueError:
            out.append({"roto": linea[:80]})
    return out


def anotar_registro(**campos):
    """Añade una línea al registro, encadenada a la anterior. Devuelve el registro."""
    os.makedirs(DIR, mode=0o700, exist_ok=True)
    nuevo = not os.path.exists(REGISTRO)
    with open(CERROJO, "w") as bloqueo:
        fcntl.flock(bloqueo, fcntl.LOCK_EX)
        previas = lineas()
        ultimo = previas[-1] if previas else {}
        r = {"n": (ultimo.get("n", 0) + 1), "t": dt.datetime.now().astimezone().isoformat(timespec="seconds"), **campos}
        r["prev"] = ultimo.get("h", "0" * 64)
        r["h"] = hash_de(r["prev"], r)
        fd = os.open(REGISTRO, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        if nuevo:
            sellar_archivo()
        guardar_ancla(r)
    publicar()
    return r


def sellar_archivo():
    """Solo añadir (chattr +a): si el sistema de archivos no lo admite, el registro sigue encadenado."""
    if not PRUEBAS:
        subprocess.run(["chattr", "+a", REGISTRO], capture_output=True)


def guardar_ancla(r):
    datos = {"n": r["n"], "h": r["h"], "t": r["t"]}
    for ruta in (ANCLA, ANCLA2):
        try:
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta + ".nuevo", "w", encoding="utf-8") as f:
                json.dump(datos, f)
            os.chmod(ruta + ".nuevo", 0o644 if ruta == ANCLA2 else 0o600)
            os.replace(ruta + ".nuevo", ruta)
        except OSError:
            pass


def verificar():
    """Comprueba la cadena y que el último sello coincide con las anclas guardadas aparte."""
    prev = "0" * 64
    previas = lineas()
    for i, r in enumerate(previas, 1):
        if "roto" in r or r.get("prev") != prev or hash_de(prev, r) != r.get("h") or r.get("n") != i:
            return {"ok": False, "n": len(previas), "error": f"La línea {i} no encaja con la anterior: el registro se ha modificado."}
        prev = r["h"]
    if previas:
        for ruta in (ANCLA, ANCLA2):
            a = json.loads(leer(ruta) or "{}")
            if a and (a.get("n") != len(previas) or a.get("h") != prev):
                return {"ok": False, "n": len(previas), "error": "El último sello no coincide con el guardado aparte: faltan o sobran líneas."}
    elif os.path.exists(ANCLA2) or os.path.exists(ANCLA):
        return {"ok": False, "n": 0, "error": "Había un registro y ahora está vacío."}
    return {"ok": True, "n": len(previas), "sello": prev[:12]}


def publicar():
    """Resumen sin datos sensibles, legible por todos: sirve a la barra y a la ventana (cuántas novedades hay).
    Solo cuenta lo de origen DESCONOCIDO: lo «inferido» (p. ej. un apt install desde tu terminal) se ve en la ventana, pero no
    enciende la barra, o avisaría con cada instalación normal."""
    regs = lineas()
    revisadas = {r.get("ref") for r in regs if r.get("tipo") == "revision"}
    pendientes = [r for r in regs if r.get("tipo") in ("paquete", "fuera_de_apt") and r.get("accion") in ("instalado", "apareció")
                  and r.get("nivel") == "desconocido" and r.get("n") not in revisadas]
    ultimo = regs[-1] if regs else {}
    datos = {"version": VERSION, "total": len(regs), "sin_revisar": len(pendientes),
             "sello": {"n": ultimo.get("n", 0), "h": (ultimo.get("h") or "")[:12]},
             "actualizado": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
    try:
        os.makedirs(os.path.dirname(PUBLICO), exist_ok=True)
        with open(PUBLICO + ".nuevo", "w", encoding="utf-8") as f:
            json.dump(datos, f)
        os.chmod(PUBLICO + ".nuevo", 0o644)
        os.replace(PUBLICO + ".nuevo", PUBLICO)
    except OSError:
        pass


# ---------- apt ----------
def paquetes_instalados():
    r = subprocess.run(["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Status}\n"], capture_output=True, text=True)
    out = {}
    for linea in r.stdout.splitlines():
        p = linea.split("\t")
        if len(p) == 3 and p[2].endswith("installed"):
            out[p[0]] = p[1]
    return out


def gancho(fase):
    """Lo llama apt antes y después de dpkg. Nunca debe romper una instalación: cualquier error se traga."""
    try:
        os.makedirs(EFIMERO, mode=0o700, exist_ok=True)
        if fase == "pre":
            with open(EFIMERO + "/antes.json", "w", encoding="utf-8") as f:
                json.dump({"antes": paquetes_instalados(), "cadena": cadena_de_procesos(os.getppid())}, f)
            return
        previo = json.loads(leer(EFIMERO + "/antes.json") or "{}")
        if not previo:
            return
        antes, ahora = previo["antes"], paquetes_instalados()
        modo, origen, nivel, detalle = clasificar(previo.get("cadena", []))
        comun = {"tipo": "paquete", "modo": modo, "origen": origen, "nivel": nivel, "detalle": detalle}
        for nombre in sorted(set(ahora) - set(antes)):
            anotar_registro(accion="instalado", nombre=nombre, version=ahora[nombre], **comun)
        for nombre in sorted(set(antes) - set(ahora)):
            anotar_registro(accion="eliminado", nombre=nombre, version=antes[nombre], **comun)
        cambiados = sorted(n for n in ahora if n in antes and ahora[n] != antes[n])
        if cambiados:
            anotar_registro(accion="actualizado", nombre=f"{len(cambiados)} paquetes", version="",
                            **{**comun, "detalle": {**detalle, "paquetes": cambiados[:40]}})
        os.remove(EFIMERO + "/antes.json")
    except Exception:       # noqa: BLE001  un fallo del registro no puede impedir instalar
        pass


# ---------- lo que aparece fuera de apt ----------
def carpetas_de_usuarios():
    forzadas = os.environ.get("LEKSSO_AUDITORIA_HOMES") if PRUEBAS else None
    if forzadas:
        return [h for h in forzadas.split(":") if os.path.isdir(h)]
    return [u.pw_dir for u in pwd.getpwall() if 1000 <= u.pw_uid < 60000 and u.pw_dir.startswith("/home/") and os.path.isdir(u.pw_dir)]


def rutas_a_vigilar():
    rutas = [RAIZ + "/usr/local/bin", RAIZ + "/usr/local/sbin"]
    opt = RAIZ + "/opt"
    if os.path.isdir(opt):
        rutas += [os.path.join(opt, d) for d in sorted(os.listdir(opt)) if os.path.isdir(os.path.join(opt, d))]
    for h in carpetas_de_usuarios():
        rutas += [os.path.join(h, s) for s in (".local/bin", "bin", "Applications", ".cargo/bin")]
    return rutas


def escanear():
    """{ruta: {tam, mtime, hash}} de los ejecutables y AppImage de las carpetas vigiladas. Los comandos de LeksSO no cuentan."""
    visto = {}
    candidatos = []
    for base in rutas_a_vigilar():
        if os.path.isdir(base):
            candidatos += [os.path.join(base, n) for n in sorted(os.listdir(base))]
    for h in carpetas_de_usuarios():
        for raiz, dirs, archivos in os.walk(h):
            dirs[:] = [d for d in dirs if raiz.count(os.sep) - h.count(os.sep) < 2 and not d.startswith(".cache")]
            candidatos += [os.path.join(raiz, f) for f in archivos if f.endswith(".AppImage")]
    for ruta in candidatos:
        nombre = os.path.basename(ruta)
        if nombre.startswith("leksso-") or not os.path.isfile(ruta):
            continue
        if not (os.access(ruta, os.X_OK) or nombre.endswith(".AppImage")):
            continue
        try:
            st = os.stat(ruta)
            with open(ruta, "rb") as f:
                h = hashlib.sha256(f.read(4_000_000)).hexdigest()[:16]
        except OSError:
            continue
        visto[ruta] = {"tam": st.st_size, "mtime": int(st.st_mtime), "hash": h, "uid": st.st_uid}
    return visto


def foto():
    ahora = escanear()
    previa = json.loads(leer(FOTO) or "null")
    if previa is None:
        anotar_registro(tipo="inicio", accion="línea base", nombre=f"{len(ahora)} programas fuera de apt", version="",
                        modo="primera foto", origen="LeksSO", nivel="confirmado", detalle={"rutas": sorted(ahora)[:60]})
    else:
        for ruta in sorted(set(ahora) - set(previa)):
            d = ahora[ruta]
            try:
                dueno = pwd.getpwuid(d["uid"]).pw_name
            except KeyError:
                dueno = str(d["uid"])
            anotar_registro(tipo="fuera_de_apt", accion="apareció", nombre=os.path.basename(ruta), version="",
                            modo="apareció fuera de apt (no se sabe cómo)", origen="desconocido", nivel="desconocido",
                            detalle={"ruta": ruta, "propietario": dueno, "tam": d["tam"], "hash": d["hash"]})
        for ruta in sorted(set(previa) - set(ahora)):
            anotar_registro(tipo="fuera_de_apt", accion="desapareció", nombre=os.path.basename(ruta), version="",
                            modo="borrado o movido", origen="desconocido", nivel="inferido", detalle={"ruta": ruta})
    os.makedirs(DIR, mode=0o700, exist_ok=True)
    with open(FOTO + ".nuevo", "w", encoding="utf-8") as f:
        json.dump(ahora, f)
    os.chmod(FOTO + ".nuevo", 0o600)
    os.replace(FOTO + ".nuevo", FOTO)
    publicar()


# ---------- órdenes ----------
def exige_root():
    if not PRUEBAS and os.geteuid() != 0:
        sys.exit(json.dumps({"ok": False, "error": "Hace falta ser administrador (sudo)."}))


def listar(ultimos=300, solo_no_confirmados=False):
    exige_root()
    regs = lineas()
    revisadas = {r.get("ref") for r in regs if r.get("tipo") == "revision"}
    util = []
    for r in regs:
        if r.get("tipo") == "revision" or "roto" in r:
            continue
        r["revisada"] = r["n"] in revisadas
        if solo_no_confirmados and r.get("nivel") == "confirmado":
            continue
        util.append(r)
    print(json.dumps(util[-ultimos:][::-1], ensure_ascii=False))


def estado():
    print(leer(PUBLICO) or json.dumps({"version": VERSION, "total": 0, "sin_revisar": 0, "sello": {"n": 0, "h": ""}}))


def barra():
    d = json.loads(leer(PUBLICO) or "{}")
    n = d.get("sin_revisar", 0)
    texto = "▲ Seguridad" if n else ""
    tip = (f"{n} programa(s) nuevo(s) de origen desconocido. Ábrelos en Ajustes, Seguridad." if n else "")
    print(json.dumps({"text": texto, "tooltip": tip, "class": "novedad" if n else ""}, ensure_ascii=False))


def riel():
    """El botón de seguridad del rail: siempre se ve; se ilumina si hay novedades de instalaciones o de conexiones."""
    d = json.loads(leer(PUBLICO) or "{}")
    c = json.loads(leer(RAIZ + "/var/lib/leksso/conexiones-estado.json") or "{}")
    avisos = []
    if d.get("sin_revisar"):
        avisos.append(f"{d['sin_revisar']} programa(s) instalado(s) de origen desconocido")
    if c.get("novedades"):
        avisos.append(f"{c['novedades']} programa(s) nuevo(s) conectando sin validar")
    if c.get("envios_altos"):
        avisos.append(f"{c['envios_altos']} programa(s) enviando más de lo habitual")
    tip = "Seguridad: conexiones e instalaciones" + ("\n" + "\n".join(avisos) if avisos else "")
    print(json.dumps({"text": "\uf132", "tooltip": tip, "class": "novedad" if avisos else ""}, ensure_ascii=False))


def main(a):
    p = argparse.ArgumentParser(prog="leksso-auditoria", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="orden", required=True)
    x = s.add_parser("listar"); x.add_argument("--ultimos", type=int, default=300); x.add_argument("--no-confirmados", action="store_true")
    for n in ("verificar", "foto", "estado", "barra", "riel"):
        s.add_parser(n)
    x = s.add_parser("revisar"); x.add_argument("n", type=int)
    x = s.add_parser("gancho"); x.add_argument("fase", choices=["pre", "post"])
    x = s.add_parser("anotar")
    x.add_argument("--nombre", required=True); x.add_argument("--modo", required=True)
    x.add_argument("--origen", default="catalogo"); x.add_argument("--version", default="")
    o = p.parse_args(a)
    if o.orden == "gancho":
        gancho(o.fase); return 0
    if o.orden == "estado": estado(); return 0
    if o.orden == "barra": barra(); return 0
    if o.orden == "riel": riel(); return 0
    exige_root()
    if o.orden == "listar": listar(max(1, min(o.ultimos, 5000)), o.no_confirmados)
    elif o.orden == "verificar": print(json.dumps(verificar(), ensure_ascii=False))
    elif o.orden == "foto": foto()
    elif o.orden == "revisar":
        if not any(r.get("n") == o.n and r.get("tipo") != "revision" for r in lineas()):
            print(json.dumps({"ok": False, "error": "Esa entrada no existe."})); return 2
        anotar_registro(tipo="revision", accion="revisada", nombre=f"entrada {o.n}", version="", modo="revisada por el usuario",
                        origen="usuario", nivel="confirmado", ref=o.n, detalle={})
        print(json.dumps({"ok": True}))
    elif o.orden == "anotar":
        nombre_origen = {"catalogo": "leksso-apps"}.get(o.origen, o.origen[:60])
        r = anotar_registro(tipo="paquete", accion="instalado", nombre=o.nombre[:120], version=o.version[:60], modo=o.modo[:120],
                            origen=nombre_origen, nivel="confirmado", detalle={})
        print(json.dumps({"ok": True, "n": r["n"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
