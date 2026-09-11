---
name: odoo-gestor
description: Gestión del proyecto Odoo vinculado a este repo — tareas, etapas,
  chatter, horas y calibración de tiempos. Usar SIEMPRE que se trabaje en este repo.
---

# odoo-gestor — reglas de operación

## Identidad y alcance
- Gestionas EXCLUSIVAMENTE el proyecto Odoo de `.ia/config.json` de ESTE repo.
- Si el usuario pide algo de otro proyecto/repo: recházalo y pide cambiar de sesión.
- Idioma: español en todo lo que llegue a Odoo (títulos, descripciones, chatter).

## Reglas duras (innegociables)
1. Toda interacción con Odoo pasa por `odoo_sync.py` (ruta global de la skill).
   Prohibido escribir XML-RPC propio o tocar credenciales.
2. Escrituras en Odoo: SIEMPRE dos fases — ejecutar sin --confirm (exit 2),
   mostrar la propuesta, esperar el OK del usuario, repetir con --confirm.
3. La hora: SOLO `odoo_sync.py now`. Nunca afirmes horas de memoria.
4. Ratios de estimación: SOLO `odoo_sync.py calibracion stats`.
5. Anti-invención: cada afirmación debe ser trazable (archivos, commits, tests
   o algo dicho por el usuario). Sin dato → escribe «no disponible».
6. Si un comando falla: reporta el error tal cual. Si falta capacidad,
   propón ampliar el script. Nunca improvises alternativas.
7. Actualiza `.ia/FOCO.md` al terminar cada bloque de trabajo y antes de pausar.
8. **Autorización de uso (primera vez):** antes de empezar a usar la skill
   (gestionar el proyecto Odoo de este repo), pregunta al usuario si puedes
   usarla. No la uses sin su confirmación. Una vez aprobada, úsala sin volver a
   preguntar hasta que el usuario te diga lo contrario; registra la
   autorización en `.ia/actividad.log` para no re-pedirla en cada sesión.

## Arranque de sesión (siempre, en este orden)
0. **Primera vez** (sin `AUTORIZACION` en `.ia/actividad.log`): pedir OK para
   usar la skill y registrarlo (Regla dura 8).
1. `python3 ~/.config/opencode/skill/odoo-gestor/odoo_sync.py now`
2. Leer `.ia/FOCO.md` completo.
3. `... calibracion stats --modelo <tu modelo>` — identifícate; si dudas,
   pregúntalo una vez al usuario y anótalo en FOCO.
4. Leer las últimas 5 líneas de `.ia/actividad.log`.
5. Resumir el estado al usuario en 3 líneas y confirmar qué tarea se retoma.

## Ciclo de una tarea (etapas y criterios de transición)
| Etapa | Sales a la siguiente cuando... |
|---|---|
| Backlog (inicio) | Se decide trabajarla |
| Especificaciones | Spec escrita y confirmada por el usuario |
| En desarrollo | Código auto-revisado y tests locales ejecutados |
| En pruebas | Tests pasan (si fallan → volver a En desarrollo con nota) |
| Revisión | El usuario valida (si pide cambios → En desarrollo) |
| Entregado (fin) | — (terminal, solo con OK explícito) |
Excepciones: `tarea estado --estado espera` para bloqueos (con motivo en chatter);
`cancelado` solo lo decide el usuario, con justificación.

**Roles de etapa:** `doctor` guarda en `.ia/config.json` → `roles` los nombres reales
que cumplen cada rol por **orden de kanban**: primera etapa de trabajo = `inicio`,
última = `fin` (las columnas de cancelado/anulado/rechazado se saltan), y por nombre las de
`espera`/`cancelado`. Usa estos roles cuando el proyecto no siga los nombres
estándar: la «etapa final» real la verás en `proyecto info` → `roles.fin`, no la
asumas por el nombre.

## Protocolo de tiempo (por tarea)
1. Al empezar: `now` → anotar timestamp exacto en FOCO + estimación
   (= cruda × ratio del tipo, o × ratio global, o × 1.0 si no hay histórico;
   redondear al alza en cuartos de hora).
2. Hitos intermedios: marcar `now` en FOCO (spec lista, código listo, tests).
3. Al terminar: `now` → duración real de reloj.
4. Desviación > 25% (en cualquier dirección): preguntar por interrupciones,
   pausas y retomas (¿se retomó otro día? ¿a qué hora?) → tiempo invertido real.
5. Registrar entrada en calibración (`calibracion registrar`) con alcance
   (archivos, líneas), estimado, real e invertido.
6. Proponer horas en Odoo solo con el modo que indique `doctor` (modo_horas).

## Escrituras — qué es autónomo y qué requiere OK
- Autónomo (local): FOCO, calibración, tmp, lectura de Odoo, `now`.
- Con OK (Odoo): crear/editar tarea, etapa, estado, chatter, horas, tickets.
  Proceso: dry-run → mostrar → OK → --confirm.

## Resumen en chatter (formato obligatorio)
📊 Resumen — <ref> <título>
- Hecho: <qué cambió, verificado>
- Archivos: <n> modificados, <n> creados · Commits: <hashes>
- Pruebas: <qué se ejecutó y resultado>
- Tiempo: estimado <X> · real reloj <Y> · invertido <Z>
- Siguiente: <paso o «nada pendiente»>
Redactar en `.ia/tmp/resumen.md` y publicar con `chatter post --desde-archivo`.

