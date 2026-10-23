# Versión Linux (rama `linux-port`)

Port a Fedora KDE Plasma (Wayland). El resto de `DOCs/` describe la versión
Windows; este archivo describe solo lo que difiere en Linux.

## Qué funciona

| Funcionalidad                                                       | Estado |
| ------------------------------------------------------------------- | ------ |
| Indicador de capas (círculo grande arriba-centro)                   | Activo |
| Punto chico que sigue al cursor (posición real vía KWin, ver abajo) | Activo |
| Calibración de Mouse Keys (`utils/qmk_calibracion`)                 | Activo |
| Reconexión automática al Corne tras desconexión/suspensión          | Activo |
| Wrap-around del cursor (salto de borde a borde, ver abajo)          | Activo |
| Marca de scroll en Konsole (cuadrado que sigue al texto, ver abajo) | Activo |
| Punto chico sobre el cursor de texto en Konsole (ver abajo)         | Activo |

## Qué está deshabilitado y por qué

| Funcionalidad                                   | Motivo                                                    |
| ----------------------------------------------- | --------------------------------------------------------- |
| Scroll Lock (F15) y toggle de indicadores (F21) | La librería `keyboard` exige root en Linux                |
| Alt-Tab reset                                   | Requiere `keyboard`/`mouse` (root)                        |
| Captura (Win+Shift+S)                           | Vigila el overlay de Snipping Tool de Windows             |
| OneNote Nav                                     | Usa `ctypes.windll` (import protegido, no crashea)        |
| Ocultar indicador cerca del mouse               | `pyautogui.position()` no lee el cursor real bajo Wayland |
| Punto chico siguiendo al mouse                  | Mismo motivo: quedó fijo al centro de la pantalla         |

Están comentados en `main()` de `layer_status_script.py`, no borrados.

## Seguimiento del cursor (punto chico)

Bajo Wayland, `pyautogui`/Tk no pueden leer la posición global del cursor
(devuelven un valor obsoleto). KWin sí la conoce, así que `utils/cursor_kwin`:

1. registra el servicio D-Bus `org.statusscript.Cursor` (vía `Gio`, paquete `python3-gobject`),
2. carga en KWin el script QML `linux/kwin/CursorPos.qml`, que envía `Workspace.cursorPos`
   por D-Bus ~60 veces por segundo,
3. `seguimiento_mouse()` mueve el punto chico a esa posición (22 px bajo el cursor).

Al cerrar, el script de KWin se descarga solo. Detalle importante: KWin cachea el
listado de la carpeta y el QML compilado por ruta, y falla con
`File name case mismatch` con archivos nuevos o modificados; por eso el QML se
copia a una carpeta temporal nueva en cada arranque (`$XDG_RUNTIME_DIR`).

## Wrap-around del cursor

Al empujar el cursor contra un borde de la pantalla aparece en el borde opuesto
(los cuatro bordes). `utils/wrap_around` es una reescritura para Linux, no usa el
código de Windows que describe [`wrap_around.md`](wrap_around.md).

1. **Empuje:** el mismo script de KWin (`linux/kwin/CursorPos.qml`) reserva los
   cuatro bordes con `ScreenEdgeHandler`. En un borde reservado KWin rebota el
   cursor 1 px mientras se empuja, y eso se ve en cada muestra del cursor como
   empuje real. Un cursor quieto, un movimiento solo a lo largo del borde o un
   botón presionado (seleccionar, arrastrar) no generan empuje.
2. **Validación:** un empuje es una racha de muestras con empuje contra el mismo
   borde. Se salta cuando la racha lleva `RESISTENCIA_MS` y en ese último lapso el
   cursor casi no se movió a lo largo del borde. Mientras se recorren íconos no
   salta; al frenar y empujar de frente, sí. Las esquinas no saltan.
3. **Salto:** un puntero absoluto virtual (`/dev/uinput`, paquete `python3-evdev`)
   lleva el cursor al otro lado.

