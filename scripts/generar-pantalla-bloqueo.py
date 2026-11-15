#!/usr/bin/env python3
"""Genera la imagen de la pantalla de bloqueo de LekSO: un mensaje claro de que está bloqueada y qué hacer.

Se coloca centrada sobre el color de fondo; el anillo de la contraseña de swaylock queda justo debajo.
Uso: python3 generar-pantalla-bloqueo.py [destino]   (por defecto /usr/share/lekso/bloqueo.png)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONDO = (16, 21, 27)       # #10151b
CIAN = (76, 195, 224)      # #4cc3e0
TEXTO = (223, 230, 238)    # #dfe6ee
APAGADO = (138, 152, 168)  # #8a98a8


def fuente(tam, negrita=False):
    nombre = "DejaVuSans-Bold.ttf" if negrita else "DejaVuSans.ttf"
    for base in ("/usr/share/fonts/truetype/dejavu", "C:/Windows/Fonts", "/usr/share/fonts/TTF"):
        ruta = os.path.join(base, nombre)
        if os.path.exists(ruta):
            return ImageFont.truetype(ruta, tam)
    return ImageFont.load_default()


def centrado(d, y, texto, f, color, ancho):
    caja = d.textbbox((0, 0), texto, font=f)
    d.text(((ancho - (caja[2] - caja[0])) // 2, y), texto, font=f, fill=color)


def main(destino):
    ancho, alto = 1000, 720
    img = Image.new("RGB", (ancho, alto), FONDO)
    d = ImageDraw.Draw(img)
    centrado(d, 30, "LekSO", fuente(64, True), CIAN, ancho)
    centrado(d, 118, "Pantalla bloqueada", fuente(30), TEXTO, ancho)
    centrado(d, 164, "Escribe tu contraseña y pulsa Intro", fuente(22), APAGADO, ancho)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    img.save(destino)
    print(f"Imagen creada: {destino}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/usr/share/lekso/bloqueo.png")
