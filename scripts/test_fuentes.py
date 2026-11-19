#!/usr/bin/env python3
"""Fuentes de apt para el firmware automático (solo debian.org) y entrada estándar para lo secreto.
Uso: python3 scripts/test_fuentes.py"""
import importlib.util
import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
_e = importlib.util.spec_from_file_location("leksso_hardware", os.path.join(AQUI, "leksso_hardware.py"))
hw = importlib.util.module_from_spec(_e)
_e.loader.exec_module(hw)

DEB822 = "Types: deb\nURIs: https://deb.debian.org/debian\nSuites: trixie\nComponents: main\n"


class FuentesDeDebian(unittest.TestCase):
    def test_solo_debian_pasa(self):
        self.assertTrue(hw.es_fuente_de_debian(DEB822))
        self.assertTrue(hw.es_fuente_de_debian(
            "deb http://security.debian.org/debian-security trixie-security main\n# deb http://otro.com x\n"))
        self.assertTrue(hw.es_fuente_de_debian("deb [signed-by=/x.gpg] https://deb.debian.org/debian trixie main"))

    def test_un_repositorio_externo_no_pasa(self):
        self.assertFalse(hw.es_fuente_de_debian(
            "deb [signed-by=/usr/share/keyrings/b.gpg] https://brave-browser-apt-release.s3.brave.com/ stable main"))
        self.assertFalse(hw.es_fuente_de_debian(
            "Types: deb\nURIs: https://packages.microsoft.com/repos/code\nSuites: stable\n"))
        self.assertFalse(hw.es_fuente_de_debian("deb http://deb.debian.org.evil.com/debian trixie main"))
        self.assertFalse(hw.es_fuente_de_debian("deb http://evildebian.org/debian trixie main"))
        self.assertFalse(hw.es_fuente_de_debian(""))
        self.assertFalse(hw.es_fuente_de_debian(DEB822 + "URIs: https://x.example.com/\n"))

    def test_uris_en_varias_lineas_se_leen_todas(self):
        multi = "Types: deb\nURIs: https://deb.debian.org/debian\n https://packages.microsoft.com/repos/code\nSuites: stable\n"
        self.assertFalse(hw.es_fuente_de_debian(multi))
        solo_debian = ("Types: deb\nURIs: https://deb.debian.org/debian\n"
                       " http://security.debian.org/debian-security\nSuites: trixie\n")
        self.assertTrue(hw.es_fuente_de_debian(solo_debian))

    def test_lo_secreto_no_va_en_los_argumentos(self):
        rc, sal = hw.ejecutar(["cat"], entrada="secreto\n")
        self.assertEqual((rc, sal), (0, "secreto\n"))


if __name__ == "__main__":
    unittest.main()
