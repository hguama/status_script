import hid
import tkinter as tk
import threading
import pyautogui
import time
import mouse
import keyboard
import ctypes # Añade esto al inicio de tu archivo

from datetime import datetime

pyautogui.FAILSAFE = False

# ===============================================================
# CONFIGURACIÓN
# ===============================================================
VID, PID = 0x4653, 0x0001

DISTANCIA_SALTO = 450
PAUSA_ENTRE_SALTOS = 0.3
UMBRAL_CAMBIO_DIR = 25
TURBO_MARGIN = 25
WRAP_MARGIN = 2
VENTANA_GESTO_MS = 0.03  # 30 ms



# ===============================================================
# ESTADOS GLOBALES
# ===============================================================
alt_tab_menu_visible = False

tecla_horiz_down = False
direccion_fijada = 0
pos_x_referencia = 0

wrap_enabled = threading.Event()
wrap_enabled.set()

# ===============================================================
# UI
# ===============================================================
DIAMETRO, PUNTO_MOUSE, OFFSET_MOUSE = 40, 14, 28

colores = {
    "ALFA": "#66BB6A",
    "MODE": "#8E24AA",
    "COMMIT": "#E53935",
    "NUMB": "#9E9E9E",
    "MOUSE_1": "#FFEB3B",
    "MOUSE_2": "#64B5F6",
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

def actualizar_ui(capa_msg):
    clave = next((k for k in colores if k in capa_msg), None)
    if clave:
        c = colores[clave]
        canvas.delete("all")
        canvas.create_oval(2, 2, DIAMETRO-2, DIAMETRO-2, fill=c, outline="")
        canvas_mouse.delete("all")
        canvas_mouse.create_oval(0, 0, PUNTO_MOUSE, PUNTO_MOUSE, fill=c, outline="")
        root.deiconify()
        mouse_win.deiconify()
    else:
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
            x, y = pyautogui.position()
            mouse_win.geometry(f"+{x-PUNTO_MOUSE//2}+{y+OFFSET_MOUSE}")
        except:
            pass
        time.sleep(0.01)

# ===============================================================
# F22 – SALTO HORIZONTAL INTELIGENTE
# ===============================================================
def presiona_f22(e):
    global tecla_horiz_down, direccion_fijada, pos_x_referencia

    if tecla_horiz_down:
        return

    tecla_horiz_down = True
    x0, _ = pyautogui.position()
    pos_x_referencia = x0
    direccion_fijada = 0

    # 🔍 Ventana corta para capturar gesto rápido
    inicio = time.time()
    while time.time() - inicio < VENTANA_GESTO_MS:
        x1, _ = pyautogui.position()
        dx = x1 - x0
        if abs(dx) > 0:
            direccion_fijada = 1 if dx > 0 else -1
            pos_x_referencia = x1
            break
        time.sleep(0.005)

def suelta_f22(e):
    global tecla_horiz_down, direccion_fijada
    tecla_horiz_down = False
    direccion_fijada = 0

keyboard.on_press_key("f22", presiona_f22)
keyboard.on_release_key("f22", suelta_f22)

def loop_auto_salto():
    global direccion_fijada, pos_x_referencia
    while True:
        if tecla_horiz_down:
            curr_x, curr_y = pyautogui.position()
            dx = curr_x - pos_x_referencia

            if direccion_fijada == 0 and abs(dx) > 0:
                direccion_fijada = 1 if dx > 0 else -1

            if direccion_fijada != 0:
                nx = curr_x + (DISTANCIA_SALTO * direccion_fijada)
                nx = max(TURBO_MARGIN, min(pantalla_ancho - TURBO_MARGIN, nx))
                pyautogui.moveTo(nx, curr_y)
                pos_x_referencia = nx

                inicio = time.time()
                while time.time() - inicio < PAUSA_ENTRE_SALTOS:
                    if not tecla_horiz_down:
                        break
                    tx, _ = pyautogui.position()
                    diff = tx - pos_x_referencia
                    if abs(diff) >= UMBRAL_CAMBIO_DIR:
                        nueva = 1 if diff > 0 else -1
                        if nueva != direccion_fijada:
                            direccion_fijada = nueva
                            break
                    time.sleep(0.01)
        time.sleep(0.01)

# ===============================================================
# WRAP AROUND (PROTEGIDO)
# ===============================================================

def wrap_loop():
    # Función para detectar si el botón izquierdo está presionado a nivel sistema
    def click_izquierdo_activo():
        # GetAsyncKeyState(0x01) verifica el estado del botón izquierdo (clic = 0x01)
        # Si el bit más alto está activo, el botón está presionado/bloqueado
        return ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000 != 0

    while True:
        # Ahora verificamos: 
        # 1. Tu variable de F22
        # 2. La librería mouse (clic físico)
        # 3. La API de Windows (clic bloqueado/virtual)
        if not tecla_horiz_down and not mouse.is_pressed("left") and not click_izquierdo_activo():
            try:
                x, y = pyautogui.position()
                
                # Solo ejecutamos el salto si el mouse está REALMENTE en el borde (0 o ancho-1)
                # y no hay ninguna selección activa detectada por Windows
                if x <= 0:
                    pyautogui.moveTo(pantalla_ancho - WRAP_MARGIN, y)
                elif x >= pantalla_ancho - 1:
                    pyautogui.moveTo(WRAP_MARGIN, y)

                if y <= 0:
                    pyautogui.moveTo(x, pantalla_alto - WRAP_MARGIN)
                elif y >= pantalla_alto - 1:
                    pyautogui.moveTo(x, WRAP_MARGIN)
            except:
                pass
        
        # Aumentamos ligeramente el tiempo de espera para que al sistema 
        # le de tiempo de procesar el estado del clic bloqueado
        time.sleep(0.01)
# ===============================================================
# MAIN
# ===============================================================
def main():
    path = next((d["path"] for d in hid.enumerate()
                if d["vendor_id"] == VID and d["product_id"] == PID), None)
    if not path:
        print("❌ Teclado no encontrado")
        return

    dev = hid.device()
    dev.open_path(path)
    dev.set_nonblocking(True)

    threading.Thread(target=escuchar_hid, args=(dev,), daemon=True).start()
    threading.Thread(target=detectar_clic_reset_alt, args=(dev,), daemon=True).start()
    threading.Thread(target=seguimiento_mouse, daemon=True).start()
    threading.Thread(target=loop_auto_salto, daemon=True).start()
    threading.Thread(target=wrap_loop, daemon=True).start()

    print("========================================")
    print("  CORNELL READY – SALTO + WRAP INTEGRADO ")
    print("========================================")

    root.mainloop()

if __name__ == "__main__":
    main()
