import hid
import tkinter as tk
import threading
import pyautogui
import time
import mouse
import keyboard
import ctypes # Añade esto al inicio de tu archivo

from datetime import datetime
import utils.onenote_nav  # Integración OneNote Nav

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
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "f22_debug.log")
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)03d %(levelname)s - %(message)s', datefmt='%H:%M:%S', handlers=[
    logging.FileHandler(log_path, encoding='utf-8', mode='a'),
    logging.StreamHandler()
])
logger = logging.getLogger(__name__)
logger.info("==========================================")
logger.info("SISTEMA REINICIADO CON DPI AWARENESS")
logger.info(f"ARCHIVO DE LOGS: {log_path}")
logger.info("==========================================")

pyautogui.FAILSAFE = False

# ===============================================================
# CONFIGURACIÓN
# ===============================================================
VID, PID = 0x4653, 0x0001

# MODO 2: Activación del salto por pausa y empuje
MODO_WRAP_DELAY_HABILITADO = True
WRAP_MARGEN_PORCENTAJE = 0.02    # 1% del tamaño de la pantalla
WRAP_DELAY_MS = 0.2              # 200ms

DISTANCIA_SALTO = 450
PAUSA_ENTRE_SALTOS = 0.3
UMBRAL_CAMBIO_DIR = 15 # Reducido para mayor sensibilidad
TURBO_MARGIN = 25
WRAP_MARGIN = 5
VENTANA_GESTO_MS = 0.1  # Aumentado a 100ms
RADIO_OCULTAR = 80

# --- NUEVOS PARÁMETROS DE SUAVIDAD ---
VEL_BASE = 3.0
VEL_MAX = 42.0
ACEL_POR_FRAME = 0.65  # Incremento de velocidad por cada ciclo de 10ms
PAUSA_BORDE_S = 0.6    # Pausa al tocar el borde antes de saltar
COOLDOWN_WRAP = 0.5    # Tiempo mínimo entre saltos automáticos
TIEMPO_ANCLAJE = 0.5   # Segundos que el mouse queda bloqueado tras un salto (reducido para mayor fluidez)
pyautogui.PAUSE = 0    # Eliminar delay interno de pyautogui para máxima fluidez

# --- PARÁMETROS DE PRECISIÓN EN BORDES ---
MARGIN_ESQUINA = 100    # Píxeles desde las esquinas donde el muro es sólido (no salta)
DISTANCIA_FRENADO = 500 # Píxeles antes del borde donde empieza a frenar dinámicamente
MARGEN_BLOQUEO = 50     # Píxeles antes del borde donde el cursor choca y se detiene
UMBRAL_VIAJE_LARGO = 450 # Distancia recorrida para activar el bloqueo de esquinas
ZONA_LIBRE_BORDE = 0.25  # 25% de la pantalla para permitir paso fluido sin bloqueos

# --- PARAMETERS MOUSE WITH KEYBOARD---
QMK_MOUSE_MAX_SPEED    = 7# Camos la velocidad máxima a la mitad (ya no saldrá disparado)
QMK_MOUSE_TIME_TO_MAX  = 30 #  rampa
QMK_MOUSE_INTERVAL     = 18 # Refresco de ~60Hz (estándar de monitores), movimiento muy progresivo
QMK_MOUSE_MOVE_DELTA   = 1    # El paso mínimo posible por ciclo


# ===============================================================
# ESTADOS GLOBALES
# ===============================================================
alt_tab_menu_visible = False
INDICADOR_HABILITADO = True

tecla_horiz_down = False
tecla_vert_down = False
direccion_fijada = 0
direccion_y_fijada = 0
pos_y_referencia = 0

color_actual = "#FFFFFF"
wrap_enabled = threading.Event()
wrap_enabled.set()
indicador_visible_por_capa = False


# ===============================================================
# --- UI CONFIG ---
DIAMETRO, PUNTO_MOUSE, OFFSET_MOUSE = 30, 10, 22

colores = {
    "ALFA": "#66BB6A",
    "MODE": "#8E24AA",
    "COMMIT": "#E53935",
    "NUMB": "#9E9E9E",
    "MIRROR": "#8D6E63",
    "MOVE": "#FFEB3B",
}

root = tk.Tk()
root.withdraw()

pantalla_ancho = root.winfo_screenwidth()
pantalla_alto = root.winfo_screenheight()

root.overrideredirect(True)
root.attributes("-topmost", True)
root.config(bg="magenta")
root.wm_attributes("-transparentcolor", "magenta")
root.geometry(f"{DIAMETRO}x{DIAMETRO}+{(pantalla_ancho-DIAMETRO)//2}+5")

canvas = tk.Canvas(root, width=DIAMETRO, height=DIAMETRO,
                   highlightthickness=0, bg="magenta")
canvas.pack()

mouse_win = tk.Toplevel()
mouse_win.overrideredirect(True)
mouse_win.attributes("-topmost", True)
mouse_win.config(bg="magenta")
mouse_win.wm_attributes("-transparentcolor", "magenta")
mouse_win.geometry(f"{PUNTO_MOUSE}x{PUNTO_MOUSE}+0+0")

canvas_mouse = tk.Canvas(mouse_win, width=PUNTO_MOUSE, height=PUNTO_MOUSE,
                         highlightthickness=0, bg="magenta")
canvas_mouse.pack()

# --- VENTANA PARA EFECTO PULSO ELEGANTE (DESACTIVADO) ---
# ripple_win = tk.Toplevel() ...

