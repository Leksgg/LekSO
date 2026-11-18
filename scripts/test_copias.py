#!/usr/bin/env python3
"""Pruebas de leksso-copias con un restic falso: el orden copiar → comprobar → borrar las que sobran, los fallos, la
clave, el horario y los límites de lo que puede recuperar un usuario. Uso: python3 scripts/test_copias.py
(No hace falta restic ni ser root: todo cuelga de una carpeta temporal.)"""
import importlib.util
import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
PROGRAMA = os.path.join(AQUI, "leksso-copias.py")

RESTIC_FALSO = r'''#!/usr/bin/env python3
import json, os, sys, datetime
d = os.environ["STUB_DIR"]
repo = os.environ["RESTIC_REPOSITORY"]
a = sys.argv[1:]
def cargar():
    try: return json.load(open(d + "/snaps.json"))
    except OSError: return []
def guardar(x): json.dump(x, open(d + "/snaps.json", "w"))
open(d + "/llamadas.log", "a").write(" ".join(a) + "\n")
if not os.path.exists(os.environ["RESTIC_PASSWORD_FILE"]):
    sys.exit(1)
if a[0] == "init":
    os.makedirs(repo, exist_ok=True); open(repo + "/config", "w").write("x")
elif a[0] == "snapshots":
    print(json.dumps([{"short_id": s["id"], "time": s["time"]} for s in cargar()]))
elif a[0] == "backup":
    if os.path.exists(d + "/falla_copia"): print("error: no space left on device", file=sys.stderr); sys.exit(1)
    s = cargar(); n = len(s) + int(open(d + "/contador").read() if os.path.exists(d + "/contador") else 0) + 1
    open(d + "/contador", "w").write(str(n))
    s.append({"id": "%08x" % (0xabc000 + n), "time": (datetime.datetime(2026, 11, 1, 3, 0).astimezone() + datetime.timedelta(days=n)).isoformat()})
    guardar(s); open(repo + "/datos", "a").write("x" * 100)
    sys.exit(3 if os.path.exists(d + "/ilegibles") else 0)
elif a[0] == "check":
    if os.path.exists(d + "/falla_check"): print("error: pack dañado", file=sys.stderr); sys.exit(1)
elif a[0] == "forget":
    n = int(a[a.index("--keep-last") + 1]); s = sorted(cargar(), key=lambda x: x["time"]); guardar(s[-n:])
elif a[0] == "restore":
    t = a[a.index("--target") + 1]; r = a[a.index("--include") + 1]
    os.makedirs(t + os.path.dirname(r), exist_ok=True); open(t + r, "w").write("recuperado")
elif a[0] == "ls":
    print(json.dumps({"struct_type": "snapshot"}))
    for p, t in (("/home", "dir"), ("/home/u", "dir"), ("/home/u/Docs", "dir"), ("/home/otro", "dir"), ("/home/u/nota.txt", "file")):
        print(json.dumps({"struct_type": "node", "name": os.path.basename(p), "path": p, "type": t, "size": 3}))
'''


