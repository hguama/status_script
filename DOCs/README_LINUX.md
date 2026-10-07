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