Parámetros en `utils/wrap_around/__init__.py`:

| Parámetro            | Valor  | Efecto                                                                 |
| -------------------- | ------ | ---------------------------------------------------------------------- |
| `HABILITADA`         | `True` | Bandera maestra                                                        |
| `RESISTENCIA_MS`     | 90     | Empuje sostenido necesario para saltar                                 |
| `TOLERANCIA_LATERAL` | 15 px  | Recorrido máximo a lo largo del borde en ese lapso (~170 px/s)         |
| `PAUSA_MAX`          | 0.06 s | Pausa sin empuje que corta la racha                                    |
| `COOLDOWN`           | 0.5 s  | Tiempo mínimo entre saltos                                             |
| `INSET`              | 15 px  | Distancia al borde opuesto donde aterriza el cursor                    |
| `RETARDO_KWIN_MS`    | 60000  | Valor esperado de `ElectricBorderDelay` de KWin (ver Instalación)      |

Guía de ajuste (cada salto, y cada empuje largo que no saltó, queda en el journal
como `[WRAP]` con la duración y el recorrido lateral medidos):

| Síntoma                          | Ajuste                   |
| -------------------------------- | ------------------------ |
| Salta al recorrer íconos         | ↓ `TOLERANCIA_LATERAL`   |
| No salta aunque empujo de frente | ↑ `TOLERANCIA_LATERAL`   |
| Salta demasiado fácil            | ↑ `RESISTENCIA_MS`       |
| Hay que empujar mucho tiempo     | ↓ `RESISTENCIA_MS`       |

Aviso visual opcional: con `AVISO_WRAP = True` en `layer_status_script.py` el punto
chico se pone blanco mientras se arma el salto. Está apagado (`False`).

El efecto «Screen Edge» de KWin (el resplandor azul al acercarse a un borde reservado)
está desactivado: `screenedgeEnabled=false` en el grupo `[Plugins]` de `kwinrc`.

`ElectricBorderDelay` va en 60 s para que KWin nunca active sus propios bordes:
al activarlos deja de rebotar el cursor un instante y el empuje se vuelve
irregular. Es un ajuste global, así que **las esquinas y bordes activos de KWin
(Vista general en la esquina superior izquierda, y los de Preferencias del sistema →
Bordes de pantalla) dejan de funcionar con el puntero**. El mosaico al arrastrar
ventanas contra un borde no cambia. Asume una sola pantalla.

## Marca de scroll en Konsole

Al hacer scroll con la rueda del Corne en una ventana de Konsole aparece un
cuadrado blanco en el margen izquierdo, sobre la **última fila de texto visible**
(el pie de la página que se estaba leyendo). Cada paso de rueda lo mueve igual que
el texto, así queda sobre esa misma línea y indica dónde seguir. Si sale de la ventana queda pegado al borde y se pone
rojo. Sin scroll por 3 s desaparece y el siguiente scroll empieza otra vez desde
el ancla. Es el módulo `utils/marca_scroll`.

1. **Pasos de rueda:** `evdev` lee la interfaz de mouse del Corne (`/dev/input/event7`
   hoy; se busca por nombre). Necesita `linux/71-corne-wheel.rules`, que da acceso
   solo a esa interfaz y no al teclado. Sin la regla el servicio avisa en el log
   (`sin acceso a la rueda del Corne`) y la marca no hace nada.
2. **Ventana activa:** `linux/kwin/CursorPos.qml` envía por D-Bus la clase y la
   geometría de la ventana activa (`ventana`, ~5 por segundo). KWin las manda como
   `double`: la interfaz de `utils/cursor_kwin` debe declararlas así.
3. **Dibujo:** `CuadradoARGB` (`utils/indicador_argb`), desde el hilo de Tk.

Parámetros en `utils/marca_scroll/__init__.py`:

