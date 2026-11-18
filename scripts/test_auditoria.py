#!/usr/bin/env python3
"""Pruebas del registro de instalaciones: la clasificación del origen (con su nivel de certeza), la cadena de hashes
(detecta ediciones y recortes), el gancho de apt con un dpkg falso y la vigilancia de lo que aparece fuera de apt.
Uso: python3 scripts/test_auditoria.py (no hace falta ser root: todo cuelga de una carpeta temporal)."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
PROGRAMA = os.path.join(AQUI, "leksso-auditoria.py")


def p(cmd, comm="bash", cgroup="0::/user.slice/user-1000.slice/session-3.scope", ssh=None, sudo=None):
    return {"cmd": cmd, "comm": comm, "cgroup": cgroup, "ssh": ssh, "sudo_usuario": sudo}


class Pruebas(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.casa = os.path.join(self.t, "home", "u")
        os.makedirs(os.path.join(self.casa, ".local", "bin"))
        os.environ["LEKSSO_AUDITORIA_RAIZ"] = self.t
        os.environ["LEKSSO_AUDITORIA_HOMES"] = self.casa
        spec = importlib.util.spec_from_file_location("leksso_auditoria", PROGRAMA)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    # ---- origen y certeza ----
    def test_origen_confirmado_lo_que_prueba_quien_lo_hizo(self):
        apt = p("/usr/bin/apt-get install -y ripgrep", "apt-get")
        casos = [
            ([apt, p("python3 /usr/local/lib/leksso-ia/leksso_admin.py", "python3", "0::/system.slice/leksso-admin.service")], "IA"),
            ([apt, p("python3 permisor.py", "python3", "0::/user.slice/user@1000.service/app.slice/leksso-permisor.service")], "IA"),
            ([apt, p("python3 /usr/local/bin/leksso-actualizar aplicar", "python3")], "leksso-actualizar"),
            ([apt, p("/usr/bin/unattended-upgrade", "unattended-upgr")], "unattended"),
            ([apt, p("python3 /usr/local/bin/leksso-apps instalar ripgrep", "python3")], "leksso-apps"),
            ([apt, p("sudo apt install x", "sudo"), p("-bash", "bash", ssh="192.168.1.20 51234 192.168.1.5 22")], "SSH desde 192.168.1.20"),
            ([apt, p("sshd-session: u@pts/0", "sshd-session")], "SSH desde"),
        ]
        for cadena, esperado in casos:
            modo, origen, nivel, _ = self.m.clasificar(cadena)
            self.assertEqual(nivel, "confirmado", f"{esperado}: {modo}")
            self.assertIn(esperado, origen)

    def test_origen_inferido_y_desconocido_nunca_usuario_por_defecto(self):
        apt = p("/usr/bin/apt-get install -y x", "apt-get")
        modo, origen, nivel, d = self.m.clasificar([apt, p("sudo apt install x", "sudo", sudo="u"), p("bash", "bash"), p("kitty", "kitty")])
        self.assertEqual((nivel, modo), ("inferido", "terminal local"))
        self.assertEqual(d["usuario"], "u")
        modo, _, nivel, _ = self.m.clasificar([apt, p("sh -c curl -fsSL https://x.y/i.sh | sudo sh", "sh")])
        self.assertEqual((nivel, modo), ("inferido", "script descargado y ejecutado (curl | sh)"))
        modo, origen, nivel, _ = self.m.clasificar([apt])
        self.assertEqual((nivel, origen), ("desconocido", "desconocido"))
        self.assertNotIn("usuario", self.m.clasificar([])[1].lower())

    def test_la_ia_gana_a_la_terminal_y_a_ssh(self):
        # la IA que se ejecuta desde una sesión SSH sigue siendo la IA
        cadena = [p("apt-get install x", "apt-get"), p("bash", "bash", "0::/system.slice/leksso-admin.service", ssh="1.2.3.4 1 5.6.7.8 22")]
        self.assertEqual(self.m.clasificar(cadena)[2:3], ("confirmado",))
        self.assertIn("IA", self.m.clasificar(cadena)[1])

    # ---- la cadena ----
    def rellenar(self, n=4):
        for i in range(n):
            self.m.anotar_registro(tipo="paquete", accion="instalado", nombre=f"p{i}", version="1", modo="terminal local",
                                   origen="terminal", nivel="inferido", detalle={})

    def test_cadena_integra(self):
        self.rellenar()
        v = self.m.verificar()
        self.assertTrue(v["ok"], v)
        self.assertEqual(v["n"], 4)

    def test_edicion_de_una_linea_se_detecta(self):
        self.rellenar()
        lineas = open(self.m.REGISTRO, encoding="utf-8").read().splitlines()
        r = json.loads(lineas[1])
        r["origen"] = "usuario"          # alguien cambia el origen de la 2.ª línea
        lineas[1] = json.dumps(r, ensure_ascii=False)
        open(self.m.REGISTRO, "w", encoding="utf-8").write("\n".join(lineas) + "\n")
        v = self.m.verificar()
        self.assertFalse(v["ok"])
        self.assertIn("línea 2", v["error"])

    def test_recortar_el_final_se_detecta_con_el_sello_aparte(self):
        self.rellenar()
        lineas = open(self.m.REGISTRO, encoding="utf-8").read().splitlines()
        open(self.m.REGISTRO, "w", encoding="utf-8").write("\n".join(lineas[:-1]) + "\n")
        v = self.m.verificar()
        self.assertFalse(v["ok"])
        self.assertIn("sello", v["error"])

    def test_vaciar_el_registro_se_detecta(self):
        self.rellenar()
        open(self.m.REGISTRO, "w").close()
        self.assertFalse(self.m.verificar()["ok"])

    # ---- gancho de apt ----
    def test_gancho_registra_altas_bajas_y_actualizaciones_con_su_origen(self):
        m = self.m
        m.cadena_de_procesos = lambda pid: [p("/usr/bin/apt-get install -y ripgrep", "apt-get"), p("bash", "bash", ssh="10.0.0.9 1 10.0.0.2 22")]
        m.paquetes_instalados = lambda: {"vim": "9.0", "viejo": "1", "git": "2.0"}
        m.gancho("pre")
        m.paquetes_instalados = lambda: {"vim": "9.1", "git": "2.0", "ripgrep": "14"}
        m.gancho("post")
        regs = [r for r in m.lineas()]
        acciones = {(r["accion"], r["nombre"]) for r in regs}
        self.assertIn(("instalado", "ripgrep"), acciones)
        self.assertIn(("eliminado", "viejo"), acciones)
        self.assertTrue(any(r["accion"] == "actualizado" and "vim" in r["detalle"]["paquetes"] for r in regs))
        nuevo = next(r for r in regs if r["nombre"] == "ripgrep")
        self.assertEqual((nuevo["nivel"], nuevo["origen"]), ("confirmado", "SSH desde 10.0.0.9"))
        self.assertTrue(m.verificar()["ok"])

    def test_gancho_sin_cambios_no_escribe_y_un_error_no_rompe_apt(self):
        m = self.m
        m.cadena_de_procesos = lambda pid: []
        m.paquetes_instalados = lambda: {"a": "1"}
        m.gancho("pre"); m.gancho("post")
        self.assertEqual(m.lineas(), [])
        def roto():
            raise RuntimeError("dpkg no responde")
        m.paquetes_instalados = roto
        m.gancho("pre"); m.gancho("post")        # no lanza nada

    # ---- fuera de apt ----
    def test_fuera_de_apt_linea_base_novedades_y_revision(self):
        m = self.m
        m.foto()
        self.assertEqual(m.lineas()[0]["tipo"], "inicio")             # la primera foto es solo la línea base
        ejecutable = os.path.join(self.casa, ".local", "bin", "herramienta")
        open(ejecutable, "w").write("#!/bin/sh\necho hola\n"); os.chmod(ejecutable, 0o755)
        suelto = os.path.join(self.casa, ".local", "bin", "notas.txt")
        open(suelto, "w").write("no es ejecutable")
        propio = os.path.join(self.t, "usr", "local", "bin"); os.makedirs(propio)
        open(os.path.join(propio, "leksso-algo"), "w").write("#!/bin/sh\n"); os.chmod(os.path.join(propio, "leksso-algo"), 0o755)
        m.foto()
        nuevos = [r for r in m.lineas() if r.get("tipo") == "fuera_de_apt"]
        self.assertEqual([r["nombre"] for r in nuevos], ["herramienta"])    # ni el .txt ni los leksso-* cuentan
        self.assertEqual((nuevos[0]["nivel"], nuevos[0]["origen"]), ("desconocido", "desconocido"))
        self.assertEqual(json.loads(open(m.PUBLICO).read())["sin_revisar"], 1)
        m.anotar_registro(tipo="revision", accion="revisada", nombre="x", version="", modo="", origen="usuario", nivel="confirmado", ref=nuevos[0]["n"], detalle={})
        self.assertEqual(json.loads(open(m.PUBLICO).read())["sin_revisar"], 0)
        os.remove(ejecutable)
        m.foto()
        self.assertEqual(m.lineas()[-1]["accion"], "desapareció")

    def test_lo_inferido_no_enciende_la_barra_solo_lo_desconocido(self):
        m = self.m
        m.anotar_registro(tipo="paquete", accion="instalado", nombre="a", version="1", modo="terminal local", origen="terminal", nivel="inferido", detalle={})
        m.anotar_registro(tipo="paquete", accion="instalado", nombre="b", version="1", modo="sesión remota (ssh)", origen="SSH desde 1.2.3.4", nivel="confirmado", detalle={})
        self.assertEqual(json.loads(open(m.PUBLICO).read())["sin_revisar"], 0)
        m.anotar_registro(tipo="paquete", accion="instalado", nombre="c", version="1", modo="comando desconocido", origen="desconocido", nivel="desconocido", detalle={})
        self.assertEqual(json.loads(open(m.PUBLICO).read())["sin_revisar"], 1)

    def test_appimage_en_la_carpeta_personal(self):
        m = self.m
        m.foto()
        ruta = os.path.join(self.casa, "Descargas"); os.makedirs(ruta)
        open(os.path.join(ruta, "Cosa.AppImage"), "w").write("x")
        m.foto()
        self.assertTrue(any(r.get("nombre") == "Cosa.AppImage" for r in m.lineas()))

    # ---- por la línea de órdenes ----
    def corre(self, *a):
        env = dict(os.environ, LEKSSO_AUDITORIA_RAIZ=self.t, LEKSSO_AUDITORIA_HOMES=self.casa)
        return subprocess.run([sys.executable, PROGRAMA, *a], env=env, capture_output=True, text=True)

    def test_listar_anotar_revisar_barra(self):
        r = self.corre("anotar", "--nombre", "claude-code", "--modo", "npm install -g")
        self.assertEqual(json.loads(r.stdout)["ok"], True)
        self.corre("foto")
        ejecutable = os.path.join(self.casa, ".local", "bin", "raro")
        open(ejecutable, "w").write("#!/bin/sh\n"); os.chmod(ejecutable, 0o755)
        self.corre("foto")
        todo = json.loads(self.corre("listar").stdout)
        self.assertEqual(todo[0]["nombre"], "raro")                  # lo más reciente, primero
        solo = json.loads(self.corre("listar", "--no-confirmados").stdout)
        self.assertEqual([x["nombre"] for x in solo], ["raro"])
        b = json.loads(self.corre("barra").stdout)
        self.assertEqual(b["text"], "▲ Seguridad")
        self.assertEqual(json.loads(self.corre("revisar", str(todo[0]["n"])).stdout)["ok"], True)
        self.assertEqual(json.loads(self.corre("barra").stdout)["text"], "")
        self.assertEqual(self.corre("revisar", "999").returncode, 2)
        v = json.loads(self.corre("verificar").stdout)
        self.assertTrue(v["ok"], v)


if __name__ == "__main__":
    unittest.main()
