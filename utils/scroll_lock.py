import ctypes
import time
import threading
import logging
import keyboard
import pyautogui

logger = logging.getLogger(__name__)


def _safe_horizontal_scroll(delta, MOUSEEVENTF_HWHEEL):
    try:
        pyautogui.hscroll(delta)
        logger.debug("[SCROLL LOCK] Enviado pyautogui.hscroll(%d)", delta)
        return
    except Exception as e:
        logger.debug("[SCROLL LOCK] pyautogui.hscroll falló: %s", e)

    try:
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, delta, 0)
        logger.debug("[SCROLL LOCK] Enviado mouse_event HWHEEL(%d)", delta)
        return
    except Exception as e:
        logger.debug("[SCROLL LOCK] mouse_event HWHEEL falló: %s", e)

    pressed_shift = False
    if not keyboard.is_pressed("shift"):
        keyboard.press("shift")
        pressed_shift = True
    try:
        pyautogui.scroll(delta)
        logger.debug("[SCROLL LOCK] Enviado scroll vertical con Shift(%d) como fallback horizontal", delta)
    finally:
        if pressed_shift:
            keyboard.release("shift")


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def run_in_background(is_mirror_active):
    t = threading.Thread(
        target=_scroll_lock_loop, args=(is_mirror_active,), daemon=True
    )
    t.start()


def _scroll_lock_loop(is_mirror_active):
    SCROLL_THRESHOLD_Y = 8
    SCROLL_THRESHOLD_X = 8
    SCROLL_DELTA = 120

    lock_x = 0
    lock_y = 0
    accum_y = 0
    accum_x = 0
    active = False
    last_direction = None

    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_HWHEEL = 0x1000

    while True:
        try:
            mirror_active = is_mirror_active()

            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            curr_x, curr_y = pt.x, pt.y

            if mirror_active:
                if not active:
                    lock_x = curr_x
                    lock_y = curr_y
                    accum_y = 0
                    accum_x = 0
                    last_direction = None
                    active = True
                    logger.info(
                        "[SCROLL LOCK] Activado - cursor anclado en (%d, %d)",
                        lock_x,
                        lock_y,
                    )

                dy = lock_y - curr_y
                dx = curr_x - lock_x
                abs_dx = abs(dx)
                abs_dy = abs(dy)
                direction = None

                if abs_dx >= SCROLL_THRESHOLD_X or abs_dy >= SCROLL_THRESHOLD_Y:
                    if abs_dx > abs_dy + 3:
                        direction = "horizontal"
                    elif abs_dy > abs_dx + 3:
                        direction = "vertical"
                    elif last_direction is None:
                        direction = "horizontal" if abs_dx > abs_dy else "vertical"
                    else:
                        direction = last_direction
                else:
                    direction = last_direction

                if direction is not None and direction != last_direction:
                    if direction == "vertical":
                        accum_x = 0
                    else:
                        accum_y = 0
                    last_direction = direction
                    logger.debug("[SCROLL LOCK] Cambio de eje a %s", direction)

                if direction == "vertical":
                    accum_y += dy
                    accum_x = 0
                elif direction == "horizontal":
                    accum_x += dx
                    accum_y = 0
                elif last_direction == "vertical":
                    accum_y += dy
                    accum_x = 0
                elif last_direction == "horizontal":
                    accum_x += dx
                    accum_y = 0

                ctypes.windll.user32.SetCursorPos(lock_x, lock_y)

                if abs(accum_y) >= SCROLL_THRESHOLD_Y:
                    if keyboard.is_pressed("ctrl"):
                        keyboard.release("ctrl")
                        logger.debug("[SCROLL LOCK] Liberando Ctrl para enviar scroll sin zoom")
                    if keyboard.is_pressed("shift"):
                        keyboard.release("shift")
                        logger.debug("[SCROLL LOCK] Liberando Shift para enviar scroll vertical")

                    steps = int(accum_y / SCROLL_THRESHOLD_Y)
                    delta = steps * SCROLL_DELTA
                    try:
                        pyautogui.scroll(delta)
                    except Exception:
                        ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
                    accum_y -= steps * SCROLL_THRESHOLD_Y
                    logger.debug(
                        "[SCROLL LOCK] Scroll vertical %s (%d pasos)",
                        "arriba" if delta > 0 else "abajo",
                        abs(steps),
                    )

                if abs(accum_x) >= SCROLL_THRESHOLD_X:
                    if keyboard.is_pressed("ctrl"):
                        keyboard.release("ctrl")
                        logger.debug("[SCROLL LOCK] Liberando Ctrl para enviar scroll sin zoom")
                    steps = int(accum_x / SCROLL_THRESHOLD_X)
                    delta = -steps * SCROLL_DELTA
                    _safe_horizontal_scroll(delta, MOUSEEVENTF_HWHEEL)
                    accum_x -= steps * SCROLL_THRESHOLD_X
                    logger.debug(
                        "[SCROLL LOCK] Scroll horizontal %s (%d pasos)",
                        "derecha" if steps > 0 else "izquierda",
                        abs(steps),
                    )

            else:
                if active:
                    active = False
                    accum_y = 0
                    accum_x = 0
                    logger.info("[SCROLL LOCK] Desactivado")

            time.sleep(0.01)
        except Exception as e:
            logger.error("[SCROLL LOCK] Error: %s", e)
            time.sleep(0.05)