| Parámetro                       | Valor          | Efecto                                                           |
| ------------------------------- | -------------- | ---------------------------------------------------------------- |
| `HABILITADA`                    | `True`         | Bandera maestra                                                  |
| `APPS`                          | `("konsole",)` | Fragmentos de la clase de ventana donde actúa                    |
| `LINEAS_POR_PASO`, `ALTO_LINEA` | 3, 18 px       | Líneas que mueve Qt por paso y alto de línea (ver abajo)         |
| `ORIGEN_TEXTO`                  | 114 px         | Distancia del borde superior de la ventana a la 1ª fila de texto |
| `ANCLA_X`, `TAM`                | 3 px, 14 px    | Posición horizontal y tamaño                                     |
| `COLOR`, `COLOR_FUERA`          | blanco, rojo   | Dentro de la ventana / pegado al borde                           |
| `INACTIVIDAD`                   | 3 s            | Tiempo sin scroll para ocultarla                                 |

El desplazamiento por paso no es fijo: `px_por_paso()` lo calcula al armar la marca como
`LINEAS_POR_PASO × ScrollFactor × ALTO_LINEA`, leyendo el `ScrollFactor` del Corne en
`~/.config/kcminputrc` (grupo `[Libinput][18003][1][foostan Corne]`). Si cambias el factor
la marca se adapta sola (en el siguiente scroll tras una pausa). Verificado con capturas
en Kate y Konsole: factor 5 → 270 px por paso, factor 3 → 162 px (lineal, igual hacia arriba
y abajo). Solo hay que recalibrar si cambia el tamaño de letra (`ALTO_LINEA`).

Una pulsación del Corne manda 3 pasos de rueda (a 0, +10 y +90 ms; mantenida, sigue cada
~80 ms). Los pasos salen del firmware (`MOUSEKEY_WHEEL_*` de `config.h` y los valores por
defecto de QMK; los parámetros que envía `qmk_calibracion` son del movimiento del cursor,
no de la rueda) y el factor de KDE los amplifica después: se multiplican. Con factor 3, una
pulsación mueve 486 px. La marca cuenta los pasos reales, así que sigue cualquier cambio
del firmware. Cada rueda recibida queda en el journal como `[MARCA]`, con la ventana
activa que vio el servicio.

El ancla es el centro de la última fila completa: `centro_ultima_fila()` reparte la
ventana en filas de `ALTO_LINEA` desde `ORIGEN_TEXTO` (lo que sobra queda como margen
abajo, así que no es una distancia fija al borde). Validado con capturas en ventanas de
1154 y 1000 px de alto: tras una pulsación (486 px) la marca queda a ±0,5 px de la línea
que era la última visible. Si cambias las barras de Konsole, ajusta `ORIGEN_TEXTO`.

Límites: solo la ventana **activa** (la rueda va a la ventana bajo el puntero, que
puede ser otra); no sabe cuándo el texto llegó a su tope, así que la marca se
mueve aunque el texto no; solo el Corne (otros ratones no pasan por aquí).

## Punto sobre el cursor de texto (Konsole)

En un terminal el puntero del mouse se oculta al escribir y el punto chico, que sigue
al puntero, no se ve. Con Konsole como ventana activa el punto se pone en el cursor de
texto (más chico que sobre el mouse, 12 px en vez de 20, y 6 px bajo su celda; `PUNTO_TEXTO` y `OFFSET_TEXTO` en `layer_status_script.py`); en cualquier otra ventana vuelve a seguir al mouse. Es el
módulo `utils/cursor_texto`. Sirve también con Claude Code, que deja el cursor nativo
del terminal en el punto de escritura.

1. **Cursor:** Konsole expone el terminal por AT-SPI como un widget `Text`; de ahí salen
   el offset del cursor y el rectángulo de su celda (relativo al widget). `python3-gobject`
   ya trae `Atspi`. Cada consulta cuesta ~0,3 ms; se hacen ~30 por segundo en un proceso ayudante (punto 5).
