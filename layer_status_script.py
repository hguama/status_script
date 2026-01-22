# ===============================================================
#   layer_status_script_TurboF22_v1_5.py
#   ---------------------------------------------------------------
#   Versión 1.5 - Corrección "Frenado de Seguridad"
#
#   Cambios respecto v1.4:
#    • NUEVO: Margen de seguridad (TURBO_MARGIN). Cuando usas Turbo,
#      el cursor se detiene unos píxeles antes del borde real.
#      Esto evita que al soltar la tecla, el Wrap-Around se active
#      accidentalmente.
# ===============================================================

import hid
import tkinter as tk
import threading
import pyautogui
import time
import logging
import mouse  
from pynput import mouse as pynput_mouse  

pyautogui.FAILSAFE = False
INTENT_EPSILON = 2      # movimiento mínimo para considerar intención

# --- Variables de estado para el scroll ---
scroll_auto_speed = 0
last_static_x = 0
last_static_y = 0
last_scroll_time = 0
 
logging.getLogger().handlers.clear()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s"
)


# -------- CONFIG --------
TURBO_MULTIPLIER = 2.5   # Un poco más rápido si gustas
SAMPLE_INTERVAL = 0.08   # Muestreo ligeramente más rápido
ACTION_KEY = "F22"

# === NUEVO: MARGEN DE SEGURIDAD ===
# Píxeles antes del borde donde se detiene el mouse si usas TURBO.
# 10 o 15 px es suficiente para evitar el salto accidental.
TURBO_MARGIN = 12 

# Rebote (usado en lógica anterior, mantenido por si acaso)
REBOUND_DISTANCE = 18
REBOUND_STEPS = 6
REBOUND_DELAY = 0.007

# Colores de capas
colores = {
    "ALFA": "#66BB6A",
    "MODE": "#8E24AA",
    "COMMIT": "#E53935",
    "NUMB": "#9E9E9E",
    "MOUSE_1": "#FFEB3B",
    "MOUSE_2": "#64B5F6",
}

DIAMETRO = 40
PUNTO_MOUSE = 14
OFFSET_MOUSE = 28

# ===============================================================
# UI – Indicador
# ===============================================================
root = tk.Tk()
root.withdraw()
pantalla_ancho = root.winfo_screenwidth()
pantalla_alto = root.winfo_screenheight()
root.deiconify()

root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-alpha", 0.0)
root.config(bg="magenta")
root.wm_attributes("-transparentcolor", "magenta")
pos_x = (pantalla_ancho - DIAMETRO) // 2
pos_y = 5
root.geometry(f"{DIAMETRO}x{DIAMETRO}+{pos_x}+{pos_y}")
root.withdraw()

canvas = tk.Canvas(root, width=DIAMETRO, height=DIAMETRO,
                   highlightthickness=0, bg="magenta")
canvas.pack()

def dibujar_boton(color):
    canvas.delete("all")
    M = 2
    canvas.create_oval(M, M, DIAMETRO-M, DIAMETRO-M, fill=color, outline="")

mouse_win = tk.Toplevel()
mouse_win.overrideredirect(True)
mouse_win.attributes("-topmost", True)
mouse_win.attributes("-alpha", 0.0)
mouse_win.config(bg="magenta")
mouse_win.wm_attributes("-transparentcolor", "magenta")
mouse_win.geometry(f"{PUNTO_MOUSE}x{PUNTO_MOUSE}+0+0")
mouse_win.withdraw()

canvas_mouse = tk.Canvas(mouse_win, width=PUNTO_MOUSE, height=PUNTO_MOUSE,
                         highlightthickness=0, bg="magenta")
canvas_mouse.pack()

def dibujar_punto_mouse(color):
    canvas_mouse.delete("all")
    canvas_mouse.create_oval(0, 0, PUNTO_MOUSE, PUNTO_MOUSE, fill=color, outline="")

