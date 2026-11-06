"""
turbo_trackball — Turbo de los trackballs al sostener la tecla de _AI del Corne.

La velocidad normal de cada trackball es la de precisión y no pasa por aquí.
Mientras el Corne está en la capa _AI (sostener la tecla del meñique izquierdo,
LT(_AI, MOVE_WIN_TG), o la del derecho, LT(_AI, MOVE_TG)), el módulo toma cada
trackball (grab de evdev) y reenvía sus movimientos multiplicados por un
dispositivo virtual (uinput). Los clics y la rueda pasan sin cambio. Al soltar
la tecla, suelta el trackball y vuelve a ir directo al sistema.

- Cada virtual copia los ajustes de KWin de su trackball real (velocidad,
  perfil, rueda…), así el turbo es la velocidad normal × el factor.
- Con un botón apretado (arrastre) no cambia de modo hasta soltarlo, para no
  dejar un clic pegado.
- Si el script se cae, el kernel suelta los trackballs solos.
- Si un trackball se desconecta (se duerme), lo vuelve a tomar al reaparecer.

Necesita leer los trackballs: linux/72-trackball-turbo.rules en
/etc/udev/rules.d/. Origen: tarea 23 del firmware (spec-turbo-trackball.md).

Uso:
    from utils import turbo_trackball
    turbo_trackball.iniciar()                 # arranca en un hilo propio
    turbo_trackball.set_capa(clave)           # desde actualizar_ui
"""

import logging
import subprocess
import threading
import time

logger = logging.getLogger(__name__)

HABILITADA = True

# Clave de capa (la de `colores` en layer_status_script.py) que enciende el turbo.
CAPA_TURBO = "AI"

# Por trackball, con el nombre exacto que da el sistema:
#   "normal": velocidad normal de KDE (−1 … 1; 1 es el máximo). Se aplica al
#             arrancar. None = no tocar la que tenga KDE.
#   "turbo":  (horizontal, vertical) — factores mientras se sostiene _AI.
# Horizontal 6,4 = 4 × 1,6 (la pantalla 1920×1200 es 1,6 veces más ancha que
# alta); vertical 8, porque girar la bola en vertical cuesta más con el pulgar.
TRACKBALLS = {
    "Logitech ERGO M575": {
        "normal": 1.0,
        "turbo": (6.4, 8.0),
    },
    "Kensington Expert Wireless TB Mouse": {
        "normal": 1.0,
        "turbo": (6.4, 8.0),
    },
}

INTERVALO_BUSQUEDA = 3.0     # s entre búsquedas de trackballs que falten

# Ajustes de KWin que se copian del trackball real a su virtual.
_PROPIEDADES = [("pointerAcceleration", "d"), ("pointerAccelerationProfileAdaptive", "b"),
                ("pointerAccelerationProfileFlat", "b"), ("scrollFactor", "d"),
                ("naturalScroll", "b"), ("leftHanded", "b"), ("middleEmulation", "b")]

_turbo_pedido = False
_activos = {}                # nombre → _Turbo, de los trackballs conectados
_virtuales = {}              # nombre → UInput, se reutiliza al reconectar


def log_configuracion():
    estado = "ACTIVO" if HABILITADA else "INACTIVO"
    logger.info("├─ TURBO-TRACKBALL  [%s]  capa = %s", estado, CAPA_TURBO)
    for nombre, cfg in TRACKBALLS.items():
        fx, fy = cfg["turbo"]
        normal = "sin tocar" if cfg["normal"] is None else f"{cfg['normal']:g}"
        logger.info("│  %s: normal %s  |  turbo horizontal ×%g, vertical ×%g", nombre, normal, fx, fy)


def set_capa(clave):
    """Lo llama actualizar_ui con la clave de la capa activa ('' si el Corne se fue)."""
    global _turbo_pedido
    pedido = clave == CAPA_TURBO
    if pedido != _turbo_pedido:
        _turbo_pedido = pedido
        logger.debug("[TURBO] %s", "pedido" if pedido else "apagado")


# ------------------------------------------------------------------ KWin
def _kwin(*args):
    return subprocess.run(["busctl", "--user", *args], capture_output=True, text=True)


def _kwin_rutas():
    """nombre exacto → ruta D-Bus de cada dispositivo de entrada de KWin."""
    salida = _kwin("tree", "org.kde.KWin", "--list").stdout
    rutas = {}
    for ruta in salida.split():
        if "/InputDevice/event" in ruta:
            r = _kwin("get-property", "org.kde.KWin", ruta, "org.kde.KWin.InputDevice", "name")
            if r.returncode == 0 and r.stdout.startswith('s "'):
                rutas[r.stdout.strip()[3:-1]] = ruta
    return rutas


def _kwin_get(ruta, prop):
    r = _kwin("get-property", "org.kde.KWin", ruta, "org.kde.KWin.InputDevice", prop)
    return r.stdout.split()[1] if r.returncode == 0 else None


def _kwin_set(ruta, prop, tipo, valor):
    _kwin("set-property", "org.kde.KWin", ruta, "org.kde.KWin.InputDevice", prop, tipo, str(valor))


