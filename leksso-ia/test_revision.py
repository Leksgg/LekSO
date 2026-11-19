"""Arreglos de la revisión de seguridad (Beta 0.1.22): aprobaciones del permisor y su panel."""
import json
import os
import stat
import tempfile
import time
import unittest

os.environ["LEKSSO_SIN_AVISOS"] = "1"
_TMP = tempfile.mkdtemp()
os.environ["LEKSSO_ASISTENTES"] = os.path.join(_TMP, "asistentes.json")

import asistentes  # noqa: E402
import leksso_admin  # noqa: E402
import panel  # noqa: E402
import permisor  # noqa: E402
from nucleo import Denegado  # noqa: E402


def fijar(**por_asistente):
    with open(os.environ["LEKSSO_ASISTENTES"], "w", encoding="utf-8") as f:
        json.dump({permisor._usuario(): por_asistente}, f)


class Aprobaciones(unittest.TestCase):
    def setUp(self):
        self.p = permisor.Permisor(tempfile.mkdtemp())
        self.hechas = []
        self.p.correr = {False: lambda o, e, c: self._corre("usuario", o), True: lambda o, e, c: self._corre("root", o)}

    def _corre(self, quien, orden):
        self.hechas.append((quien, orden))
        return {"codigo": 0, "salida": "ok"}

    def ia(self, asistente, **m):
        return self.p.manejar_ia(m, "nube", asistente)

    def pedir_destructiva(self, asistente="claude"):
        r = self.ia(asistente, op="ejecutar", orden="apt update", admin=True)
        self.assertEqual(r["estado"], "pendiente")
        return r["pid"]

    def test_orden_aprobada_caduca(self):
        fijar(claude={"activo": True, "comandos": True, "admin": "preguntar"})
        pid = self.pedir_destructiva()
        self.p.manejar_control({"op": "aprobar", "pid": pid})
        self.p.ordenes[pid]["hasta"] = time.time() - 1
        with self.assertRaises(Denegado):
            self.ia("claude", op="ejecutar", pid=pid)
        self.assertEqual(self.hechas, [])

    def test_revocar_el_permiso_tras_aprobar_la_frena(self):
        fijar(claude={"activo": True, "comandos": True, "admin": "preguntar"})
        pid = self.pedir_destructiva()
        self.p.manejar_control({"op": "aprobar", "pid": pid})
        fijar(claude={"activo": False, "comandos": True, "admin": "preguntar"})              # el usuario apaga el asistente
        with self.assertRaises(Denegado):
            self.ia("claude", op="ejecutar", pid=pid)
        self.assertEqual(self.hechas, [])

    def test_quitar_comandos_tras_aprobar_la_frena(self):
        fijar(claude={"activo": True, "comandos": True, "admin": "preguntar"})
        pid = self.pedir_destructiva()
        self.p.manejar_control({"op": "aprobar", "pid": pid})
        fijar(claude={"activo": True, "comandos": False, "admin": "no"})
        with self.assertRaises(Denegado):
            self.ia("claude", op="ejecutar", pid=pid)

    def test_aprobada_y_vigente_se_ejecuta_una_sola_vez(self):
        fijar(claude={"activo": True, "comandos": True, "admin": "preguntar"})
        pid = self.pedir_destructiva()
        self.p.manejar_control({"op": "aprobar", "pid": pid})
        self.assertEqual(self.ia("claude", op="ejecutar", pid=pid)["codigo"], 0)
        with self.assertRaises(Denegado):
            self.ia("claude", op="ejecutar", pid=pid)
        self.assertEqual(len(self.hechas), 1)

    def test_otro_asistente_no_canjea_la_orden(self):
        fijar(claude={"activo": True, "comandos": True, "admin": "preguntar"}, codex={"activo": True, "comandos": True, "admin": "preguntar"})
        pid = self.pedir_destructiva("claude")
        self.p.manejar_control({"op": "aprobar", "pid": pid})
        with self.assertRaises(Denegado):
            self.ia("codex", op="ejecutar", pid=pid)

    def test_orden_que_hay_que_aprobar_no_puede_ser_enorme(self):
        fijar(claude={"activo": True, "comandos": True, "admin": "preguntar"})
        larga = "apt update " + "a" * (permisor.MAX_ORDEN_PREGUNTAR + 10)
        with self.assertRaises(Denegado):
            self.ia("claude", op="ejecutar", orden=larga, admin=True)
        self.assertEqual(self.p.pendientes, {})
        # una orden larga que NO hay que aprobar sigue funcionando
        self.assertEqual(self.ia("claude", op="ejecutar", orden="echo " + "a" * 2000)["codigo"], 0)

    def test_peticiones_sin_responder_caducan(self):
        fijar(claude={"activo": True, "comandos": True, "admin": "preguntar"})
        pid = self.pedir_destructiva()
        self.p.pendientes[pid]["t"] -= permisor.CADUCA_PENDIENTE + 1
        self.assertEqual(self.p.manejar_control({"op": "pendientes"})["pendientes"], {})
        self.assertEqual(self.ia("claude", op="estado", pid=pid)["estado"], "rechazada")

    def test_los_identificadores_son_largos(self):
        fijar(claude={"activo": True, "comandos": True, "admin": "preguntar"})
        self.assertGreaterEqual(len(self.pedir_destructiva()), 17)

    def test_una_tarea_no_sirve_en_otro_canal(self):
        casa = str(self.p.n.casa)
        os.makedirs(os.path.join(casa, "docs"))
        open(os.path.join(casa, "docs", "a.txt"), "w").write("hola")
        fijar(claude={"activo": True, "archivos": "libre"}, codex={"activo": True})
        r = self.p.manejar_ia({"op": "pedir", "titulo": "leer", "carpetas": {os.path.join(casa, "docs"): "r"}},
                              "nube", "claude")
        t = r["tarea"]
        ruta = os.path.join(casa, "docs", "a.txt")
        self.assertEqual(self.p.manejar_ia({"op": "leer", "tarea": t, "ruta": ruta}, "nube", "claude")["texto"], "hola")
        for destino, quien in (("nube", "codex"), ("local", None), ("nube", None)):
            with self.assertRaises(Denegado, msg=(destino, quien)):
                self.p.manejar_ia({"op": "leer", "tarea": t, "ruta": ruta}, destino, quien)
        with self.assertRaises(Denegado):                      # ni siquiera sabe que existe
            self.p.manejar_ia({"op": "estado", "pid": r["pid"]}, "nube", "codex")

    def test_archivos_libre_no_sale_de_la_carpeta_personal(self):
        casa = str(self.p.n.casa)
        fuera = tempfile.mkdtemp()
        os.makedirs(os.path.join(casa, ".secreta"))
        fijar(claude={"activo": True, "archivos": "libre"})
        for carpeta in (fuera, os.path.join(casa, ".secreta")):
            r = self.p.manejar_ia({"op": "pedir", "titulo": "x", "carpetas": {carpeta: "r"}}, "nube", "claude")
            self.assertEqual(r["estado"], "pendiente", carpeta)

    def test_archivos_libre_pide_asistente_activo(self):
        casa = str(self.p.n.casa)
        os.makedirs(os.path.join(casa, "docs"))
        fijar(claude={"activo": False, "archivos": "libre"})
        r = self.p.manejar_ia({"op": "pedir", "titulo": "x", "carpetas": {os.path.join(casa, "docs"): "r"}},
                              "nube", "claude")
        self.assertEqual(r["estado"], "pendiente")


