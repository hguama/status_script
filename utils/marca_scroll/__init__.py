"""
marca_scroll — Marca que acompaña al texto cuando se hace scroll con la rueda del Corne.

Al empezar a hacer scroll en una ventana de ``APPS`` se deja una marca fija en
el margen izquierdo, justo encima de donde está el cuadro de entrada (el último
texto leído). Cada paso de rueda mueve la marca ``PX_POR_PASO`` píxeles igual
que el texto, así señala a dónde fue a parar esa línea. Si sale de la ventana
queda pegada al borde y cambia de color. Tras ``INACTIVIDAD`` segundos sin
scroll desaparece y el siguiente scroll vuelve a empezar desde el ancla.

La rueda se lee directamente del Corne (evdev, interfaz de mouse): hace falta
la regla udev linux/71-corne-wheel.rules. Sin ella el módulo no hace nada.

Hilos: el lector de evdev solo anota los pasos; el dibujo (python-xlib) lo hace
``tick()``, que debe llamarse desde el hilo de Tk.

Uso:
    from utils import marca_scroll
    marca = CirculoARGB(marca_scroll.TAM)
    marca_scroll.iniciar()
    root.after(33, lambda: marca_scroll.tick(marca))      # y repetirlo
"""

import configparser
import glob
import logging
import os
import threading
import time

from utils import cursor_kwin

logger = logging.getLogger(__name__)

HABILITADA = False

APPS = ("konsole",)          # fragmentos de la clase de la ventana (en minúsculas)
LINEAS_POR_PASO = 3          # líneas que desplaza Qt por paso de rueda con factor 1 (Kate y Konsole)
ALTO_LINEA = 18              # px de una línea con la fuente actual de Konsole/Kate
KCMINPUTRC = os.path.expanduser("~/.config/kcminputrc")
GRUPO_CORNE = "Libinput][18003][1][foostan Corne"   # [Libinput][vid][pid][nombre], vid/pid en decimal
ORIGEN_TEXTO = 114           # px desde el borde superior de la ventana hasta la 1ª fila (barras de Konsole)
ANCLA_X = 3                  # px desde el borde izquierdo de la ventana
MARGEN_SUP = 40              # px arriba de la ventana que no son texto (título/barra)
TAM = 14                     # diámetro de la marca
COLOR, COLOR_FUERA = "#FFFFFF", "#D50000"
INACTIVIDAD = 3.0            # s sin scroll para ocultar la marca
NOMBRE_DISPOSITIVO = "foostan Corne"

_lock = threading.Lock()
_activa = False
_ancla_y = 0
_dy = 0
_ventana = None              # (x, y, ancho, alto) al armar la marca
_t_ultimo = 0.0
_px = 0.0
_dibujada = None             # último (x, y, color) dibujado, o None si está oculta


def log_configuracion():
    estado = "ACTIVO" if HABILITADA else "INACTIVO"
    logger.info("├─ MARCA-SCROLL  [%s]", estado)
    logger.info("│  apps = %s  |  %.0f px por paso  |  ancla = centro de la última fila (filas de %d px)",
                ", ".join(APPS), px_por_paso(), ALTO_LINEA)


def centro_ultima_fila(y, alto):
    """y del centro de la última fila completa de texto de una ventana (y, alto), sin dibujar nada.

    Konsole reparte el texto en filas de ALTO_LINEA px desde ORIGEN_TEXTO; lo que sobra
    queda como margen abajo, así que la última fila no está a una distancia fija del borde.
    """
    filas = (alto - ORIGEN_TEXTO) // ALTO_LINEA
    return y + ORIGEN_TEXTO + filas * ALTO_LINEA - ALTO_LINEA / 2


def px_por_paso():
    """Lo que se mueve el texto por paso de rueda, según el ScrollFactor del Corne en KDE."""
    try:
        cp = configparser.ConfigParser(interpolation=None, strict=False)
        cp.optionxform = str
        cp.read(KCMINPUTRC)
        factor = float(cp.get(GRUPO_CORNE, "ScrollFactor", fallback="1"))
    except Exception as e:
        logger.debug("[MARCA] no se pudo leer ScrollFactor (%s); se usa 1", e)
        factor = 1.0
    return LINEAS_POR_PASO * factor * ALTO_LINEA


