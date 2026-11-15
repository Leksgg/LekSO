"""Pruebas del núcleo. Ejecutar en Linux: python3 -I -m unittest test_nucleo -v"""
import os
import tempfile
import unittest
from pathlib import Path

from nucleo import Nucleo, Denegado


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lekso-test-"))
        self.casa = self.tmp / "casa"
        self.casa.mkdir()
        self.proy = self.casa / "proyecto"
        self.proy.mkdir()
        self.secreto = self.casa / "secreto.txt"
        self.secreto.write_text("clave")
        self.n = Nucleo(self.casa)
        self.t = self.n.conceder("prueba", {str(self.proy): "rwd"})

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


class Alcance(Base):
    def test_lee_y_escribe_dentro(self):
        self.n.escribir(self.t, str(self.proy / "a.txt"), "hola")
        self.assertEqual(self.n.leer(self.t, str(self.proy / "a.txt")), "hola")

    def test_fuera_del_alcance(self):
        with self.assertRaises(Denegado):
            self.n.leer(self.t, str(self.secreto))

    def test_punto_punto(self):
        with self.assertRaises(Denegado):
            self.n.leer(self.t, str(self.proy / ".." / "secreto.txt"))

    def test_enlace_hacia_fuera(self):
        os.symlink(self.secreto, self.proy / "enlace")
        with self.assertRaises(Denegado):
            self.n.leer(self.t, str(self.proy / "enlace"))

    def test_carpeta_enlace_hacia_fuera(self):
        os.symlink(self.casa, self.proy / "salida")
        with self.assertRaises(Denegado):
            self.n.leer(self.t, str(self.proy / "salida" / "secreto.txt"))
        with self.assertRaises(Denegado):
            self.n.escribir(self.t, str(self.proy / "salida" / "nuevo.txt"), "x")
        self.assertFalse((self.casa / "nuevo.txt").exists())

    def test_ocultos_denegados(self):
        with self.assertRaises(Denegado):
            self.n.escribir(self.t, str(self.proy / ".bashrc"), "x")

    def test_sin_permiso_de_borrar(self):
        t2 = self.n.conceder("solo lectura", {str(self.proy): "r"})
        (self.proy / "x.txt").write_text("1")
        with self.assertRaises(Denegado):
            self.n.borrar(t2, str(self.proy / "x.txt"))
        with self.assertRaises(Denegado):
            self.n.escribir(t2, str(self.proy / "x.txt"), "2")

    def test_carpetas_demasiado_amplias(self):
        for ruta in ("/", str(self.casa), "/etc"):
            with self.assertRaises(Denegado):
                self.n.conceder("mal", {ruta: "r"})

    def test_no_se_concede_datos_internos(self):
        with self.assertRaises(Denegado):
            self.n.conceder("mal", {str(self.n.datos): "rw"})

    def test_tarea_cerrada(self):
        self.n.cerrar(self.t)
        with self.assertRaises(Denegado):
            self.n.leer(self.t, str(self.proy / "a.txt"))

    def test_listar_oculta_dotfiles(self):
        (self.proy / ".oculto").write_text("x")
        (self.proy / "visible").write_text("x")
        nombres = [e["nombre"] for e in self.n.listar(self.t, str(self.proy))]
        self.assertEqual(nombres, ["visible"])


class Deshacer(Base):
    def test_deshacer_edicion(self):
        f = self.proy / "a.txt"
        f.write_text("original")
        aid = self.n.escribir(self.t, str(f), "nuevo")
        self.assertEqual(f.read_text(), "nuevo")
        self.n.deshacer(aid)
        self.assertEqual(f.read_text(), "original")

    def test_deshacer_creacion_va_a_papelera(self):
        f = self.proy / "nuevo.txt"
        aid = self.n.escribir(self.t, str(f), "x")
        self.n.deshacer(aid)
        self.assertFalse(f.exists())
        self.assertTrue(any((self.n.papelera / "files").iterdir()))

    def test_borrar_y_deshacer(self):
        f = self.proy / "b.txt"
        f.write_text("dato")
        aid = self.n.borrar(self.t, str(f))
        self.assertFalse(f.exists())
        self.assertTrue((self.n.papelera / "files" / "b.txt").exists())
        self.n.deshacer(aid)
        self.assertEqual(f.read_text(), "dato")

    def test_mover_y_deshacer(self):
        (self.proy / "o.txt").write_text("m")
        aid = self.n.mover(self.t, str(self.proy / "o.txt"), str(self.proy / "sub" / "d.txt"))
        self.assertTrue((self.proy / "sub" / "d.txt").exists())
        self.n.deshacer(aid)
        self.assertTrue((self.proy / "o.txt").exists())

    def test_aviso_si_cambio_despues(self):
        f = self.proy / "c.txt"
        f.write_text("1")
        aid = self.n.escribir(self.t, str(f), "2")
        f.write_text("3 (editado a mano)")
        with self.assertRaises(Denegado):
            self.n.deshacer(aid)
        self.assertEqual(f.read_text(), "3 (editado a mano)")
        self.n.deshacer(aid, forzar=True)
        self.assertEqual(f.read_text(), "1")

    def test_deshacer_tarea_completa_en_orden(self):
        f = self.proy / "d.txt"
        f.write_text("v0")
        self.n.escribir(self.t, str(f), "v1")
        self.n.escribir(self.t, str(f), "v2")
        self.n.borrar(self.t, str(f))
        self.assertEqual(self.n.deshacer_tarea(self.t), 3)
        self.assertEqual(f.read_text(), "v0")

    def test_registro_persiste(self):
        f = self.proy / "e.txt"
        aid = self.n.escribir(self.t, str(f), "x")
        n2 = Nucleo(self.casa)
        self.assertIn(aid, n2.acciones)

    def test_no_se_deshace_dos_veces(self):
        aid = self.n.escribir(self.t, str(self.proy / "f.txt"), "x")
        self.n.deshacer(aid)
        with self.assertRaises(Denegado):
            self.n.deshacer(aid)

    def test_escrituras_simultaneas_y_deshacer_tarea(self):
        import threading
        f = self.proy / "comp.txt"
        def hilo(k):
            for i in range(30):
                self.n.escribir(self.t, str(f), f"{k}-{i}")
        hs = [threading.Thread(target=hilo, args=(k,)) for k in range(6)]
        [h.start() for h in hs]
        [h.join() for h in hs]
        self.assertEqual(self.n.deshacer_tarea(self.t, forzar=True), 180)
        self.assertFalse(f.exists())
        self.assertEqual([p.name for p in self.proy.iterdir()], [])
    def test_purga_por_tamano_y_aviso_al_deshacer(self):
        f = self.proy / "p.txt"
        f.write_text("original")
        aid = self.n.escribir(self.t, str(f), "nuevo")
        self.assertEqual(self.n.purgar_versiones(max_bytes=0), 1)
        with self.assertRaises(Denegado):
            self.n.deshacer(aid)
        self.assertEqual(f.read_text(), "nuevo")

if __name__ == "__main__":
    unittest.main()