# ===============================================================
# Seguimiento del mouse
# ===============================================================
def seguimiento_mouse():
    while True:
        try:
            x, y = pyautogui.position()
            mouse_win.geometry(f"+{x - PUNTO_MOUSE//2}+{y + OFFSET_MOUSE}")
        except:
            pass
        time.sleep(0.01)

# ===============================================================
# Ocultar indicador si el cursor pasa encima
# ===============================================================
ocultado_por_cursor = False
def check_cursor_encima():
    global ocultado_por_cursor
    try:
        x, y = pyautogui.position()
        encima = (pos_x <= x <= pos_x + DIAMETRO and
                  pos_y <= y <= pos_y + DIAMETRO)
        if encima and not ocultado_por_cursor:
            ocultado_por_cursor = True
            root.withdraw()
        elif not encima and ocultado_por_cursor:
            ocultado_por_cursor = False
            root.deiconify()
            root.attributes("-alpha", 0.9)
    except:
        pass
    root.after(20, check_cursor_encima)

# ===============================================================
# Keyboard fallback
# ===============================================================
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except:
    KEYBOARD_AVAILABLE = False

turbo_on = False

# ===============================================================
# Mover al centro (F23)
# ===============================================================
def mover_al_centro(source="unknown"):
    cx = pantalla_ancho // 2
    cy = pantalla_alto // 2
    pyautogui.moveTo(cx, cy, duration=0)
    print(f"🎯 Centro ({source}) → ({cx}, {cy})")

# ===============================================================
# Turbo loop (MODIFICADO CON MARGEN)
# ===============================================================
def turbo_loop():
    last_human_x, last_human_y = pyautogui.position()
    intent_dx, intent_dy = 0, 0
    
    while True:
        try:
            # Si estamos en scroll automático, pausa la lógica turbo posicional
            if scroll_auto_speed != 0:
                intent_dx, intent_dy = 0, 0
                last_human_x, last_human_y = pyautogui.position()
                time.sleep(SAMPLE_INTERVAL)
                continue

            x, y = pyautogui.position()
            human_dx, human_dy = x - last_human_x, y - last_human_y
            
            if abs(human_dx) > 0 or abs(human_dy) > 0:
                intent_dx, intent_dy = human_dx, human_dy
                last_human_x, last_human_y = x, y
            
            if turbo_on and (intent_dx != 0 or intent_dy != 0):
                # Calculamos el destino teórico
                raw_target_x = int(x + intent_dx * (TURBO_MULTIPLIER - 1))
                raw_target_y = int(y + intent_dy * (TURBO_MULTIPLIER - 1))

                # --- APLICACIÓN DEL MARGEN DE SEGURIDAD ---
                # En lugar de permitir llegar a 0 o pantalla_ancho, 
                # limitamos a [TURBO_MARGIN, pantalla_ancho - TURBO_MARGIN]
                
                # Eje X
                nx = max(TURBO_MARGIN, min(pantalla_ancho - 1 - TURBO_MARGIN, raw_target_x))
                
                # Eje Y
                ny = max(TURBO_MARGIN, min(pantalla_alto - 1 - TURBO_MARGIN, raw_target_y))
                
                pyautogui.moveTo(nx, ny, duration=0)
                
        except: pass
        time.sleep(SAMPLE_INTERVAL)


# ===============================================================
#   Turbo Scroll - Versión Integrada
# ===============================================================
def on_scroll(x, y, dx, dy):
    global scroll_auto_speed, last_static_x, last_static_y, last_scroll_time
    if turbo_on:
        current_time = time.time()
        time_delta = current_time - last_scroll_time
        last_scroll_time = current_time
        
        if scroll_auto_speed == 0:
            last_static_x, last_static_y = pyautogui.position()

        if time_delta < 0.04:
            impulso = dy * 7  
        elif time_delta < 0.08:
            impulso = dy * 3
        else:
            impulso = dy * 1.2
            
        scroll_auto_speed += impulso

listener = pynput_mouse.Listener(on_scroll=on_scroll)
listener.start()

