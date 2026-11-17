#!/usr/bin/env python3
"""lekso-actualizar: versión de LekSO y actualizaciones desde GitHub, con firma y con tu permiso.

  lekso-actualizar version [--detalle]  muestra la versión instalada (con --detalle, su commit y firma)
  lekso-actualizar comprobar [--avisar] mira si hay una versión nueva (y avisa con una notificación)
  lekso-actualizar barra                estado para la barra (lee lo ya comprobado, sin red)
  lekso-actualizar cambios [VERSIÓN]    qué trae la versión nueva
  sudo lekso-actualizar aplicar [VERSIÓN]   instala la versión nueva (solo si su firma es válida)
  sudo lekso-actualizar volver          vuelve a la versión anterior
  lekso-actualizar hardware ...         controladores y firmware (detectar, comprobar, aplicar...): ver `hardware`

Seguridad: solo se instalan versiones con etiqueta (vX.Y.Z-alpha) firmadas con la clave de LekSO que
ya está instalada en /etc/lekso/allowed_signers. Sin firma válida no se toca nada. Una subida normal
al repositorio nunca llega a un equipo: solo las versiones publicadas.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

REPO_URL = "https://github.com/Leksgg/LekSO.git"
RAW_URL = "https://raw.githubusercontent.com/Leksgg/LekSO/{tag}/CHANGELOG.md"
FICHERO_VERSION = "/etc/lekso-release"
FIRMANTES = "/etc/lekso/allowed_signers"
CLON = "/var/lib/lekso/repo"
ANTERIOR = "/var/lib/lekso/version-anterior"
SIN_FIRMA = "/etc/lekso/sin-firma"                # fase de pruebas: si existe, no se exige firma (lo crea el USB de pruebas)
INSTALADA = "/var/lib/lekso/instalada.json"      # versión, commit y firmante de lo instalado
RAMA_PRINCIPAL = "origin/main"
CACHE = os.path.expanduser("~/.cache/lekso/actualizacion.json")
AVISADO = os.path.expanduser("~/.cache/lekso/avisado")

ETIQUETA = re.compile(r"^v(\d+)\.(\d+)\.(\d+)-(alpha|beta|rc)\Z")   # \Z: sin salto de línea final
RANGO = {"alpha": 0, "beta": 1, "rc": 2}
NOMBRE = {"alpha": "Alpha", "beta": "Beta", "rc": "RC"}


def clave(v):
    """'0.1.1-alpha' → tupla ordenable. None si no es una versión válida."""
    m = ETIQUETA.match("v" + v) if v and not v.startswith("v") else ETIQUETA.match(v or "")
    if not m:
        return None
    return (int(m[1]), int(m[2]), int(m[3]), RANGO[m[4]])


def bonita(v):
    """'0.1.0-alpha' → 'Alpha 0.1.0'."""
    m = ETIQUETA.match("v" + v) if v and not v.startswith("v") else ETIQUETA.match(v or "")
    return f"{NOMBRE[m[4]]} {m[1]}.{m[2]}.{m[3]}" if m else (v or "desconocida")


def version_actual():
    for ruta in (FICHERO_VERSION, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "VERSION")):
        try:
            v = open(ruta, encoding="utf-8").read().strip()
            if clave(v):
                return v
        except OSError:
            pass
    return None


def git(*args, cwd=None, entrada=None):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1", LC_ALL="C")
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=300)


def etiquetas_remotas():
    """Versiones publicadas en GitHub (solo nombres; la firma se comprueba al aplicar)."""
    r = git("ls-remote", "--tags", "--refs", REPO_URL, "refs/tags/v*")
    if r.returncode != 0:
        raise RuntimeError("No se pudo consultar GitHub (¿hay conexión?)")
    out = []
    for linea in r.stdout.splitlines():
        nombre = linea.split("refs/tags/")[-1].strip()
        if ETIQUETA.match(nombre):
            out.append(nombre[1:])
    return sorted(out, key=clave)


def ultima_mayor(actual):
    tags = etiquetas_remotas()
    ca = clave(actual) if actual else None
    nuevas = [t for t in tags if ca is None or clave(t) > ca]
    return nuevas[-1] if nuevas else None


def leer_cache():
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def notificar(titulo, texto):
    try:
        subprocess.run(["notify-send", "-a", "lekso-actualizar", "-t", "15000", titulo, texto], timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass


def comprobar(avisar=False):
    actual = version_actual()
    disponible = ultima_mayor(actual)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump({"actual": actual, "disponible": disponible, "comprobado": int(time.time())}, f)
    if not disponible:
        print(f"Estás al día: LekSO {bonita(actual)}.")
        return 0
    print(f"Hay una versión nueva: LekSO {bonita(disponible)} (instalada: {bonita(actual)}).")
    if avisar:
        ya = ""
        try:
            ya = open(AVISADO, encoding="utf-8").read().strip()
        except OSError:
            pass
        if ya != disponible:        # un solo aviso por versión
            notificar("Hay una versión nueva de LekSO",
                      f"LekSO {bonita(disponible)} está disponible (tienes {bonita(actual)}). "
                      "Pulsa el aviso de la barra de abajo o abre Ajustes para ver qué cambia.")
            with open(AVISADO, "w", encoding="utf-8") as f:
                f.write(disponible)
    return 0


def barra():
    c = leer_cache()
    if c.get("disponible") and clave(c["disponible"]) and c.get("actual") and clave(c["actual"]) \
            and clave(c["disponible"]) > clave(c["actual"]):
        print(json.dumps({"text": f"↑ {bonita(c['disponible'])}", "class": "hay",
                          "tooltip": f"Versión nueva: LekSO {bonita(c['disponible'])}\nInstalada: {bonita(c['actual'])}\nClic para ver qué cambia."}))
    else:
        print(json.dumps({"text": "", "class": "al-dia"}))
    return 0


def cambios(tag=None):
    c = leer_cache()
    v = tag or c.get("disponible")
    if not v or not clave(v):
        print("No hay una versión nueva que mostrar.")
        return 1
    url = RAW_URL.format(tag="v" + v.lstrip("v"))
    req = urllib.request.Request(url, headers={"User-Agent": "lekso-actualizar"})
    with urllib.request.urlopen(req, timeout=20) as r:
        texto = r.read(300000).decode("utf-8", "replace")
    # solo la parte más reciente: hasta la segunda cabecera de versión o de fecha
    lineas, vistas, dentro = [], 0, False
    for linea in texto.splitlines():
        if linea.startswith("## "):
            dentro = True
            vistas += 1
            if vistas > 2:
                break
        if dentro:
            lineas.append(linea)
    print("\n".join(lineas[:80]))
    return 0


def raiz_o_salir():
    if os.geteuid() != 0:
        sys.exit("Este paso necesita permisos de administrador: sudo lekso-actualizar ...")


def preparar_clon():
    os.makedirs(os.path.dirname(CLON), exist_ok=True)
    if not os.path.isdir(os.path.join(CLON, ".git")):
        r = git("clone", "--no-checkout", REPO_URL, CLON)
        if r.returncode != 0:
            sys.exit("No se pudo descargar el repositorio: " + r.stderr.strip()[:200])
    # la copia de un equipo instalado desde USB apunta al paquete del USB: siempre se baja del repositorio oficial
    git("remote", "set-url", "origin", REPO_URL, cwd=CLON)
    r = git("fetch", "--tags", "--force", "origin", cwd=CLON)
    if r.returncode != 0:
        sys.exit("No se pudo actualizar la copia local: " + r.stderr.strip()[:200])


def verificar(tag):
    """Comprueba que la versión es legítima y devuelve (commit, huella de la firma). Si algo falla, no se sigue.

    1. La etiqueta está firmada con una clave de /etc/lekso/allowed_signers (la que ya hay instalada).
    2. El commit al que apunta pertenece a la rama principal del repositorio oficial.
    """
    if git("rev-parse", "-q", "--verify", f"refs/tags/{tag}", cwd=CLON).returncode != 0:
        sys.exit(f"No encuentro la versión {tag} en la copia descargada del repositorio (¿falló la descarga?).")
    sin_firma = os.path.exists(SIN_FIRMA)
    salida = ""
    if sin_firma:
        print("AVISO: equipo en FASE DE PRUEBAS (/etc/lekso/sin-firma): no se comprueba la firma de la versión.")
    else:
        if not os.path.exists(FIRMANTES):
            sys.exit(f"Falta {FIRMANTES}: no hay clave con la que comprobar la firma.")
        r = git("-c", f"gpg.ssh.allowedSignersFile={FIRMANTES}", "verify-tag", tag, cwd=CLON)
        salida = (r.stderr + r.stdout)
        if r.returncode != 0 or "Good \"git\" signature for " not in salida:   # «for»: la firma coincide con un firmante autorizado
            sys.exit(f"La versión {tag} NO tiene una firma válida. No se instala nada.\n{salida.strip()[:300]}")
    c = git("rev-list", "-n", "1", tag, cwd=CLON)
    commit = c.stdout.strip()
    if c.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", commit):
        sys.exit(f"No se pudo identificar el commit de {tag}.")
    anc = git("merge-base", "--is-ancestor", commit, RAMA_PRINCIPAL, cwd=CLON)
    if anc.returncode != 0:
        sys.exit(f"La versión {tag} no pertenece a la rama principal del repositorio. No se instala nada.")
    m = re.search(r"key (\S+:\S+)", salida)
    huella = m[1] if m else ""
    if sin_firma:
        print(f"Versión {tag} (commit {commit[:7]}, rama principal) SIN comprobar firma.")
        return commit, "sin-comprobar"
    print(f"Firma válida de la versión {tag} (commit {commit[:7]}, rama principal).")
    return commit, huella


def instalar_version(tag, usuario, commit="", huella=""):
    r = git("checkout", "--force", "--detach", tag, cwd=CLON)
    if r.returncode != 0:
        sys.exit("No se pudo preparar la versión: " + r.stderr.strip()[:200])
    git("clean", "-fdx", cwd=CLON)
    script = os.path.join(CLON, "scripts", "provision-base.sh")
    print(f"Instalando LekSO {bonita(tag.lstrip('v'))} (puede tardar unos minutos)…")
    p = subprocess.run(["bash", script, usuario])
    if p.returncode != 0:
        sys.exit("La instalación terminó con errores. Puedes volver con: sudo lekso-actualizar volver")
    tmp = FICHERO_VERSION + ".nuevo"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(tag.lstrip("v") + "\n")
    os.replace(tmp, FICHERO_VERSION)
    with open(INSTALADA + ".nuevo", "w", encoding="utf-8") as f:
        json.dump({"version": tag.lstrip("v"), "commit": commit, "firma": huella}, f)
    os.replace(INSTALADA + ".nuevo", INSTALADA)


def usuario_real():
    u = os.environ.get("SUDO_USER")
    if not u or u == "root":
        sys.exit("Ejecuta con sudo desde tu usuario: sudo lekso-actualizar aplicar")
    return u


def aplicar(tag=None):
    raiz_o_salir()
    usuario = usuario_real()
    actual = version_actual()
    destino = (tag or "").lstrip("v") or ultima_mayor(actual)
    if not destino or not clave(destino):
        print("No hay ninguna versión nueva.")
        return 0
    if actual and clave(destino) <= clave(actual):
        sys.exit(f"{bonita(destino)} no es más nueva que la instalada ({bonita(actual)}).")
    etiqueta = "v" + destino
    preparar_clon()
    commit, huella = verificar(etiqueta)
    os.makedirs(os.path.dirname(ANTERIOR), exist_ok=True)
    with open(ANTERIOR, "w", encoding="utf-8") as f:
        f.write((actual or "") + "\n")
    instalar_version(etiqueta, usuario, commit, huella)
    print(f"\nListo: LekSO {bonita(destino)}. Cierra la sesión y vuelve a entrar para estrenar todo.")
    return 0


def volver():
    raiz_o_salir()
    usuario = usuario_real()
    try:
        previa = open(ANTERIOR, encoding="utf-8").read().strip()
    except OSError:
        sys.exit("No hay una versión anterior guardada.")
    if not clave(previa):
        sys.exit("La versión anterior guardada no es válida.")
    preparar_clon()
    commit, huella = verificar("v" + previa)
    actual = version_actual()
    instalar_version("v" + previa, usuario, commit, huella)
    with open(ANTERIOR, "w", encoding="utf-8") as f:
        f.write((actual or "") + "\n")
    print(f"\nVuelves a LekSO {bonita(previa)}. Cierra la sesión y vuelve a entrar.")
    return 0


def modulo_hardware():
    """Carga lekso_hardware.py, instalado junto a las bibliotecas de LekSO o al lado de este script."""
    for carpeta in ("/usr/local/lib/lekso", os.path.dirname(os.path.abspath(__file__))):
        if os.path.exists(os.path.join(carpeta, "lekso_hardware.py")):
            sys.path.insert(0, carpeta)
            break
    import lekso_hardware
    return lekso_hardware


def main(a):
    if not a or a[0] in ("-h", "--help", "ayuda"):
        print(__doc__)
        return 0
    c = a[0]
    try:
        if c == "version":
            v = a[1] if len(a) > 1 and clave(a[1]) else version_actual()   # con un argumento, solo le da nombre
            texto = f"LekSO {bonita(v)}" if v else "LekSO (versión desconocida)"
            if "--detalle" in a:
                try:
                    d = json.load(open(INSTALADA, encoding="utf-8"))
                    if d.get("commit"):
                        texto += f" · commit {d['commit'][:7]} · firmada {d.get('firma', '')}".rstrip()
                except (OSError, ValueError):
                    pass
            print(texto)
            return 0
        if c == "comprobar":
            return comprobar("--avisar" in a)
        if c == "barra":
            return barra()
        if c == "cambios":
            return cambios(a[1] if len(a) > 1 else None)
        if c == "aplicar":
            return aplicar(a[1] if len(a) > 1 else None)
        if c == "volver":
            return volver()
        if c == "hardware":
            return modulo_hardware().main(a[1:])
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