class PruebasCopias(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.stub = os.path.join(self.t, "stub")
        os.makedirs(self.stub)
        self.restic = os.path.join(self.t, "restic_falso.py")
        open(self.restic, "w").write(RESTIC_FALSO)
        os.chmod(self.restic, 0o755)
        self.casa = os.path.join(self.t, "home", "u")
        os.makedirs(self.casa)
        open(os.path.join(self.casa, "a.txt"), "w").write("hola")
        self.env = dict(os.environ, LEKSSO_COPIAS_RAIZ=self.t, LEKSSO_RESTIC=self.restic, STUB_DIR=self.stub,
                        LEKSSO_COPIAS_HOMES=self.casa, LEKSSO_COPIAS_SIN_SYSTEMD="1",
                        LEKSSO_COPIAS_USUARIO=pwd.getpwuid(os.getuid()).pw_name)
        self.env.pop("SUDO_USER", None)

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def corre(self, *a, entrada=None):
        return subprocess.run([sys.executable, PROGRAMA, *a], env=self.env, capture_output=True, text=True, input=entrada)

    def activar(self, **extra):
        d = {"frecuencia": "diaria", "hora": "03:30", "clave": "Lks15"}
        d.update(extra)
        return self.corre("activar", entrada=json.dumps(d))

    def llamadas(self):
        try:
            return open(os.path.join(self.stub, "llamadas.log")).read().splitlines()
        except OSError:
            return []

    def estado(self):
        return json.load(open(self.t + "/var/lib/leksso/copias-estado.json"))

    # ---- datos puros ----
    def modulo(self):
        os.environ["LEKSSO_COPIAS_RAIZ"] = self.t
        spec = importlib.util.spec_from_file_location("leksso_copias", PROGRAMA)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_calendario(self):
        m = self.modulo()
        self.assertEqual(m.calendario("diaria", "03:30"), "*-*-* 03:30:00")
        self.assertEqual(m.calendario("semanal", "21:05"), "Mon *-*-* 21:05:00")
        self.assertEqual(m.calendario("mensual", "00:00"), "*-*-01 00:00:00")
        for malo in (("anual", "03:00"), ("diaria", "25:00"), ("diaria", "3:00"), ("diaria", "")):
            with self.assertRaises(m.Error):
                m.calendario(*malo)

    def test_clave_y_discos_y_espacio(self):
        m = self.modulo()
        self.assertEqual(m.validar_clave("Lks15"), "Lks15")
        for mala in ("abc", "a\nb", "", "x" * 201, None):
            with self.assertRaises(m.Error):
                m.validar_clave(mala)
        lvm = "lekso--vg-root lvm\nsda3          part\nsda           disk\n"
        self.assertEqual(m.discos_de(lvm), {"sda"})
        self.assertEqual(m.discos_de("sdb1 part\nsdb disk"), {"sdb"})
        self.assertEqual(m.hace_falta_espacio(0, 36 * 1024 ** 3), 2 * 1024 ** 3 if 36 * 1024 ** 3 // 20 < 2 * 1024 ** 3 else 36 * 1024 ** 3 // 20)
        self.assertEqual(m.hace_falta_espacio(0, 1000 * 1024 ** 3), 50 * 1024 ** 3)

    def test_copia_antigua(self):
        import datetime as dt
        m = self.modulo()
        ahora = dt.datetime(2026, 11, 18, 12, 0).astimezone()
        self.assertTrue(m.vieja(None, "diaria"))
        self.assertFalse(m.vieja((ahora - dt.timedelta(days=2)).isoformat(), "diaria", ahora))
        self.assertTrue(m.vieja((ahora - dt.timedelta(days=4)).isoformat(), "diaria", ahora))
        self.assertFalse(m.vieja((ahora - dt.timedelta(days=14)).isoformat(), "semanal", ahora))
        self.assertTrue(m.vieja((ahora - dt.timedelta(days=16)).isoformat(), "semanal", ahora))

    # ---- activar, horario y clave ----
    def test_activar_crea_clave_privada_horario_y_config(self):
        r = self.activar()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        clave = self.t + "/etc/leksso/copias.key"
        self.assertEqual(open(clave).read(), "Lks15")
        self.assertEqual(oct(os.stat(clave).st_mode & 0o777), "0o400")
        self.assertEqual(oct(os.stat(self.t + "/var/lib/leksso-copias").st_mode & 0o777), "0o700")
        h = open(self.t + "/etc/systemd/system/leksso-copias.timer.d/horario.conf").read()
        self.assertIn("OnCalendar=*-*-* 03:30:00", h)
        self.assertTrue(json.load(open(self.t + "/var/lib/leksso/copias.json"))["activa"])

    def test_desactivadas_por_defecto_y_se_pueden_desactivar(self):
        e = json.loads(self.corre("estado").stdout)
        self.assertFalse(e["activa"])
        self.activar()
        self.assertTrue(json.loads(self.corre("estado").stdout)["activa"])
        self.assertEqual(self.corre("desactivar").returncode, 0)
        self.assertFalse(json.loads(self.corre("estado").stdout)["activa"])
        self.assertTrue(os.path.exists(self.t + "/etc/leksso/copias.key"))   # la clave y las copias se conservan

    def test_cambiar_horario_sin_pedir_clave(self):
        self.activar()
        r = self.corre("configurar", entrada=json.dumps({"frecuencia": "semanal", "hora": "22:15"}))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Mon *-*-* 22:15:00", open(self.t + "/etc/systemd/system/leksso-copias.timer.d/horario.conf").read())
        self.assertEqual(open(self.t + "/etc/leksso/copias.key").read(), "Lks15")

    def test_clave_mala_no_deja_nada_activado(self):
        r = self.activar(clave="ab")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(os.path.exists(self.t + "/etc/leksso/copias.key"))
        self.assertFalse(json.loads(self.corre("estado").stdout)["activa"])

    # ---- copias y retención ----
    def test_retencion_de_cinco_borra_la_mas_antigua(self):
        self.activar()
        for _ in range(7):
            self.assertEqual(self.corre("ejecutar", "--ahora").returncode, 0)
        e = self.estado()
        self.assertEqual(len(e["snapshots"]), 5)
        fechas = [s["fecha"] for s in e["snapshots"]]
        self.assertEqual(fechas, sorted(fechas, reverse=True))
        ids = {s["id"] for s in e["snapshots"]}
        self.assertNotIn("00abc001", ids)          # la 1.ª y la 2.ª ya no están
        self.assertEqual(e["ultima"]["resultado"], "ok")

    def test_orden_copiar_comprobar_borrar(self):
        self.activar()
        self.corre("ejecutar", "--ahora")
        ordenes = [l.split()[0] for l in self.llamadas() if l.split()[0] in ("backup", "check", "forget")]
        self.assertEqual(ordenes, ["backup", "check", "forget"])

    def test_si_la_comprobacion_falla_no_se_borra_nada(self):
        self.activar()
        for _ in range(5):
            self.corre("ejecutar", "--ahora")
        open(os.path.join(self.stub, "falla_check"), "w").close()
        r = self.corre("ejecutar", "--ahora")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.estado()["ultima"]["resultado"], "fallo")
        self.assertEqual(len(json.load(open(os.path.join(self.stub, "snaps.json")))), 6)   # nada se borró
        self.assertEqual([l for l in self.llamadas()].count("forget --group-by  --keep-last 5 --prune"), 5)

    def test_copia_fallida_se_cuenta_y_no_borra(self):
        self.activar()
        open(os.path.join(self.stub, "falla_copia"), "w").close()
        r = self.corre("ejecutar", "--ahora")
        self.assertEqual(r.returncode, 1)
        u = self.estado()["ultima"]
        self.assertEqual(u["resultado"], "fallo")
        self.assertIn("no space left", u["mensaje"])
        barra = json.loads(self.corre("barra").stdout)
        self.assertEqual(barra["text"], "▲ Copias")
        self.assertIn("falló", barra["tooltip"])

    def test_archivos_ilegibles_es_aviso_no_fallo(self):
        self.activar()
        open(os.path.join(self.stub, "ilegibles"), "w").close()
        self.assertEqual(self.corre("ejecutar", "--ahora").returncode, 0)
        self.assertEqual(self.estado()["ultima"]["resultado"], "aviso")

    def test_sin_activar_no_copia(self):
        r = self.corre("ejecutar", "--ahora")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Falta el repositorio", r.stderr)

    def test_barra_vacia_si_todo_va_bien(self):
        self.activar()
        self.corre("ejecutar", "--ahora")
        self.assertEqual(json.loads(self.corre("barra").stdout)["text"], "")

    def test_estado_dice_hasta_cuando_se_puede_volver(self):
        self.activar()
        for _ in range(3):
            self.corre("ejecutar", "--ahora")
        e = json.loads(self.corre("estado").stdout)
        self.assertEqual(len(e["copias"]), 3)
        self.assertEqual(e["volver_hasta"], e["copias"][-1]["fecha"])
        self.assertEqual(e["maximo"], 5)
        self.assertIn("mismo_disco", e)

    # ---- recuperar ----
    def test_restaurar_solo_lo_propio_y_sin_pisar(self):
        self.activar()
        self.corre("ejecutar", "--ahora")
        u = pwd.getpwuid(os.getuid())
        # la carpeta personal del usuario de prueba es la del sistema; lo que importa es que se rechace lo ajeno
        r = self.corre("restaurar", "00abc001", "/etc/passwd")
        self.assertEqual(r.returncode, 2)
        self.assertIn("propia carpeta", r.stdout)
        r = self.corre("restaurar", "../x", u.pw_dir + "/a")
        self.assertEqual(r.returncode, 2)
        r = self.corre("restaurar", "00abc001", u.pw_dir + "/../etc/passwd")
        self.assertEqual(r.returncode, 2)

    def test_lo_recuperado_se_copia_sin_seguir_enlaces(self):
        import importlib.machinery
        import importlib.util
        cargador = importlib.machinery.SourceFileLoader("copias_prueba", os.path.join(os.path.dirname(os.path.abspath(__file__)), "leksso-copias.py"))
        mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("copias_prueba", cargador))
        cargador.exec_module(mod)
        prep, dest = tempfile.mkdtemp(), os.path.join(tempfile.mkdtemp(), "Recuperado", "2026-01-01_0000")
        os.makedirs(os.path.join(prep, "a"))
        open(os.path.join(prep, "a", "b.txt"), "w").write("hola")
        os.symlink("/etc/passwd", os.path.join(prep, "a", "enlace"))
        mod._copiar_como_usuario(pwd.getpwuid(os.getuid()), prep, dest)
        self.assertEqual(open(os.path.join(dest, "a", "b.txt")).read(), "hola")
        self.assertTrue(os.path.islink(os.path.join(dest, "a", "enlace")))        # el enlace queda como enlace

    def test_listar_solo_muestra_lo_del_usuario(self):
        self.activar()
        self.corre("ejecutar", "--ahora")
        self.env["LEKSSO_COPIAS_USUARIO"] = "u"
        # el usuario falso «u» no existe: pwd falla → se rechaza en vez de mostrar todo
        r = self.corre("listar", "00abc001", "/home")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
