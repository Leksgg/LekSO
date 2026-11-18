"""Asistentes de IA y sus permisos, uno por uno.

El archivo vive en /etc/leksso/asistentes.json y solo lo cambia el administrador (con tu contraseña): así un
asistente no puede darse permisos a sí mismo. Lo leen el permisor, el servicio de administración y la barra.

Por cada asistente y usuario:
  activo     si se usa en este equipo
  archivos   "preguntar" (cada carpeta pide tu permiso) | "libre" (carpetas de tu carpeta personal sin preguntar)
  comandos   si puede ejecutar comandos en el equipo con tu usuario
  admin      "no" | "preguntar" (cada orden de administrador pide un clic) | "libre" (sin preguntar)
Lo destructivo (borrar el sistema, formatear, cambiar contraseñas…) pregunta siempre.
"""
import json
import os
import re

RUTA = os.environ.get("LEKSSO_ASISTENTES") or "/etc/leksso/asistentes.json"
NOMBRES = {"claude": "Claude", "codex": "Codex"}
DEFECTO = {"activo": False, "archivos": "preguntar", "comandos": False, "admin": "no"}
PREAJUSTES = {
    "archivos": {"archivos": "preguntar", "comandos": False, "admin": "no"},
    "equipo": {"archivos": "libre", "comandos": True, "admin": "preguntar"},
    "total": {"archivos": "libre", "comandos": True, "admin": "libre"},
}
NOMBRE_PREAJUSTE = {"archivos": "Solo archivos", "equipo": "Este equipo", "total": "Acceso total"}


def validar(p):
    """Devuelve unos permisos limpios a partir de lo que venga (lo que no se entienda vuelve al valor seguro)."""
    p = p if isinstance(p, dict) else {}
    limpio = dict(DEFECTO)
    limpio["activo"] = p.get("activo") is True
    if p.get("archivos") in ("preguntar", "libre"):
        limpio["archivos"] = p["archivos"]
    limpio["comandos"] = p.get("comandos") is True
    if p.get("admin") in ("no", "preguntar", "libre"):
        limpio["admin"] = p["admin"]
    if limpio["admin"] != "no":
        limpio["comandos"] = True          # quien administra también ejecuta como usuario
    return limpio


def leer(usuario, ruta=None):
    """Permisos de todos los asistentes para un usuario. Sin archivo, todo apagado y en «solo archivos»."""
    try:
        with open(ruta or RUTA, encoding="utf-8") as f:
            todo = json.load(f)
    except (OSError, ValueError):
        todo = {}
    suyos = todo.get(usuario) if isinstance(todo, dict) else None
    suyos = suyos if isinstance(suyos, dict) else {}
    return {n: validar(suyos.get(n)) for n in NOMBRES}


def guardar(usuario, permisos, ruta=None):
    """Solo como administrador. Escribe de forma atómica y deja el archivo legible pero no modificable por otros."""
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", usuario or ""):
        raise ValueError("usuario no válido")
    ruta = ruta or RUTA
    try:
        with open(ruta, encoding="utf-8") as f:
            todo = json.load(f)
        if not isinstance(todo, dict):
            todo = {}
    except (OSError, ValueError):
        todo = {}
    todo[usuario] = {n: validar(permisos.get(n)) for n in NOMBRES}
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = ruta + ".nuevo"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(todo, f, indent=1)
    os.chmod(tmp, 0o644)
    os.replace(tmp, ruta)


def alguno_administra(usuario, ruta=None):
    return any(p["activo"] and p["admin"] != "no" for p in leer(usuario, ruta).values())


def resumen(p):
    """Una línea legible de unos permisos."""
    for clave, valores in PREAJUSTES.items():
        if all(p[k] == v for k, v in valores.items()):
            return NOMBRE_PREAJUSTE[clave]
    partes = ["archivos sin preguntar" if p["archivos"] == "libre" else "archivos con permiso"]
    if p["comandos"]:
        partes.append("comandos")
    if p["admin"] != "no":
        partes.append("administración" + (" preguntando" if p["admin"] == "preguntar" else " sin preguntar"))
    return ", ".join(partes)


# Órdenes que piden confirmación SIEMPRE, tenga el asistente el nivel que tenga. Es una red de seguridad, no
# una garantía: detecta lo evidente (una orden rebuscada puede esquivarla).
_DESTRUCTIVO = [re.compile(x, re.I) for x in (
    r"\brm\b[^|;&\n]*\s-\w*[rR]\w*[^|;&\n]*\s(/|/\*|~|~/|\$HOME|/home|/etc|/usr|/var|/boot|/bin|/lib\w*|/opt|/root|/srv)(/\*)?(\s|$)",
    r"\b(mkfs(\.\w+)?|wipefs|sgdisk|sfdisk|fdisk|parted|cryptsetup|blkdiscard|shred)\b",
    r"\bdd\b[^|;&\n]*\bof=/dev/",
    r">\s*/dev/(sd|nvme|vd|mmcblk|hd)",
    r"\b(passwd|chpasswd|userdel|deluser|usermod|visudo)\b",
    r"\b(shutdown|poweroff|reboot|halt)\b|\bsystemctl\s+(poweroff|reboot|halt|kexec)\b",
    r"\bch(mod|own)\b[^|;&\n]*\s-\w*R\w*[^|;&\n]*\s/(\s|$)",
    r"/etc/(sudoers|shadow|passwd|leksso)\b",
    r"\bnft\b[^|;&\n]*\bflush\b|\bleksso-acceso-remoto\b",
    r":\(\)\s*\{",
)]


# Las copias de seguridad quedan fuera del alcance de la IA: ni el programa, ni el repositorio, ni la clave, ni su horario.
# Esto se comprueba en el permisor y otra vez en el servicio de administración (que corre como root). Es una barrera de
# texto: la real es que el repositorio y la clave son de root (0700/0400) y que administrar exige que el usuario lo permita.
_COPIAS = re.compile(r"leksso[-_]copias|/var/lib/leksso-copias|/etc/leksso/copias|/var/lib/leksso/copias|leksso-copias\.(?:service|timer)|\brestic\b", re.I)


def toca_copias(orden):
    """True si la orden nombra el programa, el repositorio, la clave o el horario de las copias de seguridad."""
    return bool(_COPIAS.search(orden))


# El registro de instalaciones y de conexiones: la IA puede LEERLO solo si el usuario lo aprueba en el panel, y no puede
# tocarlo nunca (ni el programa, ni los datos, ni los sellos). Igual que las copias, es una barrera de texto en el
# permisor y en el servicio de administración; la real es que los datos son de root, con permisos 0600 y de solo añadir.
_AUDITORIA = re.compile(r"leksso[-_]auditoria|/var/lib/leksso-auditoria|/etc/leksso/auditoria|/var/lib/leksso/seguridad|/run/leksso-auditoria|99leksso-auditoria", re.I)
_AUDITORIA_LEER = re.compile(r"^\s*(?:sudo\s+(?:-n\s+)?)?leksso-auditoria\s+(?:listar|estado|verificar)(?:\s+--[a-z-]+(?:\s+\d+)?)*\s*$")


def toca_auditoria(orden):
    """True si la orden nombra el programa, los datos o los sellos del registro de seguridad."""
    return bool(_AUDITORIA.search(orden))


def lee_auditoria(orden):
    """True si la orden es solo una LECTURA del registro (listar, estado o verificar): esa pide permiso al usuario."""
    return bool(_AUDITORIA_LEER.match(orden))


def destructivo(orden):
    return any(p.search(orden) for p in _DESTRUCTIVO)
