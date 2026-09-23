import hid

# Compat HID: cython-hidapi expone hid.device (minúsculas); pyhidapi (dep de qmk)
# expone hid.Device y puede sombrear al anterior. Normalizar a hid.device.
if not hasattr(hid, "device"):
    _PyHidDevice = hid.Device

    class _CompatHidDevice:
        def __init__(self):
            self._d = None

        def open_path(self, path):
            self._d = _PyHidDevice(path=path)

        def set_nonblocking(self, value):
            self._d.nonblocking = 1 if value else 0

        def read(self, size, timeout_ms=500):
            return self._d.read(size, timeout_ms)

        def write(self, data):
            return self._d.write(bytes(bytearray(data)))

        def close(self):
            self._d.close()

    hid.device = _CompatHidDevice

import tkinter as tk
import threading
import pyautogui
import time
import mouse
import keyboard
import ctypes # Añade esto al inicio de tu archivo

from datetime import datetime
import utils
try:
    import utils.onenote_nav  # Integración OneNote Nav — usa ctypes.windll, solo Windows
except AttributeError:
    utils.onenote_nav = None
import utils.scroll_lock as scroll_lock
import utils.qmk_calibracion as qmk_cal
import utils.wrap_around as wrap_around
import utils.captura as captura
from utils import cursor_kwin
from utils.indicador_argb import CirculoARGB

import logging
import os
import ctypes
import subprocess

# Hacer el proceso consciente de los DPI para que las coordenadas de pantalla coincidan
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

# Configuración de logs con ruta absoluta
DEBUG_LOG_ENABLED = False  # True = escribe f22_debug.log en disco; False = solo consola (modo pruebas)

log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "f22_debug.log")
log_handlers = [logging.StreamHandler()]
if DEBUG_LOG_ENABLED:
    log_handlers.insert(0, logging.FileHandler(log_path, encoding='utf-8', mode='a'))

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)03d %(levelname)s - %(message)s', datefmt='%H:%M:%S', handlers=log_handlers)
logger = logging.getLogger(__name__)
logger.info("=" * 55)
logger.info("  SISTEMA INICIADO — DPI AWARENESS ACTIVO")
logger.info(f"  LOGS → {log_path if DEBUG_LOG_ENABLED else '(archivo desactivado, solo consola)'}")
logger.info("=" * 55)

pyautogui.FAILSAFE = False

# ===============================================================
# CONFIGURACIÓN
# ===============================================================
VID, PID = 0x4653, 0x0001

RADIO_OCULTAR = 80
pyautogui.PAUSE = 0    # Eliminar delay interno de pyautogui para máxima fluidez

# --- WRAP-AROUND ---
# Ahora en utils/wrap_around/__init__.py (bandera HABILITADA)

# --- PARAMETERS MOUSE WITH KEYBOARD ---
# Estos valores ahora se manejan en utils/qmk_calibracion/__init__.py
# Importarlos desde allí permite activar/desactivar el envío con la bandera HABILITADA


# ===============================================================
# ESTADOS GLOBALES
# ===============================================================
alt_tab_menu_visible = False
INDICADOR_HABILITADO = True
f15_down = False

color_actual = "#FFFFFF"
indicador_visible_por_capa = False


# ===============================================================
# --- UI CONFIG ---
DIAMETRO, PUNTO_MOUSE, OFFSET_MOUSE = 30, 20, 22
# Posición del indicador grande: True = abajo-centro, False = arriba-centro.
INDICADOR_INFERIOR = True
MARGEN_BORDE = 5   # px entre el indicador grande y el borde de la pantalla
TAMANO_SCROLL, COLOR_SCROLL = 18, "#2982F0"

colores = {
    "ALFA": "#66BB6A",    # Verde claro / Menta (Material Green 400)
    "MOVEWIN": "#8E24AA",    # Púrpura / Morado (Material Purple 600)
    "FAST": "#E53935",    # Rojo intenso / Carmesí (Material Red 600)
    "NUMB": "#9E9E9E",    # Gris neutro / Medio (Material Grey 500)
    "SCROLL": "#24A4F2",  # tomate / SIN USAR
    "MOVE": "#FFEB3B",    # Amarillo brillante (Material Yellow 500)
    "AI": "#429C9E",    # purpura
    "MOUSE": "#202D80",    # azul
}

root = tk.Tk()
root.withdraw()  # raíz de Tk solo para mainloop/after; los indicadores son ventanas ARGB

pantalla_ancho = root.winfo_screenwidth()
pantalla_alto = root.winfo_screenheight()

