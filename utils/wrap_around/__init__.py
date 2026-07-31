"""
wrap_around — Módulo independiente para salto de borde a borde de pantalla.

Detecta cuando el cursor llega al borde de la pantalla y lo transporta
automáticamente al borde opuesto (wrap-around). Funciona con cualquier
fuente de movimiento: QMK nativo, ratón físico, etc.

Uso:
    from utils.wrap_around import HABILITADA, wrap_loop, log_configuracion

    if HABILITADA:
        threading.Thread(
            target=wrap_loop,
            args=(pantalla_ancho, pantalla_alto),
            daemon=True,
        ).start()
"""

import ctypes
import logging
import time

logger = logging.getLogger(__name__)

HABILITADA = True

MARGEN_PORCENTAJE = 0.005
DELAY_MS         = 0.05
COOLDOWN         = 0.5


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def log_configuracion():
    estado = "ACTIVO" if HABILITADA else "INACTIVO"
    logger.info("├─ WRAP-AROUND  [%s]", estado)
    logger.info("│  margen      = %.1f%% del borde", MARGEN_PORCENTAJE * 100)
    logger.info("│  delay       = %d ms", int(DELAY_MS * 1000))
    logger.info("│  cooldown    = %.2f s", COOLDOWN)


def wrap_loop(ancho_pantalla: int, alto_pantalla: int):
    if not HABILITADA:
        logger.info("[WRAP] Módulo desactivado.")
        return

    logger.info(
        "🖱️  WRAP-AROUND: Hilo iniciado [margen=%.1f%%, delay=%d ms, cooldown=%.1f s]",
        MARGEN_PORCENTAJE * 100, int(DELAY_MS * 1000), COOLDOWN,
    )

    borde_activo_x = 0
    borde_activo_y = 0
    tiempo_choque_x = 0.0
    tiempo_choque_y = 0.0
    prev_x, prev_y = 0, 0
    UMBRAL_MOV = 1

    while True:
        try:
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            curr_x, curr_y = pt.x, pt.y
            ahora = time.time()

            margen_x = int(ancho_pantalla * MARGEN_PORCENTAJE)
            margen_y = int(alto_pantalla * MARGEN_PORCENTAJE)

            vx = curr_x - prev_x
            vy = curr_y - prev_y

            if curr_x >= ancho_pantalla - margen_x - 1:
                ctypes.windll.user32.SetCursorPos(ancho_pantalla - margen_x - 1, int(curr_y))
                curr_x = ancho_pantalla - margen_x - 1
                if vx > UMBRAL_MOV and abs(vy) <= UMBRAL_MOV:
                    if borde_activo_x != 1:
                        borde_activo_x = 1
                        tiempo_choque_x = ahora
                    elif ahora - tiempo_choque_x >= DELAY_MS:
                        nuevo_x = margen_x + 5
                        ctypes.windll.user32.SetCursorPos(nuevo_x, int(curr_y))
                        curr_x = nuevo_x
                        borde_activo_x = 0
                        tiempo_choque_x = ahora + COOLDOWN
                else:
                    borde_activo_x = 0
            elif curr_x <= margen_x:
                ctypes.windll.user32.SetCursorPos(margen_x, int(curr_y))
                curr_x = margen_x
                if vx < -UMBRAL_MOV and abs(vy) <= UMBRAL_MOV:
                    if borde_activo_x != -1:
                        borde_activo_x = -1
                        tiempo_choque_x = ahora
                    elif ahora - tiempo_choque_x >= DELAY_MS:
                        nuevo_x = ancho_pantalla - margen_x - 5
                        ctypes.windll.user32.SetCursorPos(nuevo_x, int(curr_y))
                        curr_x = nuevo_x
                        borde_activo_x = 0
                        tiempo_choque_x = ahora + COOLDOWN
                else:
                    borde_activo_x = 0
            else:
                borde_activo_x = 0

            if curr_y >= alto_pantalla - margen_y - 1:
                ctypes.windll.user32.SetCursorPos(int(curr_x), alto_pantalla - margen_y - 1)
                curr_y = alto_pantalla - margen_y - 1
                if vy > UMBRAL_MOV and abs(vx) <= UMBRAL_MOV:
                    if borde_activo_y != 1:
                        borde_activo_y = 1
                        tiempo_choque_y = ahora
                    elif ahora - tiempo_choque_y >= DELAY_MS:
                        nuevo_y = margen_y + 5
                        ctypes.windll.user32.SetCursorPos(int(curr_x), nuevo_y)
                        curr_y = nuevo_y
                        borde_activo_y = 0
                        tiempo_choque_y = ahora + COOLDOWN
                else:
                    borde_activo_y = 0
            elif curr_y <= margen_y:
                ctypes.windll.user32.SetCursorPos(int(curr_x), margen_y)
                curr_y = margen_y
                if vy < -UMBRAL_MOV and abs(vx) <= UMBRAL_MOV:
                    if borde_activo_y != -1:
                        borde_activo_y = -1
                        tiempo_choque_y = ahora
                    elif ahora - tiempo_choque_y >= DELAY_MS:
                        nuevo_y = alto_pantalla - margen_y - 5
                        ctypes.windll.user32.SetCursorPos(int(curr_x), nuevo_y)
                        curr_y = nuevo_y
                        borde_activo_y = 0
                        tiempo_choque_y = ahora + COOLDOWN
                else:
                    borde_activo_y = 0
            else:
                borde_activo_y = 0

            prev_x, prev_y = curr_x, curr_y

        except Exception as e:
            logger.debug("[WRAP ERROR] %s", e)

        time.sleep(0.01)
