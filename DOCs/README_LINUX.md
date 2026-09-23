# Versión Linux (rama `linux-port`)

Port a Fedora KDE Plasma (Wayland). El resto de `DOCs/` describe la versión
Windows; este archivo describe solo lo que difiere en Linux.

## Qué funciona

| Funcionalidad | Estado |
|---|---|
| Indicador de capas (círculo grande arriba-centro, punto chico fijo al centro) | Activo |
| Calibración de Mouse Keys (`utils/qmk_calibracion`) | Activo |
| Reconexión automática al Corne tras desconexión/suspensión | Activo |

## Qué está deshabilitado y por qué

| Funcionalidad | Motivo |
|---|---|
| Scroll Lock (F15) y toggle de indicadores (F21) | La librería `keyboard` exige root en Linux |
| Alt-Tab reset | Requiere `keyboard`/`mouse` (root) |
| Wrap-around del cursor | Usa `ctypes.windll`, sin puerto a Linux |
| Captura (Win+Shift+S) | Vigila el overlay de Snipping Tool de Windows |
| OneNote Nav | Usa `ctypes.windll` (import protegido, no crashea) |
| Ocultar indicador cerca del mouse | `pyautogui.position()` no lee el cursor real bajo Wayland |
| Punto chico siguiendo al mouse | Mismo motivo: quedó fijo al centro de la pantalla |

Están comentados en `main()` de `layer_status_script.py`, no borrados.

## Diferencias técnicas respecto a Windows

- **Interfaz HID:** el Corne expone 3 interfaces con el mismo VID/PID. Se usa la
  raw HID de QMK (`usage_page == 0xFF60`); en Linux `hid.enumerate()` no la
  devuelve primero.
- **Instancia única:** `flock` sobre `/tmp/layer_status_script.lock` (en Windows, mutex).
- **Ventanas:** opacas con fondo magenta; `-transparentcolor` no existe en Tk/X11.
- **Posición:** KWin no respeta la geometría pedida antes de mapear la ventana
  `overrideredirect`, por eso se reaplica en cada `deiconify()`.

## Instalación

Dependencias Python: `pip install --user hid pyautogui keyboard mouse`
(`hid` viene con `pip install qmk`). Sistema: `hidapi`, `python3-tkinter`.

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