2. **Posición en pantalla:** Wayland no da posición global, así que se suma la geometría
   de la ventana activa que envía KWin (`cursor_kwin.ventana()`), el origen del widget y
   `TITULO_SSD` + `MARGEN_X` (ver tabla).
3. **Foco, pestañas y paneles:** se guardan todos los terminales de todas las ventanas de
   Konsole y en cada consulta se revisa cuál tiene el foco (solo lo tiene uno, el de la
   ventana activa), así el punto sigue al panel enfocado sin esperar nada. Si ninguno lo
   tiene (panel, pestaña o ventana nuevos) se recorre otra vez el árbol de AT-SPI, como
   máximo una vez por segundo. Si el foco está fuera del terminal (p. ej. la barra de
   búsqueda) el punto vuelve al mouse.
4. **Paneles divididos:** cada panel lleva una barra de título que AT-SPI no descuenta (el
   widget y su contenedor reportan el mismo rectángulo), así que con más de un panel
   visible en la ventana se suman `CABECERA_PANEL` px. Validado con capturas en división
   izquierda/derecha y arriba/abajo anidadas: el punto queda centrado bajo el cursor del
   panel enfocado, igual que con un solo panel.
5. **Proceso ayudante:** las consultas a AT-SPI corren en otro proceso
   (`python3 -m utils.cursor_texto`), no en un hilo del indicador. `libatspi` llegó a
   corromper la memoria cuando Konsole tardó en responder (al bloquear la sesión) y
   tumbó el script entero; aparte, solo cae el ayudante. El principal le manda por stdin
   el origen de la ventana activa si es Konsole, y el ayudante responde por stdout una
   línea por ciclo (`x y`, o `-` sin cursor), que sirve también de señal de vida. Si el
   pipe se cierra (murió) o pasan `SIN_RESPUESTA` s sin líneas (se colgó), el principal
   lo mata y lo relanza tras `RELANZAR` s; mientras, el punto sigue al mouse. En el log:
   `[CURSOR-TEXTO] el ayudante terminó (código …)`.

Parámetros en `utils/cursor_texto/__init__.py`:

| Parámetro        | Valor          | Efecto                                                        |
| ---------------- | -------------- | ------------------------------------------------------------- |
| `HABILITADA`     | `True`         | Bandera maestra                                               |
| `APPS`           | `("konsole",)` | Fragmentos de la clase de ventana donde actúa                 |
| `INTERVALO`      | 0,033 s        | Tiempo entre consultas                                        |
| `TITULO_SSD`     | 29 px          | Barra de título de KWin sobre el área de cliente              |
| `MARGEN_X`       | 4 px           | Margen interno del widget que AT-SPI no incluye               |
| `CABECERA_PANEL` | 22 px          | Barra de título de cada panel cuando la ventana está dividida |
| `REBUSCAR`       | 1 s            | Mínimo entre recorridos del árbol de AT-SPI (~60 ms cada uno) |
| `SIN_RESPUESTA`  | 3 s            | Silencio del ayudante tras el que se lo da por colgado        |
| `RELANZAR`       | 2 s            | Espera antes de relanzar el ayudante                          |

`TITULO_SSD` y `MARGEN_X` se calibraron con capturas (el punto queda centrado bajo el
bloque del cursor, ±1 px). Si cambias el tema de ventanas o el margen del perfil de
Konsole, hay que recalibrarlos.

**Requiere accesibilidad activa en Konsole.** Qt solo publica el árbol de AT-SPI si se
arranca con `QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1`. Se activa solo para Konsole con un
lanzador de usuario (no toca el resto de apps):

```sh
sed -E 's/^Exec=konsole/Exec=env QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1 konsole/' \
  /usr/share/applications/org.kde.konsole.desktop > ~/.local/share/applications/org.kde.konsole.desktop
```