def scroll_auto_executor():
    global scroll_auto_speed
    while True:
        if turbo_on and scroll_auto_speed != 0:
            pyautogui.moveTo(last_static_x, last_static_y, duration=0)
            pyautogui.scroll(int(scroll_auto_speed * 15))
            scroll_auto_speed *= 0.97
        else:
            scroll_auto_speed = 0
        time.sleep(0.02)

# ===============================================================
# Wrap-around cuando Turbo OFF 
# ===============================================================
def wrap_loop():
    while True:
        # Solo ejecutamos el wrap si Turbo está OFF Y NO se está presionando click izquierdo
        if not turbo_on:
            try:
                if not mouse.is_pressed("left"):
                    x, y = pyautogui.position()
                    
                    # Wrap Horizontal
                    if x <= 0:
                        pyautogui.moveTo(pantalla_ancho - 2, y)
                    elif x >= pantalla_ancho - 1:
                        pyautogui.moveTo(1, y)
                    
                    # Wrap Vertical
                    if y <= 0:
                        pyautogui.moveTo(x, pantalla_alto - 2)
                    elif y >= pantalla_alto - 1:
                        pyautogui.moveTo(x, 1)
                else:
                    pass
            except:
                pass
        time.sleep(0.004)

# ===============================================================
# HID listener
# ===============================================================
def escuchar_hid():
    dispositivo = next((d['path'] for d in hid.enumerate()
                        if d['vendor_id']==0x4653 and d['product_id']==0x0001 and d['usage_page']!=1),
                       None)
    if not dispositivo:
        print("❌ HID no encontrado.")
        return

    dev = hid.device()
    dev.open_path(dispositivo)
    print("✅ Escuchando RAW HID...")
    capa_actual = None

    while True:
        data = dev.read(32, timeout_ms=500)
        if not data:
            continue

        msg = "".join(chr(b) for b in data if b != 0)

        nueva_capa = next((c for c in colores if c in msg), None)
        if nueva_capa != capa_actual:
            capa_actual = nueva_capa
            root.after(0, actualizar_color, nueva_capa)

        global turbo_on
        if "F22_DOWN" in msg:
            turbo_on = True
            print("⚡ TURBO ON")
        if "F22_UP" in msg:
            turbo_on = False
            print("⚡ TURBO OFF")

        if "F23" in msg:
            mover_al_centro("HID")

# ===============================================================
# UI actualización
# ===============================================================
def actualizar_color(capa_activa):
    if capa_activa in colores:
        c = colores[capa_activa]
        dibujar_boton(c)
        root.deiconify()
        root.attributes("-alpha", 0.9)
        dibujar_punto_mouse(c)
        mouse_win.deiconify()
        mouse_win.attributes("-alpha", 1.0)
    else:
        root.withdraw()
        mouse_win.withdraw()

# ===============================================================
# MAIN
# ===============================================================
def main():
    threading.Thread(target=escuchar_hid, daemon=True).start()
    threading.Thread(target=seguimiento_mouse, daemon=True).start()
    threading.Thread(target=turbo_loop, daemon=True).start()
    threading.Thread(target=wrap_loop, daemon=True).start()
    threading.Thread(target=scroll_auto_executor, daemon=True).start()

    if KEYBOARD_AVAILABLE:
        keyboard.on_press_key("f22", lambda _: set_turbo(True))
        keyboard.on_release_key("f22", lambda _: set_turbo(False))
        keyboard.on_press_key("f23", lambda _: mover_al_centro("keyboard"))
        print("🔑 Hotkeys F22 (Turbo) y F23 (Centro) activas.")

    root.after(20, check_cursor_encima)
    print("✔ Script TurboF22 v1.5 iniciado con MARGEN DE SEGURIDAD.")
    root.mainloop()

def set_turbo(state):
    global turbo_on
    turbo_on = state
    print("⚡ TURBO", "ON" if state else "OFF")

if __name__ == "__main__":
    main()