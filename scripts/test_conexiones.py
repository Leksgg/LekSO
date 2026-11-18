#!/usr/bin/env python3
"""Pruebas del monitor de conexiones con datos de ss y de procesos simulados: clasificación, confianza (y herencia), novedades
y semana de aprendizaje, entradas por SSH, envíos altos, bloqueos (y lo que NO se puede bloquear) y parar con comprobaciones.
Uso: python3 scripts/test_conexiones.py (no hace falta ser root ni tener ss: todo cuelga de una carpeta temporal)."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
PROGRAMA = os.path.join(AQUI, "leksso-conexiones.py")

SS = """\
tcp   LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=900,fd=3))
tcp   LISTEN 0 4096 127.0.0.1:631 0.0.0.0:* users:(("cupsd",pid=901,fd=7))
tcp   ESTAB  0 0 192.168.1.5:22 192.168.1.20:51234 users:(("sshd-session",pid=950,fd=4)) cubic bytes_sent:1200 bytes_received:3400
tcp   ESTAB  0 0 192.168.1.5:43210 142.250.1.1:443 users:(("brave",pid=1000,fd=40)) cubic bytes_sent:5000 bytes_received:90000
tcp   ESTAB  0 0 192.168.1.5:50000 93.184.216.34:443 users:(("raro",pid=1100,fd=5)) cubic bytes_sent:700 bytes_received:10
tcp   ESTAB  0 0 192.168.1.5:50001 192.168.1.1:80 users:(("curl",pid=1200,fd=5)) cubic bytes_sent:100 bytes_received:10
tcp   ESTAB  0 0 127.0.0.1:50002 127.0.0.1:631 users:(("lp",pid=1300,fd=5)) cubic bytes_sent:1 bytes_received:1
tcp   ESTAB  0 0 [2001:db8::5]:50003 [2606:4700::1]:443 users:(("brave",pid=1000,fd=41)) cubic bytes_sent:900 bytes_received:900
udp   UNCONN 0 0 0.0.0.0:68 0.0.0.0:* users:(("dhclient",pid=500,fd=6))
tcp   ESTAB  0 0 192.168.1.5:50010 93.184.216.35:443 users:(("juego",pid=1400,fd=5)) cubic bytes_sent:4000 bytes_received:10
"""

PROCESOS = {
    900: {"pid": 900, "ppid": 1, "comm": "sshd", "exe": "/usr/sbin/sshd", "cmd": "sshd", "unidad": "ssh.service", "uid": 0, "inicio": 10},
    901: {"pid": 901, "ppid": 1, "comm": "cupsd", "exe": "/usr/sbin/cupsd", "cmd": "cupsd", "unidad": "cups.service", "uid": 0, "inicio": 11},
    950: {"pid": 950, "ppid": 900, "comm": "sshd-session", "exe": "/usr/lib/openssh/sshd-session", "cmd": "sshd-session", "unidad": "ssh.service", "uid": 0, "inicio": 12},
    1000: {"pid": 1000, "ppid": 1, "comm": "brave", "exe": "/opt/brave/brave", "cmd": "brave", "unidad": "", "uid": 1000, "inicio": 20},
    1100: {"pid": 1100, "ppid": 1, "comm": "raro", "exe": "/home/u/.local/bin/raro", "cmd": "raro", "unidad": "", "uid": 1000, "inicio": 30},
    1200: {"pid": 1200, "ppid": 1, "comm": "curl", "exe": "/usr/bin/curl", "cmd": "curl http://192.168.1.1", "unidad": "", "uid": 1000, "inicio": 31},
    1300: {"pid": 1300, "ppid": 1, "comm": "lp", "exe": "/usr/bin/lp", "cmd": "lp", "unidad": "", "uid": 1000, "inicio": 32},
    500: {"pid": 500, "ppid": 1, "comm": "dhclient", "exe": "/usr/sbin/dhclient", "cmd": "dhclient", "unidad": "", "uid": 0, "inicio": 5},
    1400: {"pid": 1400, "ppid": 1390, "comm": "juego", "exe": "/home/u/.steam/juego/bin", "cmd": "juego", "unidad": "", "uid": 1000, "inicio": 40},
    1390: {"pid": 1390, "ppid": 1, "comm": "steam", "exe": "/usr/lib/steam/steam", "cmd": "steam", "unidad": "", "uid": 1000, "inicio": 39},
}
PAQUETES = {"/usr/sbin/sshd": "openssh-server", "/usr/lib/openssh/sshd-session": "openssh-server", "/usr/sbin/cupsd": "cups-daemon",
            "/opt/brave/brave": "brave-browser", "/usr/bin/curl": "curl", "/usr/bin/lp": "cups-client", "/usr/sbin/dhclient": "isc-dhcp-client",
            "/usr/lib/steam/steam": "steam-launcher"}


class Pruebas(unittest.TestCase):
    def setUp(self):
        self.run_original = subprocess.run
        self.t = tempfile.mkdtemp()
        os.environ["LEKSSO_CONEXIONES_RAIZ"] = self.t
        os.makedirs(self.t + "/etc")
        spec = importlib.util.spec_from_file_location("leksso_conexiones", PROGRAMA)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        m = self.m
        m.leer_ss = lambda: SS
        m.info_proceso = lambda pid: PROCESOS.get(pid)
        m.dueno_paquete = lambda ruta: PAQUETES.get(ruta, "")
        m.huella = lambda ruta: "0123456789abcdef"
        m.notificar = lambda *a, **k: self.avisos.append(a)
        self.avisos = []
        self.nft = []
        m.nft = lambda *a, entrada=None: (self.nft.append((a, entrada)), subprocess.CompletedProcess(a, 0, "", ""))[1]
        m.subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a, 0, "", "")     # ni ss -K ni systemctl
        m.puerta_de_enlace = lambda: {"192.168.1.1"}

    def tearDown(self):
        subprocess.run = self.run_original          # el módulo y la prueba comparten subprocess: se restaura
        shutil.rmtree(self.t, ignore_errors=True)

    def estado(self):
        return json.load(open(self.m.PUBLICO))

    def terminar_aprendizaje(self):
        c = self.m.leer_json(self.m.CONOCIDAS, {})
        c["_meta"]["aprende_hasta"] = 0
        self.m.escribir_json(self.m.CONOCIDAS, c)

    # ---- leer y clasificar ----
    def test_parsear_ss(self):
        cs = self.m.parsear_ss(SS)
        self.assertEqual(len(cs), 10)
        brave = next(c for c in cs if c["peer_ip"] == "142.250.1.1")
        self.assertEqual((brave["comm"], brave["pid"], brave["enviados"], brave["peer_puerto"]), ("brave", 1000, 5000, 443))
        v6 = next(c for c in cs if c["peer_ip"] == "2606:4700::1")
        self.assertEqual((v6["local_ip"], v6["peer_puerto"]), ("2001:db8::5", 443))
        udp = next(c for c in cs if c["proto"] == "udp")
        self.assertEqual((udp["estado"], udp["peer_puerto"], udp["local_puerto"]), ("UNCONN", 0, 68))

    def test_categorias(self):
        m, cs = self.m, self.m.parsear_ss(SS)
        puertos = {22, 631, 68}
        cat = {(c["comm"], c["peer_ip"]): m.categoria(c, puertos) for c in cs}
        self.assertEqual(cat[("sshd", "0.0.0.0")], "escuchando")
        self.assertEqual(cat[("sshd-session", "192.168.1.20")], "entrante")
        self.assertEqual(cat[("brave", "142.250.1.1")], "internet")
        self.assertEqual(cat[("brave", "2606:4700::1")], "internet")
        self.assertEqual(cat[("curl", "192.168.1.1")], "red_local")
        self.assertEqual(cat[("lp", "127.0.0.1")], "local")

    # ---- confianza ----
    def test_la_confianza_se_hereda_de_steam_y_lo_desconocido_queda_sin_validar(self):
        m = self.m
        lista, _ = m.hacer_foto()
        por = {r["nombre"]: r for r in lista if r["categoria"] != "escuchando"}
        self.assertEqual(por["brave"]["confianza"], "validada")          # de fábrica
        self.assertEqual(por["juego"]["confianza"], "validada")          # lo lanza Steam
        self.assertIn("steam", por["juego"]["por_que"])
        self.assertEqual(por["raro"]["confianza"], "sin validar")
        self.assertTrue(por["raro"]["ident"].startswith("bin:/home/u/.local/bin/raro#"))

    # ---- novedades y aprendizaje ----
    def test_la_primera_semana_solo_aprende(self):
        self.m.hacer_foto()
        e = self.estado()
        self.assertTrue(e["aprendiendo"])
        self.assertEqual(e["novedades"], 0)                              # «raro» conecta, pero aún se está aprendiendo
        self.assertEqual(json.loads(self.run_cli("barra"))["text"], "")

    def test_despues_de_aprender_lo_nuevo_sin_validar_enciende_el_aviso_y_confiar_lo_apaga(self):
        m = self.m
        m.hacer_foto()
        self.terminar_aprendizaje()
        PROCESOS[1500] = {"pid": 1500, "ppid": 1, "comm": "nuevo", "exe": "/tmp/nuevo", "cmd": "nuevo", "unidad": "", "uid": 1000, "inicio": 50}
        self.addCleanup(PROCESOS.pop, 1500, None)
        m.leer_ss = lambda: SS + 'tcp ESTAB 0 0 192.168.1.5:50020 8.8.4.4:443 users:(("nuevo",pid=1500,fd=3)) cubic bytes_sent:10 bytes_received:1\n'
        lista, novedades = m.hacer_foto()
        self.assertEqual(len(novedades), 1)
        self.assertTrue(novedades[0].startswith("bin:/tmp/nuevo#"))
        self.assertEqual(self.estado()["novedades"], 1)
        self.assertIn("Conexiones", json.loads(self.run_cli("barra"))["text"])
        m.confiar(novedades[0])
        self.assertFalse(m.leer_json(m.CONOCIDAS, {})[novedades[0]]["nueva"])
        lista, _ = m.hacer_foto()
        self.assertEqual(next(r for r in lista if r["nombre"] == "nuevo")["confianza"], "validada")
        self.assertEqual(self.estado()["novedades"], 0)

    def test_vistas_apaga_el_contador_sin_confiar(self):
        m = self.m
        m.hacer_foto(); self.terminar_aprendizaje()
        c = m.leer_json(m.CONOCIDAS, {})
        c["bin:/x#0000000000000000"] = {"primera": 1, "nueva": True, "visto": False, "dias": {}, "nombre": "x"}
        m.escribir_json(m.CONOCIDAS, c)
        m.hacer_foto()
        self.assertGreaterEqual(self.estado()["novedades"], 1)
        m.vistas()
        self.assertEqual(self.estado()["novedades"], 0)

    def test_cambiar_el_binario_revoca_la_confianza(self):
        m = self.m
        m.confiar("bin:/home/u/.local/bin/raro#0123456789abcdef")
        lista, _ = m.hacer_foto()
        self.assertEqual(next(r for r in lista if r["nombre"] == "raro")["confianza"], "validada")
        m.huella = lambda ruta: "ffffffffffffffff"                         # alguien cambió el programa
        lista, _ = m.hacer_foto()
        self.assertEqual(next(r for r in lista if r["nombre"] == "raro")["confianza"], "sin validar")

    def test_entrada_por_ssh_avisa_al_momento_y_solo_una_vez(self):
        m = self.m
        m.hacer_foto()                                                   # la primera foto ya ve la conexión de 192.168.1.20
        self.assertTrue(any(a[0] == "Alguien ha entrado por SSH" for a in self.avisos))
        self.avisos.clear()
        m.hacer_foto()
        self.assertEqual(self.avisos, [])                                # no se repite mientras siga abierta
        self.assertTrue(any(e["tipo"] == "entrada" for e in m.recientes_eventos(60)))

    def test_un_servicio_nuevo_que_escucha_hacia_fuera_es_novedad(self):
        m = self.m
        m.hacer_foto(); self.terminar_aprendizaje()
        PROCESOS[1600] = {"pid": 1600, "ppid": 1, "comm": "servidorcillo", "exe": "/opt/x/servidor", "cmd": "servidor", "unidad": "x.service", "uid": 0, "inicio": 60}
        self.addCleanup(PROCESOS.pop, 1600, None)
        m.leer_ss = lambda: SS + 'tcp LISTEN 0 5 0.0.0.0:8080 0.0.0.0:* users:(("servidorcillo",pid=1600,fd=3))\n'
        _, novedades = m.hacer_foto()
        self.assertEqual(len(novedades), 1)
        self.assertTrue(any("escuchar en el puerto 8080" in e["texto"] for e in m.recientes_eventos(60)))

    def test_envio_mucho_mayor_de_lo_habitual_avisa_una_vez_al_dia(self):
        import datetime as dt
        m = self.m
        m.hacer_foto(); self.terminar_aprendizaje()
        c = m.leer_json(m.CONOCIDAS, {})
        ident = next(i for i in c if i.startswith("pkg:brave"))
        hoy = dt.date.today()
        c[ident]["dias"] = {(hoy - dt.timedelta(days=d)).isoformat(): 1_000_000 for d in range(1, 5)}
        m.escribir_json(m.CONOCIDAS, c)
        m.leer_ss = lambda: SS.replace("bytes_sent:5000", f"bytes_sent:{300 * 1024 * 1024}")
        self.avisos.clear()
        m.hacer_foto()
        self.assertTrue(any(a[0] == "Un programa envía más de lo habitual" for a in self.avisos))
        self.avisos.clear()
        m.hacer_foto()
        self.assertFalse(any(a[0] == "Un programa envía más de lo habitual" for a in self.avisos))

    # ---- bloquear ----
    def test_no_se_pueden_bloquear_lo_vital_ni_la_red_local(self):
        m = self.m
        open(self.t + "/etc/resolv.conf", "w").write("nameserver 9.9.9.9\n")
        for destino, puerto in (("127.0.0.1", 0), ("192.168.1.1", 0), ("10.0.0.5", 443), ("9.9.9.9", 0), ("8.8.8.8", 53), ("1.1.1.1", 853), ("no-es-ip", 0), ("224.0.0.1", 0)):
            with self.assertRaises(m.Error, msg=f"{destino}:{puerto}"):
                m.comprobar_bloqueable(destino, puerto)
        self.assertEqual(str(m.comprobar_bloqueable("93.184.216.34", 443)), "93.184.216.34")

    def test_bloquear_es_permanente_se_carga_entero_y_se_puede_quitar(self):
        m = self.m
        b = m.bloquear("93.184.216.34", 443, "tcp", "raro")
        guion = self.nft[-1][1]
        self.assertIn("add table inet leksso_usuario", guion)                # tabla propia: endurecer.sh no la borra
        self.assertIn("flush chain inet leksso_usuario salida", guion)
        self.assertIn(f'ip daddr 93.184.216.34 tcp dport 443 counter drop comment "leksso-bloqueo-{b["id"]}"', guion)
        self.assertEqual(len(m.leer_json(m.BLOQUEOS, [])), 1)               # queda guardado hasta que el usuario lo quite
        with self.assertRaises(m.Error):
            m.bloquear("93.184.216.34", 443, "tcp")                         # duplicado
        lista, _ = m.hacer_foto()
        self.assertTrue(next(r for r in lista if r["nombre"] == "raro")["bloqueada"])
        m.desbloquear(b["id"])
        self.assertEqual(m.leer_json(m.BLOQUEOS, []), [])
        self.assertNotIn("leksso-bloqueo", self.nft[-1][1])
        with self.assertRaises(m.Error):
            m.desbloquear("noexiste")

    def test_bloquear_ipv6_y_sin_puerto(self):
        g = self.m.guion_de_bloqueos([{"id": "a1", "destino": "2606:4700::1", "puerto": 0, "proto": "udp"}])
        self.assertIn('ip6 daddr 2606:4700::1 meta l4proto udp counter drop', g)

    def test_aplicar_bloqueos_recarga_los_guardados(self):
        m = self.m
        m.bloquear("93.184.216.34", 443)
        n = len(self.nft)
        m.aplicar_bloqueos()
        self.assertEqual(len(self.nft), n + 1)
        self.assertIn("93.184.216.34", self.nft[-1][1])

    # ---- parar ----
    def test_parar_comprueba_que_sigue_siendo_el_mismo_y_no_toca_lo_vital(self):
        m = self.m
        enviadas = []
        m.os.kill = lambda pid, sig: (enviadas.append((pid, sig)), PROCESOS.pop(pid))
        with self.assertRaises(m.Error):
            m.parar(1100, "/otro/ejecutable", 30)                           # ya no es lo que viste
        with self.assertRaises(m.Error):
            m.parar(1100, "/home/u/.local/bin/raro", 999)                   # mismo programa, pero es otro proceso (PID reutilizado)
        with self.assertRaises(m.Error):
            m.parar(500, "/usr/sbin/dhclient", 5)                           # red: intocable
        with self.assertRaises(m.Error):
            m.parar(1, "/sbin/init", 1)
        self.assertEqual(enviadas, [])
        PROCESOS[1100] = dict(PROCESOS[1100]); copia = PROCESOS[1100]
        m.parar(1100, "/home/u/.local/bin/raro", 30)
        self.assertEqual([s for _, s in enviadas][:1], [15])                # SIGTERM
        PROCESOS[1100] = copia

    def test_parar_un_servicio_usa_systemctl_no_el_pid(self):
        m = self.m
        llamadas = []
        m.subprocess.run = lambda cmd, **k: (llamadas.append(cmd), subprocess.CompletedProcess(cmd, 0, "", ""))[1]
        PROCESOS[1700] = {"pid": 1700, "ppid": 1, "comm": "demonio", "exe": "/opt/d/demonio", "cmd": "demonio", "unidad": "demonio.service", "uid": 0, "inicio": 70}
        self.addCleanup(PROCESOS.pop, 1700, None)
        m.os.kill = lambda pid, sig: PROCESOS.pop(pid, None)
        m.parar(1700, "/opt/d/demonio", 70)
        self.assertIn(["systemctl", "stop", "demonio.service"], llamadas)

    def test_confiar_rechaza_identidades_raras(self):
        for malo in ("", "pkg:", "cualquier cosa", "pkg:a; rm -rf /", "bin:relativo#0123456789abcdef", None):
            with self.assertRaises(self.m.Error):
                self.m.confiar(malo)

    def run_cli(self, *a):
        env = dict(os.environ, LEKSSO_CONEXIONES_RAIZ=self.t)
        p = subprocess.Popen([sys.executable, PROGRAMA, *a], env=env, stdout=subprocess.PIPE, text=True)
        return p.communicate()[0]


if __name__ == "__main__":
    unittest.main()
