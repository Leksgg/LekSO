# Changelog

Formato: `+` nuevo · `-` eliminado o retirado · `~` modificado · `*` otros.
Lo más reciente, arriba.

## Sin publicar

+ Antes de instalar se comprueba también que el commit de la versión pertenece a la rama principal del repositorio; se guarda y se muestra el commit y la firma de lo instalado.
+ `scripts/desbloquear-firma.sh` y `scripts/publicar-version.sh --auto`: publicar la siguiente versión con un solo comando, con la clave de firma protegida por contraseña y desbloqueada unas horas; si algo falla, se deshace la preparación.
+ Pruebas de la verificación (`scripts/test_actualizar.py`): firma buena, de otra clave, sin firmar, etiqueta ligera, inexistente, fuera de la rama principal y nombres de versión hostiles.
~ La comprobación de firma exige que coincida con un firmante autorizado, no solo que exista una firma.
* Una etiqueta con salto de línea final se aceptaba como versión válida; corregido.
~ La ventana de Actualizaciones nombra las versiones por su nombre (Alpha 0.1.1) y muestra solo lo nuevo.

## Alpha 0.1.1 · 2026-11-15

+ Primera actualización de prueba: se publica como versión firmada y llega al equipo con aviso.
~ Ajustes muestra la versión instalada («LekSO Alpha 0.1.1») junto a la información del sistema.
~ El indicador de IA de la barra se actualiza cada 30 segundos en vez de cada 5, con menos despertares del procesador y más batería.

## Alpha 0.1.0 · 2026-11-15

Primera versión de prueba.

+ Escritorio por zonas sobre Debian 13 y sway: raíl de iconos, explorador, centro con terminal, panel de la IA y barra de tareas.
+ Permisor de IA con alcance por tarea, registro firmado y deshacer; caja de Bubblewrap para programas y para la IA; asistente con Claude Code conectado solo al permisor.
+ Instalación repetible (`scripts/provision-base.sh`) y catálogo de aplicaciones (`lekso-apps`).
+ Notificaciones, capturas, portapapeles, ajustes, energía, reposo, red, Bluetooth, discos y Stream Deck.
+ Cortafuegos, actualizaciones de seguridad de Debian y ajustes del núcleo.
+ Versión visible y actualizaciones firmadas: `lekso-actualizar`, Ajustes → Actualizaciones y aviso en la barra.

## 2026-11-15 · Calidad de vida

+ Notificaciones (mako) con la paleta de LekSO, arriba a la derecha.
+ Teclas de volumen, micrófono, brillo y multimedia con aviso en pantalla, también con la pantalla bloqueada.
+ Capturas de pantalla: `Impr` (región), `Mayús+Impr` (pantalla) y `Mod+Impr` (ventana); se guardan en `~/Imágenes/Capturas`, se copian al portapapeles y avisan.
+ Historial del portapapeles (`Mod+V`, botón en el raíl).
+ Ajustes: un solo sitio (`Mod+I`, el engranaje del raíl) para sonido, red, pantallas, Bluetooth, apariencia, impresoras, aplicaciones y modo de energía.
+ Reposo: bloqueo a los 5 minutos, pantalla apagada a los 10 y suspensión a los 25 solo con batería; la pantalla completa (vídeo, juegos, directos) lo impide. `Mod+L` bloquea al momento.
+ Visual Studio Code como editor de código (`lekso-apps instalar code`, repositorio firmado de Microsoft): arranca con Wayland nativo y sin telemetría si el usuario no tiene ya sus ajustes.
- Se quita del raíl el botón «Cuenta», que no hacía nada.
~ Los botones del raíl y la barra funcionan aunque la barra se reinicie a mano: los programas que llaman a sway buscan su socket si no lo heredan.
~ Las ventanas de portapapeles y ajustes flotan en el centro; el gestor de redes (`lekso-redes`) usa los colores de LekSO.
+ Batería en la barra (solo en portátiles), Bluetooth con interfaz, servicio de impresión, miniaturas de vídeo, fuentes con emoji y compatibles con Arial.

## 2026-11-15 · Asistente de IA con Claude Code

