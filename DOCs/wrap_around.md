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

Funciona con **cualquier fuente de movimiento**: QMK nativo, ratón físico,
trackpad, etc. El módulo no distingue — solo mira la posición del cursor.

---

## 🎛️ Parámetros

Todos en `utils/wrap_around/__init__.py`:

```python
HABILITADA         = True    # Bandera maestra

MARGEN_PORCENTAJE  = 0.005   # 0.5% del borde (~10 px en 1920)
DELAY_MS           = 0.05    # Pausa en el borde antes de saltar (s)
COOLDOWN           = 0.5     # Tiempo mínimo entre saltos (s)
```

| Parámetro | Actual | Rango | Efecto |
|---|---|---|---|
| `MARGEN_PORCENTAJE` | 0.5% | 0.001–0.05 | Zona del borde donde se activa |
| `DELAY_MS` | 50 ms | 0.01–0.5 | Cuánto esperar en el borde antes de saltar |
| `COOLDOWN` | 0.5 s | 0.1–2.0 | Tiempo mínimo entre saltos consecutivos |

---

## 🧪 Guía de ajuste

| Síntoma | Solución |
|---|---|
| Salta **sin querer** (muy cerca del borde) | ↓ `MARGEN_PORCENTAJE` |
| No salta (hay que empujar mucho) | ↑ `MARGEN_PORCENTAJE` |
| Salta **muy rápido** (sin pausa) | ↑ `DELAY_MS` |
| Tarda mucho en saltar | ↓ `DELAY_MS` |
| Salta **múltiples veces** seguidas | ↑ `COOLDOWN` |

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
