# LeksSO

Escritorio ligero sobre Debian, con una capa de aislamiento para programas y un permisor para que una IA solo toque lo que se le concede, cuando se le pide.

## Qué incluye

| Carpeta | Qué es |
| --- | --- |
| `lekso-ia/` | Permisor de IA: alcance por tarea (leer, escribir, borrar), registro firmado, deshacer, gestor de modelos de Ollama y panel de texto. |
| `scripts/caja.sh` | Caja con Bubblewrap para programas y para una IA (`--ia`, `--ia-nube`), con pantalla, audio y GPU opcionales y un perfil `--estricta`. |
| `scripts/provision-base.sh` | Prepara un Debian mínimo con el escritorio. |
| `scripts/bench-obs.sh`, `bench-obs.ps1` | Medición comparable de OBS entre Linux y Windows. |
| `config/` | Configuración de sway, waybar, foot, qt6ct y pcmanfm-qt. |

## Principios

- **Ligero.** Escritorio mínimo, sin tienda, widgets ni telemetría.
- **No reescribir lo que ya existe.** Debian, sway, Bubblewrap, Wine, Ollama.
- **La IA actúa bajo petición.** No lee ni indexa nada por su cuenta. Cada tarea lleva su alcance y sus permisos, cada acción queda registrada y se puede deshacer.
- **Aislamiento por defecto.** Una caja sin red, sin tus archivos y con el sistema en solo lectura.

## Versiones y actualizaciones

La versión instalada se ve en Ajustes → Actualizaciones, con `lekso-actualizar version` y en la pantalla de inicio de sesión. Cuando se publica una versión nueva aparece un aviso en la barra y una notificación; se instala desde Ajustes, con tu permiso y solo si está firmada por LeksSO. Se puede volver a la anterior.

## Pruebas

```
cd lekso-ia
PYTHONPATH=. python3 -m unittest test_nucleo test_modelo test_ataques
bash prueba_e2e.sh
python3 test_caida.py
python3 mutar.py
bash ../scripts/test_caja_ataques.sh
bash ../scripts/test_caja_ia.sh
```

Requiere Linux, Python 3 y Bubblewrap.

## Licencia

MIT. Ver [LICENSE](LICENSE).
