# Changelog

Formato: `+` nuevo · `-` eliminado o retirado · `~` modificado · `*` otros.
Lo más reciente, arriba.

## Sin publicar

~ El sistema pasa a llamarse **LeksSO** (Leks + Sistema Operativo). Cambia el nombre que se ve; los comandos (`lekso-*`) y las carpetas siguen igual. El repositorio de GitHub también se llama ahora LeksSO, y el nombre antiguo sigue funcionando para los equipos ya instalados.
~ Colores nuevos, tema **Marea**: fondo petróleo oscuro con acento turquesa, y avisos de OK, aviso y error que ya no se confunden con el acento. Se aplica a barra, ventanas, menús, terminal, avisos, bloqueo y iconos. El tema **Pizarra** (grafito cálido y azul) queda preparado en `scripts/aplicar-tema.py`, sin selector en Ajustes todavía. Solo modo oscuro.
+ Controladores y firmware: a los 3 minutos de arrancar y una vez al día, LeksSO actualiza solo el microcódigo y el firmware de Debian, y avisa si hay un controlador NVIDIA nuevo o una actualización de firmware de dispositivos. Esos dos se instalan con un clic en Ajustes → Actualizaciones, con confirmación y comprobando antes Secure Boot, el espacio libre y que el equipo esté enchufado. `lekso-actualizar hardware detectar` muestra lo que hay.
+ `lekso-actualizar hardware quitar-nvidia` vuelve al controlador libre si el de NVIDIA da problemas.
~ Con el controlador de NVIDIA instalado, el escritorio arranca con `--unsupported-gpu`; sin eso, sway no arranca con ese controlador.
* Con Secure Boot activo no se instala el controlador de NVIDIA: el módulo sin firmar no cargaría. Aún no se puede registrar la clave desde aquí.

## Alpha 0.1.13 · 2026-11-16

~ Docker arranca bajo demanda: ya no se inicia con el equipo (retrasaba el arranque unos 6 segundos y ocupaba unos 135 MB siempre). Se pone en marcha solo con la primera orden `docker`.
~ Reiniciar y apagar ya no se quedan hasta dos minutos esperando a un servicio que no responde (pasaba con el ayudante de Bluetooth `mpris-proxy`): la espera máxima es de 20 segundos.

## Alpha 0.1.12 · 2026-11-16

+ Perfil de energía en la ventana de Energía: Ahorro, Equilibrado o Rendimiento, con lo que hace cada uno.
+ Modo juego (botón del mando en el carril, o `lekso-juego`): pone el perfil de rendimiento y quita la protección del núcleo que frena a algunos juegos de Windows; al apagarlo vuelve todo a como estaba. Se instala GameMode (en Steam: `gamemoderun %command%`).
~ `lekso-apps` dice en cada entrada si es «oficial» (el programa de su fabricante para Linux) o «alternativa» (otro programa, de terceros), y por qué. Antes se confundían. `--todo` ya solo instala lo oficial.
~ `lekso-apps` reconoce Playwright como instalado.

## Alpha 0.1.11 · 2026-11-16

~ Fase de pruebas: las versiones se publican sin firmar (`publicar-version.sh --sin-firma`). Solo las instalan los equipos que tienen `/etc/lekso/sin-firma`; los demás las rechazan.
+ Archivos de LekSO (`lekso-archivos`): el explorador en dos piezas que van juntas. A la izquierda, «Carpetas» (lugares habituales, dispositivos conectados y el árbol); en el centro, el contenido de la carpeta, que es lo que se ve cuando no hay ninguna aplicación abierta. Abrir una aplicación la pone encima, como una pestaña más. En español: abrir, copiar, cortar, pegar (sin pisar nada), renombrar, carpeta nueva, papelera, arrastrar y ver ocultos.
+ Las carpetas se pliegan y despliegan (botón de archivos del carril o Súper+E) para dar más sitio a la aplicación.
~ El explorador completo (pcmanfm-qt) sigue instalado para pestañas, miniaturas y discos; se abre desde el menú de aplicaciones.
~ Panel de la IA: el título de «lo que ha cambiado» ya no se pisa con el texto de debajo. La versión de la barra se refresca cada minuto.

## Alpha 0.1.10 · 2026-11-16

