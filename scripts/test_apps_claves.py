#!/usr/bin/env python3
"""Huellas de las claves de repositorios de terceros (leksso-apps): una clave distinta de la esperada no pasa.
Requiere gpg. Uso: python3 scripts/test_apps_claves.py"""
import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
_l = importlib.machinery.SourceFileLoader("leksso_apps", os.path.join(AQUI, "leksso-apps.py"))
apps = importlib.util.module_from_spec(importlib.util.spec_from_loader("leksso_apps", _l))
_l.exec_module(apps)


@unittest.skipUnless(shutil.which("gpg"), "falta gpg")
class Claves(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.env = dict(os.environ, GNUPGHOME=self.d)
        os.chmod(self.d, 0o700)

    def clave(self, nombre):
        subprocess.run(["gpg", "--batch", "--passphrase", "", "--quick-gen-key", f"{nombre} <{nombre}@example.com>",
                        "ed25519", "sign", "never"], env=self.env, capture_output=True, check=True)
        return subprocess.run(["gpg", "--export", nombre], env=self.env, capture_output=True, check=True).stdout

    def huella_de(self, nombre):
        r = subprocess.run(["gpg", "--list-keys", "--with-colons", nombre], env=self.env, capture_output=True, text=True)
        return [l.split(":")[9] for l in r.stdout.splitlines() if l.startswith("fpr")][0]

    def test_calcula_la_huella_de_la_clave_principal(self):
        k = self.clave("uno")
        self.assertEqual(apps.huellas_de(k), {self.huella_de("uno")})

    def test_dos_claves_dan_dos_huellas(self):
        k = self.clave("uno") + self.clave("dos")
        self.assertEqual(apps.huellas_de(k), {self.huella_de("uno"), self.huella_de("dos")})

    def test_basura_no_da_huellas(self):
        self.assertFalse(apps.huellas_de(b"esto no es una clave"))

    def test_una_clave_ajena_no_esta_entre_las_esperadas(self):
        ajena = apps.huellas_de(self.clave("intruso"))
        for nombre, esperadas in apps.HUELLAS.items():
            self.assertFalse(ajena <= esperadas, nombre)

    def test_las_huellas_fijadas_tienen_formato_de_huella(self):
        for nombre, esperadas in apps.HUELLAS.items():
            self.assertTrue(esperadas, nombre)
            for h in esperadas:
                self.assertRegex(h, r"^[0-9A-F]{40}$")


if __name__ == "__main__":
    unittest.main()
