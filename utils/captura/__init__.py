"""utils.captura — captura con evento para el Corne (Task 15, migra-captura).

Dirigido por eventos, sin poll permanente: el hilo duerme en un Event
(cero CPU en reposo) y el lector lo despierta al ver CAP_ARM. Vigila el
overlay de Recortes hasta VENTANA_S y manda 'S' una vez.

Protocolo (congelado en firmware 24.390, ver contrato captura §§6-7):
  hold -> Win+Shift+S + CAP_ARM + arma; S -> espera 150ms -> engancha
  + CAP_EVT; sin S, red 800ms + CAP_NET.
"""

import ctypes
import logging
import threading
import time

logger = logging.getLogger(__name__)

# Ventana de vigilancia tras CAP_ARM (el overlay aparece a ~220ms;
# medido 200-410ms; la red del firmware cubre lo que pase de aquí).
VENTANA_S = 0.7
POLL_S = 0.02

# Candado para dev.write compartido (este hilo escribe 'S'; el hilo
# alt-tab escribe 'R' sobre el mismo handle).
WRITE_LOCK = threading.Lock()

_armed = threading.Event()
_deadline = 0.0
_gen = 0


def _overlay_visible():
    """Huella del overlay: fullscreen + clase + título (validada §5 captura)."""
    user32 = ctypes.windll.user32
    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    CMPCF = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        rect = (ctypes.c_long * 4)()
        user32.GetWindowRect(hwnd, rect)
        if (rect[2] - rect[0], rect[3] - rect[1]) == (sw, sh):
            ln = user32.GetWindowTextLengthW(hwnd)
            t = ctypes.create_unicode_buffer(ln + 1)
            user32.GetWindowTextW(hwnd, t, ln + 1)
            c = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, c, 256)
            if t.value == "Snipping Tool Overlay" and c.value == "SnipOverlayRootWindow":
                found.append(hwnd)
        return True

    found = []
    user32.EnumWindows(CMPCF(cb), None)
    return bool(found)


def notificar_cap(msg):
    """Entrada desde escuchar_hid para todo mensaje CAP_*/VER_*. Sin Tk aquí."""
    global _deadline, _gen
    if msg.startswith("CAP_ARM"):
        _deadline = time.perf_counter() + VENTANA_S
        _gen += 1
        _armed.set()
        logger.info("[CAPTURA] hold armado, vigilando overlay")
    elif msg.startswith("CAP_EVT"):
        logger.info("[CAPTURA] enganche por evento")
    elif msg.startswith("CAP_NET"):
        logger.info("[CAPTURA] enganche por red 800ms")
    elif msg.startswith("CAP_TGL_"):
        logger.info("[CAPTURA] toggle manual: %s", msg)
    elif msg.startswith("CAP_S_SKIP"):
        logger.debug("[CAPTURA] S tardía ignorada por firmware")
    elif msg.startswith("VER_CAPTURE"):
        logger.info("[CAPTURA] firmware: %s", msg)


def enviar_s(dev):
    """Aviso al teclado con la convención del script (report ID + comando)."""
    buf = [0] * 33
    buf[0] = 0x00
    buf[1] = ord("S")
    with WRITE_LOCK:
        dev.write(buf)


def hilo_overlay(dev):
    """Duerme hasta CAP_ARM; vigila acotado; manda S una vez; se desarma."""
    logger.info("[CAPTURA] vigilancia lista (dirigida por CAP_ARM)")
    while True:
        try:
            _armed.wait()
            gen = _gen
            while time.perf_counter() < _deadline:
                if _overlay_visible():
                    enviar_s(dev)
                    logger.info("[CAPTURA] overlay visto -> S enviada")
                    break
                time.sleep(POLL_S)
            if _gen == gen:
                _armed.clear()
            # si llegó otro CAP_ARM en el camino, no se limpia: se re-vigila
        except Exception as e:
            logger.error("[CAPTURA ERROR] %s (reintentando)", e)
            _armed.clear()
            time.sleep(1.0)