+ Permisos por asistente. Cada asistente (Claude, Codex) tiene los suyos, con casillas en la ventana «Asistentes de IA» (`lekso-asistentes`, o clic derecho en el botón del asistente): usarlo o no; archivos con permiso carpeta a carpeta o sin preguntar; ejecutar órdenes en el equipo con tu usuario; tareas de administrador (no, preguntando cada vez, sin preguntar). Tres niveles de un clic: «Solo archivos», «Este equipo» y «Acceso total».
+ La IA puede operar el equipo: herramienta `ejecutar` (también como administrador si se lo permites). Hace las cosas y cuenta el resultado, en vez de dictarte comandos. Cada orden queda en el registro del panel de la IA.
+ Varios asistentes activos a la vez, cada uno en su ventana.
~ Lo destructivo (borrar carpetas del sistema, formatear, contraseñas, apagar) pide confirmación siempre, sea cual sea el nivel. Es una red de seguridad para lo evidente, no una garantía.
~ Los permisos viven en `/etc/lekso/asistentes.json` y solo se cambian con tu contraseña: un asistente no puede dárselos a sí mismo. La identidad de cada asistente la da su propio canal, no lo que diga.
~ Instalación nueva: asistentes instalados, apagados y en «Solo archivos». La barra avisa («· admin») si alguno puede administrar.
* Aviso: con «Ejecutar órdenes» el asistente actúa con tu usuario y ve todos tus archivos; con «Acceso total», todo el equipo. Un texto malicioso en una web o un archivo podría manipularlo. Actívalo sabiendo eso.

## Alpha 0.1.9 · 2026-11-16

~ Barra: iconos para Wi-Fi, batería (con rayo al cargar y enchufe si está conectada) y volumen, en vez de «Wi-Fi 82%» o «BAT 99%». Los títulos largos ya no empujan los indicadores fuera de la pantalla, y las zonas fijas no aparecen como ventanas.
+ La versión de LekSO se ve en la barra y en el panel de la IA.
~ El estado de la IA muestra el asistente elegido («IA · Claude»), no solo los modelos locales. Clic: abre el panel.
+ El panel de la IA enseña también lo que ha consultado (leer, listar, medir el equipo), no solo lo que ha cambiado.
~ El asistente conoce los comandos propios de LekSO y los recomienda en vez de recetas genéricas de Linux.
~ Los títulos de las zonas ya no muestran sus nombres internos.

## Alpha 0.1.8 · 2026-11-16

+ `lekso-asistente`: elige tu asistente de IA. Claude y Codex vienen instalados pero inactivos; ninguno se usa hasta que lo activas (`lekso-asistente activar claude|codex`). El botón del asistente abre el activo o te deja elegir. `desactivar` lo apaga sin desinstalar.
+ La IA puede medir el equipo: herramienta `estado_equipo` (memoria, disco, CPU, carga, batería, temperaturas y procesos que más consumen). Solo lectura, sin permiso: da cifras y nombres de proceso, nunca archivos ni argumentos.
+ `lekso-codex`: Codex CLI dentro de la caja de IA, conectado al permisor.
~ La instalación incluye Node y los dos asistentes cuando hay conexión; sin red, se instalan al elegirlos.
~ `lekso-claude` avisa con claridad si Claude Code no está instalado, en vez de cerrarse sin explicación.

## Alpha 0.1.7 · 2026-11-16

+ Fase de pruebas en equipos reales: una imagen creada con `construir-iso.sh --fase-pruebas` instala un equipo que acepta actualizaciones sin exigir firma (`/etc/lekso/sin-firma`; se sigue exigiendo que la versión esté en la rama principal) y que arranca con el acceso remoto encendido en la red local. Borrar ese archivo vuelve a exigir firma.
~ El actualizador distingue «no encuentro la versión descargada» de «firma no válida».

## Alpha 0.1.6 · 2026-11-16

~ Los equipos instalados desde USB no podían actualizarse: su copia del repositorio apuntaba al paquete del USB. Ahora el actualizador descarga siempre del repositorio oficial y el instalador lo deja bien al terminar. En un equipo ya instalado con la 0.1.4 o la 0.1.5 desde USB, una sola vez: `sudo git -C /var/lib/lekso/repo remote set-url origin https://github.com/Leksgg/LekSO.git`.

## Alpha 0.1.5 · 2026-11-16

