# --- Se agrega. Salto horizontal.  ---
import hid
import tkinter as tk
import threading
import pyautogui
import time
import mouse
import keyboard 

pyautogui.FAILSAFE = False

# --- CONFIGURACIÓN ---
DISTANCIA_SALTO = 450    
PAUSA_ENTRE_SALTOS = 0.4 
TURBO_MARGIN = 25        
UMBRAL_CAMBIO_DIR = 2    

colores = {
    "ALFA": "#66BB6A", "MODE": "#8E24AA", "COMMIT": "#E53935",
    "NUMB": "#9E9E9E", "MOUSE_1": "#FFEB3B", "MOUSE_2": "#64B5F6",
}

DIAMETRO, PUNTO_MOUSE, OFFSET_MOUSE = 40, 14, 28

# Variables de estado
tecla_horiz_down = False
direccion_fijada = 0  
pos_x_referencia = 0 

# ===============================================================
# UI – Indicadores
# ===============================================================
root = tk.Tk()
root.withdraw()
pantalla_ancho, pantalla_alto = root.winfo_screenwidth(), root.winfo_screenheight()
root.deiconify()
root.overrideredirect(True)
root.attributes("-topmost", True, "-alpha", 0.0)
root.config(bg="magenta")
root.wm_attributes("-transparentcolor", "magenta")
root.geometry(f"{DIAMETRO}x{DIAMETRO}+{(pantalla_ancho-DIAMETRO)//2}+5")

canvas = tk.Canvas(root, width=DIAMETRO, height=DIAMETRO, highlightthickness=0, bg="magenta")
canvas.pack()

mouse_win = tk.Toplevel()
mouse_win.overrideredirect(True)
mouse_win.attributes("-topmost", True, "-alpha", 0.0)
mouse_win.config(bg="magenta")
mouse_win.wm_attributes("-transparentcolor", "magenta")
mouse_win.geometry(f"{PUNTO_MOUSE}x{PUNTO_MOUSE}+0+0")

canvas_mouse = tk.Canvas(mouse_win, width=PUNTO_MOUSE, height=PUNTO_MOUSE, highlightthickness=0, bg="magenta")
canvas_mouse.pack()

def actualizar_ui(capa):
    if capa in colores:
        c = colores[capa]
        canvas.delete("all")
        canvas.create_oval(2, 2, DIAMETRO-2, DIAMETRO-2, fill=c, outline="")
        canvas_mouse.delete("all")
        canvas_mouse.create_oval(0, 0, PUNTO_MOUSE, PUNTO_MOUSE, fill=c, outline="")
        root.deiconify(); root.attributes("-alpha", 0.9)
        mouse_win.deiconify(); mouse_win.attributes("-alpha", 1.0)
    else:
        root.withdraw(); mouse_win.withdraw()

# ===============================================================
# Detección de Teclado (F22)
# ===============================================================
def presiona_f22(e):
    global tecla_horiz_down, direccion_fijada, pos_x_referencia
    if not tecla_horiz_down:
        # Capturamos la posición un instante después para asegurar que hay vector de movimiento
        tecla_horiz_down = True
        pos_x_referencia, _ = pyautogui.position() 
        direccion_fijada = 0

def suelta_f22(e):
    global tecla_horiz_down, direccion_fijada
    tecla_horiz_down = False
    direccion_fijada = 0 

keyboard.on_press_key("f22", presiona_f22)
keyboard.on_release_key("f22", suelta_f22)

# ===============================================================
# Lógica de Salto (Pausa Activa)
# ===============================================================
def loop_auto_salto():
    global direccion_fijada, pos_x_referencia
    while True:
        if tecla_horiz_down:
            curr_x, curr_y = pyautogui.position()
            dx = curr_x - pos_x_referencia
            
            # Si aún no sabemos a dónde ir, buscamos cualquier movimiento
            if direccion_fijada == 0:
                if abs(dx) > 0: # Cualquier movimiento, por pequeño que sea
                    direccion_fijada = 1 if dx > 0 else -1
            

            if direccion_fijada != 0:
                nx = curr_x + (DISTANCIA_SALTO * direccion_fijada)
                nx = max(TURBO_MARGIN, min(pantalla_ancho - TURBO_MARGIN, nx))
                pyautogui.moveTo(nx, curr_y)
                pos_x_referencia = nx 
                
                inicio_pausa = time.time()
                while time.time() - inicio_pausa < PAUSA_ENTRE_SALTOS:
                    if not tecla_horiz_down: break
                    temp_x, _ = pyautogui.position()
                    diff_pausa = temp_x - pos_x_referencia
                    if abs(diff_pausa) >= UMBRAL_CAMBIO_DIR:
                        nueva_dir = 1 if diff_pausa > 0 else -1
                        if nueva_dir != direccion_fijada:
                            direccion_fijada = nueva_dir
                            break 
                    time.sleep(0.01)
        time.sleep(0.01)

# ===============================================================
# Wrap-Around y Hilos Finales
# ===============================================================
def wrap_loop():
    while True:
        if not tecla_horiz_down:
            try:
                if not mouse.is_pressed("left"):
                    x, y = pyautogui.position()
                    if x <= 0: pyautogui.moveTo(pantalla_ancho - 2, y)
                    elif x >= pantalla_ancho - 1: pyautogui.moveTo(1, y)
                    if y <= 0: pyautogui.moveTo(x, pantalla_alto - 2)
                    elif y >= pantalla_alto - 1: pyautogui.moveTo(x, 1)
            except: pass
        time.sleep(0.005)

def escuchar_hid():
    dispositivo = next((d['path'] for d in hid.enumerate() if d['vendor_id']==0x4653 and d['product_id']==0x0001), None)
    if not dispositivo: return
    dev = hid.device()
    dev.open_path(dispositivo)
    capa_actual = None
    while True:
        data = dev.read(32, timeout_ms=500)
        if not data: continue
        msg = "".join(chr(b) for b in data if 31 < b < 127)
        nueva_capa = next((c for c in colores if c in msg), None)
        if nueva_capa != capa_actual:
            capa_actual = nueva_capa
            root.after(0, lambda: actualizar_ui(capa_actual))

def seguimiento_mouse():
    while True:
        try:
            x, y = pyautogui.position()
            mouse_win.geometry(f"+{x - PUNTO_MOUSE//2}+{y + OFFSET_MOUSE}")
        except: pass
        time.sleep(0.01)

def main():
    threading.Thread(target=escuchar_hid, daemon=True).start()
    threading.Thread(target=seguimiento_mouse, daemon=True).start()
    threading.Thread(target=loop_auto_salto, daemon=True).start()
    threading.Thread(target=wrap_loop, daemon=True).start()
    
    # Mensaje de inicio limpio
    print("========================================")
    print("   TECLADO CORNELL LISTO PARA FUNCIONAR  ")
    print("   Modo Salto Horizontal (F22) Activo    ")
    print("========================================")
    
    root.mainloop()

if __name__ == "__main__":
    main()