# Círculos con fondo transparente real (ver utils/indicador_argb)
indicador_y = (pantalla_alto - DIAMETRO - MARGEN_BORDE) if INDICADOR_INFERIOR else MARGEN_BORDE
ind_grande = CirculoARGB(DIAMETRO, (pantalla_ancho-DIAMETRO)//2, indicador_y)
ind_mouse = CirculoARGB(PUNTO_MOUSE, (pantalla_ancho-PUNTO_MOUSE)//2, (pantalla_alto-PUNTO_MOUSE)//2)

scroll_lock_win = tk.Toplevel()
scroll_lock_win.overrideredirect(True)
scroll_lock_win.attributes("-topmost", True)
scroll_lock_win.config(bg="magenta")
scroll_lock_win.geometry(f"{TAMANO_SCROLL}x{TAMANO_SCROLL}+{(pantalla_ancho-DIAMETRO)//2 + DIAMETRO + 4}+5")

canvas_scroll = tk.Canvas(scroll_lock_win, width=TAMANO_SCROLL, height=TAMANO_SCROLL,
                          highlightthickness=0, bg="magenta")
canvas_scroll.pack()

# --- VENTANA PARA EFECTO PULSO ELEGANTE (DESACTIVADO) ---
# ripple_win = tk.Toplevel() ...

scroll_lock_activo = False

def activar_scroll_lock():
    global scroll_lock_activo
    if not scroll_lock_activo:
        scroll_lock_activo = True
        logger.info("===> [SCROLL LOCK] Activado por Ctrl+Shift+F15.")
        root.after(0, actualizar_scroll_lock_ui)


def desactivar_scroll_lock():
    global scroll_lock_activo
    if scroll_lock_activo:
        scroll_lock_activo = False
        logger.info("===> [SCROLL LOCK] Desactivado.")
        root.after(0, actualizar_scroll_lock_ui)


def on_f15_press(e):
    global f15_down
    if not f15_down and keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift"):
        f15_down = True
        logger.info("Ctrl+Shift+F15: activando funcionalidad SCROLL LOCK.")
        activar_scroll_lock()


def on_f15_release(e):
    global f15_down
    if f15_down:
        f15_down = False
        desactivar_scroll_lock()


# F15 (Scroll Lock): deshabilitado en Linux — requiere la librería `keyboard`,
# que exige ejecutar como root. Ver decisión en README_LINUX.
# keyboard.on_press_key("f15", on_f15_press)
# keyboard.on_release_key("f15", on_f15_release)


def efecto_onda(x, y):
    """Efecto desactivado a petición del usuario."""
    pass
    
# def animar_pulso(step):
#    ... (resto de la función comentada lógicamente)

def toggle_indicadores(e=None):
    """Alterna la bandera global de visibilidad de los indicadores."""
    global INDICADOR_HABILITADO
    INDICADOR_HABILITADO = not INDICADOR_HABILITADO
    logger.info(f"Indicadores habilitados: {INDICADOR_HABILITADO}")
    
    if not INDICADOR_HABILITADO:
        ind_grande.hide()
        ind_mouse.hide()
        scroll_lock_win.withdraw()
    elif indicador_visible_por_capa:
        ind_grande.show()
        ind_mouse.show()
    
    root.after(0, actualizar_scroll_lock_ui)

# F21 (toggle indicadores): deshabilitado en Linux — misma razón que F15.
# keyboard.on_press_key("f21", toggle_indicadores)

def actualizar_ui(capa_msg):
    global indicador_visible_por_capa, color_actual, scroll_lock_activo

    clave = next((k for k in colores if k in capa_msg), None)

    if clave:
        color_actual = colores[clave]
        c = color_actual
        ind_grande.set_color(c)
        ind_mouse.set_color(c)
        indicador_visible_por_capa = True
        logger.debug(f"[UI] Capa detectada: {clave} - Indicadores: {'ON' if INDICADOR_HABILITADO else 'OFF'}")
        
        if INDICADOR_HABILITADO:
            ind_grande.show()
            ind_mouse.show()
    else:
        indicador_visible_por_capa = False
        ind_grande.hide()
        ind_mouse.hide()

    actualizar_scroll_lock_ui()


def actualizar_scroll_lock_ui():
    global scroll_lock_activo
    if scroll_lock_activo and INDICADOR_HABILITADO:
        canvas_scroll.delete("all")
        canvas_scroll.create_rectangle(2, 2, TAMANO_SCROLL-2, TAMANO_SCROLL-2, fill=COLOR_SCROLL, outline="")
        scroll_lock_win.deiconify()
    else:
        canvas_scroll.delete("all")
        scroll_lock_win.withdraw()


# ===============================================================
# HID
# ===============================================================
def escuchar_hid(dev):
    global alt_tab_menu_visible
    capa_actual = None
    print("[HID] Escuchando...")

    while True:
        try:
            data = dev.read(32, timeout_ms=500)
            if not data:
                continue

            msg = "".join(chr(b) for b in data if 31 < b < 127).strip()

            if msg.startswith("CAP_") or msg.startswith("VER_CAPTURE"):
                captura.notificar_cap(msg)
                continue

            if "AT_ON" in msg:
                alt_tab_menu_visible = True
            elif "AT_OFF" in msg:
                alt_tab_menu_visible = False

            nombres = list(colores.keys()) + ["LAYER_BASE"]
            nueva = next((n for n in nombres if n in msg), None)

            if nueva and nueva != capa_actual:
                logger.info(f"======> [HID] CAMBIO DE CAPA DETECTADO: '{capa_actual}' -> '{nueva}'")
                capa_actual = nueva
                root.after(0, lambda c=capa_actual: actualizar_ui(c))

        except Exception as e:
            logger.error(f"[HID ERROR] {e} — Corne desconectado, reintentando...")
            capa_actual = None
            root.after(0, lambda: actualizar_ui(""))
            try:
                dev.close()
            except Exception:
                pass
            dev = _reconectar_hid()
            logger.info("[HID] Corne reconectado")
            try:
                qmk_cal.enviar_calibracion(dev)
            except Exception as e2:
                logger.error(f"[HID] Calibración tras reconexión falló: {e2}")


def _reconectar_hid():
    """Reintenta abrir la interfaz raw HID del Corne hasta que reaparezca."""
    while True:
        path = next((d["path"] for d in hid.enumerate()
                     if d["vendor_id"] == VID and d["product_id"] == PID
                     and d.get("usage_page") == 0xFF60), None)
        if path:
            try:
                nuevo = hid.device()
                nuevo.open_path(path)
                nuevo.set_nonblocking(True)
                return nuevo
            except Exception:
                pass
        time.sleep(2)

# ===============================================================
# ALT-TAB RESET
# ===============================================================
def detectar_clic_reset_alt(dev):
    global alt_tab_menu_visible
    while True:
        if alt_tab_menu_visible and mouse.is_pressed("left"):
            while mouse.is_pressed("left"):
                time.sleep(0.01)
            keyboard.release("alt")
            try:
                buf = [0]*33
                buf[1] = ord("R")
                with captura.WRITE_LOCK:
                    dev.write(buf)
            except:
                pass
            alt_tab_menu_visible = False
        time.sleep(0.01)

# ===============================================================
# SEGUIMIENTO VISUAL DEL MOUSE
# ===============================================================
def seguimiento_mouse():
    """Mueve el punto chico junto al cursor real (posición vía KWin, ver utils/cursor_kwin)."""
    pos = cursor_kwin.get()
    if pos:
        x, y = pos
        ind_mouse.move(x-PUNTO_MOUSE//2, y+OFFSET_MOUSE)
    root.after(16, seguimiento_mouse)


# ===============================================================
# ocultar indicador
# ===============================================================
def ocultar_indicador_si_mouse_cerca():
    while True:
        try:
            if not indicador_visible_por_capa and not scroll_lock_activo:
                time.sleep(0.05)
                continue

            mx, my = pyautogui.position()

            cx = pantalla_ancho // 2
            cy = indicador_y + DIAMETRO // 2
            dx = mx - cx
            dy = my - cy
            distancia = (dx*dx + dy*dy) ** 0.5

            cx_scroll = (pantalla_ancho - DIAMETRO)//2 + DIAMETRO + TAMANO_SCROLL//2
            cy_scroll = 5 + TAMANO_SCROLL//2
            dxs = mx - cx_scroll
            dys = my - cy_scroll
            distancia_scroll = (dxs*dxs + dys*dys) ** 0.5

            ocultar = distancia < RADIO_OCULTAR or distancia_scroll < RADIO_OCULTAR

            if ocultar:
                ind_grande.hide()
                scroll_lock_win.withdraw()
            else:
                if INDICADOR_HABILITADO and indicador_visible_por_capa:
                    ind_grande.show()
                root.after(0, actualizar_scroll_lock_ui)

        except:
            pass

        time.sleep(0.03)

# ===============================================================
# MAIN
# ===============================================================

# Global reference to avoid Garbage Collection del file descriptor del lock
_lock_fd = None

def check_single_instance():
    """Instancia única en Linux vía flock (reemplaza el mutex de Windows)."""
    global _lock_fd
    import fcntl
    import sys
    lock_path = "/tmp/layer_status_script.lock"
    _lock_fd = open(lock_path, "w")
    try:
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("❌ Ya hay una instancia de este script ejecutándose. Saliendo para evitar conflictos...")
        sys.exit(0)

def log_configuracion():
    """Vuelca todos los parámetros de configuración al log para diagnóstico."""
    sep = "─" * 55
    logger.info(sep)
    logger.info("📋 CONFIGURACIÓN DEL SISTEMA")
    logger.info(sep)

    # ── Identificación del teclado ──
    logger.info("┌─ TECLADO")
    logger.info(f"│  VID = 0x{VID:04X}  |  PID = 0x{PID:04X}")

    # ── QMK Mouse (→ módulo independiente) ──
    qmk_cal.log_configuracion()

    # ── Wrap-around (→ módulo independiente) ──
    wrap_around.log_configuracion()

    # ── Resumen de módulos activos ──
    modulos = []
    if qmk_cal.HABILITADA:     modulos.append("QMK calibración")
    if wrap_around.HABILITADA: modulos.append("WRAP-AROUND")
    logger.info("├─ MÓDULOS ACTIVOS: %s", ", ".join(modulos) if modulos else "(ninguno)")

    # ── Otros ──
    logger.info("├─ OTROS")
    logger.info(f"│  RADIO_OCULTAR    = {RADIO_OCULTAR} px")
    logger.info(sep)


def main():
    check_single_instance()
    
    # usage_page 0xFF60 = interfaz raw HID de QMK (VIA), por donde el firmware
    # manda los mensajes de capa. En Linux hid.enumerate() no la devuelve
    # primero (a diferencia de Windows), hay que filtrar explícitamente.
    path = next((d["path"] for d in hid.enumerate()
                if d["vendor_id"] == VID and d["product_id"] == PID
                and d.get("usage_page") == 0xFF60), None)
    if not path:
        print("❌ Teclado no encontrado")
        return

    dev = hid.device()
    dev.open_path(path)
    dev.set_nonblocking(True)

    # ── Volcar toda la configuración al log ──
    log_configuracion()

    # ── Enviar calibración de mouse keys al firmware (solo si HABILITADA = True) ──
    qmk_cal.enviar_calibracion(dev)

    threading.Thread(target=escuchar_hid, args=(dev,), daemon=True).start()
    # Alt-Tab reset: deshabilitado en Linux — requiere `keyboard`/`mouse` (root).
    # threading.Thread(target=detectar_clic_reset_alt, args=(dev,), daemon=True).start()
    # Captura (overlay de Snipping Tool de Windows): sin puerto a Linux, no existe el overlay.
    # threading.Thread(target=captura.hilo_overlay, args=(dev,), daemon=True).start()
    # El punto chico sigue al cursor: KWin manda la posición real por D-Bus.
    cursor_kwin.start()
    root.after(100, seguimiento_mouse)
    # Wrap-around de cursor: sin puerto a Linux (usa ctypes.windll).
    # threading.Thread(target=wrap_around.wrap_loop,
    #                  args=(pantalla_ancho, pantalla_alto), daemon=True).start()
    # ocultar_indicador_si_mouse_cerca: deshabilitado — depende de pyautogui.position(),
    # que no puede leer la posición real del cursor en Wayland (limitación de seguridad
    # de Wayland para apps XWayland en segundo plano), causando parpadeo falso.
    # threading.Thread(target=ocultar_indicador_si_mouse_cerca, daemon=True).start()

    # Inicia la captura de Alt para OneNote 2016 (no disponible en Linux)
    if utils.onenote_nav is not None:
        utils.onenote_nav.run_in_background()
    # Scroll Lock: deshabilitado en Linux — requiere `keyboard` (root) y ctypes.windll.
    # scroll_lock.run_in_background(lambda: scroll_lock_activo)

    logger.info("=" * 55)
    logger.info("  🎯 CORNELL READY — SALTO + WRAP INTEGRADO")
    logger.info("=" * 55)
    print("=" * 40)
    print("  CORNELL READY")
    print("=" * 40)

    root.mainloop()

if __name__ == "__main__":
    main()