def _ajustar_kwin(nombre, nombre_virtual):
    """Aplica la velocidad normal al real y copia sus ajustes al virtual."""
    for _ in range(20):                # KWin tarda un instante en ver un virtual nuevo
        rutas = _kwin_rutas()
        if nombre in rutas and nombre_virtual in rutas:
            break
        time.sleep(0.2)
    real, virtual = rutas.get(nombre), rutas.get(nombre_virtual)
    if not real:
        logger.warning("[TURBO] %s: KWin no lo ve; sin ajustes.", nombre)
        return
    normal = TRACKBALLS[nombre]["normal"]
    if normal is not None:
        _kwin_set(real, "pointerAcceleration", "d", normal)
    if not virtual:
        logger.warning("[TURBO] %s: KWin no ve el virtual; queda con ajustes de fábrica.", nombre)
        return
    for prop, tipo in _PROPIEDADES:
        valor = _kwin_get(real, prop)
        if valor is not None:
            _kwin_set(virtual, prop, tipo, valor)


# ------------------------------------------------------------------ trackballs
class _Turbo:
    def __init__(self, tb, ui):
        from evdev import ecodes as e
        self.e = e
        self.tb, self.ui = tb, ui
        fx, fy = TRACKBALLS[tb.name]["turbo"]
        self.factores = {e.REL_X: fx, e.REL_Y: fy}
        self.activo = False
        self.resto = {e.REL_X: 0.0, e.REL_Y: 0.0}

    def bucle(self):
        e, tb, ui = self.e, self.tb, self.ui
        try:
            while True:
                # Cambiar de modo solo sin botones apretados, para no dejar un clic pegado.
                if _turbo_pedido != self.activo and not tb.active_keys():
                    try:
                        tb.grab() if _turbo_pedido else tb.ungrab()
                    except OSError as err:
                        if err.errno != 16:          # EBUSY: otro programa lo tiene tomado
                            raise
                        logger.warning("[TURBO] %s: ocupado por otro programa.", tb.name)
                        time.sleep(1)
                        continue
                    self.activo = _turbo_pedido
                    self.resto = {e.REL_X: 0.0, e.REL_Y: 0.0}
                    logger.debug("[TURBO] %s: %s", tb.name, "ENCENDIDO" if self.activo else "apagado")

                ev = tb.read_one()
                if ev is None:
                    time.sleep(0.002)
                    continue
                if not self.activo:
                    continue                   # el sistema ya lo recibe directo
                if ev.type == e.EV_REL and ev.code in self.resto:
                    v = ev.value * self.factores[ev.code] + self.resto[ev.code]
                    n = int(v)
                    self.resto[ev.code] = v - n
                    if n:
                        ui.write(e.EV_REL, ev.code, n)
                elif ev.type == e.EV_SYN:
                    ui.syn()
                else:
                    ui.write(ev.type, ev.code, ev.value)
        except OSError:
            logger.info("[TURBO] %s se desconectó; lo vuelvo a tomar al reaparecer.", tb.name)
        finally:
            try:
                tb.close()
            except Exception:
                pass
            _activos.pop(tb.name, None)


def _conectar(tb):
    from evdev import UInput, ecodes as e
    nombre = tb.name
    nombre_virtual = f"Turbo {nombre}"
    ui = _virtuales.get(nombre)
    if ui is None:
        caps = tb.capabilities()
        ui = UInput({k: v for k, v in caps.items() if k in (e.EV_KEY, e.EV_REL, e.EV_MSC)},
                    name=nombre_virtual)
        _virtuales[nombre] = ui
    _ajustar_kwin(nombre, nombre_virtual)
    t = _Turbo(tb, ui)
    _activos[nombre] = t
    threading.Thread(target=t.bucle, daemon=True, name=f"turbo-{nombre}").start()
    fx, fy = t.factores.values()
    logger.info("[TURBO] %s listo (turbo horizontal ×%g, vertical ×%g).", nombre, fx, fy)


def _vigilar():
    from evdev import InputDevice, list_devices, ecodes as e
    avisados = set()
    while True:
        faltan = [n for n in TRACKBALLS if n not in _activos]
        if faltan:
            for ruta in list_devices():    # solo lista los que se pueden abrir
                try:
                    d = InputDevice(ruta)
                except OSError:
                    continue
                if d.name in faltan and d.name not in _activos and e.EV_REL in d.capabilities():
                    try:
                        _conectar(d)
                        avisados.discard(d.name)
                    except Exception as err:
                        logger.error("[TURBO] %s: no pude prepararlo: %s", d.name, err)
                        d.close()
                else:
                    d.close()
            for n in TRACKBALLS:
                if n not in _activos and n not in avisados:
                    logger.info("[TURBO] %s no está o no lo puedo leer "
                                "(¿falta linux/72-trackball-turbo.rules?).", n)
                    avisados.add(n)
        time.sleep(INTERVALO_BUSQUEDA)


def iniciar():
    if not HABILITADA:
        return
    try:
        import evdev  # noqa: F401
    except ImportError:
        logger.error("[TURBO] Falta python-evdev; módulo deshabilitado.")
        return
    threading.Thread(target=_vigilar, daemon=True, name="turbo-vigilar").start()