class MoverYDeshacer(unittest.TestCase):
    def setUp(self):
        from pathlib import Path
        from nucleo import Nucleo
        self.casa = Path(tempfile.mkdtemp())
        self.proy = self.casa / "proy"
        (self.proy / "sub").mkdir(parents=True)
        (self.proy / "a.txt").write_text("A")
        self.n = Nucleo(self.casa)

    def test_sacar_de_la_carpeta_pide_poder_borrar(self):
        t = self.n.conceder("rw", {str(self.proy): "rw"})
        self.n.mover(t, str(self.proy / "a.txt"), str(self.proy / "b.txt"))           # renombrar: basta escribir
        with self.assertRaises(Denegado):
            self.n.mover(t, str(self.proy / "b.txt"), str(self.proy / "sub" / "b.txt"))
        t2 = self.n.conceder("rwd", {str(self.proy): "rwd"})
        self.n.mover(t2, str(self.proy / "b.txt"), str(self.proy / "sub" / "b.txt"))
        self.assertTrue((self.proy / "sub" / "b.txt").exists())

    def test_no_pisa_un_destino_existente(self):
        t = self.n.conceder("rwd", {str(self.proy): "rwd"})
        (self.proy / "sub" / "a.txt").write_text("OTRO")
        with self.assertRaises(Denegado):
            self.n.mover(t, str(self.proy / "a.txt"), str(self.proy / "sub" / "a.txt"))
        self.assertEqual((self.proy / "sub" / "a.txt").read_text(), "OTRO")
        self.assertEqual((self.proy / "a.txt").read_text(), "A")

    def test_renombrar_sin_pisar_cierra_el_hueco(self):
        import nucleo
        d = os.open(str(self.proy), os.O_RDONLY | os.O_DIRECTORY)
        try:
            (self.proy / "x").write_text("x")
            with self.assertRaises(FileExistsError):
                nucleo.renombrar_sin_pisar("x", "a.txt", d, d)
            self.assertEqual((self.proy / "a.txt").read_text(), "A")
        finally:
            os.close(d)

    def test_deshacer_un_movimiento_comprueba_que_es_lo_mismo(self):
        t = self.n.conceder("rwd", {str(self.proy): "rwd"})
        aid = self.n.mover(t, str(self.proy / "a.txt"), str(self.proy / "sub" / "a.txt"))
        (self.proy / "sub" / "a.txt").unlink()                    # alguien cambia el archivo movido por otro
        (self.proy / "sub" / "a.txt").write_text("INTRUSO")
        with self.assertRaises(Denegado):
            self.n.deshacer(aid)
        self.assertFalse((self.proy / "a.txt").exists())

    def test_deshacer_un_borrado_comprueba_la_papelera(self):
        t = self.n.conceder("rwd", {str(self.proy): "rwd"})
        aid = self.n.borrar(t, str(self.proy / "a.txt"))
        nombre = [a for a in self.n.acciones.values() if a["id"] == aid][0]["papelera"]
        ruta = self.n.papelera / "files" / nombre
        ruta.unlink()
        ruta.write_text("OTRA COSA")
        with self.assertRaises(Denegado):
            self.n.deshacer(aid)
        self.assertFalse((self.proy / "a.txt").exists())

    def test_deshacer_normal_sigue_funcionando(self):
        t = self.n.conceder("rwd", {str(self.proy): "rwd"})
        aid = self.n.mover(t, str(self.proy / "a.txt"), str(self.proy / "sub" / "a.txt"))
        self.n.deshacer(aid)
        self.assertEqual((self.proy / "a.txt").read_text(), "A")
        aid = self.n.borrar(t, str(self.proy / "a.txt"))
        self.n.deshacer(aid)
        self.assertEqual((self.proy / "a.txt").read_text(), "A")


