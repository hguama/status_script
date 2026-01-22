import hid
import tkinter as tk
import threading

# Colores por capa
colores = {
    "ALFA": "#66BB6A",
    "MODE": "#8E24AA",
    "COMMIT": "#E53935",
    "NUMB": "#9E9E9E",
}

# Tamaño del botón redondo S
DIAMETRO = 40  

# Crear ventana completamente transparente
root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-alpha", 0.0)
root.config(bg="magenta")  # color transparente
root.wm_attributes("-transparentcolor", "magenta")

# Centrar en parte superior de la pantalla
pantalla_ancho = root.winfo_screenwidth()
pos_x = (pantalla_ancho - DIAMETRO) // 2
pos_y = 5  # ⬅ Cambiado: posición vertical más baja para evitar la barra
root.geometry(f"{DIAMETRO}x{DIAMETRO}+{pos_x}+{pos_y}")
root.withdraw()

# Canvas para dibujar el botón
canvas = tk.Canvas(root, width=DIAMETRO, height=DIAMETRO, highlightthickness=0, bg="magenta")
canvas.pack()

# Dibuja el botón redondo
def dibujar_boton(color):
    canvas.delete("all")
    MARGEN = 2
    canvas.create_oval(MARGEN, MARGEN, DIAMETRO - MARGEN, DIAMETRO - MARGEN, fill=color, outline="")

# Cambia el color según la capa activa
def actualizar_color(capa_activa):
    if capa_activa in colores:
        dibujar_boton(colores[capa_activa])
        root.deiconify()
        root.attributes("-alpha", 0.9)
    else:
        root.withdraw()

# Escucha HID en segundo plano
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
    except Exception as e:
        print("❌ Error:", e)

# Ejecutar aplicación
def main():
    threading.Thread(target=escuchar_hid, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()

