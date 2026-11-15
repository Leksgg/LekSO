#!/usr/bin/env python3
"""Panel de IA de LekSO: una pantalla, pocas teclas. Se abre con Mod+a.

  a aprobar    r aprobar y recordar carpetas    x rechazar
  ↑ ↓ elegir una acción      u deshacer la acción      t deshacer toda su tarea
  q salir
Arriba: estado de la IA y RAM. En medio: lo que la IA pide. Abajo: lo que ha hecho.
"""
import curses
import socket
import json

import modelo
import permisor

NOMBRES = {"r": "leer", "w": "escribir", "d": "borrar (a la papelera)"}


def llamar(**m):
    try:
        with socket.socket(socket.AF_UNIX) as s:
            s.settimeout(3)
            s.connect(str(permisor.rutas()[1]))
            s.sendall((json.dumps(m) + "\n").encode())
            return json.loads(s.makefile().readline())
    except OSError:
        return {"ok": False, "error": "El permisor no está en marcha (lekso-ia servir)"}


def instantanea():
    total, libre = modelo.ram()
    est = modelo.estado_barra()
    pend = llamar(op="pendientes")
    reg = llamar(op="registro", n=60)
    acciones = [r for r in reg.get("registro", [])
                if r.get("ok") and r.get("id") and r.get("accion") in ("escribir", "borrar", "mover")]
    hechas = {r["deshace"] for r in reg.get("registro", []) if "deshace" in r}
    for r in acciones:
        r["deshecha"] = r["id"] in hechas
    return {"ia": est["text"], "ram": f"{modelo.gb(total - libre)} de {modelo.gb(total)}",
            "pendientes": pend.get("pendientes", {}), "error": pend.get("error"),
            "acciones": list(reversed(acciones))[:12]}


def dibujar(p, s, sel, mensaje):
    p.erase()
    h, w = p.getmaxyx()
    p.addstr(0, 1, f"{s['ia']}    RAM {s['ram']}"[: w - 2], curses.A_BOLD)
    y = 2
    if s["error"]:
        p.addstr(y, 1, s["error"][: w - 2], curses.color_pair(3))
        y += 2
    if s["pendientes"]:
        for pid, q in s["pendientes"].items():
            p.addstr(y, 1, "La IA pide:", curses.A_BOLD)
            p.addstr(y, 13, q["titulo"][: w - 14])
            y += 1
            for ruta, perms in q["carpetas"].items():
                p.addstr(y, 3, f"{ruta}: " + ", ".join(NOMBRES[x] for x in perms))
                y += 1
            if q["destino"] == "nube":
                p.addstr(y, 3, "Lo que lea saldrá a la NUBE", curses.color_pair(2))
                y += 1
            p.addstr(y, 3, "[a] permitir   [r] permitir y recordar   [x] rechazar", curses.color_pair(1))
            y += 2
    else:
        p.addstr(y, 1, "La IA no ha pedido nada.", curses.color_pair(4))
        y += 2
    p.addstr(y, 1, "Lo que ha hecho (↑↓ elegir, u deshacer, t toda la tarea)", curses.A_BOLD)
    y += 1
    for i, a in enumerate(s["acciones"]):
        if y >= h - 2:
            break
        marca = "deshecha" if a["deshecha"] else ""
        linea = f"{a['t'][11:]} {a['accion']:<9} {a['ruta']} {marca}"
        p.addstr(y, 3, linea[: w - 4], curses.A_REVERSE if i == sel else curses.A_NORMAL)
        y += 1
    if mensaje:
        p.addstr(h - 1, 1, mensaje[: w - 2], curses.color_pair(2))
    p.refresh()


def bucle(p):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)
    p.timeout(1000)
    sel, mensaje = 0, ""
    while True:
        s = instantanea()
        dibujar(p, s, sel, mensaje)
        mensaje = ""
        k = p.getch()
        pid = next(iter(s["pendientes"]), None)
        if k in (ord("q"), 27):
            return
        if k == curses.KEY_DOWN:
            sel = min(sel + 1, max(len(s["acciones"]) - 1, 0))
        elif k == curses.KEY_UP:
            sel = max(sel - 1, 0)
        elif k in (ord("a"), ord("r")) and pid:
            r = llamar(op="aprobar", pid=pid, recordar=(k == ord("r")))
            mensaje = "Permitido." if r.get("ok") else r.get("error", "")
        elif k == ord("x") and pid:
            llamar(op="rechazar", pid=pid)
            mensaje = "Rechazado."
        elif k in (ord("u"), ord("t")) and s["acciones"]:
            a = s["acciones"][min(sel, len(s["acciones"]) - 1)]
            if k == ord("u"):
                r = llamar(op="deshacer", accion=a["id"])
            else:
                r = llamar(op="deshacer_tarea", tarea=a["tarea"])
            mensaje = "Deshecho." if r.get("ok") else r.get("error", "")


if __name__ == "__main__":
    curses.wrapper(bucle)