+ Adaptador MCP del permisor (`lekso-ia/mcp_permisor.py`, solo biblioteca estándar): ocho herramientas (pedir acceso, listar, leer, escribir, borrar, mover, cerrar tarea y consultar una petición). No expone aprobar, ejecutar programas ni el canal de control. Lo leído se recorta por defecto para ahorrar tokens y el acceso espera la aprobación en una sola llamada.
+ `lekso-claude`: Claude Code dentro de `caja --ia-nube`, con sus herramientas propias desactivadas y solo las del permisor; su sesión vive en una carpeta aparte.
+ `caja --env VAR=VALOR` para pasar variables a la caja de forma explícita.
+ Botón del asistente en el raíl; se acopla como pestaña en la zona derecha.
+ Terminal nueva (kitty, un solo proceso para todas las ventanas) con copiar y pegar como en cualquier otra aplicación: `Ctrl+C` copia si hay texto seleccionado y, si no, interrumpe el programa; `Ctrl+V` pega; seleccionar con el ratón copia solo.
~ foot sigue instalado como alternativa; el resto del sistema abre terminales con `lekso-term`.
+ Botón y atajo (`Mod+M`) para ocultar y mostrar las ventanas flotantes: el «minimizar» de LekSO.
+ Pruebas del adaptador (`lekso-ia/test_mcp.py`): protocolo, flujo completo, argumentos hostiles y entrada gigante.
* La caja del asistente tiene red completa; limitarla al dominio del proveedor queda pendiente.

## 2026-11-15 · Seguridad del equipo, energía y teclado

+ Cortafuegos (`scripts/endurecer.sh`): todo lo entrante bloqueado salvo respuestas a lo que el equipo pide; saliente libre.
+ Actualizaciones de seguridad automáticas (solo el repositorio de seguridad de Debian, sin reinicios automáticos).
+ Ajustes del núcleo: sin espionaje entre procesos, sin lectura de direcciones del sistema y sin eBPF para usuarios sin privilegios. Se siguen permitiendo los espacios de usuario que necesita la caja.
+ Botón de energía en el raíl: bloquear, suspender, hibernar, cerrar sesión, reiniciar y apagar. Solo activa lo que el equipo admite y pide confirmación en lo que cierra programas.
+ El teclado de la sesión sigue al del sistema (español por defecto).
~ El permisor de IA corre como servicio de usuario con filtro de llamadas al sistema y sin permisos de administrador.
~ Los programas de la propia interfaz comparten estilo (`lekso_ui`).
* Corregido en la instalación: la carpeta `~/.local` quedaba a nombre de root.

## 2026-11-15 · Instalar aplicaciones

+ Comando `lekso-apps`: catálogo de equivalentes en Linux de las aplicaciones habituales de Windows (desarrollo, Docker, Playwright, IA, navegadores, comunicación, multimedia, utilidades y juegos). Lista lo instalado, instala por nombre o por grupo, simula con `--simular` y explica lo que no tiene equivalente (`pendientes`).
+ Fuentes: paquetes de Debian, repositorios firmados (Brave, VS Code), descargas directas del proveedor (Discord, Obsidian, Heroic, r2modman) y npm.
~ Al instalar un navegador, pasa a ser el predeterminado para páginas web y enlaces.

## 2026-11-15 · Dispositivos y nombres de ventana

+ Pendrives y discos: automontaje (también NTFS y exFAT) desde el explorador.
+ Soporte de cámaras, listado de USB y Bluetooth instalados.
+ Volumen: indica el dispositivo activo; clic abre el mezclador, clic derecho silencia, la rueda sube o baja.
+ Botón «Aplicaciones» en el raíl: menú flotante con iconos, buscador y botón de cerrar (X, Esc o el propio botón). No se cierra al mover el ratón. Sin entradas técnicas.
+ Stream Deck (streamdeck-ui): se inicia solo al conectarlo, con acceso por USB para el usuario y botón en el raíl para configurarlo.
+ Red con NetworkManager: la barra indica cable o Wi-Fi, IP y puerta de enlace al pasar el ratón; un clic abre el gestor de redes.
~ Las ventanas de la terminal, el editor, el panel de la IA y la información de archivo tienen nombre propio en la barra de tareas.

## 2026-11-15 · Escritorio por zonas