+ `lekso-acceso-remoto on|off|estado`: acceso por SSH a tu equipo, apagado por defecto. Encendido, solo acepta conexiones de la red local, nunca como root, y sobrevive a reinicios y actualizaciones hasta que lo apagues.
+ `scripts/instalador/crear-usb.ps1`: crea la memoria USB de instalación desde Windows. Comprueba la suma y la firma de la imagen, solo ofrece discos USB (nunca el del sistema), pide escribir BORRAR y graba la imagen tal cual.
+ `scripts/instalador/firmar-imagen.sh`: firma la imagen de instalación (suma SHA-256 y firma con la clave de versiones).

## Alpha 0.1.4 · 2026-11-15

+ `scripts/instalar.sh`: instala LekSO sobre un Debian 13 recién instalado. Descarga la versión más reciente (o la indicada), comprueba su firma con la clave incluida en el propio script (nunca con la del repositorio descargado), exige que el commit esté en la rama principal y pide confirmación. Acepta un origen local (`--origen`) para instalar desde un paquete del USB, y `--simular` para comprobarlo todo sin instalar.
+ Firmware y microcódigo según el hardware real (Wi-Fi, sonido, gráficos y control térmico en Intel; microcódigo en AMD), con detección automática de dispositivos. En una máquina virtual no se instala.
+ Instalador en USB que no necesita internet (`scripts/instalador/`): imagen de Debian 13 con firmware más el paquete de LekSO (repositorio local de 789 paquetes, 595 MB, creado con `construir-repo-offline.sh`) y una respuesta automática que borra el disco que elijas, lo cifra (LUKS + LVM), crea el intercambio para hibernar según la RAM (1,2 veces) e instala Debian y LekSO. Solo pregunta lo que decide quien instala: el disco, su usuario, su contraseña, la del cifrado y la confirmación final de borrado. `construir-iso.sh` genera la imagen; la versión que lleva se comprueba con su firma al instalar.
~ El instalador y el endurecimiento funcionan sin red y dentro del instalador de Debian (sin systemd en marcha).
+ `publicar-version.sh --sin-subir`: prepara y firma una versión en local sin publicarla, para probar el instalador antes de subirla.
~ El instalador en USB deja un registro de la instalación en `/var/log/lekso-postinstalar.log` y lleva también el servidor SSH en el repositorio local (solo se usa en las imágenes de prueba).
+ Pruebas del instalador (`scripts/test_instalar.py`): elección de versión, firma buena, de otra clave, sin firmar, huella distinta, commit fuera de la rama principal y una clave de atacante metida en el repositorio.

## Alpha 0.1.3 · 2026-11-15

~ Las teclas de micrófono y brillo avisan cuando el equipo no tiene micrófono o brillo regulable, y la captura de ventana avisa si no hay ninguna activa, en vez de no hacer nada.
+ Cuando la IA pide permiso aparece una notificación («La IA pide permiso», con la carpeta y lo que quiere hacer); al pulsarla se abre el panel donde se aprueba. Antes la petición esperaba en una pestaña que nadie estaba mirando y el asistente parecía bloqueado.
~ El foco del teclado va a la ventana donde haces clic, no a donde se queda el ratón (antes, con el ratón sobre otra ventana, el teclado «no respondía» en la que estabas mirando).
~ El asistente ya no pregunta «¿confías en esta carpeta?» en cada inicio: su carpeta de trabajo, vacía y solo suya, se marca de confianza.
+ La IA puede pedir una carpeta nueva (un nivel, dentro de una que exista): el panel la marca como «carpeta NUEVA: se creará», se crea solo al aprobar y se puede deshacer si sigue vacía. La carpeta personal entera sigue sin poder pedirse.
* El asistente de IA no sabía cuál era la carpeta personal real: veía la de su caja (`/home/caja`) y pedía rutas que el permisor no reconocía. Ahora el adaptador traduce `~/…` y `/home/caja/…` a la carpeta real, y las instrucciones al modelo se lo explican (también que `escribir` crea las carpetas que falten).
~ El reposo bloquea a los 10 minutos, apaga la pantalla a los 15 y suspende a los 30 (solo con batería), en vez de 5, 10 y 25.
~ Pantalla de bloqueo con un mensaje claro («Pantalla bloqueada · escribe tu contraseña y pulsa Intro») y el anillo de contraseña siempre visible: antes era una pantalla oscura vacía y parecía un equipo colgado.

## Alpha 0.1.2 · 2026-11-15

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
