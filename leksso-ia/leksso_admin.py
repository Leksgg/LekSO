#!/usr/bin/env python3
"""Servicio de administración de LeksSO: ejecuta como administrador las órdenes que le pasa el permisor.

Corre como root. Solo atiende si se cumplen las tres cosas:
  1. quien llama es el servicio del permisor de ese usuario (se comprueba el grupo de control y el programa);
  2. ese usuario tiene algún asistente activo con permiso de administración en /etc/leksso/asistentes.json;
  3. el mensaje es una orden de texto de tamaño razonable.
Quién puede pedir qué (qué asistente, si hay que preguntar) lo decide el permisor; esto es la última puerta.
Límite conocido: un programa que ya controla la cuenta del usuario puede suplantar al permisor. Por eso la
administración está apagada salvo que el usuario la encienda con su contraseña.
"""
import json
import os
import pwd
import socket
import socketserver
import struct
import subprocess

import asistentes

RUTA = "/run/leksso-admin.sock"
MAX_LINEA = 64 * 1024
MAX_SALIDA = 400_000


def _es_el_permisor(pid):
    try:
        with open(f"/proc/{pid}/cgroup", encoding="utf-8") as f:
            grupos = f.read()
        programa = os.path.realpath(f"/proc/{pid}/exe")
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            orden = f.read().split(b"\0")
    except OSError:
        return False
    return ("/leksso-permisor.service" in grupos and os.path.basename(programa).startswith("python3")
            and programa.startswith("/usr/bin/") and b"/usr/local/lib/leksso-ia/permisor.py" in orden)


def ejecutar(orden, espera, casa):
    entorno = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root",
               "LANG": os.environ.get("LANG", "C.UTF-8"), "DEBIAN_FRONTEND": "noninteractive", "TERM": "dumb"}
    try:
        r = subprocess.run(["/bin/bash", "-c", orden], cwd=casa if os.path.isdir(casa) else "/", env=entorno,
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=espera, start_new_session=True)
        return {"ok": True, "codigo": r.returncode, "salida": r.stdout.decode("utf-8", "replace")[-MAX_SALIDA:]}
    except subprocess.TimeoutExpired as e:
        salida = (e.stdout or b"").decode("utf-8", "replace")[-MAX_SALIDA:]
        return {"ok": True, "codigo": 124, "salida": salida + f"\n[se cortó a los {espera} s]"}


class H(socketserver.StreamRequestHandler):
    def handle(self):
        pid, uid, _ = struct.unpack("3i", self.request.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
        try:
            r = self._atender(pid, uid)
        except Exception as e:      # nunca tumbar el servicio por una petición
            r = {"ok": False, "error": f"error interno: {type(e).__name__}"}
        try:
            self.wfile.write((json.dumps(r, ensure_ascii=False) + "\n").encode())
        except OSError:
            pass

    def _atender(self, pid, uid):
        if uid < 1000 or not _es_el_permisor(pid):
            return {"ok": False, "error": "solo atiende al permisor de LeksSO"}
        usuario = pwd.getpwuid(uid)
        if not asistentes.alguno_administra(usuario.pw_name):
            return {"ok": False, "error": "ningún asistente tiene permiso de administración"}
        self.request.settimeout(30)
        linea = self.rfile.readline(MAX_LINEA + 1)
        if not linea or len(linea) > MAX_LINEA:
            return {"ok": False, "error": "mensaje no válido"}
        m = json.loads(linea)
        orden, espera = m.get("orden"), m.get("espera", 120)
        if not isinstance(orden, str) or not 0 < len(orden) <= 8000 or "\0" in orden:
            return {"ok": False, "error": "orden no válida"}
        if isinstance(espera, bool) or not isinstance(espera, int):
            espera = 120
        self.request.settimeout(None)
        return ejecutar(orden, min(max(espera, 1), 1800), usuario.pw_dir)


def main():
    if os.path.exists(RUTA):
        os.unlink(RUTA)
    s = socketserver.ThreadingUnixStreamServer(RUTA, H)
    os.chmod(RUTA, 0o666)        # cualquiera puede llamar; quién es se comprueba en cada conexión
    s.daemon_threads = True
    s.serve_forever()


if __name__ == "__main__":
    main()
