"""
qmk_calibracion — Módulo independiente para calibración de mouse keys QMK.

Envía parámetros de mouse (delay, max_speed, time_to_max, interval)
al firmware del teclado Corne vía HID raw, durante la fase de pruebas.

Una vez definidos los valores finales, se recomienda hardcodearlos
directamente en config.h del firmware QMK y desactivar este módulo
con la bandera ``HABILITADA = False``.

Uso:
    from utils.qmk_calibracion import (
        HABILITADA, enviar_calibracion, log_configuracion,
    )

    if HABILITADA:
        enviar_calibracion(dev)
"""

import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# BANDERA DE ACTIVACIÓN
# ═══════════════════════════════════════════════════════════════════
# Cambia a False cuando los valores ya estén hardcodeados en el
# firmware QMK (config.h). Así el script no dependerá de este envío.
HABILITADA = True


# ═══════════════════════════════════════════════════════════════════
# PARÁMETROS DE MOUSE KEYS (→ firmware QMK vía HID raw)
# ═══════════════════════════════════════════════════════════════════
# Orden en el buffer HID:
#   data[0] = 'M'            → firma de comando
#   data[1] = mk_delay       → retardo inicial antes de repetir (ms, 0-255)
#   data[2] = mk_max_speed   → velocidad máxima estable (1-255)
#   data[3] = mk_time_to_max → eventos para alcanzar velocidad máxima (1-255)
#   data[4] = mk_interval    → intervalo entre eventos de repetición (ms, 1-255)
#
# Guía rápida de ajuste:
#   - ¿Muy lento?       → sube MAX_SPEED, baja INTERVAL, baja TIME_TO_MAX
#   - ¿Arranca muy lento? → baja DELAY
#   - ¿Muy brusco?      → baja MAX_SPEED, sube TIME_TO_MAX, sube INTERVAL

MK_DELAY       = 5   # Retardo inicial (ms)
MK_MAX_SPEED   = 22  # Velocidad máxima
MK_TIME_TO_MAX = 10  # Eventos hasta vel. máxima
MK_INTERVAL    = 6   # Intervalo entre eventos (ms)


# ═══════════════════════════════════════════════════════════════════
# LOG DE CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════

def log_configuracion():
    """Vuelca los parámetros QMK actuales al log."""
    sep = "─" * 55
    estado = "ACTIVO" if HABILITADA else "INACTIVO (valores en firmware)"
    logger.info("├─ QMK MOUSE (→ firmware vía HID raw)  [%s]", estado)
    logger.info(f"│  mk_delay       = {MK_DELAY:>3} ms   (retardo inicial)")
    logger.info(f"│  mk_max_speed   = {MK_MAX_SPEED:>3}       (velocidad máxima, 1-255)")
    logger.info(f"│  mk_time_to_max = {MK_TIME_TO_MAX:>3}       (eventos hasta vel. máx.)")
    logger.info(f"│  mk_interval    = {MK_INTERVAL:>3} ms   (intervalo entre eventos)")


# ═══════════════════════════════════════════════════════════════════
# ENVÍO HID AL FIRMWARE
# ═══════════════════════════════════════════════════════════════════

def enviar_calibracion(dev):
    """
    Construye el buffer HID con la firma 'M' y envía los parámetros
    de mouse keys al Corne.

    Args:
        dev: Dispositivo HID abierto (hid.device).

    Returns:
        True si se envió correctamente, False en caso de error.
    """
    if not HABILITADA:
        logger.info("[QMK CALIB] Módulo desactivado — no se envían parámetros.")
        return False

    try:
        # Buffer de 33 bytes: [0]=Report ID, [1..32]=payload para QMK raw HID.
        # QMK raw_hid_receive recibe data[0..31] (sin Report ID).
        buf = [0] * 33
        buf[0] = 0x00                # Report ID (requerido por Windows)
        buf[1] = ord("M")            # data[0] = 'M' — firma de comando
        buf[2] = MK_DELAY            # data[1] = mk_delay
        buf[3] = MK_MAX_SPEED        # data[2] = mk_max_speed
        buf[4] = MK_TIME_TO_MAX      # data[3] = mk_time_to_max
        buf[5] = MK_INTERVAL         # data[4] = mk_interval

        dev.write(buf)

        logger.info("=" * 55)
        logger.info("  ✅ CALIBRACIÓN QMK ENVIADA AL CORNE")
        logger.info(f"  mk_delay       = {MK_DELAY} ms")
        logger.info(f"  mk_max_speed   = {MK_MAX_SPEED}")
        logger.info(f"  mk_time_to_max = {MK_TIME_TO_MAX}")
        logger.info(f"  mk_interval    = {MK_INTERVAL} ms")
        logger.info("=" * 55)
        return True

    except Exception as e:
        logger.error(f"[QMK CALIB ERROR] No se pudieron enviar los valores: {e}")
        return False
