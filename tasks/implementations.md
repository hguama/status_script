# Procedimientos — status script

> [!index] Índice de procedimientos
> | Nº | Procedimiento | Ver |
> |---|---|---|
> | 1 | Smoke test de módulo HID sin hardware | [Smoke test HID](#^hid-smoke) |

---

> [!procedure] **Procedimiento 1 · Smoke test de módulo HID sin hardware** ^hid-smoke
> Probar la lógica de un módulo que habla por `raw_hid` sin teclado conectado.
> Origen: Task 1 (captura), 2026-09-10.
>
> - Importar el módulo desde la raíz del repo y sustituir el `dev` real por un
>   objeto con `write(buf)` que capture los bytes.
> - Controlar las entradas del mundo real (evento de armero, `_overlay_visible`)
>   y correr el hilo en daemon.
> - Afirmar: sin evento armador, cero escrituras; con condición presente, una
>   sola escritura con el comando esperado en `buf[1]`; segundo evento sin
>   condición, sin re-escritura.
