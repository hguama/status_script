"""
wrap_around — Salto de borde a borde de pantalla (versión Linux, KDE Wayland).

Al empujar el cursor contra un borde de la pantalla lo transporta al borde
opuesto, salvo que el movimiento parezca navegación a lo largo del borde
(recorrer íconos de un panel o una barra lateral).

Cómo funciona:
  1. utils/cursor_kwin entrega ~60 muestras por segundo del cursor; cada una
     dice si hubo empuje real contra un borde (KWin rebota el cursor 1 px en
     los bordes reservados; con un botón presionado no hay rebote ni empuje).
  2. Un empuje es una racha de muestras con empuje contra el mismo borde. Se
     salta cuando la racha lleva RESISTENCIA_MS y en ese último lapso el cursor
     casi no se movió a lo largo del borde.
  3. El salto se hace con un puntero absoluto virtual (uinput).

KWin no debe activar sus propios bordes mientras tanto (al hacerlo deja de
rebotar el cursor): por eso ElectricBorderDelay va en RETARDO_KWIN_MS.

Uso:
    from utils import wrap_around
    wrap_around.iniciar(pantalla_ancho, pantalla_alto)   # tras cursor_kwin.start()
"""

import logging
import subprocess
import time

from utils import cursor_kwin

logger = logging.getLogger(__name__)

HABILITADA = True

RESISTENCIA_MS     = 90    # empuje sostenido necesario para saltar
TOLERANCIA_LATERAL = 15    # px a lo largo del borde en ese lapso; más = navegar íconos
PAUSA_MAX          = 0.06  # s sin empuje que cortan la racha
COOLDOWN           = 0.5   # s mínimos entre saltos
INSET              = 15    # px desde el borde opuesto donde aterriza el cursor
ARMADO_MS          = 50    # racha mínima para el aviso visual
RETARDO_KWIN_MS    = 60000 # ElectricBorderDelay de KWin (kwinrc): que nunca se active

_ancho = _alto = 0
_uinput = None
_bloqueado_hasta = 0.0

# Racha de empuje en curso
_borde = None          # "izq" | "der" | "arriba" | "abajo" | None
_t_inicio = 0.0
_t_ultimo = 0.0
_lateral_min = None    # menor recorrido lateral visto en la racha (para el log)


def log_configuracion():
    estado = "ACTIVO" if HABILITADA else "INACTIVO"
    logger.info("├─ WRAP-AROUND  [%s]", estado)
    logger.info("│  resistencia = %d ms de empuje sostenido", RESISTENCIA_MS)
    logger.info("│  tolerancia  = %d px a lo largo del borde", TOLERANCIA_LATERAL)
    logger.info("│  cooldown    = %.2f s", COOLDOWN)


def borde_de(x, y, ancho, alto):
    """Borde que toca el cursor, o None (las esquinas no cuentan: son ambiguas)."""
    tocados = []
    if x <= 1:
        tocados.append("izq")
    if x >= ancho - 2:
        tocados.append("der")
    if y <= 1:
        tocados.append("arriba")
    if y >= alto - 2:
        tocados.append("abajo")
    return tocados[0] if len(tocados) == 1 else None


def lateral(borde, muestras, ahora):
    """Recorrido a lo largo del borde en los últimos RESISTENCIA_MS. Función pura."""
    eje = 2 if borde in ("izq", "der") else 1
    v = [m[eje] for m in muestras if ahora - m[0] <= RESISTENCIA_MS / 1000]
    return max(v) - min(v) if v else 0


def destino(borde, x, y, ancho, alto):
    return {
        "izq":    (ancho - 1 - INSET, y),
        "der":    (INSET, y),
        "arriba": (x, alto - 1 - INSET),
        "abajo":  (x, INSET),
    }[borde]


def armando():
    """True mientras hay un empuje en curso contra un borde (para el aviso visual)."""
    ahora = time.monotonic()
    return _borde is not None and ahora - _t_ultimo < PAUSA_MAX \
        and ahora - _t_inicio >= ARMADO_MS / 1000 and ahora >= _bloqueado_hasta


