"""
dictado_terminal — Avisa al Corne si la ventana activa es Konsole.

Con Konsole activa, el firmware cambia la tecla de Handy (Ctrl+Espacio) por un
toque de Alt+K, que en Claude Code es el dictado nativo (``~/.claude/keybindings.json``
→ ``"meta+k": "voice:pushToTalk"``, con ``/voice tap``). En cualquier otra ventana
la tecla sigue siendo Ctrl+Espacio para Handy.

Protocolo raw HID: ``'T','1'`` (Konsole activa) / ``'T','0'`` (otra ventana). Solo
se manda al cambiar el estado, y otra vez tras reconectar el Corne (su bandera
arranca apagada). Si este script no corre, la bandera queda apagada y la tecla
es Ctrl+Espacio en todos lados.

La ventana activa sale de utils/cursor_kwin (KWin la manda por D-Bus).
"""

import logging
import threading
import time

from utils import cursor_kwin
import utils.captura as captura

logger = logging.getLogger(__name__)

HABILITADA = True

APPS = ("konsole",)          # fragmentos de la clase de la ventana (en minúsculas)
INTERVALO = 0.05             # s entre revisiones de la ventana activa

_enviado = None              # último estado mandado al Corne (None = hay que reenviar)


def log_configuracion():
    estado = "ACTIVO" if HABILITADA else "INACTIVO"
    logger.info("├─ DICTADO-TERMINAL  [%s]", estado)
    logger.info("│  apps = %s  |  Ctrl+Espacio → Alt+K", ", ".join(APPS))


def reenviar():
    """Tras reconectar el Corne: fuerza a mandar el estado actual otra vez."""
    global _enviado
    _enviado = None


def _es_terminal():
    v = cursor_kwin.ventana()
    return bool(v) and any(app in v[0].lower() for app in APPS)


def _vigilar(get_dev):
    global _enviado
    while True:
        activa = _es_terminal()
        if activa != _enviado:
            buf = [0] * 33
            buf[1] = ord("T")
            buf[2] = ord("1" if activa else "0")
            try:
                with captura.WRITE_LOCK:
                    get_dev().write(buf)
                _enviado = activa
                logger.debug("[DICTADO] terminal activa = %s", activa)
            except Exception as e:
                # El Corne se desconectó: escuchar_hid reconecta y llama a reenviar()
                logger.debug("[DICTADO] no se pudo avisar al Corne: %s", e)
        time.sleep(INTERVALO)


def iniciar(get_dev):
    """get_dev() devuelve el dispositivo HID actual (cambia al reconectar)."""
    if not HABILITADA:
        logger.info("[DICTADO] Módulo desactivado.")
        return
    threading.Thread(target=_vigilar, args=(get_dev,), daemon=True).start()
