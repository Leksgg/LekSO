# Changelog

Formato: `+` nuevo · `-` eliminado o retirado · `~` modificado · `*` otros.
Lo más reciente, arriba.

## 2026-11-15 · Dispositivos y nombres de ventana

+ Pendrives y discos: automontaje (también NTFS y exFAT) desde el explorador.
+ Soporte de cámaras, listado de USB y Bluetooth instalados.
+ Volumen: indica el dispositivo activo; clic abre el mezclador, clic derecho silencia, la rueda sube o baja.
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
