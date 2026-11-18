#!/usr/bin/env python3
"""Pruebas de leksso-tema: cambiar de tema reescribe los colores de la configuración del usuario, la ida y vuelta
deja los archivos idénticos y un tema que no existe no toca nada. Uso: python3 scripts/test_tema.py"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "config", "ui"))
import leksso_ui  # noqa: E402

TEMA = os.path.join(RAIZ, "scripts", "leksso-tema.py")
COPIAS = {
    "waybar/style.css": ".config/waybar/style.css",
    "kitty/kitty.conf": ".config/kitty/kitty.conf", "sway/config": ".config/sway/config",
    "mako/config": ".config/mako/config", "fuzzel/fuzzel.ini": ".config/fuzzel/fuzzel.ini",
    "swaylock/config": ".config/swaylock/config", "qt6ct/colors/leksso.conf": ".config/qt6ct/colors/leksso.conf",
    "pcmanfm-qt/settings.conf": ".config/pcmanfm-qt/default/settings.conf",
    "labwc/tema/LeksSO/openbox-3/themerc": ".local/share/themes/LeksSO/openbox-3/themerc",
}


class PruebasTema(unittest.TestCase):
    def setUp(self):
        self.casa = tempfile.mkdtemp()
        for origen, destino in COPIAS.items():
            d = os.path.join(self.casa, destino)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy(os.path.join(RAIZ, "config", origen), d)
        self.env = dict(os.environ, HOME=self.casa)
        qt = os.path.join(self.casa, ".config", "qt6ct", "qt6ct.conf")
        shutil.copy(os.path.join(RAIZ, "config", "qt6ct", "qt6ct.conf"), qt)

    def tearDown(self):
        shutil.rmtree(self.casa, ignore_errors=True)

    def tema(self, *a):
        return subprocess.run([sys.executable, TEMA, *a], env=self.env, capture_output=True, text=True)

    def contenido(self):
        out = {}
        for destino in COPIAS.values():
            out[destino] = open(os.path.join(self.casa, destino), "rb").read()
        return out

    def test_ida_y_vuelta_identica(self):
        antes = self.contenido()
        self.assertEqual(self.tema("aplicar", "pizarra").returncode, 0)
        self.assertNotEqual(antes, self.contenido())
        self.assertEqual(self.tema("actual").stdout.strip(), "pizarra")
        self.assertEqual(self.tema("aplicar", "marea").returncode, 0)
        self.assertEqual(antes, self.contenido())

    def test_no_quedan_colores_del_tema_anterior(self):
        self.tema("aplicar", "pizarra")
        viejo = set(leksso_ui.tokens("marea").values()) - set(leksso_ui.tokens("pizarra").values())
        for destino, datos in self.contenido().items():
            if destino.endswith("settings.conf"):
                continue  # solo lleva algunos colores
            texto = datos.decode("utf-8").lower()
            for c in ("021012", "00c4bf", "e3edef"):
                self.assertNotIn(c, texto, f"{destino} sigue con {c}")
        self.assertTrue(viejo)

    def test_tema_desconocido_no_toca_nada(self):
        antes = self.contenido()
        r = self.tema("aplicar", "noexiste")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(antes, self.contenido())

    def test_reaplicar_tras_copiar_la_base(self):
        self.tema("aplicar", "pizarra")
        for origen, destino in COPIAS.items():  # una actualización vuelve a copiar la base (Marea)
            shutil.copy(os.path.join(RAIZ, "config", origen), os.path.join(self.casa, destino))
        self.assertEqual(self.tema("reaplicar").returncode, 0)
        self.tema("aplicar", "marea")
        base = {d: open(os.path.join(RAIZ, "config", o), "rb").read() for o, d in COPIAS.items()}
        self.assertEqual(base, self.contenido())

    def test_hay_tres_temas(self):
        self.assertEqual(set(self.tema("listar").stdout.split()), {"marea", "pizarra", "waves"})

    def test_waves_ida_y_vuelta_identica(self):
        antes = self.contenido()
        self.assertEqual(self.tema("aplicar", "waves").returncode, 0)
        texto = open(os.path.join(self.casa, ".config", "waybar", "style.css"), encoding="utf-8").read().lower()
        self.assertIn(leksso_ui.tokens("waves")["bg"], texto)
        self.assertNotIn("021012", texto)
        self.assertEqual(self.tema("aplicar", "pizarra").returncode, 0)  # de un tema a otro sin pasar por Marea
        self.assertEqual(self.tema("aplicar", "marea").returncode, 0)
        self.assertEqual(antes, self.contenido())

    def test_qt6ct_no_se_queda_con_otro_esquema(self):
        qt = os.path.join(self.casa, ".config", "qt6ct", "qt6ct.conf")
        texto = open(qt, encoding="utf-8").read().replace("leksso.conf", "waves.conf").replace("custom_palette=true", "custom_palette=false")
        open(qt, "w", encoding="utf-8").write(texto)  # el usuario eligió «waves» en qt6ct
        self.tema("aplicar", "pizarra")
        conf = open(qt, encoding="utf-8").read()
        self.assertIn("colors/leksso.conf", conf)
        self.assertIn("custom_palette=true", conf)

    def test_estilo_de_ventanas_sigue_el_tema(self):
        os.makedirs(os.path.join(self.casa, ".config", "leksso"))
        open(os.path.join(self.casa, ".config", "leksso", "tema"), "w").write("pizarra\n")
        casa_real = os.environ.get("HOME")
        os.environ["HOME"] = self.casa
        try:
            self.assertNotIn("#021012", leksso_ui.pintar(leksso_ui.ESTILO_BASE))
        finally:
            if casa_real is None:
                del os.environ["HOME"]
            else:
                os.environ["HOME"] = casa_real


if __name__ == "__main__":
    unittest.main()