Hay que **cerrar todas las ventanas de Konsole** y abrirlo de nuevo desde el lanzador (un
Konsole ya abierto absorbe las ventanas nuevas y seguiría sin accesibilidad). Si el
servicio ve a Konsole sin el árbol, avisa una vez en el log:
`[CURSOR-TEXTO] Konsole no aparece en AT-SPI`. Para revertir, borrar ese `.desktop`.

Límites: solo Konsole (apps que dibujan su propio terminal, como Alacritty o kitty, no
exponen el cursor); con scroll en el historial el cursor queda fuera de la vista y el
punto vuelve al mouse; como el punto solo se muestra con una capa activa del Corne, en
`LAYER_BASE` tampoco aparece sobre el cursor de texto; asume pantalla única sin escalado.

## Diferencias técnicas respecto a Windows

- **Interfaz HID:** el Corne expone 3 interfaces con el mismo VID/PID. Se usa la
  raw HID de QMK (`usage_page == 0xFF60`); en Linux `hid.enumerate()` no la
  devuelve primero.
- **Instancia única:** `flock` sobre `/tmp/layer_status_script.lock` (en Windows, mutex).
- **Ventanas:** círculos con fondo transparente real (`utils/indicador_argb`). `-transparentcolor`
  no existe en Tk/X11 y el recorte con la extensión Shape no se respeta bajo XWayland
  (queda el cuadrado de fondo), así que son ventanas X11 propias de 32 bits (ARGB) dibujadas
  con `python-xlib`. Los clics las atraviesan. Bordes sin suavizado.

## Instalación

Dependencias Python: `pip install --user hid pyautogui keyboard mouse`
(`hid` viene con `pip install qmk`). Sistema: `hidapi`, `python3-tkinter`, `python3-gobject`, `python3-evdev`, `qt6-qttools` (`qdbus-qt6`, solo para depurar).

Archivos en `linux/` de este repo:

```sh
# Permiso de acceso al Corne sin root (regla udev)
sudo cp linux/70-corne-hid.rules /etc/udev/rules.d/
sudo cp linux/71-corne-wheel.rules /etc/udev/rules.d/   # rueda del Corne (marca de scroll)
sudo udevadm control --reload-rules && sudo udevadm trigger

# Servicio de usuario (arranque automático al iniciar sesión)
mkdir -p ~/.config/systemd/user
cp linux/status-script.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now status-script.service
```

El servicio asume el repo en `~/dev/status_script`.

Para el wrap-around, que KWin no active sus propios bordes (ver arriba qué implica):

```sh
kwriteconfig6 --file kwinrc --group Windows --key ElectricBorderDelay 60000
qdbus-qt6 org.kde.KWin /KWin org.kde.KWin.reconfigure
```

## Operación

```sh
systemctl --user status status-script.service
systemctl --user restart status-script.service
journalctl --user -u status-script.service -f
```

## Problemas conocidos

- **El indicador no aparece:** revisar `journalctl`; si hay un `[HID ERROR]`,
  el Corne se desconectó y el script se reconecta solo en ~2 s. Si el servicio
  está caído, `restart`.
- **Aparece y desaparece en LAYER_BASE:** es lo esperado, el indicador solo se
  muestra en capas con color asignado.
- **`Permission denied` en `/dev/hidraw*`:** falta la regla udev.
- **El wrap no salta:** revisar en el journal `WRAP-AROUND: activo`. Si dice que no
  pudo crear el puntero virtual, falta permiso sobre `/dev/uinput` o `python3-evdev`.
  Si avisa de `ElectricBorderDelay`, repetir el paso de Instalación.
- **El punto chico no sigue al mouse:** revisar en el journal la línea
  `[CURSOR] script de KWin cargado`; verificar mensajes con
  `dbus-monitor "interface='org.statusscript.Cursor'"` (deben ser ~60/s).
