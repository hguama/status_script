# Instrucciones para agentes de IA

> ⚠️ Leer antes de trabajar en este proyecto.

Las skills están en `~/.agents/skills/`. Si vas a gestionar el plan de
trabajo, usa la skill `task-manager` (`~/.agents/skills/task-manager/SKILL.md`)
— si no se activa sola, leerla directamente desde ahí antes de continuar.

## Dos variantes del script

| Variante | Rama | Sistema | Funcionalidades |
|---|---|---|---|
| **Windows** | `main` | Windows | Todas |
| **Linux** | `linux-port` | Fedora KDE (Wayland) | Reducidas (solo indicador de capas + calibración QMK) |

**Toda la documentación de `DOCs/` (excepto `DOCs/README_LINUX.md`) describe la
versión Windows.** Antes de tocar código, confirmar en qué rama se está.

### Funcionalidades de la versión Windows (`main`)

- Indicador de capas del Corne (círculo grande arriba-centro + punto que sigue al mouse)
- Calibración de Mouse Keys vía HID raw (`utils/qmk_calibracion`)
- Wrap-around del cursor (`utils/wrap_around`)
- Scroll Lock por gesto (`utils/scroll_lock.py`, hotkey Ctrl+Shift+F15)
- Alt-Tab reset (libera Alt al hacer clic con el menú de Alt-Tab abierto)
- Captura con Win+Shift+S (`utils/captura`)
- Integración con OneNote 2016 (`utils/onenote_nav.py`)
- Toggle de indicadores con F21
- Ocultar indicador cuando el mouse está cerca
- Arranque: `start_status_silent.vbs` (silencioso) / `restart_status_test.bat` (pruebas)

### Versión Linux (`linux-port`)

Solo indicador de capas + calibración QMK, con reconexión automática si el
Corne se desconecta. El resto se deshabilitó porque depende de APIs de Windows
(`ctypes.windll`) o exige root (`keyboard`/`mouse`). Detalle completo en
[`DOCs/README_LINUX.md`](DOCs/README_LINUX.md).

Archivo a ejecutar: `layer_status_script.py` (raíz del repo). En Linux corre
como servicio de usuario de systemd (`status-script.service`) y arranca solo al
iniciar sesión:

```sh
systemctl --user status status-script.service    # ver estado
systemctl --user restart status-script.service   # reiniciar (tras editar el código o si el indicador no aparece)
systemctl --user stop status-script.service      # detener
journalctl --user -u status-script.service -f    # logs en vivo
```

Ejecución manual (sin servicio; detener el servicio antes):
`python3 layer_status_script.py`