+ Distribución por zonas sobre sway: raíl de iconos a la izquierda, explorador, centro (la app activa, a pantalla completa de su zona) con terminal debajo, y panel de la IA a la derecha.
+ Todo lo que abre el usuario va a la zona central.
+ Barra de tareas abajo, con un botón por ventana (clic para ir a ella, clic central para cerrarla).
+ Botón «Restaurar vista» en el raíl: vuelve a la distribución por defecto sin cerrar las apps abiertas, que pasan a pestañas del centro.
+ El escritorio arranca solo al iniciar sesión en la primera consola.
+ labwc queda como alternativa (ventanas flotantes con minimizar, maximizar y cerrar, e iconos en el escritorio).

## 2026-11-15 · Abrir archivos

+ Programa predeterminado para cada tipo de archivo del sistema (917): editor de texto, visor de imágenes, lector de PDF, reproductor, archivador y, para el resto, una pantalla con la información del archivo.
+ Los programas de Windows se abren dentro de la caja, con solo su carpeta en lectura.
+ `scripts/asociar-archivos.py` rellena solo lo que falta: lo que elija el usuario no se toca.
~ Los binarios de Linux no se ejecutan con doble clic.

## 2026-11-15 · Iconos por tipo de archivo

+ Tema de iconos LekSO: 126 SVG ligeros (unos 150 KB), uno por tipo de archivo, con color por familia y letras (código, web, datos, documentos, imagen, vídeo, audio, paquetes, programas) y carpetas en cian.
+ `scripts/generar-iconos.py` genera el tema; hereda de Adwaita para lo que no define.
~ El script de preparación instala el tema y el complemento SVG de Qt, y deja la carpeta de configuración a nombre del usuario.

## 2026-11-15 · La IA dentro de su caja

+ `caja --ia` y `caja --ia-nube`: la caja de una IA. Dentro entra solo el socket de su canal; no ve archivos ni el socket de control, y para tocar cualquier cosa pide permiso al permisor.
+ El canal de nube siempre pregunta, aunque la carpeta esté recordada.
+ El cliente elige solo el canal que exista en su caja.
+ Prueba `scripts/test_caja_ia.sh`.

## 2026-11-15 · Endurecimiento del permisor y de la caja

+ Registro firmado: las líneas editadas a mano se ignoran.
+ Canal separado para IA en la nube; el destino de lo leído lo fija el canal, no el mensaje.
+ Cada lectura devuelve un aviso de contenido no confiable y marca instrucciones ocultas o caracteres invisibles.
+ Perfil `--estricta` de la caja con filtro seccomp.
+ Pruebas de ataque, de corte brusco, de escapes de la caja y de mutación.
~ Las carpetas se muestran resueltas (sin enlaces) al pedir permiso.
~ Títulos y rutas de una petición solo admiten caracteres imprimibles.
~ Las operaciones que cambian archivos van de una en una.
~ Topes de peticiones pendientes, tareas abiertas y tamaño de mensajes y escrituras.
~ El panel lee solo el final del registro.
~ Leer una tubería o un dispositivo ya no bloquea el permisor.
- Borrar ya no se recuerda entre tareas.
- La caja ya no hereda las variables de entorno.

## 2026-11-15 · Permisor de IA, modelos, panel y explorador

+ Permisor de IA: tareas con carpetas y permisos, registro, deshacer por acción o por tarea, papelera estándar, versiones previas con purga y carpetas recordadas.
+ Gestor de modelos de Ollama con descarga por inactividad y aviso si no cabe en la RAM.
+ Panel de texto para permitir, rechazar y deshacer.
+ Explorador con árbol lateral y ruta con botones.
+ Caja con pantalla, audio y GPU opcionales.
+ Scripts de medición de OBS para Linux y Windows.
+ Licencia MIT.
~ El estado de la IA en la barra sale del gestor de modelos.

## 2026-11-15 · Base y tema

+ Debian 13 mínimo con sway, waybar, foot, fuzzel y pcmanfm-qt; script de preparación repetible.
+ Caja con Bubblewrap: sin red, sin carpeta personal y con el sistema en solo lectura.
+ Tema oscuro común en barra, pestañas y aplicaciones Qt.
