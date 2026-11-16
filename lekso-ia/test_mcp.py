"""Pruebas del adaptador MCP del permisor: protocolo, herramientas, argumentos hostiles y flujo completo."""
import os as _os
_os.environ["LEKSO_SIN_AVISOS"] = "1"   # sin notificaciones de escritorio durante las pruebas
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import mcp_permisor as mcp
import permisor

AQUI = os.path.dirname(os.path.abspath(__file__))


def rpc(metodo, params=None, mid=1):
    m = {"jsonrpc": "2.0", "id": mid, "method": metodo}
    if params is not None:
        m["params"] = params
    return mcp.responder(m)


def llamar(nombre, **args):
    r = rpc("tools/call", {"name": nombre, "arguments": args})
    texto = r["result"]["content"][0]["text"]
    return (texto if r["result"]["isError"] and not texto.startswith("{") else json.loads(texto)), r["result"]["isError"]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lekso-mcp-"))
        os.environ["XDG_RUNTIME_DIR"] = str(self.tmp)
        self.casa = self.tmp / "casa"
        self.proy = self.casa / "proy"
        self.proy.mkdir(parents=True)
        (self.casa / "secreto.txt").write_text("no tocar")
        (self.proy / "a.txt").write_text("hola")
        self.p = permisor.Permisor(self.casa)
        ia, _ = permisor.rutas()
        self.s1 = permisor._servidor(str(ia), self.p.manejar_ia)
        threading.Thread(target=self.s1.serve_forever, daemon=True).start()

    def tearDown(self):
        try:
            self.s1.shutdown()
        except Exception:
            pass

    def aprobar(self, perms="rwd"):
        r, err = llamar("pedir_acceso", titulo="prueba", carpetas={str(self.proy): perms}, esperar_s=0)
        self.assertFalse(err, r)
        self.assertEqual(r["estado"], "pendiente")
        tarea = self.p.manejar_control({"op": "aprobar", "pid": r["pid"]})["tarea"]
        return r["pid"], tarea


