# Changelog

Formato: `+` nuevo · `-` eliminado o retirado · `~` modificado · `*` otros.
Lo más reciente, arriba.

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