# ==========================================
# CONFIGURACIÓN DEL MODO ESPEJO (INTEGRADO)
# ==========================================
MIRROR_DISTANCIA = 25          
MIRROR_LADO = "derecha"        
MIRROR_MOSTRAR_PRINCIPAL = False  
MIRROR_MOSTRAR_DEST_H = False     
MIRROR_MOSTRAR_DEST_V = False     

MIRROR_COLOR_PRINCIPAL = "#00FFFF" 
MIRROR_COLOR_DEST_H = "#FF9900"    
MIRROR_COLOR_DEST_V = "#00FF00"    

MIRROR_GROSOR = 2              
MIRROR_ALTURA = 20            

def create_mirror_window(color):
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.config(bg="magenta")
    win.wm_attributes("-transparentcolor", "magenta")
    win.geometry(f"{MIRROR_GROSOR}x{MIRROR_ALTURA}+0+0")
    win.withdraw()
    canvas = tk.Canvas(win, width=MIRROR_GROSOR, height=MIRROR_ALTURA, highlightthickness=0, bg="magenta")
    canvas.pack()
    canvas.create_line(MIRROR_GROSOR//2, 0, MIRROR_GROSOR//2, MIRROR_ALTURA, fill=color, width=MIRROR_GROSOR)
    return win

win_mirror_main = create_mirror_window(MIRROR_COLOR_PRINCIPAL) if MIRROR_MOSTRAR_PRINCIPAL else None
win_mirror_dest_h = create_mirror_window(MIRROR_COLOR_DEST_H) if MIRROR_MOSTRAR_DEST_H else None
win_mirror_dest_v = create_mirror_window(MIRROR_COLOR_DEST_V) if MIRROR_MOSTRAR_DEST_V else None

es_capa_mirror = False

def ejecutar_teletransporte_horizontal():
    if es_capa_mirror:
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        teleport_x = pantalla_ancho - pt.x
        ctypes.windll.user32.SetCursorPos(teleport_x, pt.y)

def ejecutar_teletransporte_vertical():
    if es_capa_mirror:
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        teleport_y = pantalla_alto - pt.y
        ctypes.windll.user32.SetCursorPos(pt.x, teleport_y)

def on_f13_press(e):
    if keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift"):
        logger.info("Teletransporte HORIZONTAL (Ctrl+Shift+F13) solicitado de forma nativa.")
        ejecutar_teletransporte_horizontal()

def on_f14_press(e):
    if keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift"):
        logger.info("Teletransporte VERTICAL (Ctrl+Shift+F14) solicitado de forma nativa.")
        ejecutar_teletransporte_vertical()

keyboard.on_press_key("f13", on_f13_press)
keyboard.on_press_key("f14", on_f14_press)

# ==========================================
# CONFIGURACIÓN DE SALTOS POR ZONA LIBRE (F15 / F16)
# ==========================================
ZONA_MARGEN_PORCENTAJE = 0.10  # 10% de margen en los extremos de la pantalla
ZONA_UMBRAL_CENTRO = 0.05      # 5% de tolerancia para considerar que se está "en el centro"

# Historial de dirección para saber hacia dónde continuar el salto (1 = Adelante/Derecha/Abajo, -1 = Atrás/Izquierda/Arriba)
_last_h_dir = 0
_last_v_dir = 0
_last_d1_dir = 0
_last_d2_dir = 0

# Variables para el comportamiento por defecto en el centro (sin historial)
# Para F17 (Diagonal 1: Arriba-Izq a Abajo-Der): 1 = Abajo-Der, -1 = Arriba-Izq
ZONA_DIAG1_DEFAULT_DIR = -1 
# Para F18 (Diagonal 2: Abajo-Izq a Arriba-Der): 1 = Arriba-Der, -1 = Abajo-Izq
ZONA_DIAG2_DEFAULT_DIR = 1

def ejecutar_salto_zona_horizontal():
    global _last_h_dir
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    x, y = pt.x, pt.y
    w = pantalla_ancho
    
    margen_px = w * ZONA_MARGEN_PORCENTAJE
    L = margen_px
    C = w * 0.5
    R = w - margen_px
    
    zona_izq = w * (0.5 - ZONA_UMBRAL_CENTRO)
    zona_der = w * (0.5 + ZONA_UMBRAL_CENTRO)
    
    if x < zona_izq:
        target_x = C
        _last_h_dir = 1
        logger.debug(f"[SALTO LIBRE POR ZONA] X:{x}->{target_x} | Izq->Centro")
    elif x > zona_der:
        target_x = C
        _last_h_dir = -1
        logger.debug(f"[SALTO LIBRE POR ZONA] X:{x}->{target_x} | Der->Centro")
    else:
        # Estamos en la zona central
        if _last_h_dir == 1:
            target_x = R
            logger.debug(f"[SALTO LIBRE POR ZONA] X:{x}->{target_x} | Centro->Der")
        elif _last_h_dir == -1:
            target_x = L
            logger.debug(f"[SALTO LIBRE POR ZONA] X:{x}->{target_x} | Centro->Izq")
        else:
            # Si no hay historial, saltar al extremo opuesto de donde estemos inclinados
            if x < C:
                target_x = R
                _last_h_dir = 1
            else:
                target_x = L
                _last_h_dir = -1
            logger.debug(f"[SALTO LIBRE POR ZONA] X:{x}->{target_x} | Centro->Extremo (Sin historial)")
            
    ctypes.windll.user32.SetCursorPos(int(target_x), int(y))

def ejecutar_salto_zona_vertical():
    global _last_v_dir
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    x, y = pt.x, pt.y
    h = pantalla_alto
    
    margen_px = h * ZONA_MARGEN_PORCENTAJE
    T = margen_px
    C = h * 0.5
    B = h - margen_px
    
    zona_arr = h * (0.5 - ZONA_UMBRAL_CENTRO)
    zona_aba = h * (0.5 + ZONA_UMBRAL_CENTRO)
    
    if y < zona_arr:
        target_y = C
        _last_v_dir = 1
        logger.debug(f"[SALTO LIBRE POR ZONA] Y:{y}->{target_y} | Arr->Centro")
    elif y > zona_aba:
        target_y = C
        _last_v_dir = -1
        logger.debug(f"[SALTO LIBRE POR ZONA] Y:{y}->{target_y} | Aba->Centro")
    else:
        if _last_v_dir == 1:
            target_y = B
            logger.debug(f"[SALTO LIBRE POR ZONA] Y:{y}->{target_y} | Centro->Aba")
        elif _last_v_dir == -1:
            target_y = T
            logger.debug(f"[SALTO LIBRE POR ZONA] Y:{y}->{target_y} | Centro->Arr")
        else:
            if y < C:
                target_y = B
                _last_v_dir = 1
            else:
                target_y = T
                _last_v_dir = -1
            logger.debug(f"[SALTO LIBRE POR ZONA] Y:{y}->{target_y} | Centro->Extremo (Sin historial)")
            
    ctypes.windll.user32.SetCursorPos(int(x), int(target_y))

def ejecutar_salto_zona_diagonal_1():
    global _last_d1_dir
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    x, y = pt.x, pt.y
    w, h = pantalla_ancho, pantalla_alto
    
    margen_x = w * ZONA_MARGEN_PORCENTAJE
    margen_y = h * ZONA_MARGEN_PORCENTAJE
    
    C_x, C_y = w * 0.5, h * 0.5
    TL_x, TL_y = margen_x, margen_y
    BR_x, BR_y = w - margen_x, h - margen_y
    
    umbral_x = w * ZONA_UMBRAL_CENTRO
    umbral_y = h * ZONA_UMBRAL_CENTRO
    
    es_centro = (abs(x - C_x) < umbral_x) and (abs(y - C_y) < umbral_y)
    
    if not es_centro:
        if x < C_x and y < C_y:
            target_x, target_y = C_x, C_y
            _last_d1_dir = 1
        elif x >= C_x and y >= C_y:
            target_x, target_y = C_x, C_y
            _last_d1_dir = -1
        else:
            target_x, target_y = C_x, C_y
            _last_d1_dir = ZONA_DIAG1_DEFAULT_DIR
    else:
        dir_to_use = _last_d1_dir if _last_d1_dir != 0 else ZONA_DIAG1_DEFAULT_DIR
        if dir_to_use == 1:
            target_x, target_y = BR_x, BR_y
            _last_d1_dir = 1
        else:
            target_x, target_y = TL_x, TL_y
            _last_d1_dir = -1
            
    ctypes.windll.user32.SetCursorPos(int(target_x), int(target_y))
    logger.debug(f"[SALTO DIAG 1] (X:{x},Y:{y}) -> (X:{target_x},Y:{target_y})")

def ejecutar_salto_zona_diagonal_2():
    global _last_d2_dir
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    x, y = pt.x, pt.y
    w, h = pantalla_ancho, pantalla_alto
    
    margen_x = w * ZONA_MARGEN_PORCENTAJE
    margen_y = h * ZONA_MARGEN_PORCENTAJE
    
    C_x, C_y = w * 0.5, h * 0.5
    BL_x, BL_y = margen_x, h - margen_y
    TR_x, TR_y = w - margen_x, margen_y
    
    umbral_x = w * ZONA_UMBRAL_CENTRO
    umbral_y = h * ZONA_UMBRAL_CENTRO
    
    es_centro = (abs(x - C_x) < umbral_x) and (abs(y - C_y) < umbral_y)
    
    if not es_centro:
        if x < C_x and y > C_y:
            target_x, target_y = C_x, C_y
            _last_d2_dir = 1
        elif x >= C_x and y <= C_y:
            target_x, target_y = C_x, C_y
            _last_d2_dir = -1
        else:
            target_x, target_y = C_x, C_y
            _last_d2_dir = ZONA_DIAG2_DEFAULT_DIR
    else:
        dir_to_use = _last_d2_dir if _last_d2_dir != 0 else ZONA_DIAG2_DEFAULT_DIR
        if dir_to_use == 1:
            target_x, target_y = TR_x, TR_y
            _last_d2_dir = 1
        else:
            target_x, target_y = BL_x, BL_y
            _last_d2_dir = -1
            
    ctypes.windll.user32.SetCursorPos(int(target_x), int(target_y))
    logger.debug(f"[SALTO DIAG 2] (X:{x},Y:{y}) -> (X:{target_x},Y:{target_y})")

def on_f15_press(e):
    if keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift"):
        logger.info("Salto por Zonas HORIZONTAL (Ctrl+Shift+F15) solicitado.")
        ejecutar_salto_zona_horizontal()

def on_f16_press(e):
    if keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift"):
        logger.info("Salto por Zonas VERTICAL (Ctrl+Shift+F16) solicitado.")
        ejecutar_salto_zona_vertical()

# Registrar teclas para el modo de saltos por zona
keyboard.on_press_key("f15", on_f15_press)
keyboard.on_press_key("f16", on_f16_press)

def on_f17_press(e):
    if keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift"):
        logger.info("Salto DIAGONAL 1 (Ctrl+Shift+F17) solicitado.")
        ejecutar_salto_zona_diagonal_1()

def on_f18_press(e):
    if keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift"):
        logger.info("Salto DIAGONAL 2 (Ctrl+Shift+F18) solicitado.")
        ejecutar_salto_zona_diagonal_2()

keyboard.on_press_key("f17", on_f17_press)
keyboard.on_press_key("f18", on_f18_press)


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
        root.withdraw()
        mouse_win.withdraw()
    elif indicador_visible_por_capa:
        root.deiconify()
        mouse_win.deiconify()

# Asignar F21 para alternar la visibilidad de las burbujas
keyboard.on_press_key("f21", toggle_indicadores)

mirror_process = None

def actualizar_ui(capa_msg):
    global indicador_visible_por_capa, color_actual, mirror_process, es_capa_mirror

    clave = next((k for k in colores if k in capa_msg), None)
    
    # Manejar el modo espejo (MIRROR) nativamente en memoria
    if clave == "MIRROR":
        if not es_capa_mirror:
            es_capa_mirror = True
            logger.info("===> [CAPA MIRROR] Activada instantáneamente en memoria.")
            if win_mirror_main: win_mirror_main.deiconify()
            if win_mirror_dest_h: win_mirror_dest_h.deiconify()
            if win_mirror_dest_v: win_mirror_dest_v.deiconify()
    else:
        if es_capa_mirror:
            es_capa_mirror = False
            logger.info("===> [CAPA MIRROR] Desactivada.")
            if win_mirror_main: win_mirror_main.withdraw()
            if win_mirror_dest_h: win_mirror_dest_h.withdraw()
            if win_mirror_dest_v: win_mirror_dest_v.withdraw()

    if clave:
        color_actual = colores[clave]
        c = color_actual
        canvas.delete("all")
        canvas.create_oval(2, 2, DIAMETRO-2, DIAMETRO-2, fill=c, outline="")
        canvas_mouse.delete("all")
        canvas_mouse.create_oval(0, 0, PUNTO_MOUSE, PUNTO_MOUSE, fill=c, outline="")
        indicador_visible_por_capa = True
        logger.debug(f"[UI] Capa detectada: {clave} - Indicadores: {'ON' if INDICADOR_HABILITADO else 'OFF'}")
        
        if INDICADOR_HABILITADO:
            root.deiconify()
            mouse_win.deiconify()
    else:
        indicador_visible_por_capa = False
        root.withdraw()
        mouse_win.withdraw()


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
            print("[HID ERROR]", e)
            break

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
                dev.write(buf)
            except:
                pass
            alt_tab_menu_visible = False
        time.sleep(0.01)

# ===============================================================
# SEGUIMIENTO VISUAL DEL MOUSE
# ===============================================================
def seguimiento_mouse():
    while True:
        try:
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            x, y = pt.x, pt.y
            mouse_win.geometry(f"+{x-PUNTO_MOUSE//2}+{y+OFFSET_MOUSE}")
            
            # --- Actualización instantánea de los indicadores Mirror ---
            if es_capa_mirror:
                if MIRROR_LADO.lower() == "izquierda":
                    main_x = x - MIRROR_DISTANCIA - (MIRROR_GROSOR // 2)
                else:
                    main_x = x + MIRROR_DISTANCIA - (MIRROR_GROSOR // 2)
                main_y = y - (MIRROR_ALTURA // 2)
                
                if win_mirror_main:
                    win_mirror_main.geometry(f"+{main_x}+{main_y}")
                
                if win_mirror_dest_h:
                    dest_x = pantalla_ancho - x
                    if MIRROR_LADO.lower() == "izquierda":
                        ghost_h_x = dest_x - MIRROR_DISTANCIA - (MIRROR_GROSOR // 2)
                    else:
                        ghost_h_x = dest_x + MIRROR_DISTANCIA - (MIRROR_GROSOR // 2)
                    win_mirror_dest_h.geometry(f"+{ghost_h_x}+{main_y}")
                    
                if win_mirror_dest_v:
                    dest_y = pantalla_alto - y
                    ghost_v_y = dest_y - (MIRROR_ALTURA // 2)
                    win_mirror_dest_v.geometry(f"+{main_x}+{ghost_v_y}")

        except:
            pass
        time.sleep(0.01)

# ===============================================================
# F24 / F23 – MOVIMIENTO SUAVE Y CONTROLADO
# ===============================================================

forzar_nuevo_viaje = False

def presiona_f24(e):
    global tecla_horiz_down, forzar_nuevo_viaje
    if not tecla_horiz_down:
        forzar_nuevo_viaje = True
        logger.debug("[TECLA F24 PRESIONADA] - NUEVO VIAJE FORZADO")
    tecla_horiz_down = True

def suelta_f24(e):
    global tecla_horiz_down, direccion_fijada
    tecla_horiz_down = False
    direccion_fijada = 0
    logger.debug("[TECLA F24 SOLTADA]")

def presiona_f23(e):
    global tecla_vert_down, forzar_nuevo_viaje
    if not tecla_vert_down:
        forzar_nuevo_viaje = True
        logger.debug("[TECLA F23 PRESIONADA] - NUEVO VIAJE FORZADO")
    tecla_vert_down = True

def suelta_f23(e):
    global tecla_vert_down, direccion_y_fijada
    tecla_vert_down = False
    direccion_y_fijada = 0
    logger.debug("[TECLA F23 SOLTADA]")

keyboard.on_press_key("f24", presiona_f24)
keyboard.on_release_key("f24", suelta_f24)
keyboard.on_press_key("f23", presiona_f23)
keyboard.on_release_key("f23", suelta_f23)

def loop_movimiento_suave():
    global direccion_fijada, direccion_y_fijada
    
    speed_x = 0
    speed_y = 0
    pause_until = 0
    distancia_recorrida = 0
    anclado_x = False
    anclado_y = False
    limite_x = 0
    limite_y = 0
    dir_anclaje_x = 0
    dir_anclaje_y = 0
    tiempo_anclaje_x = 0
    tiempo_anclaje_y = 0
    
    last_x, last_y = pyautogui.position()
    
    origen_swipe_x, origen_swipe_y = pyautogui.position()
    prev_actual_x, prev_actual_y = origen_swipe_x, origen_swipe_y
    tiempo_ultimo_movimiento_x = time.time()
    tiempo_ultimo_movimiento_y = time.time()
    
    tiempo_choque_x = 0
    tiempo_choque_y = 0
    borde_activo_x = 0
    borde_activo_y = 0
    
    while True:
        # --- OBTENER POSICIÓN REAL (Sin latencia de PyAutoGUI) ---
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        curr_x, curr_y = pt.x, pt.y
        ahora = time.time()
        
        global forzar_nuevo_viaje
        if forzar_nuevo_viaje:
            origen_swipe_x, origen_swipe_y = curr_x, curr_y
            if anclado_x:
                anclado_x = False
                logger.debug("[MURO X LIBERADO por nueva pulsación]")
            if anclado_y:
                anclado_y = False
                logger.debug("[MURO Y LIBERADO por nueva pulsación]")
            forzar_nuevo_viaje = False
            tiempo_ultimo_movimiento_x = ahora
            tiempo_ultimo_movimiento_y = ahora
        
        # --- RASTREO INDEPENDIENTE DE INACTIVIDAD (X e Y) ---
        # Reseteamos el origen si no hay movimiento en ESE eje específico por 150ms.
        # Esto evita que "deslizarse" verticalmente por el borde bloquee el reset horizontal.
        
        # Eje X
        if abs(curr_x - prev_actual_x) > 0 or tecla_horiz_down or speed_x > 0:
            tiempo_ultimo_movimiento_x = ahora
        elif ahora - tiempo_ultimo_movimiento_x > 0.15:
            if origen_swipe_x != curr_x:
                origen_swipe_x = curr_x
                if anclado_x:
                    anclado_x = False
                    logger.debug("[MURO X LIBERADO por inactividad horizontal]")
        
        # Eje Y
        if abs(curr_y - prev_actual_y) > 0 or tecla_vert_down or speed_y > 0:
            tiempo_ultimo_movimiento_y = ahora
        elif ahora - tiempo_ultimo_movimiento_y > 0.15:
            if origen_swipe_y != curr_y:
                origen_swipe_y = curr_y
                if anclado_y:
                    anclado_y = False
                    logger.debug("[MURO Y LIBERADO por inactividad vertical]")

        # 1. DETECTAR DIRECCIÓN
        if tecla_horiz_down:
            dx = curr_x - last_x
            if 2 <= abs(dx) < (pantalla_ancho // 2):
                direccion_fijada = 1 if dx > 0 else -1
        else:
            direccion_fijada = 0
            speed_x = 0
            
        if tecla_vert_down:
            dy = curr_y - last_y
            if 2 <= abs(dy) < (pantalla_alto // 2):
                direccion_y_fijada = 1 if dy > 0 else -1
        else:
            direccion_y_fijada = 0
            speed_y = 0

        # DETECTAR SALTO EXTERNO (Con Filtro de Zonas del 25% y Distancia de Viaje)
        if abs(curr_x - last_x) > (pantalla_ancho // 2) and not anclado_x:
            # Determinamos si fue un viaje largo basándonos en el origen real del swipe (universal)
            dist_viajada_x = abs(last_x - origen_swipe_x)
            es_viaje_corto = dist_viajada_x < UMBRAL_VIAJE_LARGO
            
            # Solo anclamos si NO es un viaje corto
            if not es_viaje_corto: 
                anclado_x = True
                tiempo_anclaje_x = ahora
                dir_anclaje_x = direccion_fijada if direccion_fijada != 0 else (1 if curr_x < last_x else -1)
                
                # Para que se "quede en la pared" sin pelear con programas de envoltura externos,
                # lo devolvemos 5 píxeles ANTES del borde absoluto.
                if curr_x < last_x: # Cruzó el borde derecho hacia el izquierdo
                    limite_x = pantalla_ancho - MARGEN_BLOQUEO
                else: # Cruzó el borde izquierdo hacia el derecho
                    limite_x = MARGEN_BLOQUEO
                    
                logger.debug(f"[SALTO PROTEGIDO EXT] X:{last_x}->{curr_x} | ANCLAJE EN BORDE: {limite_x} (Dist: {dist_viajada_x})")
            else:
                logger.debug(f"[SALTO LIBRE POR ZONA] X:{last_x}->{curr_x} | Viaje Corto (Dist: {dist_viajada_x})")
            
            # Tras un salto, el nuevo origen es donde aterrizamos (o donde fuimos anclados)
            if anclado_x:
                origen_swipe_x = limite_x
                last_x = limite_x
            else:
                origen_swipe_x = curr_x
                last_x = curr_x

        if abs(curr_y - last_y) > (pantalla_alto // 2) and not anclado_y:
            dist_viajada_y = abs(last_y - origen_swipe_y)
            es_viaje_corto_y = dist_viajada_y < UMBRAL_VIAJE_LARGO
                
            if not es_viaje_corto_y:
                anclado_y = True
                tiempo_anclaje_y = ahora
                dir_anclaje_y = direccion_y_fijada if direccion_y_fijada != 0 else (1 if curr_y < last_y else -1)
                
                if curr_y < last_y:
                    limite_y = pantalla_alto - MARGEN_BLOQUEO
                else:
                    limite_y = MARGEN_BLOQUEO
                    
                logger.debug(f"[SALTO PROTEGIDO EXT] Y:{last_y}->{curr_y} | ANCLAJE EN BORDE: {limite_y} (Dist: {dist_viajada_y})")
            else:
                logger.debug(f"[SALTO LIBRE POR ZONA] Y:{last_y}->{curr_y} | Viaje Corto (Dist: {dist_viajada_y})")
                
            if anclado_y:
                origen_swipe_y = limite_y
                last_y = limite_y
            else:
                origen_swipe_y = curr_y
                last_y = curr_y

        # --- APLICAR ANCLAJE (FUERZA CONSTANTE) ---
        if anclado_x:
            if ahora - tiempo_anclaje_x > TIEMPO_ANCLAJE:
                anclado_x = False
                logger.debug("[MURO X LIBERADO por tiempo]")
            elif ahora - tiempo_anclaje_x > 0.05:
                # Detectar si el usuario intenta alejarse del muro (movimiento fuerte opuesto)
                # Esperamos 50ms tras anclar para ignorar la distancia del salto inicial
                dx_manual = curr_x - last_x
                if abs(dx_manual) >= 8: # Umbral alto para ignorar jitter
                    if (1 if dx_manual > 0 else -1) == -dir_anclaje_x:
                        anclado_x = False
                        logger.debug("[MURO X LIBERADO por movimiento opuesto]")
                
            if anclado_x:
                # FORZAR POSICIÓN CONSTANTE: No dejamos que QMK lo mueva ni 1 píxel
                ctypes.windll.user32.SetCursorPos(int(limite_x), int(curr_y))
                curr_x = limite_x
                speed_x = 0

        if anclado_y:
            if ahora - tiempo_anclaje_y > TIEMPO_ANCLAJE:
                anclado_y = False
                logger.debug("[MURO Y LIBERADO por tiempo]")
            elif ahora - tiempo_anclaje_y > 0.05:
                dy_manual = curr_y - last_y
                if abs(dy_manual) >= 8:
                    if (1 if dy_manual > 0 else -1) == -dir_anclaje_y:
                        anclado_y = False
                        logger.debug("[MURO Y LIBERADO por movimiento opuesto]")
                
                if anclado_y:
                    ctypes.windll.user32.SetCursorPos(int(curr_x), int(limite_y))
                    curr_y = limite_y
                    speed_y = 0

        # 2. PROCESAR MOVIMIENTO ACELERADO
        if ahora > pause_until:
            if direccion_fijada != 0 or direccion_y_fijada != 0:
                if direccion_fijada != 0:
                    speed_x = min(VEL_MAX, (speed_x if speed_x > 0 else VEL_BASE) + ACEL_POR_FRAME)
                if direccion_y_fijada != 0:
                    speed_y = min(VEL_MAX, (speed_y if speed_y > 0 else VEL_BASE) + ACEL_POR_FRAME)
                
                step_x = speed_x * direccion_fijada
                step_y = speed_y * direccion_y_fijada
                distancia_recorrida += (abs(step_x) + abs(step_y))

                nx = curr_x + step_x
                ny = curr_y + step_y
                
                # --- LÓGICA DE FRENADO Y BORDES ---
                dist_borde_x = min(nx, pantalla_ancho - nx)
                dist_borde_y = min(ny, pantalla_alto - ny)
                
                es_viaje_corto = abs(curr_x - origen_swipe_x) < UMBRAL_VIAJE_LARGO
                es_viaje_corto_y = abs(curr_y - origen_swipe_y) < UMBRAL_VIAJE_LARGO
                
                if dist_borde_x < DISTANCIA_FRENADO and not es_viaje_corto:
                    # Frenado dinámico proporcional a la distancia al borde
                    factor_x = max(0.1, dist_borde_x / DISTANCIA_FRENADO)
                    speed_x = max(VEL_BASE, speed_x * factor_x)
                    nx = curr_x + (speed_x * direccion_fijada)

                if dist_borde_y < DISTANCIA_FRENADO and not es_viaje_corto_y:
                    factor_y = max(0.1, dist_borde_y / DISTANCIA_FRENADO)
                    speed_y = max(VEL_BASE, speed_y * factor_y)
                    ny = curr_y + (speed_y * direccion_y_fijada)
                if nx <= MARGEN_BLOQUEO and not es_viaje_corto:
                    nx = MARGEN_BLOQUEO
                    speed_x = 0 # Frena antes del borde
                elif nx >= pantalla_ancho - MARGEN_BLOQUEO and not es_viaje_corto:
                    nx = pantalla_ancho - MARGEN_BLOQUEO
                    speed_x = 0
                        
                if ny <= MARGEN_BLOQUEO and not es_viaje_corto:
                    ny = MARGEN_BLOQUEO
                    speed_y = 0
                elif ny >= pantalla_alto - MARGEN_BLOQUEO and not es_viaje_corto:
                    ny = pantalla_alto - MARGEN_BLOQUEO
                    speed_y = 0

                nx = max(0, min(pantalla_ancho - 1, nx))
                ny = max(0, min(pantalla_alto - 1, ny))
                if nx != curr_x or ny != curr_y:
                    pyautogui.moveTo(nx, ny)
                last_x, last_y = nx, ny
            else:
                # MOVIMIENTO MANUAL (Bloqueo de Posición y Freno)
                vx = curr_x - last_x
                vy = curr_y - last_y
                
                # RASTREO DE VIAJE
                es_viaje_corto_x = abs(curr_x - origen_swipe_x) < UMBRAL_VIAJE_LARGO
                es_viaje_corto_y = abs(curr_y - origen_swipe_y) < UMBRAL_VIAJE_LARGO

                # BLOQUEO DE POSICIÓN (Muro de 50px para viajes largos manuales)
                if not es_viaje_corto_x:
                    if curr_x >= pantalla_ancho - MARGEN_BLOQUEO and vx > 0:
                        ctypes.windll.user32.SetCursorPos(int(pantalla_ancho - MARGEN_BLOQUEO), int(curr_y))
                        curr_x = pantalla_ancho - MARGEN_BLOQUEO
                        vx = 0
                    elif curr_x <= MARGEN_BLOQUEO and vx < 0:
                        ctypes.windll.user32.SetCursorPos(int(MARGEN_BLOQUEO), int(curr_y))
                        curr_x = MARGEN_BLOQUEO
                        vx = 0


                if not es_viaje_corto_y:
                    if curr_y >= pantalla_alto - MARGEN_BLOQUEO and vy > 0:
                        ctypes.windll.user32.SetCursorPos(int(curr_x), int(pantalla_alto - MARGEN_BLOQUEO))
                        curr_y = pantalla_alto - MARGEN_BLOQUEO
                        vy = 0
                    elif curr_y <= MARGEN_BLOQUEO and vy < 0:
                        ctypes.windll.user32.SetCursorPos(int(curr_x), int(MARGEN_BLOQUEO))
                        curr_y = MARGEN_BLOQUEO
                        vy = 0


                if abs(vx) > 1 or abs(vy) > 1:
                    dist_borde_x = min(curr_x, pantalla_ancho - curr_x)
                    dist_borde_y = min(curr_y, pantalla_alto - curr_y)
                    
                    # Detectar si se mueve HACIA el borde
                    hacia_borde_x = (vx > 0 and curr_x > pantalla_ancho // 2) or (vx < 0 and curr_x < pantalla_ancho // 2)
                    hacia_borde_y = (vy > 0 and curr_y > pantalla_alto // 2) or (vy < 0 and curr_y < pantalla_alto // 2)
                    
                    # Detectar si estamos en zona segura (25% lateral) para desactivar el freno
                    en_zona_segura_x = curr_x < (pantalla_ancho * ZONA_LIBRE_BORDE) or curr_x > (pantalla_ancho * (1 - ZONA_LIBRE_BORDE))
                    en_zona_segura_y = curr_y < (pantalla_alto * ZONA_LIBRE_BORDE) or curr_y > (pantalla_alto * (1 - ZONA_LIBRE_BORDE))

                    # Aplicar límite de velocidad dinámico en zona de frenado SOLO si no estamos en zona segura y no es viaje corto
                    if hacia_borde_x and dist_borde_x < DISTANCIA_FRENADO and not en_zona_segura_x and not es_viaje_corto_x:
                        # Velocidad máxima permitida disminuye conforme nos acercamos al borde
                        v_permitida = max(VEL_BASE, VEL_MAX * (dist_borde_x / DISTANCIA_FRENADO))
                        if abs(vx) > v_permitida:
                            nueva_x = last_x + (v_permitida * (1 if vx > 0 else -1))
                            ctypes.windll.user32.SetCursorPos(int(nueva_x), int(curr_y))
                            curr_x = nueva_x
                            
                    if hacia_borde_y and dist_borde_y < DISTANCIA_FRENADO and not en_zona_segura_y and not es_viaje_corto_y:
                        v_permitida_y = max(VEL_BASE, VEL_MAX * (dist_borde_y / DISTANCIA_FRENADO))
                        if abs(vy) > v_permitida_y:
                            nueva_y = last_y + (v_permitida_y * (1 if vy > 0 else -1))
                            ctypes.windll.user32.SetCursorPos(int(curr_x), int(nueva_y))
                            curr_y = nueva_y
                            
                last_x, last_y = curr_x, curr_y
        else:
            last_x, last_y = curr_x, curr_y
            
        if MODO_WRAP_DELAY_HABILITADO:
            margen_x = int(pantalla_ancho * WRAP_MARGEN_PORCENTAJE)
            margen_y = int(pantalla_alto * WRAP_MARGEN_PORCENTAJE)
            
            vx_wrap = curr_x - prev_actual_x
            vy_wrap = curr_y - prev_actual_y
            
            # --- EVALUAR EJE X ---
            if curr_x >= pantalla_ancho - margen_x - 1:
                ctypes.windll.user32.SetCursorPos(pantalla_ancho - margen_x - 1, int(curr_y))
                curr_x = pantalla_ancho - margen_x - 1
                if vx_wrap > 0:
                    if borde_activo_x != 1:
                        borde_activo_x = 1
                        tiempo_choque_x = ahora
                    elif ahora - tiempo_choque_x >= WRAP_DELAY_MS:
                        nuevo_x = margen_x + 5
                        ctypes.windll.user32.SetCursorPos(nuevo_x, int(curr_y))
                        curr_x = nuevo_x
                        borde_activo_x = 0
                        tiempo_choque_x = ahora + 0.5
                elif vx_wrap < 0:
                    borde_activo_x = 0
            elif curr_x <= margen_x:
                ctypes.windll.user32.SetCursorPos(margen_x, int(curr_y))
                curr_x = margen_x
                if vx_wrap < 0:
                    if borde_activo_x != -1:
                        borde_activo_x = -1
                        tiempo_choque_x = ahora
                    elif ahora - tiempo_choque_x >= WRAP_DELAY_MS:
                        nuevo_x = pantalla_ancho - margen_x - 5
                        ctypes.windll.user32.SetCursorPos(nuevo_x, int(curr_y))
                        curr_x = nuevo_x
                        borde_activo_x = 0
                        tiempo_choque_x = ahora + 0.5
                elif vx_wrap > 0:
                    borde_activo_x = 0
            else:
                borde_activo_x = 0
                
            # --- EVALUAR EJE Y ---
            if curr_y >= pantalla_alto - margen_y - 1:
                ctypes.windll.user32.SetCursorPos(int(curr_x), pantalla_alto - margen_y - 1)
                curr_y = pantalla_alto - margen_y - 1
                if vy_wrap > 0:
                    if borde_activo_y != 1:
                        borde_activo_y = 1
                        tiempo_choque_y = ahora
                    elif ahora - tiempo_choque_y >= WRAP_DELAY_MS:
                        nuevo_y = margen_y + 5
                        ctypes.windll.user32.SetCursorPos(int(curr_x), nuevo_y)
                        curr_y = nuevo_y
                        borde_activo_y = 0
                        tiempo_choque_y = ahora + 0.5
                elif vy_wrap < 0:
                    borde_activo_y = 0
            elif curr_y <= margen_y:
                ctypes.windll.user32.SetCursorPos(int(curr_x), margen_y)
                curr_y = margen_y
                if vy_wrap < 0:
                    if borde_activo_y != -1:
                        borde_activo_y = -1
                        tiempo_choque_y = ahora
                    elif ahora - tiempo_choque_y >= WRAP_DELAY_MS:
                        nuevo_y = pantalla_alto - margen_y - 5
                        ctypes.windll.user32.SetCursorPos(int(curr_x), nuevo_y)
                        curr_y = nuevo_y
                        borde_activo_y = 0
                        tiempo_choque_y = ahora + 0.5
                elif vy_wrap > 0:
                    borde_activo_y = 0
            else:
                borde_activo_y = 0
                
        prev_actual_x, prev_actual_y = curr_x, curr_y
        time.sleep(0.01)




# ===============================================================
# ocultar indicador
# ===============================================================
def ocultar_indicador_si_mouse_cerca():
    while True:
        try:
            if not indicador_visible_por_capa:
                time.sleep(0.05)
                continue

            mx, my = pyautogui.position()

            # Centro del indicador superior
            cx = pantalla_ancho // 2
            cy = 5 + DIAMETRO // 2

            dx = mx - cx
            dy = my - cy
            distancia = (dx*dx + dy*dy) ** 0.5

            if distancia < RADIO_OCULTAR:
                root.withdraw()
            elif INDICADOR_HABILITADO and indicador_visible_por_capa:
                root.deiconify()

        except:
            pass

        time.sleep(0.03)

# ===============================================================
# MAIN
# ===============================================================

# Global reference to avoid Garbage Collection of the mutex
_mutex_ref = None

def check_single_instance():
    global _mutex_ref
    kernel32 = ctypes.windll.kernel32
    mutex_name = "LAYER_STATUS_SCRIPT_UNIQUE_MUTEX_123"
    _mutex_ref = kernel32.CreateMutexW(None, False, mutex_name)
    if kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        print("❌ Ya hay una instancia de este script ejecutándose. Saliendo para evitar conflictos...")
        import sys
        sys.exit(0)

def enviar_calibracion_qmk(dev):
    """Construye el buffer HID con la firma 'M' y envía las variables al Corne."""
    try:
        # Creamos un buffer de 33 bytes (1 byte para Report ID + 32 bytes de datos estándar de QMK)
        buf = [0] * 33
        buf[0] = 0x00                     # Report ID (Requerido por Windows)
        buf[1] = ord("M")                 # Firma 'M' que espera el 'if (data[0] == 'M')' en C
        buf[2] = QMK_MOUSE_MAX_SPEED     # data[1] en QMK
        buf[3] =  QMK_MOUSE_TIME_TO_MAX     # data[2] en QMK
        buf[4] =   QMK_MOUSE_INTERVAL  # data[3] en QMK

       # buf[5] =        # data[4] en QMK
       # buf[6] = QMK_MOUSE_MOVE_DELTA     # data[5] en QMK

        dev.write(buf)
        logger.info(f"[HID] Calibración enviada con éxito al Corne.")
    except Exception as e:
        logger.error(f"[HID ERROR] No se pudieron enviar los valores de calibración: {e}")

def main():
    check_single_instance()
    
    path = next((d["path"] for d in hid.enumerate()
                if d["vendor_id"] == VID and d["product_id"] == PID), None)
    if not path:
        print("❌ Teclado no encontrado")
        return

    dev = hid.device()
    dev.open_path(path)
    dev.set_nonblocking(True)

 # Enviamos los datos al teclado inmediatamente después de conectar
    enviar_calibracion_qmk(dev)

    threading.Thread(target=escuchar_hid, args=(dev,), daemon=True).start()
    threading.Thread(target=detectar_clic_reset_alt, args=(dev,), daemon=True).start()
    threading.Thread(target=seguimiento_mouse, daemon=True).start()
    threading.Thread(target=loop_movimiento_suave, daemon=True).start()
    # threading.Thread(target=wrap_loop, daemon=True).start()
    threading.Thread(target=ocultar_indicador_si_mouse_cerca, daemon=True).start()
    
    # Inicia la captura de Alt para OneNote 2016
    utils.onenote_nav.run_in_background()

    print("========================================")
    print("  CORNELL READY – SALTO + WRAP INTEGRADO ")
    print("========================================")

    root.mainloop()

if __name__ == "__main__":
    main()