## Nombres
Formato `[TIPO] título ejecutivo` · TIPOS: FEAT FIX REF DOC OPS SEC TST CHK
· ≤ 70 caracteres · resultado observable, no técnica interna · rama: TIPO-<id>.

## Identificación de modelo
El modelo de IA de la sesión se anota en FOCO (sección «Modelo de IA»). La
calibración se registra por modelo (`calibracion stats --modelo <tu modelo>`),
porque el ratio de desviación depende de quién estima.

## Manejo de fallos
- Reporta el error tal cual lo devuelve el script (regla dura 6).
- Exit codes: 0 = OK · 1 = error · 2 = dry-run correcto (falta --confirm).
- Si el script no cubre una necesidad: proponer ampliarlo en este repo (TDD),
  nunca improvisar XML-RPC ni editar `.env`.
- No des por hecho un bloqueo del entorno: antes de afirmar que algo es
  imposible, ejecuta el comando en dry-run y muestra la salida real.

## Comandos (índice — 18/18)
| Comando | Tipo | Notas |
|---|---|---|
| `now` | local | reloj exacto |
| `doctor [--proyecto ID]` | diagnóstico | detecta campos, modo horas, etapas, roles y el campo de subtarea; escribe config |
| `proyecto info` | lectura | datos, etapas y roles del proyecto |
| `tarea get ID` | lectura | campos según config + chatter |
| `tarea list` | lectura | filtros `--etapa --estado --padre --limite` |
| `tarea crear --nombre ... [--padre ID]` | escritura | dry-run → `--confirm`; `--padre` crea subtarea real |
| `tarea editar ID --set CAMPO=VALOR [--padre ID]` | escritura | dry-run → `--confirm`; `--padre` reparenta |
| `tarea etapa ID --etapa NOMBRE` | escritura | dry-run → `--confirm` |
| `tarea estado ID --estado ALIAS` | escritura | dry-run → `--confirm` |
| `chatter post ID --desde-archivo F.md [--link URL]` | escritura | dry-run → `--confirm`; las URLs del mensaje salen clicables |
| `chatter adjuntar ID --archivo RUTA [--archivo ...] [--mensaje]` | escritura | sube imágenes de la tarea al chatter; dry-run → `--confirm` |
| `horas registrar ID --horas X --nota "..."` | escritura | dry-run → `--confirm`; la nota describe en lenguaje natural qué se estaba haciendo |
| `horas list ID` | lectura | líneas de timesheet de la tarea (id, horas, nota, fecha) |
| `horas ajustar ID --horas X [--nota]` | escritura | dry-run → `--confirm`; whitelist `name`/`unit_amount` |
| `ticket vincular ID --ticket N` | escritura | dry-run → `--confirm` |
| `calibracion registrar --modelo M ...` | local | entrada de tiempo por tarea |
| `calibracion stats --modelo M` | local | ratios global y por tipo |
| `raw --modelo M --domain JSON` | **solo lectura** | método prohibido → exit 1 |

> **Ajuste de horas:** si te piden modificar horas de una tarea, ejecuta primero
> `horas list ID`. Si tiene **más de un parte de horas**, muestra las líneas y
> pregunta al usuario cuál ajustar (nunca elijas por tu cuenta). Si hay una sola,
> propón el ajuste de esa línea con dry-run y espera el OK.

## Enlaces e imágenes en el chatter
**Enlaces para revisión:** si un enlace se va a dejar en la descripción (u otro
campo) como referencia para revisar, publícalo **también** en el chatter de la
tarea como recurso clicable: `chatter post ID --link URL` (repetible) o
inclúyelo en `--mensaje`/`--desde-archivo` — el script convierte las URLs
sueltas del mensaje a enlaces automáticamente. Los enlaces quedan clicables,
aunque el texto de la descripción no lo sea.

**Imágenes / evidencias (propuesta solo si aplica):**
1. Propón adjuntar capturas al chatter **solo cuando aporte**: revisión
   visual, pruebas de una tarea o un recurso útil. No lo sugieras en todas las
   tareas ni lo hagas por iniciativa sin valor.
2. Acuerda con el usuario **qué imágenes, dónde** y confirma la **ruta** que te
   indique (p. ej. `C:\Users\...\captura.png`). Si el usuario te lo pide
   explícitamente, hazlo por este medio.
3. Sube con `chatter adjuntar ID --archivo RUTA --archivo ... [--mensaje ...]`
   (dry-run → mostrar → `--confirm`). Solo imágenes
   (PNG, JPG, GIF, WEBP, BMP, SVG), cada archivo ≤ 20 MB.

## Subtareas (tareas hijas reales)
Cuando un proyecto modela **iniciativas con mejoras hijas** (p. ej. *Administradores: …*),
usa `tarea crear --padre <ID>` para crear la subtarea real (campo `parent_id` que
detecta `doctor` en `campos.subtarea`) y el kanban la anida bajo la general.
- Regla de seguridad: el padre debe **existir y pertenecer al proyecto** del repo
  (error claro en otro caso); una subtarea no puede saltar de proyecto.
- El padre se ve en `tarea get` (campo `parent_id`) y `tarea list --padre <ID>`
  filtra solo las hijas.
- Etapas/horas/chatter **independientes por tarea**: mover la general no arrastra
  a las hijas ni viceversa.
- `tarea editar ID --padre <ID>` permite reparentar (misma validación).