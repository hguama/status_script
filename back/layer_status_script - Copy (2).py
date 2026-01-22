import hid
import tkinter as tk
import threading
import pyautogui
import time
import ctypes

# Colores por capa
colores = {
    "ALFA": "#66BB6A",       # verde
    "MODE": "#8E24AA",       # morado
    "COMMIT": "#E53935",     # rojo
    "NUMB": "#9E9E9E",       # gris
    "MOUSE_1": "#FFEB3B",    # amarillo
    "MOUSE_2": "#64B5F6",    # azul claro
}

# Tamaño del indicador superior
DIAMETRO = 40

# Tamaño del punto bajo el mouse
PUNTO_MOUSE = 14
OFFSET_MOUSE = 28   # qué tan abajo del cursor aparece

# ---------- VENTANA INDICADOR SUPERIOR ----------
root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-alpha", 0.0)
root.config(bg="magenta")
root.wm_attributes("-transparentcolor", "magenta")

pantalla_ancho = root.winfo_screenwidth()
pos_x = (pantalla_ancho - DIAMETRO) // 2
pos_y = 5
root.geometry(f"{DIAMETRO}x{DIAMETRO}+{pos_x}+{pos_y}")
root.withdraw()

canvas = tk.Canvas(root, width=DIAMETRO, height=DIAMETRO,
                   highlightthickness=0, bg="magenta")
canvas.pack()

def dibujar_boton(color):
    canvas.delete("all")
    MARGEN = 2
    canvas.create_oval(MARGEN, MARGEN,
                       DIAMETRO - MARGEN, DIAMETRO - MARGEN,
                       fill=color, outline="")

# ---------- VENTANA DEL PUNTO BAJO EL MOUSE ----------
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
    canvas_mouse.create_oval(0, 0, PUNTO_MOUSE, PUNTO_MOUSE,
                             fill=color, outline="")

# Mover la ventana del punto siguiendo el mouse
def seguimiento_mouse():
    while True:
        try:
            x, y = pyautogui.position()
            mouse_win.geometry(f"+{x - PUNTO_MOUSE//2}+{y + OFFSET_MOUSE}")
        except:
            pass
        time.sleep(0.01)

# ---------- ACTUALIZAR COLOR ----------
def actualizar_color(capa_activa):
    if capa_activa in colores:
        color = colores[capa_activa]

        # Indicador superior
        dibujar_boton(color)
        root.deiconify()
        root.attributes("-alpha", 0.9)

        # Punto bajo el mouse
        dibujar_punto_mouse(color)
        mouse_win.deiconify()
        mouse_win.attributes("-alpha", 1.0)
    else:
        root.withdraw()
        mouse_win.withdraw()

# ---------- WRAP AROUND DEL MOUSE ----------
user32 = ctypes.windll.user32
screen_width = user32.GetSystemMetrics(0)
screen_height = user32.GetSystemMetrics(1)
margin = 1
wrap_enabled = threading.Event()

def wrap_mouse_loop():
    print("🖱️ Hilo de wrap-around iniciado correctamente.")
    while True:
        try:
            if wrap_enabled.is_set():
                x, y = pyautogui.position()

                if x >= screen_width - margin:
                    pyautogui.moveTo(margin, y)
                elif x <= 0:
                    pyautogui.moveTo(screen_width - margin, y)

                if y >= screen_height - margin:
                    pyautogui.moveTo(x, margin)
                elif y <= 0:
                    pyautogui.moveTo(x, screen_height - margin)

            time.sleep(0.01)

        except Exception as e:
            print(f"⚠️ Error en wrap-around: {e}")
            time.sleep(0.5)

# ---------- ESCUCHA HID ----------
def escuchar_hid():
    dispositivo = next((d['path'] for d in hid.enumerate()
                        if d['vendor_id'] == 0x4653 and d['product_id'] == 0x0001 and d['usage_page'] != 1), None)

    if not dispositivo:
        print("❌ Dispositivo no encontrado.")
        return

    try:
        dev = hid.device()
        dev.open_path(dispositivo)
        print("✅ Escuchando RAW HID...")

        capa_actual = None

        while True:
            data = dev.read(32, timeout_ms=500)
            if data:
                mensaje = bytes(data).decode('utf-8', errors='ignore').strip('\x00')
                print("Mensaje recibido:", mensaje)

                nueva_capa = next((c for c in colores if c in mensaje), None)

                if nueva_capa != capa_actual:
                    capa_actual = nueva_capa
                    root.after(0, actualizar_color, nueva_capa)

                    if capa_actual == "MOUSE_2":
                        wrap_enabled.set()
                        print("🌀 Wrap-around ACTIVADO (MOUSE_2)")
                    else:
                        wrap_enabled.clear()
                        print("🛑 Wrap-around DESACTIVADO")

    except Exception as e:
        print("❌ Error:", e)

# ---------- MAIN ----------
def main():
    threading.Thread(target=escuchar_hid, daemon=True).start()
    threading.Thread(target=wrap_mouse_loop, daemon=True).start()
    threading.Thread(target=seguimiento_mouse, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()
