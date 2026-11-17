#!/usr/bin/env bash
# Instala LeksSO sobre un Debian 13 recién instalado (sin escritorio).
#
#   wget https://raw.githubusercontent.com/Leksgg/LeksSO/v0.1.4-alpha/scripts/instalar.sh
#   sudo bash instalar.sh
#
# Qué hace, en orden:
#   1. Comprueba que es Debian 13 (amd64), que tienes conexión y que lo lanzas con sudo desde tu usuario.
#   2. Descarga la versión más reciente (o la que indiques con --version) y COMPRUEBA SU FIRMA con la clave
#      de LeksSO incluida en este script. Sin firma válida, o si el commit no está en la rama principal, para.
#   3. Te enseña qué va a instalar y pide confirmación.
#   4. Ejecuta la instalación (escritorio, caja, permisor de IA, cortafuegos, actualizaciones firmadas...).
#
# Huella de la clave de LeksSO (compárala con la publicada por quien te dio este script):
#   SHA256:rtOK+qmzbIgjUTGIb0KTjz9fzUq2+tF2ULf04uwAoRU
#
# Opciones: --version vX.Y.Z-alpha   instala esa versión en vez de la última
#           --origen RUTA_O_URL      de dónde sale el repositorio (por ejemplo un paquete .bundle del USB de
#                                    instalación). La firma se comprueba igual, con la clave de este script.
#           --simular                comprueba todo, pero no instala
#           --si                     no pregunta antes de instalar
set -euo pipefail

REPO="https://github.com/Leksgg/LeksSO.git"
REPO_OFICIAL="$REPO"
CLON="/var/lib/lekso/repo"
CLAVE_PUBLICA='lekso-release namespaces="git" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOlE6yy0lZmsYsRBZSGDhu8VIWYVrjHbWNIrl20tAArL'
HUELLA_ESPERADA='SHA256:rtOK+qmzbIgjUTGIb0KTjz9fzUq2+tF2ULf04uwAoRU'
RAMA="origin/main"
OSRELEASE="/etc/os-release"
# Solo para las pruebas del propio instalador (nunca llegan por sudo): sustituyen la clave y el origen.
if [ "${LEKSO_INSTALAR_PRUEBAS:-}" = "1" ]; then
  REPO="${LEKSO_PRUEBA_REPO:-$REPO}"; CLON="${LEKSO_PRUEBA_CLON:-$CLON}"
  CLAVE_PUBLICA="${LEKSO_PRUEBA_CLAVE:-$CLAVE_PUBLICA}"; HUELLA_ESPERADA="${LEKSO_PRUEBA_HUELLA:-$HUELLA_ESPERADA}"
  RAMA="${LEKSO_PRUEBA_RAMA:-$RAMA}"; OSRELEASE="${LEKSO_PRUEBA_OSRELEASE:-$OSRELEASE}"
fi
ETIQUETA='^v[0-9]+\.[0-9]+\.[0-9]+-(alpha|beta|rc)$'

die() { echo "ERROR: $*" >&2; exit 1; }
info() { printf '\n==> %s\n' "$*"; }

comprobar_sistema() {
  [ "$(id -u)" -eq 0 ] || die "Ejecútalo con sudo:  sudo bash $0"
  USUARIO="${SUDO_USER:-}"
  { [ -n "$USUARIO" ] && [ "$USUARIO" != root ] && id "$USUARIO" >/dev/null 2>&1; } \
    || die "Lanza el script con sudo desde tu usuario (no entrando como root), para saber para quién se instala."
  # shellcheck disable=SC1090
  . "$OSRELEASE"
  [ "${ID:-}" = debian ] && [ "${VERSION_ID:-}" = 13 ] || die "Hace falta Debian 13 (trixie). Este sistema es: ${PRETTY_NAME:-desconocido}."
  [ "$(dpkg --print-architecture 2>/dev/null || echo amd64)" = amd64 ] || die "Solo para equipos de 64 bits (amd64)."
}

instalar_requisitos() {
  info "Preparando lo necesario (git y comprobación de firmas)"
  DEBIAN_FRONTEND=noninteractive apt-get update -qq || echo "(sin conexión: se usan los paquetes locales)"
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git ca-certificates openssh-client python3 >/dev/null
}

elegir_version() {
  local pedida="${1:-}" tags
  if [ -n "$pedida" ]; then
    [[ "$pedida" =~ $ETIQUETA ]] || die "Versión no válida: $pedida (debe ser como v0.1.4-alpha)"
    echo "$pedida"; return
  fi
  tags="$(git ls-remote --tags --refs "$REPO" 'refs/tags/v*' 2>/dev/null | sed 's#.*refs/tags/##' | grep -E "$ETIQUETA" || true)"
  [ -n "$tags" ] || die "No encuentro versiones publicadas en $REPO (¿hay conexión?)."
  # orden por número de versión: 0.9.0 < 0.10.0; a igual número, alpha < beta < rc
  echo "$tags" | python3 -c '
import re, sys
rango = {"alpha": 0, "beta": 1, "rc": 2}
def clave(t):
    m = re.match(r"^v(\d+)\.(\d+)\.(\d+)-(alpha|beta|rc)$", t)
    return (int(m[1]), int(m[2]), int(m[3]), rango[m[4]])
print(sorted((l.strip() for l in sys.stdin if l.strip()), key=clave)[-1])'
}

