"""
cursor_kwin — Posición real del cursor bajo KDE Plasma Wayland.

En Wayland las apps X11 (XWayland) no pueden leer la posición global del
cursor (pyautogui/Tk devuelven un valor obsoleto). KWin sí la conoce, así que
se carga un script QML (linux/kwin/CursorPos.qml) que la envía por D-Bus ~60
veces por segundo a este módulo, que expone el último valor con ``get()``.

Uso:
    from utils import cursor_kwin
    cursor_kwin.start()
    pos = cursor_kwin.get()   # (x, y) o None si aún no llegó ninguna
"""

import atexit
import logging
import os
import shutil
import tempfile
import threading

import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

logger = logging.getLogger(__name__)

BUS_NAME = "org.statusscript.Cursor"
OBJ_PATH = "/Cursor"
IFACE = "org.statusscript.Cursor"
SCRIPT_NAME = "statusscript-cursor"
QML_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "linux", "kwin", "CursorPos.qml"
)

_XML = f"""
<node>
  <interface name='{IFACE}'>
    <method name='pos'>
      <arg type='i' direction='in' name='x'/>
      <arg type='i' direction='in' name='y'/>
    </method>
  </interface>
</node>
"""

_pos = None
_conn = None


def get():
    """Última posición (x, y) recibida de KWin, o None."""
    return _pos


def _on_method_call(conn, sender, path, iface, method, params, invocation):
    global _pos
    if method == "pos":
        _pos = tuple(params.unpack())
    invocation.return_value(None)


def _kwin_call(method, args, path="/Scripting", iface="org.kde.kwin.Scripting"):
    return _conn.call_sync(
        "org.kde.KWin", path, iface, method, args, None,
        Gio.DBusCallFlags.NONE, 2000, None,
    )


_tmpdir = None


def _load_qml():
    # KWin cachea el listado de la carpeta y el QML compilado por ruta: si el
    # archivo es nuevo o cambió, falla con "File name case mismatch". Se copia a
    # una carpeta temporal nueva en cada arranque para evitarlo.
    global _tmpdir
    _tmpdir = tempfile.mkdtemp(prefix="statusscript-", dir=os.environ.get("XDG_RUNTIME_DIR"))
    qml = os.path.join(_tmpdir, "CursorPos.qml")
    shutil.copy(os.path.abspath(QML_PATH), qml)
    try:
        _kwin_call("unloadScript", GLib.Variant("(s)", (SCRIPT_NAME,)))
        res = _kwin_call("loadDeclarativeScript", GLib.Variant("(ss)", (qml, SCRIPT_NAME)))
        script_id = res.unpack()[0]
        _kwin_call("run", None, path=f"/Scripting/Script{script_id}", iface="org.kde.kwin.Script")
        logger.info("[CURSOR] script de KWin cargado (id=%s)", script_id)
    except Exception as e:
        logger.error("[CURSOR] no se pudo cargar el script de KWin: %s", e)


def _unload_qml():
    try:
        _kwin_call("unloadScript", GLib.Variant("(s)", (SCRIPT_NAME,)))
    except Exception:
        pass
    if _tmpdir:
        shutil.rmtree(_tmpdir, ignore_errors=True)


def _on_bus_acquired(conn, name):
    global _conn
    _conn = conn
    node = Gio.DBusNodeInfo.new_for_xml(_XML)
    conn.register_object(OBJ_PATH, node.interfaces[0], _on_method_call, None, None)


def _on_name_acquired(conn, name):
    _load_qml()


def _on_name_lost(conn, name):
    logger.error("[CURSOR] no se pudo registrar %s en D-Bus", name)


def _run():
    Gio.bus_own_name(
        Gio.BusType.SESSION, BUS_NAME, Gio.BusNameOwnerFlags.NONE,
        _on_bus_acquired, _on_name_acquired, _on_name_lost,
    )
    GLib.MainLoop().run()


def start():
    threading.Thread(target=_run, daemon=True).start()
    atexit.register(_unload_qml)