class QuienEsElPermisor(unittest.TestCase):
    G = "0::/user.slice/user-1000.slice/user@1000.service/app.slice/leksso-permisor.service\n"
    P = "/usr/bin/python3.13"
    O = [b"/usr/bin/python3", leksso_admin.SCRIPT_PERMISOR]

    def ok(self, grupos=None, programa=None, orden=None, entorno=(), uid=1000):
        return leksso_admin.parece_el_permisor(grupos or self.G, programa or self.P, orden or self.O, list(entorno), uid)

    def test_el_verdadero_pasa(self):
        self.assertTrue(self.ok())

    def test_grupo_distinto_o_de_otro_usuario_no(self):
        self.assertFalse(self.ok(grupos="0::/user.slice/user-1000.slice/user@1000.service/app.slice/x-leksso-permisor.service\n"))
        self.assertFalse(self.ok(grupos="0::/user.slice/user-1000.slice/user@1000.service/app.slice/leksso-permisor.service/otro\n"))
        self.assertFalse(self.ok(uid=1001))
        self.assertFalse(self.ok(grupos="0::/user.slice/user-1000.slice/session-3.scope\n"))

    def test_otro_programa_u_otra_orden_no(self):
        self.assertFalse(self.ok(programa="/home/yo/python3"))
        self.assertFalse(self.ok(orden=[b"python3", b"-c", b"print(1)", leksso_admin.SCRIPT_PERMISOR]))
        self.assertFalse(self.ok(orden=[b"python3", b"/tmp/permisor.py"]))
        self.assertFalse(self.ok(orden=[b"python3", b"-m", leksso_admin.SCRIPT_PERMISOR]))

    def test_variables_que_cambian_las_importaciones_no(self):
        self.assertFalse(self.ok(entorno=[b"PATH", b"PYTHONPATH"]))
        self.assertFalse(self.ok(entorno=[b"LD_PRELOAD"]))
        self.assertTrue(self.ok(entorno=[b"PATH", b"HOME", b"XDG_RUNTIME_DIR"]))


