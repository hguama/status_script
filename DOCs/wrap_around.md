# WRAP-AROUND — Salto de borde a borde de pantalla

> **Archivo:** `utils/wrap_around/__init__.py`  
> **Propósito:** Transportar el cursor automáticamente al borde opuesto
> cuando llega a un extremo de la pantalla.

---

## 🎯 ¿Qué hace?

Monitorea constantemente la posición del cursor. Cuando detecta que el
cursor "choca" contra un borde de la pantalla y el usuario sigue empujando
en esa dirección, lo **transporta al borde opuesto**.

```
┌──────────────────────────────────────────┐
│  ← cursor sale por la derecha...         │
│                                          │
│  ...y aparece en la izquierda  →         │
│                                          │
│  Igual para arriba/abajo.               │
└──────────────────────────────────────────┘
```

### Lógica de detección de intención

El módulo distingue entre dos intenciones del usuario cuando está en el borde:

| Intención | Cómo se detecta | Qué hace |
|---|---|---|
| **Cruzar al otro lado** | Empuja en dirección al borde sin mover el otro eje | Inicia un timer de 50 ms → salta |
| **Navegar íconos** | Mueve el eje perpendicular (vertical si está en borde lateral) | Cancela el timer de cruce |
| **Movimiento ambiguo** | Movimiento mixto o pequeño | **Mantiene el estado actual** (no resetea) |

> **Novedad:** antes, cualquier movimiento mixto reseteaba el timer.
> Ahora solo se resetea si hay navegación **claramente** perpendicular.
> Además, un *force timeout* de 350 ms garantiza que si llevás mucho
> tiempo en el borde, el cruce se ejecuta igual.

---

## 🎛️ Parámetros

Todos en `utils/wrap_around/__init__.py`:

```python
HABILITADA         = True    # Bandera maestra

MARGEN_PORCENTAJE  = 0.005   # 0.5% del borde (~10 px en 1920)
DELAY_MS           = 0.05    # Pausa en el borde antes de saltar (s)
COOLDOWN           = 0.5     # Tiempo mínimo entre saltos (s)
```

| Parámetro | Actual | Efecto |
|---|---|---|
| `MARGEN_PORCENTAJE` | 0.5% | Zona del borde donde se activa |
| `DELAY_MS` | 50 ms | Cuánto esperar en el borde antes de saltar |
| `COOLDOWN` | 0.5 s | Tiempo mínimo entre saltos consecutivos |
| `FORCE_TIMEOUT` | 350 ms | Si llevás este tiempo en el borde empujando, cruza forzado |

> `FORCE_TIMEOUT` está hardcodeado dentro de `wrap_loop()` (no es variable de módulo).
> Si querés ajustarlo, editá la línea `FORCE_TIMEOUT = 0.35` dentro de la función.

---

## 🧪 Guía de ajuste

| Síntoma | Solución |
|---|---|
| Salta **sin querer** | ↓ `MARGEN_PORCENTAJE` |
| No salta (hay que empujar mucho) | ↑ `MARGEN_PORCENTAJE` |
| Salta **muy rápido** (sin pausa) | ↑ `DELAY_MS` |
| Tarda mucho en saltar | ↓ `DELAY_MS` |
| Salta **múltiples veces** seguidas | ↑ `COOLDOWN` |
| **Se traba** al querer cruzar después de navegar íconos | ↓ `FORCE_TIMEOUT` (dentro de `wrap_loop()`) |

### Debug logging

El módulo escribe logs detallados en nivel `DEBUG`. Para verlos, asegurate
que el nivel de log esté en `DEBUG` (ya lo está por defecto en el script principal).

Eventos que aparecen en el log:
```
[WRAP] ▶ Borde derecho — esperando 50 ms...
[WRAP] ↕ Navegación vertical detectada — timer de cruce cancelado
[WRAP] ⚡ SALTO: derecha → izquierda  (espera=52 ms)
[WRAP] ⏰ Force timeout (352 ms) — cruz forzado derecha → izquierda
```

---

## 🚦 Bandera de activación

```python
HABILITADA = True   # ← Cambiar a False para desactivar
```

| `True` | `False` |
|---|---|
| El hilo WRAP se inicia y monitorea el cursor | No se inicia |
| Log: `🖱️ WRAP-AROUND: Hilo iniciado` | Log: `[WRAP] Módulo desactivado` |

---

## 📋 Log de ejemplo

```
12:05:23 INFO - ├─ WRAP-AROUND  [ACTIVO]
12:05:23 INFO - │  margen      = 0.5% del borde
12:05:23 INFO - │  delay       = 50 ms
12:05:23 INFO - │  cooldown    = 0.50 s
12:05:23 INFO - ├─ MÓDULOS ACTIVOS: QMK calibración, WRAP-AROUND
12:05:23 INFO - 🖱️  WRAP-AROUND: Hilo iniciado [margen=0.5%, delay=50 ms, cooldown=0.5 s]
```

---

## 🔗 Dependencias

- **Python:** `ctypes` (estándar), `threading`, `time`
- **Sistema:** Windows API (`user32.GetCursorPos`, `user32.SetCursorPos`)
