# LekSO

Sistema operativo ligero basado en Linux, pensado para ejecutar programas de Windows y para trabajar con una IA que solo actúa cuando se le pide.

> Estado: diseño inicial. Todavía no hay código.

## Objetivos

- **Ligero.** Un escritorio mínimo, sin tienda, widgets ni telemetría, con un consumo en reposo de unos cientos de MB de RAM.
- **Compatible con programas de Windows.** Steam con Proton para los juegos; Wine para programas sueltos. Lo que tenga versión nativa de Linux se usa nativo.
- **Interfaz de archivos al estilo de un editor de código.** Árbol de carpetas, ruta clicable, recorrido de carpetas visitadas y pestañas por aplicación.
- **IA bajo petición.** Un panel que está cerrado hasta que se llama. Cada petición lleva su alcance (la carpeta actual) y sus permisos (leer, escribir, borrar). El modelo, local con Ollama o en la nube, solo ocupa memoria mientras se usa. Cada acción queda en un registro y se puede deshacer.
- **Aislamiento.** Cada programa de Windows en su propia caja, con permisos de red y de archivos por programa.

## Principio de diseño

No se reescribe nada que ya exista y funcione.

| Se toma hecho | Se adapta | Se construye |
|---|---|---|
| Kernel de Linux sobre Debian mínimo, Proton, Wine, DXVK, compositor Wayland, PipeWire, servidor MCP de archivos, live-build y Calamares | Explorador de archivos, barra superior, pestañas (modo tabbed de sway), aislamiento con Bubblewrap o Firejail, instantáneas con btrfs, cliente de chat de IA | Intermediario de permisos de la IA, registro de acciones y deshacer, carga y descarga del modelo, pegamento de la interfaz, pruebas comparadas de rendimiento |

## Plan

1. Montar una máquina virtual con Debian mínimo y medir el consumo en reposo.
2. Añadir las capas una a una, con un punto de control antes de cada una.
3. Probar la compatibilidad de juegos y el rendimiento de OBS en hardware real.

## Componentes construidos

| Carpeta | Qué es |
| --- | --- |
| lekso-ia/ | Permisor de IA (alcance por tarea, registro, deshacer), gestor de modelos de Ollama y panel de texto (Mod+a). Pruebas: `python3 -m unittest` y `prueba_e2e.sh`. |
| scripts/caja.sh | Caja con Bubblewrap; opciones `--gui`, `--audio` y `--gpu`. El socket del permisor nunca entra. |
| scripts/bench-obs.sh y .ps1 | Medición comparable de OBS en LekSO y en Windows. Sin probar con OBS real. |
| config/ | sway, waybar, foot, qt6ct y pcmanfm-qt con la paleta de LekSO. |

Licencia: MIT.
