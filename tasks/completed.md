# ☑️ Tareas completadas — status script

> [!index] Índice del histórico
> | Fecha | Block | Qué dejó | Nº |
> |---|---|---|---|
> | 2026-09-10 | captura | Modo captura documentado con trazabilidad al origen y módulo verificado | [1](#^captura) |

---

> [!block]- **captura**<span class="sep">│</span><span class="count">1/1 tasks</span><span class="sep">│</span><span class="tasknums"><span class="status-completed">✓</span> <span class="num num-completed">1</span></span><span class="sep">│</span><span class="annex">📎 [contrato](attachments/captura/spec-modo-captura.md)</span> ^captura
> > [!task]- <span class="status-completed">✓</span>**Task 1** · Documentar el modo captura del Corne<span class="sep">│</span><span class="risk-med">◆ medium</span><span class="sep">│</span><span class="beat">▰▰▰▰</span> · <em class="done-note">completed 2026-09-10</em>
> > El módulo de captura ya existe sin comitear y hay que dejar por escrito qué
> > hace antes de decidir el commit.
> >
> > > [!desc]- completed (4)
> > > - [x] Contrastar el contrato contra el diff real sin comitear — **Resultado (2026-09-10):** los 4 puntos de la §7 coinciden con el diff (8+/1-); `utils/captura/__init__.py` compila y expone todos los símbolos; §8 se matizó porque `git status` ahora también lista los archivos del plan
> > > - [x] 👤 Aprobar la especificación y el diagrama del anexo — **aprobado por Hero el 2026-09-10** (incluye trazabilidad al origen E1/E2)
> > > - [x] Verificar el funcionamiento — **Resultado (2026-09-10):** smoke test del módulo con `dev` simulado: sin `CAP_ARM` no escribe nada; con overlay manda una sola `S` (`buf[1]=83`); segundo `CAP_ARM` sin overlay no re-escribe. Reposo en `Event` (cero CPU por construcción); E2E con teclado real queda al uso diario
> > > - [x] 👤 Contrastar el anexo contra el código y decidir el commit — **Resultado (2026-09-10):** contraste final OK; dos commits por decisión de Hero: código en `52e6c4e`, plan y tarea en el commit de esta operación