class Protocolo(unittest.TestCase):
    def test_initialize(self):
        r = rpc("initialize", {"protocolVersion": "2025-03-26"})["result"]
        self.assertEqual(r["protocolVersion"], "2025-03-26")
        self.assertIn("tools", r["capabilities"])
        self.assertEqual(rpc("initialize", {"protocolVersion": "1999-01-01"})["result"]["protocolVersion"], mcp.VERSIONES[0])

    def test_notificacion_sin_respuesta(self):
        self.assertIsNone(mcp.responder({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_errores_de_protocolo(self):
        self.assertEqual(mcp.responder([])["error"]["code"], -32600)
        self.assertEqual(rpc("no/existe")["error"]["code"], -32601)
        self.assertEqual(rpc("tools/call", {"name": "aprobar", "arguments": {}})["error"]["code"], -32602)
        self.assertEqual(rpc("tools/call", {"name": ["x"], "arguments": {}})["error"]["code"], -32602)

    def test_solo_las_herramientas_previstas(self):
        tools = rpc("tools/list")["result"]["tools"]
        nombres = {t["name"] for t in tools}
        self.assertEqual(nombres, {"pedir_acceso", "estado_peticion", "listar", "leer", "escribir",
                                   "borrar", "mover", "cerrar_tarea", "estado_equipo"})
        for t in tools:
            self.assertFalse(t["inputSchema"]["additionalProperties"])
        for prohibido in ("aprobar", "rechazar", "ejecutar", "shell", "control", "deshacer"):
            self.assertNotIn(prohibido, nombres)


class Flujo(Base):
    def test_flujo_completo(self):
        pid, tarea = self.aprobar()
        self.assertEqual(llamar("estado_peticion", pid=pid)[0]["tarea"], tarea)
        self.assertEqual(llamar("listar", tarea=tarea, ruta=str(self.proy))[0]["entradas"][0]["nombre"], "a.txt")
        r, _ = llamar("leer", tarea=tarea, ruta=str(self.proy / "a.txt"))
        self.assertEqual(r["texto"], "hola")
        self.assertIn("no confiable", r["aviso_general"])
        llamar("escribir", tarea=tarea, ruta=str(self.proy / "b.txt"), texto="nuevo")
        self.assertEqual((self.proy / "b.txt").read_text(), "nuevo")
        llamar("mover", tarea=tarea, origen=str(self.proy / "b.txt"), destino=str(self.proy / "c.txt"))
        self.assertTrue((self.proy / "c.txt").exists() and not (self.proy / "b.txt").exists())
        llamar("borrar", tarea=tarea, ruta=str(self.proy / "c.txt"))
        self.assertFalse((self.proy / "c.txt").exists())
        llamar("cerrar_tarea", tarea=tarea)
        r, err = llamar("leer", tarea=tarea, ruta=str(self.proy / "a.txt"))
        self.assertTrue(err or not r["ok"], "una tarea cerrada no debe poder leer")

    def test_esperar_la_aprobacion(self):
        def aprobar_tarde():
            time.sleep(1.5)
            self.p.manejar_control({"op": "aprobar", "pid": next(iter(self.p.pendientes))})
        threading.Thread(target=aprobar_tarde, daemon=True).start()
        r, err = llamar("pedir_acceso", titulo="espera", carpetas={str(self.proy): "r"}, esperar_s=10)
        self.assertFalse(err)
        self.assertEqual(r["estado"], "aprobada")

    def test_sin_respuesta_sigue_pendiente(self):
        r, _ = llamar("pedir_acceso", titulo="x", carpetas={str(self.proy): "r"}, esperar_s=1)
        self.assertEqual(r["estado"], "pendiente")
        self.assertIn("nota", r)

    def test_rechazada(self):
        r, _ = llamar("pedir_acceso", titulo="x", carpetas={str(self.proy): "r"}, esperar_s=0)
        self.p.manejar_control({"op": "rechazar", "pid": r["pid"]})
        self.assertEqual(llamar("estado_peticion", pid=r["pid"])[0]["estado"], "rechazada")

    def test_leer_recorta_para_ahorrar_tokens(self):
        _, tarea = self.aprobar()
        (self.proy / "grande.txt").write_text("x" * 50000)
        r, _ = llamar("leer", tarea=tarea, ruta=str(self.proy / "grande.txt"), max_caracteres=100)
        self.assertEqual(len(r["texto"]), 100)
        self.assertIn("recortado", r)
        r, _ = llamar("leer", tarea=tarea, ruta=str(self.proy / "grande.txt"))
        self.assertEqual(len(r["texto"]), mcp.MAX_SALIDA)


class Hostil(Base):
    def test_el_permisor_sigue_mandando(self):
        _, tarea = self.aprobar(perms="r")
        for ruta in (str(self.casa / "secreto.txt"), str(self.proy / ".." / "secreto.txt"), "/etc/passwd"):
            r, err = llamar("leer", tarea=tarea, ruta=ruta)
            self.assertTrue(err or not r["ok"], ruta)
        r, err = llamar("escribir", tarea=tarea, ruta=str(self.proy / "x.txt"), texto="no")
        self.assertTrue(err or not r["ok"], "una tarea de solo lectura no escribe")
        self.assertFalse((self.proy / "x.txt").exists())

    def test_destino_no_se_puede_falsear(self):
        llamar("pedir_acceso", titulo="x", carpetas={str(self.proy): "r"}, esperar_s=0, destino="nube")
        pid = next(iter(self.p.pendientes))
        self.assertEqual(self.p.pendientes[pid]["destino"], "local")   # lo fija el canal, no el argumento

    def test_argumentos_raros(self):
        casos = [("leer", {}), ("leer", {"tarea": 1, "ruta": 2}), ("leer", {"tarea": "x", "ruta": "a" * 5000}),
                 ("escribir", {"tarea": "x", "ruta": "/a", "texto": {}}),
                 ("pedir_acceso", {"titulo": "x", "carpetas": []}),
                 ("pedir_acceso", {"titulo": "x", "carpetas": {"/a": 5}}),
                 ("pedir_acceso", {"titulo": "\x1b[2J", "carpetas": {str(self.proy): "r"}}),
                 ("estado_peticion", {"pid": None})]
        for nombre, args in casos:
            r, err = llamar(nombre, **args)
            self.assertTrue(err or not r.get("ok", True), (nombre, args))
        r = rpc("tools/call", {"name": "leer", "arguments": "no soy un objeto"})
        self.assertTrue(r["result"]["isError"])

    def test_numeros_absurdos(self):
        mcp.ESPERA_MAX = mcp.ESPERA_DEF = 1     # los topes de espera se bajan para que la prueba no tarde
        try:
            for v in (float("inf"), float("nan"), -5, 10 ** 30, "abc", None, True):
                t0 = time.time()
                r, err = llamar("pedir_acceso", titulo="n", carpetas={str(self.proy): "r"}, esperar_s=v)
                self.assertLess(time.time() - t0, 5, v)
                self.assertIsNotNone(r)
            _, tarea = self.aprobar()
            for v in (float("inf"), float("nan"), -1, 0, "x"):
                r, _ = llamar("leer", tarea=tarea, ruta=str(self.proy / "a.txt"), max_caracteres=v)
                self.assertIsNotNone(r)
        finally:
            mcp.ESPERA_MAX, mcp.ESPERA_DEF = 300, 60

    def test_permisor_caido(self):
        self.s1.shutdown()
        self.s1.server_close()
        r, err = llamar("listar", tarea="x", ruta="/a")
        self.assertTrue(err)
        self.assertIn("permisor", r.lower())

    def test_texto_enorme(self):
        _, tarea = self.aprobar()
        r, err = llamar("escribir", tarea=tarea, ruta=str(self.proy / "g.txt"), texto="A" * (9 * 1024 * 1024))
        self.assertTrue(err or not r["ok"])
        self.assertFalse((self.proy / "g.txt").exists())


class RutasDeLaCaja(Base):
    """El modelo vive en una caja con otro HOME (/home/caja). Las rutas se traducen a las del equipo real."""

    def setUp(self):
        super().setUp()
        self._antes = os.environ.get("LEKSO_HOME_REAL")
        os.environ["LEKSO_HOME_REAL"] = str(self.casa)

    def tearDown(self):
        if self._antes is None:
            os.environ.pop("LEKSO_HOME_REAL", None)
        else:
            os.environ["LEKSO_HOME_REAL"] = self._antes
        super().tearDown()

    def test_traduccion(self):
        casa = str(self.casa)
        self.assertEqual(mcp._ruta_real("~/proy"), casa + "/proy")
        self.assertEqual(mcp._ruta_real("~"), casa)
        self.assertEqual(mcp._ruta_real("/home/caja/proy/a.txt"), casa + "/proy/a.txt")
        self.assertEqual(mcp._ruta_real("/home/caja"), casa)
        for intacta in ("/etc/passwd", "/home/cajaX/a", "~otro/a", "relativa/a", "/home/caja2"):
            self.assertEqual(mcp._ruta_real(intacta), intacta)
        self.assertEqual(mcp._ruta_real(5), 5)

    def test_sin_casa_real_no_se_traduce(self):
        os.environ.pop("LEKSO_HOME_REAL")
        self.assertEqual(mcp._ruta_real("~/proy"), "~/proy")
        os.environ["LEKSO_HOME_REAL"] = "relativa"        # no absoluta: se ignora
        self.assertEqual(mcp._ruta_real("~/proy"), "~/proy")

    def test_pedir_y_escribir_con_tilde_y_con_la_casa_de_la_caja(self):
        r, err = llamar("pedir_acceso", titulo="t", carpetas={"~/proy": "rw"}, esperar_s=0)
        self.assertFalse(err, r)
        pid = r["pid"]
        self.assertEqual(list(self.p.pendientes[pid]["carpetas"]), [str(self.proy)])
        tarea = self.p.manejar_control({"op": "aprobar", "pid": pid})["tarea"]
        r, _ = llamar("escribir", tarea=tarea, ruta="/home/caja/proy/nueva/sub/a.txt", texto="hola")   # crea las carpetas
        self.assertTrue(r["ok"], r)
        self.assertEqual((self.proy / "nueva" / "sub" / "a.txt").read_text(), "hola")
        r, _ = llamar("listar", tarea=tarea, ruta="~/proy/nueva")
        self.assertEqual([e["nombre"] for e in r["entradas"]], ["sub"])
        r, _ = llamar("leer", tarea=tarea, ruta="~/proy/nueva/sub/a.txt")
        self.assertEqual(r["texto"], "hola")

    def test_pedir_una_carpeta_nueva(self):
        nueva = self.casa / "proyectos"
        r, err = llamar("pedir_acceso", titulo="estructura", carpetas={"~/proyectos": "rw"}, esperar_s=0)
        self.assertFalse(err, r)
        self.assertFalse(nueva.exists(), "pedirla no debe crearla")
        self.assertEqual(self.p.pendientes[r["pid"]]["nuevas"], [str(nueva)])
        tarea = self.p.manejar_control({"op": "aprobar", "pid": r["pid"]})["tarea"]
        self.assertTrue(nueva.is_dir(), "al aprobar sí se crea")
        r, _ = llamar("escribir", tarea=tarea, ruta="~/proyectos/activos/README.md", texto="# activos\n")
        self.assertTrue(r["ok"], r)

    def test_la_casa_entera_no_se_puede_pedir(self):
        r, err = llamar("pedir_acceso", titulo="todo", carpetas={"~": "rwd"}, esperar_s=0)
        self.assertTrue(err or not r["ok"])

    def test_la_traduccion_no_amplia_el_alcance(self):
        _, tarea = self.aprobar(perms="r")
        for ruta in ("~/secreto.txt", "/home/caja/secreto.txt", "~/../etc/passwd"):
            r, err = llamar("leer", tarea=tarea, ruta=ruta)
            self.assertTrue(err or not r["ok"], ruta)

    def test_instrucciones_dicen_donde_esta_la_casa(self):
        texto = rpc("initialize", {"protocolVersion": "2025-06-18"})["result"]["instructions"]
        self.assertIn(str(self.casa), texto)
        self.assertIn("/home/caja", texto)
        self.assertIn("escribir crea", texto)


class Stdio(unittest.TestCase):
    def lanzar(self):
        env = dict(os.environ, XDG_RUNTIME_DIR=tempfile.mkdtemp(prefix="lekso-mcp-io-"), PYTHONPATH=AQUI)
        return subprocess.Popen([sys.executable, os.path.join(AQUI, "mcp_permisor.py")],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)

    def test_conversacion(self):
        p = self.lanzar()
        entrada = "\n".join([
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            "esto no es json",
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        ]) + "\n"
        salida, _ = p.communicate(entrada, timeout=20)
        lineas = [json.loads(x) for x in salida.strip().splitlines()]
        self.assertEqual(len(lineas), 3)           # la notificación no tiene respuesta
        self.assertEqual(lineas[1]["error"]["code"], -32700)
        self.assertEqual(len(lineas[2]["result"]["tools"]), 9)

    def test_linea_gigante_no_cuelga(self):
        p = self.lanzar()
        t0 = time.time()
        try:
            salida, _ = p.communicate("x" * (17 * 1024 * 1024) + "\n", timeout=20)
        except subprocess.TimeoutExpired:
            p.kill()
            self.fail("el adaptador se cuelga con una línea gigante")
        self.assertLess(time.time() - t0, 15)
        self.assertIn("demasiado grande", salida)


if __name__ == "__main__":
    unittest.main()
