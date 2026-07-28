# Plan: Indicador visual de Scroll Lock

## Objetivo
Agregar un indicador visual cuadrado de color cian que aparezca junto al indicador de capas existente cuando el modo Scroll Lock está activo (Ctrl+Shift+F15 mantenido).

## Contexto
- El comportamiento HOLD de Ctrl+Shift+F15 se mantiene sin cambios.
- QMK controla el toggle real; este script solo refleja visualmente el estado activo mientras se mantiene la tecla.
- El indicador de capas actual es un círculo de 30px en `layer_status_script.py` (líneas 118-132).
- No existe system tray; toda la visualización usa overlay tkinter.

## Decisiones de diseño

1. **Indicador independiente**: Crear una segunda ventana `scroll_lock_win` (Toplevel) separada de `root`, posicionada a la derecha del indicador de capas (`x = (pantalla_ancho-DIAMETRO)//2 + DIAMETRO + 4`, misma `y = 5`).

2. **Forma y color**: Canvas 24x24 dibujando un cuadrado relleno en cian puro (`#00FFFF`). Tamaño menor al círculo (30px) pero visible.

3. **Visibilidad**: 
   - Mostrar solo si `scroll_lock_activo == True` y `INDICADOR_HABILITADO == True`.
   - Ocultar si no hay scroll lock, si `INDICADOR_HABILITADO` es False, o si el mouse está cerca.

4. **Comportamiento al ocultar mouse**: Extender `ocultar_indicador_si_mouse_cerca()` para considerar el centro del nuevo cuadrado en el cálculo de distancia (radio 80px).

5. **Sin cambios en `Utils/scroll_lock.py`**: Solo se agrega UI en `layer_status_script.py`.

## Tareas de implementación

1. **Crear ventana del indicador Scroll Lock**
   - Definir constantes: `TAMANO_SCROLL = 24`, `COLOR_SCROLL = "#00FFFF"`.
   - En `layer_status_script.py`, después de crear `mouse_win`, crear `scroll_lock_win` con `overrideredirect`, `-topmost`, transparencia magenta, geometría `24x24+{x}+5`.

2. **Agregar canvas del indicador**
   - Crear `canvas_scroll` en `scroll_lock_win` (24x24, sin bordes, bg magenta).
   - Dibujar cuadrado con `create_rectangle` al inicializar (o vacío, se llena al activar).

3. **Función para actualizar el indicador de scroll lock**
   - Crear `actualizar_scroll_lock_ui()` que:
     - Si `scroll_lock_activo` y `INDICADOR_HABILITADO`: dibuja cuadrado cian, deiconifica.
     - Si no: borra cuadrado, withdraw.

4. **Integrar con eventos existentes**
   - Llamar `actualizar_scroll_lock_ui()` desde `activar_scroll_lock()` y `desactivar_scroll_lock()` usando `root.after(0, ...)`.
   - También llamar desde `toggle_indicadores()` para ocultar/mostrar según corresponda.

5. **Actualizar función de ocultar por proximidad del mouse**
   - En `ocultar_indicador_si_mouse_cerca()`, además del centro del círculo principal, calcular distancia al centro del `scroll_lock_win`:
     - `cx_scroll = (pantalla_ancho - DIAMETRO)//2 + DIAMETRO + TAMANO_SCROLL//2`
     - `cy_scroll = 5 + TAMANO_SCROLL//2`
   - Si el mouse está a menos de 80px de AMBOS centros, ocultar ambas ventanas.

6. **Revisar manejo de threads**
   - Asegurar que todas las actualizaciones de UI del nuevo indicador pasen por `root.after(0, ...)`.

## Validación
- Ejecutar `python layer_status_script.py` y verificar que al mantener Ctrl+Shift+F15 aparezca un cuadrado cian a la derecha del círculo de capas.
- Verificar que al soltar F15 el cuadrado desaparece.
- Verificar que al presionar F21 (toggle indicadores) ambos indicadores se ocultan/muestran juntos.
- Verificar que al acercar el mouse al indicador (dentro de 80px) ambos se ocultan temporalmente.
