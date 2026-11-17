"""Pruebas de lekso_hardware: lectura de salidas, listas cerradas y avisos.

No tocan el sistema: usan textos de ejemplo. Uso: python3 scripts/test_hardware.py
"""
import importlib.util
import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
_e = importlib.util.spec_from_file_location("lekso_hardware", os.path.join(AQUI, "lekso_hardware.py"))
hw = importlib.util.module_from_spec(_e)
_e.loader.exec_module(hw)

LSPCI = """00:02.0 VGA compatible controller [0300]: Intel Corporation UHD Graphics 630 [8086:3e92] (rev 02)
01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GA106 [GeForce RTX 3060 Lite Hash Rate] [10de:2504] (rev a1)
01:00.1 Audio device [0403]: NVIDIA Corporation GA106 High Definition Audio Controller [10de:228e] (rev a1)
06:00.0 3D controller [0302]: Advanced Micro Devices, Inc. [AMD/ATI] Navi 23 [1002:73ff]
"""

APT = """Inst intel-microcode [3.20250211.1] (3.20250512.1 Debian:13.1/stable [amd64])
Inst firmware-iwlwifi [20250211-1] (20250410-1 Debian:13.1/stable [all])
Inst nvidia-driver [550.1-1] (550.2-1 Debian:13.1/stable [amd64])
Inst linux-image-6.12.0-amd64 (6.12.1-1 Debian:13.1/stable [amd64])
Inst evil;rm [1] (2 x)
Conf intel-microcode (3.20250512.1 Debian:13.1/stable [amd64])
"""


class Lectura(unittest.TestCase):
    def test_gpus(self):
        g = hw.parsear_gpus(LSPCI)
        self.assertEqual([x["vendedor"] for x in g], ["intel", "nvidia", "amd"])
        self.assertEqual(g[1]["nombre"], "NVIDIA Corporation GA106 [GeForce RTX 3060 Lite Hash Rate]")

    def test_pendientes_y_listas_cerradas(self):
        p = hw.parsear_pendientes(APT)
        nombres = [x["nombre"] for x in p]
        self.assertEqual(nombres, ["intel-microcode", "firmware-iwlwifi", "nvidia-driver", "linux-image-6.12.0-amd64"])
        seguros = [x for x in nombres if hw.SEGURO.match(x)]
        self.assertEqual(seguros, ["intel-microcode", "firmware-iwlwifi"])      # el núcleo y NVIDIA no son «seguros»
        self.assertTrue(hw.NVIDIA.match("nvidia-driver"))
        self.assertFalse(hw.NVIDIA.match("linux-image-6.12.0-amd64"))

    def test_nombres_hostiles(self):
        for malo in ("-o", "firmware-x; rm -rf /", "firmware-x\n", "Firmware-x", "firmware-", "$(id)", "../x", ""):
            self.assertFalse(hw.SEGURO.match(malo), malo)
        for malo in ("nvidia-driver --force-yes", "nvidia-\n", "-nvidia-driver", "nvidia-x`id`"):
            self.assertFalse(hw.NVIDIA.match(malo), malo)

    def test_nvidia_detect(self):
        sal = "Detected NVIDIA GPUs:\n01:00.0 ...\nYour card is supported by the default drivers.\nIt is recommended to install the\n    nvidia-driver\npackage.\n"
        self.assertEqual(hw.recomendado_por_nvidia_detect(sal), "nvidia-driver")
        self.assertIsNone(hw.recomendado_por_nvidia_detect("It is recommended to install the\n    rm -rf\npackage."))
        self.assertIsNone(hw.recomendado_por_nvidia_detect(""))

    def test_firmware(self):
        sal = '{"Devices":[{"Name":"UEFI dbx","Releases":[{"Version":"371"}]},{"Name":"SSD X","Releases":[]}]}'
        self.assertEqual(hw.parsear_firmware(sal), [{"dispositivo": "UEFI dbx", "version": "371"}, {"dispositivo": "SSD X", "version": ""}])
        self.assertEqual(hw.parsear_firmware("no es json"), [])
        self.assertEqual(hw.parsear_firmware("[]"), [])


