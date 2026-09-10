# Especificación: polls del script principal a eventos

## 0. Manifiesto

| id | archivo | rol | estado |
|---|---|---|---|
| C1 | `spec-polls-eventos.md` | contrato | especificación · 2026-09-09 · auditoría 2026-09-10 (§5) · trasladada a este repo 2026-09-10 (rutas `qmk_*` y commits refieren a `qmk_firmware`) |

## 1. Objetivo

Optimizar el sistema eliminando el desperdicio de recursos del monitoreo constante: hoy 6 hilos giran 24/7 preguntando lo mismo (teclado, botón, cursor, bordes) aunque nada cambie. Pasar a eventos —el hilo duerme y solo trabaja cuando algo pasa— con el modelo ya probado de `utils/captura`. Mismo comportamiento observable, CPU en reposo. Repo: `D:\scripts\status script`, rama `main` (limpio al especificar).

## 2. Funcionalidades (qué hacen hoy → qué debe pasar tras el cambio)

### 2.1 Lector HID (`escuchar_hid`)
Hace hoy: gira sin pausa leyendo `raw_hid` en no-bloqueante; ante reporte arma texto, actualiza bandera alt-tab (`AT_ON/OFF`), resuelve capa por subcadena y refresca la UI por `root.after`; despacha `CAP_*` al módulo captura.
Verificación: cambiar de capa 3 veces → el indicador muestra cada capa (≤600ms); Alt+Tab → bandera activa; un hold de captura → el log muestra `CAP_ARM`→`CAP_EVT`; 10 min en reposo sin `[HID ERROR]` ni CPU del hilo.

### 2.2 Reset de alt-tab (`detectar_clic_reset_alt`)
Hace hoy: cada 10ms pregunta si el botón izquierdo está presionado con alt-tab visible; al soltarlo, suelta `Alt` y manda `R` al teclado (que limpia y reporta `AT_OFF`).
Verificación: Alt+Tab → clic izquierdo en una ventana → se confirma la ventana, `Alt` queda suelto y el indicador vuelve a `BASE`; clics normales (sin alt-tab) no mandan nada; un hold de captura no dispara `R`.

### 2.3 Seguimiento del mouse (`seguimiento_mouse`)
Hace hoy: cada 10ms lee el cursor y coloca el punto indicador debajo de él.
Verificación: mover el cursor por ambas pantallas → el punto lo sigue sin saltos ni rezago visible; al detener, queda quieto bajo el cursor.

### 2.4 Ocultar indicador (`ocultar_indicador_si_mouse_cerca`)
Hace hoy: cada 30-50ms mide distancia cursor→indicadores y los oculta (`withdraw`) si se acerca, los muestra al alejarse (incluye scroll-lock).
Verificación: acercar el cursor al indicador de capa → desaparece; alejarlo → reaparece; igual con el de scroll-lock cuando está activo.

### 2.5 Wrap de bordes (`wrap_around.wrap_loop`)
Hace hoy: cada 10ms revisa si el cursor choca con un borde; tras el dwell (`DELAY_MS`) lo salta al borde opuesto con cooldown anti-rebote y lo registra en log.
Verificación: empujar a cada borde (4) → salta al opuesto tras la espera habitual, una sola vez (sin doble salto); el log marca el salto; mover normal no dispara nada.

### 2.6 Scroll-lock (`scroll_lock`, loop 10ms)
Hace hoy: acumula el movimiento en pasos y emite scroll horizontal; al desactivar resetea acumuladores (log `Desactivado`).
Verificación: con scroll-lock activo, mover el mouse → scroll horizontal por pasos; desactivar → log `Desactivado` y ningún scroll posterior; con scroll-lock inactivo, mover no scrollea.

## 3. Excluidos (no se tocan)

`utils/captura` (ya es eventos), loop del hold en firmware (acotado a 800ms, no es 24/7) y `sleep` de `onenote_nav` (delays de automatización entre teclas, no polls).

## 4. Validación general

Commitear punto de partida → convertir → `py_compile` → reiniciar script (arranque limpio, sin tracebacks) → 10 min en reposo (CPU ~0, hilos vivos) → §2 una por una → uso diario normal 1 día → si algo regresa, revert por git.

## 5. Auditoría 2026-09-10 — hallazgos y veredicto

Auditado contra el código real (`layer_status_script.py` ≈457 líneas, `utils/*`) y el log de uso diario (4001 saltos de wrap, 65 activaciones de scroll-lock, 0 `[HID ERROR]` en 1.7MB).

**Veredicto: no aprobar como está.** Objetivo e inventario (§§1-2) correctos; la estrategia única es incorrecta para 4 de los 6; el riesgo es `high`, no `medium`; el punto de partida no está limpio.

### 5.1 Estrategia por categoría (reemplaza el modelo único)

| Categoría | Polls | Conversión correcta |
|---|---|---|
| Discretos | §2.1 HID, §2.2 clic-alt | evento real: lectura **bloqueante** (`set_nonblocking(False)` + `read(timeout_ms=500)`); `mouse.on_button` (verificado: existe en la librería ya importada) |
| Muestreo continuo | §2.3 dot, §2.4 ocultar, §2.5 wrap, §2.6 scroll | sin evento puro: **un solo hilo de cursor** a 10ms que reparte a los 4 + trabajo solo si la posición cambió |

### 5.2 Punto por punto

- **§1:** conteo exacto (6). Pero `main` **no está limpio**: `M layer_status_script.py` + `?? utils/captura/` (migración Task 15 sin commitear, verificado 2026-09-10). El "commitear punto de partida" de §4 arrastraría trabajo ajeno.
- **§2.1:** error conceptual — `captura.hilo_overlay` duerme en un `Event` que arma **este mismo lector**; el lector no puede usar ese modelo. La cura es lectura bloqueante. Además el hilo muere con `break` ante cualquier excepción (todos los indicadores dependen de él): falta reintento.
- **§2.2:** el único convertible limpio. Borde sin acotar: con alt-tab visible, el `MS_BTN1` de un hold de captura sí dispara `R`.
- **§2.3/§2.4:** consumen el mismo dato en dos hilos; candidatas a fusión. Ambas llaman Tk desde hilo secundario (bug latente: `mouse_win.geometry`, `withdraw`/`deiconify` fuera del hilo principal).
- **§2.5:** el más riesgoso — dwell/anti-rebote calibrados a cadencia fija + `SetCursorPos` que realimenta eventos. Extra: `DOCs/wrap_around.md` documenta `FORCE_TIMEOUT` (350ms) que **no existe en el código**.
- **§2.6:** el suavizado de eje (`recent_* × 0.82`, calibrado a 100Hz) cambia de comportamiento con eventos de frecuencia variable.
- **§4:** `py_compile` no valida hilos; "CPU ~0" sin baseline medible; falta kill-switch por módulo; "revert por git" exige un commit previo que hoy no existe.

### 5.3 Ajustes requeridos antes de implementar

1. Riesgo `⬟ high` (puede romper utilidades de uso diario) — aplicado en el plan 2026-09-10.
2. Commitear la migración de captura (punto de partida real limpio).
3. Reescribir §2 por categoría + agregar Riesgos/Alcance como en `spec-migracion-captura.md`.
4. Convertir por pieza (6 commits o banderas `HABILITADA`), no big-bang.
5. Unificar la fuente de cursor; todo Tk por `root.after`; reintento en el lector HID.