def _transportar(x, y):
    from evdev import ecodes as e
    _uinput.write(e.EV_ABS, e.ABS_X, x)
    _uinput.write(e.EV_ABS, e.ABS_Y, y)
    _uinput.syn()


def _cerrar_racha():
    """Termina la racha; si duró lo suficiente y no saltó, deja el motivo en el log."""
    global _borde
    if _borde and _lateral_min is not None:
        logger.debug("[WRAP] %s: sin salto — deslizamiento (%.0f ms de empuje, lateral mínimo=%dpx)",
                     _borde, (_t_ultimo - _t_inicio) * 1000, _lateral_min)
    _borde = None


def _al_muestrear():
    global _borde, _t_inicio, _t_ultimo, _lateral_min, _bloqueado_hasta
    muestras = cursor_kwin.muestras()
    t, x, y, empuje = muestras[-1]

    if _borde and t - _t_ultimo > PAUSA_MAX:
        _cerrar_racha()
    if not empuje or t < _bloqueado_hasta:
        return

    borde = borde_de(x, y, _ancho, _alto)
    if borde != _borde:
        _cerrar_racha()
        if borde is None:
            return
        _borde, _t_inicio, _lateral_min = borde, t, None
    _t_ultimo = t

    if t - _t_inicio < RESISTENCIA_MS / 1000:
        return
    lat = lateral(borde, muestras, t)
    if lat > TOLERANCIA_LATERAL:
        _lateral_min = lat if _lateral_min is None else min(_lateral_min, lat)
        return

    dest = destino(borde, x, y, _ancho, _alto)
    _transportar(*dest)
    logger.debug("[WRAP] ⚡ SALTO desde %s → %s  (%.0f ms de empuje, lateral=%dpx)",
                 borde, dest, (t - _t_inicio) * 1000, lat)
    _borde, _lateral_min = None, None
    _bloqueado_hasta = t + COOLDOWN


def _revisar_retardo_kwin():
    try:
        valor = subprocess.run(
            ["kreadconfig6", "--file", "kwinrc", "--group", "Windows", "--key", "ElectricBorderDelay"],
            capture_output=True, text=True, timeout=2,
        ).stdout.strip()
    except Exception:
        return
    if valor != str(RETARDO_KWIN_MS):
        logger.warning(
            "[WRAP] ElectricBorderDelay de KWin es '%s' y se esperaba %d: el wrap será "
            "irregular (ver DOCs/README_LINUX.md)", valor or "por defecto", RETARDO_KWIN_MS,
        )


def iniciar(ancho_pantalla: int, alto_pantalla: int):
    global _ancho, _alto, _uinput
    if not HABILITADA:
        logger.info("[WRAP] Módulo desactivado.")
        return

    try:
        from evdev import UInput, AbsInfo, ecodes as e
        # Puntero absoluto (como una tableta): KWin lleva el cursor a la
        # coordenada emitida. BTN_LEFT hace falta para que libinput lo acepte.
        _uinput = UInput({
            e.EV_KEY: [e.BTN_LEFT],
            e.EV_ABS: [(e.ABS_X, AbsInfo(0, 0, ancho_pantalla - 1, 0, 0, 0)),
                       (e.ABS_Y, AbsInfo(0, 0, alto_pantalla - 1, 0, 0, 0))],
        }, name="statusscript-wrap")
    except Exception as ex:
        logger.error("[WRAP] no se pudo crear el puntero virtual (/dev/uinput): %s", ex)
        return

    _ancho, _alto = ancho_pantalla, alto_pantalla
    _revisar_retardo_kwin()
    cursor_kwin.on_muestra(_al_muestrear)
    logger.info(
        "🖱️  WRAP-AROUND: activo [resistencia=%d ms, tolerancia=%d px, cooldown=%.1f s]",
        RESISTENCIA_MS, TOLERANCIA_LATERAL, COOLDOWN,
    )
