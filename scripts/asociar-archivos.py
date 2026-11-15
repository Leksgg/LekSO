#!/usr/bin/env python3
"""Da un programa predeterminado a cada tipo de archivo que LekSO sabe abrir.

Recorre los tipos MIME del sistema y rellena ~/.config/mimeapps.list solo donde
falta. Lo que el usuario ya haya elegido no se toca, así que un programa nuevo
definido como predeterminado se respeta siempre.
"""
import configparser
import os
import re
import sys

APPS = ["/usr/share/applications", "/usr/local/share/applications",
        os.path.expanduser("~/.local/share/applications")]
EDITOR, IMAGEN, PDF, REPRODUCTOR = ("lekso-editor.desktop", "imv.desktop",
                                    "org.pwmt.zathura.desktop", "mpv.desktop")
ARCHIVADOR, WINE, INFO = "xarchiver.desktop", "lekso-wine.desktop", "lekso-info.desktop"

TEXTO_APP = re.compile(r"^application/(json|.*\+json|.*\+xml|xml|x-yaml|yaml|toml|x-toml|javascript|"
                       r"x-javascript|typescript|x-shellscript|x-sh|x-gdscript|sql|x-sql|x-php|"
                       r"x-perl|x-ruby|x-python.*|x-desktop|x-wine-extension-ini|x-subrip|"
                       r"x-cue|x-yaml|ld\+json|x-httpd-php|x-awk|x-csh|x-latex|x-tex|x-troff.*|"
                       r"x-sqlite3-sql|vnd\.debian\.copyright)$")
ARCHIVOS = re.compile(r"^application/(zip|x-zip.*|x-tar|x-compressed-tar|.*-compressed-tar|gzip|x-gzip|"
                      r"x-7z-compressed|vnd\.rar|x-rar.*|x-xz|x-bzip.*|zstd|x-zstd.*|x-cpio|x-deb|"
                      r"vnd\.debian\.binary-package|x-archive|x-lzma|x-lzip|x-lz4|x-cd-image|"
                      r"x-iso9660-image|vnd\.efi\.iso|java-archive|x-java-archive|x-rpm|x-gtar|"
                      r"x-lha|x-lzh.*|x-arj|x-cab|vnd\.ms-cab-compressed|x-ms-wim|x-compress)$")
EXE = re.compile(r"^application/(x-ms-dos-executable|x-msdownload|vnd\.microsoft\.portable-executable|"
                 r"x-dosexec|x-msi|x-ms-installer)$")
# Binarios de Linux: no se ejecutan con doble clic, a propósito. Se muestra su información.


NAVEGADORES = ["brave-browser.desktop", "google-chrome.desktop"]
WEB = ("text/html", "application/xhtml+xml", "x-scheme-handler/http", "x-scheme-handler/https")


def elegir(tipo):
    if tipo in WEB:
        # El primer navegador instalado; si no hay ninguno, no se asigna nada (HTML cae al editor).
        return next((n for n in NAVEGADORES if instalada(n)), EDITOR if tipo.startswith("text/") else INFO)
    if tipo.startswith("text/"):
        return EDITOR
    if tipo == "image/svg+xml":
        return IMAGEN
    if tipo.startswith("image/"):
        return IMAGEN
    if tipo.startswith(("audio/", "video/")) or tipo in ("application/ogg", "application/x-matroska"):
        return REPRODUCTOR
    if tipo == "application/pdf":
        return PDF
    if EXE.match(tipo):
        return WINE
    if ARCHIVOS.match(tipo):
        return ARCHIVADOR
    if TEXTO_APP.match(tipo):
        return EDITOR
    return INFO  # todo lo demás: información del archivo, nunca ejecutarlo


def instalada(desktop):
    return any(os.path.exists(os.path.join(d, desktop)) for d in APPS)


def main():
    ruta = os.path.expanduser("~/.config/mimeapps.list")
    tipos = [l.strip() for l in open("/usr/share/mime/types", encoding="utf-8") if "/" in l]
    tipos += [t for t in WEB if t not in tipos]
    cfg = configparser.RawConfigParser(strict=False)
    cfg.optionxform = str
    if os.path.exists(ruta):
        cfg.read(ruta, encoding="utf-8")
    if not cfg.has_section("Default Applications"):
        cfg.add_section("Default Applications")
    d = cfg["Default Applications"]
    nuevos = 0
    for t in tipos:
        if t in d and d[t].strip():
            # Los tipos web pasan al navegador cuando se instala uno, si aún tenían el valor automático.
            if not (t in WEB and d[t] in (EDITOR, INFO) and elegir(t) in NAVEGADORES):
                continue
        app = elegir(t)
        if instalada(app):
            d[t] = app
            nuevos += 1
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        cfg.write(f, space_around_delimiters=False)
    print(f"{nuevos} tipos nuevos asociados; {len(d)} en total")


if __name__ == "__main__":
    sys.exit(main())
