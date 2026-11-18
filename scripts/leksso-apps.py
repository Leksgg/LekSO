#!/usr/bin/env python3
"""leksso-apps: instala en LeksSO los equivalentes de las aplicaciones habituales de Windows.

  leksso-apps                       lista por grupos, con lo que ya está instalado
  leksso-apps instalar NOMBRE...    instala por nombre (de Linux o de Windows) o por grupo
  leksso-apps instalar --todo       instala todo lo automático (pide confirmación)
  leksso-apps pendientes            lo que no se puede instalar con un comando y por qué
  Opciones: --simular (solo muestra lo que haría), --si (no pregunta)

Fuentes: paquetes de Debian, repositorios firmados del proveedor (Brave, VS Code),
descargas directas .deb del proveedor (Discord, Obsidian, Heroic, r2modman)
y npm (Claude Code, Codex). Nada se ejecuta sin que lo pidas.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

# (grupo, id, equivale a (Windows), tipo, objetivo, comprobación, nota)
# tipos: apt, repo-brave, repo-vscode, steam, deb-url, deb-github, npm, script, manual
CATALOGO = [
    # Desarrollo
    ("Desarrollo", "git", "Git", "apt", "git", "git", ""),
    ("Desarrollo", "gh", "GitHub CLI", "apt", "gh", "gh", ""),
    ("Desarrollo", "nodejs", "Node.js", "apt", "nodejs npm", "nodejs", "Versión de Debian (20)."),
    ("Desarrollo", "python", "Python", "apt", "python3 python3-pip python3-venv", "python3-pip", ""),
    ("Desarrollo", "rustup", "Rustup", "apt", "rustup", "rustup", "Después: rustup default stable"),
    ("Desarrollo", "ripgrep", "RipGrep", "apt", "ripgrep", "ripgrep", ""),
    ("Desarrollo", "compilador", "Visual Studio Build Tools", "apt", "build-essential", "build-essential", "gcc, make, etc."),
    ("Desarrollo", "docker", "Docker Desktop", "docker", "docker.io docker-compose docker-buildx", "docker.io",
     "Docker Engine con compose y buildx. Te añade al grupo docker (equivale a permisos de administrador); cierra sesión después."),
    ("Desarrollo", "code", "Visual Studio Code", "repo-vscode", "code", "code", "Repositorio firmado de Microsoft."),
    ("Desarrollo", "playwright", "Playwright", "playwright", "playwright", "playwright",
     "Automatización y pruebas de navegador. Instala Node, las librerías del sistema y Chromium."),
    ("Desarrollo", "tesseract", "Tesseract-OCR", "apt", "tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng", "tesseract-ocr", ""),
    ("Desarrollo", "filezilla", "FileZilla", "apt", "filezilla", "filezilla", ""),
    # Inteligencia artificial
    ("IA", "claude-code", "Claude Code", "npm", "@anthropic-ai/claude-code", "claude", "Ejecútalo dentro de `caja --ia-nube`."),
    ("IA", "codex", "Codex CLI", "npm", "@openai/codex", "codex", "Ejecútalo dentro de `caja --ia-nube`."),
    ("IA", "ollama", "Ollama", "script", "https://ollama.com/install.sh", "ollama",
     "Script oficial del proveedor; pide --si porque se ejecuta con permisos de administrador."),
    # Navegadores
    ("Navegadores", "brave", "Brave", "repo-brave", "brave-browser", "brave-browser", "Repositorio firmado de Brave."),
    # Comunicación y notas
    ("Comunicación", "discord", "Discord", "deb-url",
     "https://discord.com/api/download?platform=linux&format=deb", "discord", "No se actualiza solo; vuelve a ejecutar el comando."),
    ("Notas", "obsidian", "Obsidian", "deb-github", "obsidianmd/obsidian-releases|amd64\\.deb$", "obsidian", ""),
    # Multimedia y directo
    ("Multimedia", "obs", "OBS Studio", "apt", "obs-studio", "obs-studio", "El plugin move-transition se instala dentro de OBS."),
    ("Multimedia", "audacity", "Audacity", "apt", "audacity", "audacity", ""),
    ("Multimedia", "vlc", "VLC media player", "apt", "vlc", "vlc", ""),
    ("Multimedia", "streamdeck", "Elgato Stream Deck", "apt", "streamdeck-ui", "streamdeck-ui", "Ya viene con LeksSO."),
    ("Ofimática", "libreoffice", "Microsoft Office (Word, Excel, PowerPoint)", "apt",
     "libreoffice-writer libreoffice-calc libreoffice-impress libreoffice-l10n-es libreoffice-help-es", "libreoffice-writer",
     "Funciona sin conexión. En el menú también tienes Word, Excel y PowerPoint en su versión web (gratis, con cuenta de Microsoft)."),
    ("Multimedia", "pdf", "Wondershare PDFelement", "apt", "okular", "okular", "Leer y anotar. Edición avanzada de PDF: sin equivalente directo."),
    # Utilidades
    ("Utilidades", "compresores", "WinRAR", "apt", "p7zip-full unrar-free", "p7zip-full", "Zip, 7z, rar y tar."),
    ("Utilidades", "monitor", "CPUID HWMonitor / SIV", "apt", "btop lm-sensors", "btop", ""),
    ("Utilidades", "logitech", "Logi Options+", "apt", "solaar", "solaar", ""),
    ("Utilidades", "copias", "Smart Backup", "apt", "restic timeshift", "restic", "restic: copias a disco o nube. Timeshift: puntos de restauración del sistema."),
    ("Utilidades", "antivirus", "Malwarebytes", "apt", "clamav", "clamav", "Opcional. En Linux con la caja y sin ejecución por doble clic suele sobrar."),
    ("Utilidades", "vpn", "ExpressVPN", "apt", "wireguard", "wireguard", "WireGuard con la configuración de tu proveedor."),
    # Juegos
    ("Juegos", "steam", "Steam", "steam", "steam-installer", "steam-installer", "Activa la arquitectura de 32 bits y el repositorio contrib."),
    ("Juegos", "heroic", "Epic Games Launcher / Amazon Games", "deb-github",
     "Heroic-Games-Launcher/HeroicGamesLauncher|linux-amd64\\.deb$", "heroic", "Heroic abre Epic, GOG y Amazon."),
    ("Juegos", "minigalaxy", "GOG GALAXY", "apt", "minigalaxy", "minigalaxy", "Alternativa: Heroic."),
    ("Juegos", "lutris", "Ubisoft Connect (vía Wine)", "apt", "lutris", "lutris", "Ubisoft Connect corre con Lutris o Steam; sin garantía."),
    ("Juegos", "r2modman", "Thunderstore Mod Manager", "deb-github",
     "ebkr/r2modmanPlus|amd64\\.deb$", "r2modman", ""),
    ("Juegos", "wine", "Programas de Windows", "apt", "wine", "wine", "Se abren siempre dentro de la caja."),
]

# Entradas que NO son el programa del fabricante para Linux, sino otro programa de terceros que hace una función
# parecida (o que da acceso a tu cuenta desde fuera). La lista lo dice siempre: nadie instala una alternativa
# creyendo que es la versión oficial.
ALTERNATIVAS = {
    "libreoffice": "No hay Microsoft Office de escritorio para Linux; LibreOffice abre y guarda .docx, .xlsx y .pptx (algunas macros y animaciones pueden verse distintas).",
    "streamdeck": "Elgato no publica su programa para Linux; este es de terceros.",
    "pdf": "No hay PDFelement para Linux; es otro lector, solo leer y anotar.",
    "compresores": "No hay WinRAR con ventana para Linux; son compresores libres.",
    "monitor": "No hay HWMonitor ni SIV para Linux; son otras herramientas.",
    "logitech": "Logitech no publica Options+ para Linux; es de terceros.",
    "copias": "No hay Smart Backup para Linux; son otros programas.",
    "antivirus": "No hay Malwarebytes de escritorio para Linux; es otro antivirus.",
    "vpn": "ExpressVPN tiene aplicación oficial para Linux (en su web, con tu cuenta); esto es WireGuard genérico.",
    "heroic": "Epic, Amazon y GOG no publican su lanzador para Linux. Heroic es de terceros: entra con tu cuenta y ejecuta tus juegos.",
    "minigalaxy": "GOG no publica Galaxy para Linux; es de terceros.",
    "lutris": "Ubisoft no publica Connect para Linux; Lutris ejecuta el de Windows con Wine, sin garantía.",
    "r2modman": "No es el gestor de Thunderstore (ese depende de Overwolf); es otro gestor que usa sus mods.",
    "wine": "No es un programa de Windows: es la capa que permite ejecutarlos.",
}

# Lo que no se puede instalar con un comando. (Windows, motivo, alternativa)
PENDIENTES = [
    ("Software con licencia propia", "Se descarga del proveedor", "Instalador de Linux en la web del fabricante."),
    ("Instaladores sin dirección fija de descarga", "No se puede automatizar", "Descargar de la web del proveedor y ejecutar."),
    ("Aplicaciones sin cliente oficial para Linux", "Notion, Teams y similares", "Usar su versión web."),
    ("Navegadores adicionales", "No se instalan: el único navegador es Brave", "—"),
    ("Aplicaciones solo de Windows", "Overlays de juegos, gestores de mods de Nexus, utilidades de fabricante", "Sin equivalente."),
    ("Software de RGB, periféricos y placas base", "Específico de cada fabricante", "RGB: OpenRGB (no está en Debian)."),
    ("Controladores de NVIDIA", "Necesitan el repositorio non-free", "Se tratan al instalar en el equipo con tarjeta NVIDIA."),
    ("Plugins de audio y DAW", "Dependen de cada plugin", "Muchos tienen versión VST3 para Linux; requieren un DAW."),
    ("Juegos", "Se instalan desde su launcher", "Comprobar cada uno en ProtonDB; los que llevan antitrampas, sin verificar."),
]

COLOR = sys.stdout.isatty()


def c(t, k):
    return f"\033[{k}m{t}\033[0m" if COLOR else t


def instalado(tipo, comprobar):
    if tipo in ("npm", "script", "playwright"):
        return shutil.which(comprobar) is not None
    r = subprocess.run(["dpkg-query", "-W", "-f=${Status}", comprobar], capture_output=True, text=True)
    return r.returncode == 0 and "install ok installed" in r.stdout


def correr(cmd, simular, **kw):
    print(c("  $ ", "2") + (" ".join(cmd) if isinstance(cmd, list) else cmd), flush=True)
    if simular:
        return 0
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    return subprocess.run(cmd, env=env, **kw).returncode


def sudo(cmd, simular):
    return correr(["sudo", "--preserve-env=DEBIAN_FRONTEND"] + cmd, simular)


def apt(paquetes, simular):
    return sudo(["apt-get", "install", "-y"] + paquetes.split(), simular)


def descargar(url, destino):
    if not url.startswith("https://"):
        raise SystemExit("Solo se descarga por HTTPS")
    req = urllib.request.Request(url, headers={"User-Agent": "leksso-apps"})
    with urllib.request.urlopen(req, timeout=60) as r, open(destino, "wb") as f:
        shutil.copyfileobj(r, f)


def instalar_deb(url, simular):
    d = tempfile.mkdtemp(prefix="leksso-apps-")
    ruta = os.path.join(d, "paquete.deb")
    print(c("  descarga directa del proveedor (sin firma verificada por apt): ", "33") + url)
    if not simular:
        descargar(url, ruta)
    r = sudo(["apt-get", "install", "-y", ruta], simular)
    shutil.rmtree(d, ignore_errors=True)
    return r


def url_github(repo, patron):
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/releases/latest",
                                 headers={"User-Agent": "leksso-apps"})
    with urllib.request.urlopen(req, timeout=30) as r:
        datos = json.load(r)
    for a in datos.get("assets", []):
        if re.search(patron, a["name"]):
            return a["browser_download_url"]
    raise SystemExit(f"No hay un .deb que encaje en {repo}")


def repo_clave(nombre, url_clave, linea, simular, dearmor=False):
    llave = f"/usr/share/keyrings/{nombre}.gpg"
    if dearmor:
        sudo(["apt-get", "install", "-y", "gnupg", "curl"], simular)
        correr(f"curl -fsSL {url_clave} | sudo gpg --dearmor --yes -o {llave}", simular, shell=True)
    else:
        sudo(["curl", "-fsSLo", llave, url_clave], simular)
    correr(f"echo '{linea.format(llave=llave)}' | sudo tee /etc/apt/sources.list.d/{nombre}.list >/dev/null",
           simular, shell=True)
    return sudo(["apt-get", "update"], simular)


def configurar_code():
    """VS Code con Wayland y sin telemetría, si el usuario no tiene ya sus propios ajustes."""
    cfg = os.path.expanduser("~/.config")
    os.makedirs(os.path.join(cfg, "Code", "User"), exist_ok=True)
    flags = os.path.join(cfg, "code-flags.conf")
    if not os.path.exists(flags):
        with open(flags, "w") as f:
            f.write("--ozone-platform-hint=auto\n--password-store=basic\n")
    ajustes = os.path.join(cfg, "Code", "User", "settings.json")
    if not os.path.exists(ajustes):
        with open(ajustes, "w") as f:
            json.dump({"telemetry.telemetryLevel": "off", "update.mode": "none",
                       "workbench.enableExperiments": False}, f, indent=2)
            f.write("\n")


def hacer(item, simular, si):
    grupo, ident, win, tipo, objetivo, comprobar, nota = item
    print(c(f"\n▶ {ident}", "1;36") + f"  ({win})")
    if tipo == "apt":
        return apt(objetivo, simular)
    if tipo == "repo-brave":
        repo_clave("brave-browser", "https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg",
                   "deb [signed-by={llave}] https://brave-browser-apt-release.s3.brave.com/ stable main", simular)
        return apt(objetivo, simular)
    if tipo == "repo-vscode":
        repo_clave("microsoft", "https://packages.microsoft.com/keys/microsoft.asc",
                   "deb [arch=amd64 signed-by={llave}] https://packages.microsoft.com/repos/code stable main",
                   simular, dearmor=True)
        r = apt(objetivo, simular)
        if r == 0 and not simular:
            configurar_code()
        return r
    if tipo == "docker":
        r = apt(objetivo, simular)
        if r == 0:
            # Bajo demanda: Docker no arranca con el equipo (retrasaba el inicio unos 6 s esperando la red y ocupaba
            # memoria siempre). Queda escuchando su socket y se pone en marcha solo con la primera orden `docker`.
            sudo(["systemctl", "disable", "--now", "docker.service", "containerd.service"], simular)
            sudo(["systemctl", "enable", "--now", "docker.socket"], simular)
        usuario = os.environ.get("SUDO_USER") or os.environ.get("USER") or ""
        if r == 0 and usuario:
            sudo(["usermod", "-aG", "docker", usuario], simular)
            if not simular:
                print(c("  Te he añadido al grupo docker: cierra sesión y vuelve a entrar para usarlo sin sudo.", "33"))
        return r
    if tipo == "playwright":
        r = apt("nodejs npm", simular)
        if r == 0:
            r = sudo(["npm", "install", "-g", "playwright"], simular)
        if r == 0:
            r = sudo(["playwright", "install-deps", "chromium"], simular)
        if r == 0:
            r = correr(["playwright", "install", "chromium"], simular)  # como usuario: va a ~/.cache/ms-playwright
        return r
    if tipo == "steam":
        sudo(["dpkg", "--add-architecture", "i386"], simular)
        sudo(["apt-get", "update"], simular)
        return apt(objetivo, simular)
    if tipo == "deb-url":
        return instalar_deb(objetivo, simular)
    if tipo == "deb-github":
        repo, patron = objetivo.split("|")
        return instalar_deb(url_github(repo, patron) if not simular else f"(último .deb de github.com/{repo})", simular)
    if tipo == "npm":
        return sudo(["npm", "install", "-g", objetivo], simular)
    if tipo == "script":
        if not si and not simular:
            print(c("  Este paso ejecuta un script del proveedor con permisos de administrador. Repite con --si.", "33"))
            return 1
        return correr(f"curl -fsSL {objetivo} | sudo sh", simular, shell=True)
    return 1


def buscar(nombres):
    sel = []
    for k in (n.lower() for n in nombres):
        exactos = [it for it in CATALOGO if k in (it[1].lower(), it[0].lower())]
        encontrados = exactos or [it for it in CATALOGO if k in it[2].lower()]
        for it in encontrados:
            if it not in sel:
                sel.append(it)
    return sel


def lista():
    grupo = None
    for it in CATALOGO:
        if it[0] != grupo:
            grupo = it[0]
            print("\n" + c(grupo, "1"))
        ok = instalado(it[3], it[5])
        marca = c("✓", "32") if ok else c("·", "2")
        clase = c("alternativa", "33") if it[1] in ALTERNATIVAS else c("oficial    ", "2")
        nota = ALTERNATIVAS.get(it[1]) or (it[6] if not ok else "")
        print(f"  {marca} {it[1]:<14} {clase} {c('←', '2')} {it[2]}" + (c(f"   {nota}", "2") if nota else ""))
    print(f"\n{c('✓', '32')} ya instalado   · disponible.   Instalar: leksso-apps instalar NOMBRE   (--todo para todo lo automático)")
    print("oficial: el programa de su fabricante para Linux.   alternativa: otro programa, de terceros, que hace esa función.")
    print("Lo que no tiene comando: leksso-apps pendientes")


def pendientes():
    print(c("Sin comando de instalación", "1") + "\n")
    for win, motivo, alt in PENDIENTES:
        print(f"  {c(win, '1')}\n    {motivo}. {alt}")


def main(argv):
    simular = "--simular" in argv
    si = "--si" in argv
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        return lista()
    if args[0] in ("pendientes", "pend"):
        return pendientes()
    if args[0] != "instalar":
        print(__doc__)
        return 2
    if "--todo" in argv:
        # --todo instala solo lo oficial: las alternativas de terceros se piden siempre por su nombre
        sel = [it for it in CATALOGO if it[1] not in ALTERNATIVAS and not instalado(it[3], it[5])]
    else:
        nombres = args[1:]
        if not nombres:
            print("Indica qué instalar: un nombre, un grupo o --todo")
            return 2
        sel = buscar(nombres)
        if not sel:
            print("No encuentro nada con ese nombre. Mira la lista con: leksso-apps")
            return 1
    pend = [it for it in sel if not instalado(it[3], it[5])]
    for it in sel:
        if it not in pend:
            print(f"  ya instalado: {it[1]}")
    if not pend:
        return 0
    if "--todo" in argv and not si and not simular:
        print("Se instalará: " + ", ".join(it[1] for it in pend))
        if input("¿Continuar? [s/N] ").strip().lower() not in ("s", "si", "sí"):
            return 1
    fallos = []
    confirmado = "--todo" in argv  # la confirmación de --todo cubre también los scripts del proveedor
    for it in pend:
        if hacer(it, simular, si or confirmado) != 0:
            fallos.append(it[1])
    if not simular and shutil.which("leksso-asociar"):
        subprocess.run(["leksso-asociar"], capture_output=True)  # navegador y programas nuevos como predeterminados si faltaban
    print()
    if fallos:
        print(c("Con errores: " + ", ".join(fallos), "31"))
        return 1
    print(c("Hecho.", "32") + (" (simulado: no se ha instalado nada)" if simular else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
