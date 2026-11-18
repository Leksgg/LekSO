#!/usr/bin/env python3
"""Los monitores (root) no se cuelgan con una tubería puesta donde debería haber un programa.
Uso: python3 scripts/test_lectura_segura.py"""
import importlib.machinery
import importlib.util
import os
import signal
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def cargar(nombre, archivo):
    l = importlib.machinery.SourceFileLoader(nombre, os.path.join(AQUI, archivo))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(nombre, l))
    l.exec_module(m)
    return m


class Pruebas(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.fifo = os.path.join(self.d, "programa")
        os.mkfifo(self.fifo)
        self.normal = os.path.join(self.d, "normal")
        open(self.normal, "wb").write(b"hola")
        signal.signal(signal.SIGALRM, lambda *a: self.fail("se quedó colgado con una tubería"))
        signal.alarm(10)

    def tearDown(self):
        signal.alarm(0)

    def test_auditoria(self):
        m = cargar("auditoria_t", "leksso-auditoria.py")
        with self.assertRaises(OSError):
            m.leer_normal(self.fifo, 100)
        self.assertEqual(m.leer_normal(self.normal, 100)[1], b"hola")

    def test_conexiones(self):
        m = cargar("conexiones_t", "leksso-conexiones.py")
        with self.assertRaises(OSError):
            m.leer_normal(self.fifo, 100)
        self.assertEqual(m.huella(self.fifo), "")          # una tubería no tiene huella, y no cuelga
        self.assertNotEqual(m.huella(self.normal), "")


if __name__ == "__main__":
    unittest.main()