preparar_clon() {
  mkdir -p "$(dirname "$CLON")"
  if [ -d "$CLON/.git" ]; then
    git -C "$CLON" fetch --tags --force origin >/dev/null 2>&1 || die "No se pudo actualizar la copia local."
  else
    rm -rf "$CLON"
    git clone --no-checkout "$REPO" "$CLON" >/dev/null 2>&1 || die "No se pudo descargar $REPO"
    git -C "$CLON" fetch --tags --force origin >/dev/null 2>&1 || true
  fi
}

# Comprueba la versión con la clave incluida en ESTE script (no con la del repositorio descargado).
# Devuelve por variables globales: COMMIT, FIRMA
verificar_version() {
  local tag="$1" tmp huella salida
  tmp="$(mktemp -d)"
  trap "rm -rf '$tmp'" RETURN      # se expande ahora: el trap RETURN se repite al salir de otras funciones
  printf '%s\n' "$CLAVE_PUBLICA" > "$tmp/allowed_signers"
  # la clave incluida debe ser la esperada (huella publicada)
  huella="$(printf '%s\n' "${CLAVE_PUBLICA#* ssh-}" | sed 's/^/ssh-/' | ssh-keygen -lf - 2>/dev/null | awk '{print $2}' || true)"
  [ "$huella" = "$HUELLA_ESPERADA" ] || die "La clave de este script no coincide con la huella esperada ($HUELLA_ESPERADA). No sigo."
  salida="$(git -C "$CLON" -c gpg.ssh.allowedSignersFile="$tmp/allowed_signers" verify-tag "$tag" 2>&1)" \
    || die "La versión $tag NO tiene una firma válida de LeksSO. No se instala nada.
$salida"
  case "$salida" in *'Good "git" signature for '*) ;; *) die "La firma de $tag no es de un firmante autorizado. No se instala nada." ;; esac
  COMMIT="$(git -C "$CLON" rev-list -n 1 "$tag")"
  [[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || die "No se pudo identificar el commit de $tag."
  git -C "$CLON" merge-base --is-ancestor "$COMMIT" "$RAMA" \
    || die "La versión $tag no pertenece a la rama principal del repositorio. No se instala nada."
  FIRMA="$HUELLA_ESPERADA"
  echo "Firma válida de $tag · commit ${COMMIT:0:7} · rama principal · clave $FIRMA"
}

main() {
  local version_pedida="" simular=0 si=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --origen) [ $# -ge 2 ] || die "Falta la ruta tras --origen"; REPO="$2"; shift 2 ;;
      --version) [ $# -ge 2 ] || die "Falta la versión tras --version"; version_pedida="$2"; shift 2 ;;
      --simular) simular=1; shift ;;
      --si) si=1; shift ;;
      -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
      *) die "Opción desconocida: $1" ;;
    esac
  done
  comprobar_sistema
  instalar_requisitos
  local tag; tag="$(elegir_version "$version_pedida")"
  info "Versión elegida: $tag"
  preparar_clon
  git -C "$CLON" rev-parse -q --verify "refs/tags/$tag" >/dev/null || die "La versión $tag no existe en el repositorio."
  verificar_version "$tag"
  local nombre; nombre="$(git -C "$CLON" show "$tag:VERSION" 2>/dev/null | tr -d '[:space:]' || true)"
  echo
  echo "Se va a instalar LeksSO ${nombre:-$tag} para el usuario «$USUARIO»."
  echo "Cambiará la configuración del sistema (escritorio, cortafuegos, red, actualizaciones)."
  if [ "$simular" -eq 1 ]; then
    echo; echo "Simulación: todo comprobado, no se ha instalado nada."; return 0
  fi
  if [ "$si" -ne 1 ]; then
    read -r -p "¿Continuar? [s/N] " r
    [[ "$r" =~ ^[sS]$ ]] || { echo "Cancelado."; return 1; }
  fi
  git -C "$CLON" checkout --force --detach "$tag" >/dev/null 2>&1 || die "No se pudo preparar la versión."
  git -C "$CLON" clean -fdxq
  info "Instalando (puede tardar unos minutos)"
  bash "$CLON/scripts/provision-base.sh" "$USUARIO"
  install -d -m 0755 /var/lib/lekso
  printf '{"version": "%s", "commit": "%s", "firma": "%s"}\n' "${tag#v}" "$COMMIT" "$FIRMA" > /var/lib/lekso/instalada.json
  # instalado desde un paquete local (USB): las actualizaciones vendrán del repositorio oficial
  if [ "$REPO" != "$REPO_OFICIAL" ] && [ "${LEKSO_INSTALAR_PRUEBAS:-0}" != 1 ]; then git -C "$CLON" remote set-url origin "$REPO_OFICIAL"; fi
  info "Listo"
  echo "LeksSO ${nombre:-$tag} instalado. Reinicia el equipo (sudo reboot): al iniciar sesión en la primera consola arranca el escritorio."
}

# Para las pruebas se puede cargar el script sin ejecutarlo.
if [ "${LEKSO_INSTALAR_SOLO_FUNCIONES:-}" != "1" ]; then
  main "$@"
fi