def _on_rueda(v):
    """v = +1 (rueda hacia arriba: el texto baja) o -1 (hacia abajo: el texto sube)."""
    global _activa, _ancla_y, _dy, _ventana, _t_ultimo, _px
    logger.debug("[MARCA] rueda %+d recibida; ventana activa = %s", v, info_log := cursor_kwin.ventana())
    info = info_log
    if not info or not any(a in info[0].lower() for a in APPS):
        return
    _, x, y, ancho, alto = info
    ahora = time.monotonic()
    with _lock:
        if not _activa or ahora - _t_ultimo > INACTIVIDAD:
            _activa, _dy = True, 0
            _ventana = (x, y, ancho, alto)
            _ancla_y = centro_ultima_fila(y, alto)
            _px = px_por_paso()          # se relee al armar: si cambias el factor, se adapta solo
            logger.debug("[MARCA] marca armada: %.0f px por paso", _px)
        _dy += v * _px
        _t_ultimo = ahora
    logger.debug("[MARCA] paso %+d → desplazamiento acumulado %d px", v, _dy)


def posicion_actual(ahora=None):
    """(x, y, fuera) donde debe estar la marca, o None si no debe verse. Función sin dibujo."""
    ahora = time.monotonic() if ahora is None else ahora
    with _lock:
        if not _activa or ahora - _t_ultimo > INACTIVIDAD:
            return None
        x, y, _, alto = _ventana
        yy = _ancla_y + _dy
        ymin, ymax = y + MARGEN_SUP, y + alto - TAM
        fuera = yy < ymin or yy > ymax
        return x + ANCLA_X, round(min(max(yy, ymin), ymax)), fuera


def tick(marca):
    """Actualiza el dibujo. Llamar desde el hilo de Tk, ~30 veces por segundo."""
    global _dibujada
    pos = posicion_actual()
    if pos is None:
        if _dibujada is not None:
            marca.hide()
            _dibujada = None
        return
    x, y, fuera = pos
    estado = (x, y, COLOR_FUERA if fuera else COLOR)
    if estado == _dibujada:
        return
    if _dibujada is None or _dibujada[2] != estado[2]:
        marca.set_color(estado[2])
    marca.move(x, y - TAM // 2)
    if _dibujada is None:
        marca.show()
    _dibujada = estado


def _abrir_dispositivo():
    """Interfaz de mouse del Corne (la que tiene REL_WHEEL). Devuelve (dispositivo|None, hubo_sin_permiso)."""
    from evdev import InputDevice, ecodes as e
    sin_permiso = False
    for path in sorted(glob.glob("/dev/input/event*")):
        try:
            d = InputDevice(path)
        except PermissionError:
            sin_permiso = True
            continue
        except OSError:
            continue
        if d.name == NOMBRE_DISPOSITIVO and e.REL_WHEEL in d.capabilities().get(e.EV_REL, []):
            return d, sin_permiso
        d.close()
    return None, sin_permiso


def _leer_rueda():
    from evdev import ecodes as e
    avisado = False
    while True:
        d, sin_permiso = _abrir_dispositivo()
        if d is None:
            if sin_permiso and not avisado:
                logger.info("[MARCA] sin acceso a la rueda del Corne: falta instalar "
                            "linux/71-corne-wheel.rules (ver DOCs/README_LINUX.md)")
                avisado = True
            time.sleep(3)
            continue
        logger.info("[MARCA] leyendo la rueda de %s (%s)", d.name, d.path)
        avisado = False
        try:
            for ev in d.read_loop():
                if ev.type == e.EV_REL and ev.code == e.REL_WHEEL:
                    _on_rueda(ev.value)
        except OSError:
            logger.info("[MARCA] el Corne se desconectó; reintentando")
        finally:
            d.close()


def iniciar():
    if not HABILITADA:
        logger.info("[MARCA] Módulo desactivado.")
        return
    threading.Thread(target=_leer_rueda, daemon=True).start()