class Fuentes(unittest.TestCase):
    def test_activar_non_free_formato_lista(self):
        t = "deb http://deb.debian.org/debian trixie main non-free-firmware\n# deb http://x trixie main\ndeb http://deb.debian.org/debian trixie-updates main contrib\n"
        r = hw.con_non_free(t)
        self.assertIn("trixie main non-free non-free-firmware", r)
        self.assertIn("trixie-updates main non-free contrib", r)
        self.assertIn("# deb http://x trixie main\n", r)           # los comentarios no se tocan
        self.assertEqual(hw.con_non_free(r), r)                    # repetirlo no cambia nada

    def test_activar_non_free_formato_deb822(self):
        t = "Types: deb\nURIs: http://deb.debian.org/debian\nSuites: trixie\nComponents: main non-free-firmware\n"
        r = hw.con_non_free(t)
        self.assertIn("Components: main non-free non-free-firmware", r)
        self.assertEqual(hw.con_non_free(r), r)

    def test_non_free_firmware_no_cuenta_como_non_free(self):
        self.assertIsNone(hw.CON_NON_FREE.search("Components: main non-free-firmware"))
        self.assertTrue(hw.CON_NON_FREE.search("Components: main non-free"))


class Avisos(unittest.TestCase):
    def test_textos_en_lenguaje_llano_y_con_clave(self):
        est = {"nvidia": {"accion": "instalar", "candidato": "550.2-1"}, "firmware": [{"dispositivo": "SSD X", "version": "2"}]}
        av = hw.textos_aviso(est, ["intel-microcode"])
        self.assertEqual([a[0] for a in av], ["nvidia:instalar:550.2-1", "fw:SSD X:2", "auto:intel-microcode"])
        for _, titulo, texto in av:
            for jerga in ("DKMS", "microcode ", "kernel"):
                self.assertNotIn(jerga, titulo + texto)

    def test_sin_novedades_no_avisa(self):
        self.assertEqual(hw.textos_aviso({"nvidia": None, "firmware": []}), [])
        self.assertEqual(hw.textos_aviso({"nvidia": {"accion": None, "candidato": "1"}, "firmware": []}), [])


class Problemas(unittest.TestCase):
    def test_secure_boot_ya_no_es_un_bloqueo_sino_un_paso_previo(self):
        # Con Secure Boot se registra primero la clave (preparar_mok); problemas_antes_de_nvidia solo mira espacio y batería.
        self.assertFalse(any("Secure Boot" in p for p in hw.problemas_antes_de_nvidia({"secure_boot": True})))


class ClaveMok(unittest.TestCase):
    def test_estados(self):
        self.assertEqual(hw.interpretar_mok(False, "", ""), "sin-clave")
        self.assertEqual(hw.interpretar_mok(True, "/var/lib/dkms/mok.pub is already enrolled", ""), "registrada")
        self.assertEqual(hw.interpretar_mok(True, "/var/lib/dkms/mok.pub is not enrolled", "MokNew is empty"), "sin-registrar")
        self.assertEqual(hw.interpretar_mok(True, "/var/lib/dkms/mok.pub is not enrolled", "[key 1] SHA1 Fingerprint: 00"), "pendiente")
        self.assertEqual(hw.interpretar_mok(True, "", ""), "sin-registrar")


class ContrasenaMok(unittest.TestCase):
    def test_contrasena_corta_y_tecleable_en_teclado_ingles(self):
        for _ in range(200):
            c = hw.generar_contrasena()
            self.assertEqual(len(c), 8)
            self.assertTrue(all(ch in hw.ALFABETO_MOK for ch in c))
        self.assertNotEqual(hw.generar_contrasena(), hw.generar_contrasena())    # no es fija
        for raro in "ilo01" "ñ" "_-.":
            self.assertNotIn(raro, hw.ALFABETO_MOK)


if __name__ == "__main__":
    unittest.main()
