"""Prueba del gestor de modelos con un Ollama falso. PYTHONPATH=. python3 -m unittest test_modelo"""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

import modelo

ESTADO = {"cargado": [], "recibido": []}
TAM = {"pequeno": 1 * 1024 ** 3, "enorme": 900 * 1024 ** 3}


class Falso(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, d):
        b = json.dumps(d).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/api/version":
            self._json({"version": "x"})
        elif self.path == "/api/ps":
            self._json({"models": ESTADO["cargado"]})
        elif self.path == "/api/tags":
            self._json({"models": [{"name": f"{k}:latest", "size": v} for k, v in TAM.items()]})

    def do_POST(self):
        d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        ESTADO["recibido"].append(d)
        if d["keep_alive"] == 0:
            ESTADO["cargado"] = []
        else:
            ESTADO["cargado"] = [{"name": d["model"], "size": TAM[d["model"].split(":")[0]]}]
        self._json({})


class Pruebas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Falso)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        modelo.URL = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        ESTADO["cargado"], ESTADO["recibido"] = [], []

    def test_carga_con_keep_alive_y_descarga(self):
        ok, _ = modelo.cargar("pequeno")
        self.assertTrue(ok)
        self.assertEqual(ESTADO["recibido"][-1]["keep_alive"], modelo.KEEP_ALIVE)
        self.assertEqual(len(modelo.cargados()), 1)
        self.assertEqual(modelo.descargar(), 1)
        self.assertEqual(modelo.cargados(), [])
        self.assertEqual(ESTADO["recibido"][-1]["keep_alive"], 0)

    def test_avisa_si_no_cabe(self):
        ok, msg = modelo.cargar("enorme")
        self.assertFalse(ok)
        self.assertIn("libres", msg)
        self.assertEqual(ESTADO["recibido"], [])

    def test_modelo_no_instalado(self):
        ok, msg = modelo.cargar("inexistente")
        self.assertFalse(ok)

    def test_estado_barra(self):
        if modelo.ollama_instalado():
            self.assertEqual(modelo.estado_barra()["class"], "reposo")
            modelo.cargar("pequeno")
            self.assertEqual(modelo.estado_barra()["class"], "activa")


if __name__ == "__main__":
    unittest.main()