class SegundaRevision(unittest.TestCase):
    def setUp(self):
        self.p = permisor.Permisor(tempfile.mkdtemp())

    def ia(self, asistente, **m):
        return self.p.manejar_ia(m, "nube", asistente)

    def test_carpeta_sustituida_mientras_se_espera_no_se_concede(self):
        casa = str(self.p.n.casa)
        a = os.path.join(casa, "docs")
        os.makedirs(a)
        fijar(claude={"activo": True})
        r = self.ia("claude", op="pedir", titulo="leer", carpetas={a: "r"})
        self.assertEqual(r["estado"], "pendiente")
        os.rename(a, a + ".vieja")
        os.makedirs(a)                                        # otra carpeta con el mismo nombre
        with self.assertRaises(Denegado):
            self.p.manejar_control({"op": "aprobar", "pid": r["pid"]})

    def test_la_misma_carpeta_se_aprueba(self):
        casa = str(self.p.n.casa)
        a = os.path.join(casa, "docs")
        os.makedirs(a)
        fijar(claude={"activo": True})
        r = self.ia("claude", op="pedir", titulo="leer", carpetas={a: "r"})
        self.assertIn("tarea", self.p.manejar_control({"op": "aprobar", "pid": r["pid"]}))

    def test_desactivar_el_asistente_inutiliza_sus_tareas(self):
        casa = str(self.p.n.casa)
        a = os.path.join(casa, "docs")
        os.makedirs(a)
        open(os.path.join(a, "x.txt"), "w").write("hola")
        fijar(claude={"activo": True, "archivos": "libre"})
        t = self.ia("claude", op="pedir", titulo="leer", carpetas={a: "r"})["tarea"]
        self.assertEqual(self.ia("claude", op="leer", tarea=t, ruta=os.path.join(a, "x.txt"))["texto"], "hola")
        fijar(claude={"activo": False, "archivos": "libre"})
        with self.assertRaises(Denegado):
            self.ia("claude", op="leer", tarea=t, ruta=os.path.join(a, "x.txt"))

    def test_un_asistente_con_la_cola_llena_deja_sitio_a_otro(self):
        casa = str(self.p.n.casa)
        fijar(claude={"activo": True}, codex={"activo": True})
        for i in range(permisor.MAX_PENDIENTES_CANAL):
            d = os.path.join(casa, f"c{i}")
            os.makedirs(d)
            self.assertEqual(self.ia("claude", op="pedir", titulo="x", carpetas={d: "r"})["estado"], "pendiente")
        d = os.path.join(casa, "otra")
        os.makedirs(d)
        with self.assertRaises(Denegado):
            self.ia("claude", op="pedir", titulo="x", carpetas={d: "r"})
        self.assertEqual(self.ia("codex", op="pedir", titulo="x", carpetas={d: "r"})["estado"], "pendiente")


class PanelVeLaOrdenEntera(unittest.TestCase):
    def test_no_se_pierde_ni_un_caracter(self):
        orden = "echo uno\n" + "x" * 500 + "\nrm -rf ~/final-oculto"
        trozos = panel.trozos_orden(orden, 40)
        self.assertIn("rm -rf ~/final-oculto", "".join(trozos))
        self.assertEqual("".join(trozos).replace("\\n", ""), orden.replace("\n", ""))

    def test_los_caracteres_de_control_se_ven(self):
        v = panel.visible("ls\r; rm -rf ~\x1b[2J")
        self.assertNotIn("\r", v)
        self.assertNotIn("\x1b", v)
        self.assertIn("\\x0d", v)
        self.assertIn("\\x1b", v)
        self.assertEqual(panel.visible("echo hola ñ"), "echo hola ñ")

    def test_si_no_cabe_se_sabe(self):
        q = {"titulo": "a" * 1400}
        self.assertFalse(panel.cabe_orden(q, 24, 60))
        self.assertTrue(panel.cabe_orden(q, 60, 200))
        self.assertTrue(panel.cabe_orden({"titulo": "ls"}, 24, 60))


class EjecucionAcotada(unittest.TestCase):
    def test_guarda_solo_el_final(self):
        cod, salida, corto = asistentes.correr_acotado(
            ["/bin/bash", "-c", "for i in $(seq 1 20000); do echo linea$i; done"], 30, 1000)
        self.assertEqual(cod, 0)
        self.assertLessEqual(len(salida), 1000)
        self.assertTrue(salida.rstrip().endswith(b"linea20000"))
        self.assertFalse(corto)

    def test_el_tiempo_corta_y_mata_los_hijos(self):
        t0 = time.time()
        cod, salida, corto = asistentes.correr_acotado(["/bin/bash", "-c", "echo antes; sleep 30 & sleep 30"], 1, 1000)
        self.assertTrue(corto)
        self.assertEqual(cod, 124)
        self.assertIn(b"antes", salida)
        self.assertLess(time.time() - t0, 10)


class RegistroYSockets(unittest.TestCase):
    def test_lector_aguanta_separadores_unicode(self):
        p = permisor.Permisor(tempfile.mkdtemp())
        p.n.anotar_consulta("orden", "[claude] echo a b c\x85d → código 0")
        p.n.anotar_consulta("orden", "[claude] siguiente")
        ult = p.n.ultimas(5)
        self.assertEqual(ult[-1]["ruta"], "[claude] siguiente")
        self.assertIn("a b", ult[-2]["ruta"])

    def test_carpeta_de_sockets_ajena_o_abierta_no_se_acepta(self):
        viejo = os.environ.pop("XDG_RUNTIME_DIR", None)
        base = f"/tmp/leksso-{os.getuid()}"
        existia = os.path.exists(base)
        try:
            if not existia:
                os.mkdir(base, 0o700)
            modo = stat.S_IMODE(os.stat(base).st_mode)
            os.chmod(base, 0o755)                      # abierta a otros
            with self.assertRaises(OSError):
                permisor._carpeta_sockets()
            os.chmod(base, 0o700)
            self.assertEqual(str(permisor._carpeta_sockets()), base)
            os.chmod(base, modo)
        finally:
            if not existia:
                os.rmdir(base)
            if viejo is not None:
                os.environ["XDG_RUNTIME_DIR"] = viejo


if __name__ == "__main__":
    unittest.main()
