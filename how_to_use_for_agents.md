# Cómo usar la skill `odoo-gestor` (guía para agentes noveles)

> **Lee este archivo primero.** Si nunca has visto la skill, con esta guía te
> orientas, sabes dónde está todo y qué pedir/configurar para empezar. El
> manual de comportamiento normativo es `SKILL.md`; este documento es la
> brújula para llegar a él sin perderte.

---

## 1. Qué es esta skill

`odoo-gestor` convierte a un agente (tú) en el gestor de **una** instancia
Odoo (Community, normalmente en Docker) asociada a **este repo**: crear tareas,
moverlas de etapa, informar en el chatter, registrar horas, fechar el trabajo.

División de responsabilidades:
- **El agente decide y redacta** (qué se hace, con qué texto).
- **El script ejecuta y valida** (`odoo_sync.py`): sale JSON por stdout,
  escrituras en dos fases, whitelists, anti-invención.
- **Tú nunca tocas XML-RPC ni credenciales.** Si falta capacidad, se amplía el
  script por TDD en este mismo repo.

---

## 2. Dónde está todo (mapa del repo de la skill)

La skill se instala global por symlink/junction: `~/.config/opencode/skill/odoo-gestor`
(en Windows: `C:\Users\<usuario>\.config\opencode\skill\odoo-gestor`). Es el
**mismo** repo de desarrollo: editar uno es editar el otro.

| Ruta | Qué es |
|---|---|
| `odoo_sync.py` | El script: 18 comandos en 10 grupos. Se invoca con la ruta **global** |
| `SKILL.md` | **Normativa de comportamiento** (reglas duras, arranque, protocolos). Léela siempre |
| `how_to_use_for_agents.md` | Este archivo (onboarding para agentes) |
| `README.md` | Vista general para humanos (cifras, badges, capturas) |
| `CHANGELOG.md` | Últimos cambios por versión (rc1 … rc10) |
| `docs/ARQUITECTURA.md` | Diseño: modelo, comandos, whitelists, flujo de datos |
| `docs/PAUTAS.md` | **Cómo desarrollar la skill en sí** (TDD, gates, commits) |
| `docs/ROADMAP.md` | Historial de fases y mapa de cobertura |
| `plantillas/FOCO.md` | Plantilla de `FOCO.md` (se copia al `.ia/` del repo de usuario) |
| `plantillas/calibracion.md` | Formato de entradas de calibración |
| `tests/test_odoo_sync.py` | N1: suite unitaria sin Odoo (123 tests) |
| `tests/INTEGRACION.md` | N2/N3: casos contra instancia real y comportamiento de la IA |
| `docker/qa/` | Entorno Odoo de QA para pruebas de integración |
| `instalar.sh` | Instalación de la skill |
| `.gitignore` | Ignora `.ia/`, `__pycache__/`, etc. |

Invoca siempre al script por su **ruta global** (así las sesiones de cualquier
repo usan la misma versión):

```
python ~/.config/opencode/skill/odoo-gestor/odoo_sync.py  <comando> ...
```

En Windows el intérprete puede ser `python` (o `py`); el resto es igual.

---

## 3. Los 18 comandos, de un vistazo

| Comando | Tipo | Qué hace |
|---|---|---|
| `now` | local | Hora exacta del sistema (única fuente de verdad del tiempo) |
| `doctor [--proyecto ID]` | diagnóstico | Detecta campos, etapas, roles, modo horas y subtareas; **escribe `config.json`** |
| `proyecto info` | lectura | Datos, etapas y roles del proyecto |
| `tarea get <ID>` | lectura | Tarea con sus campos + chatter |
| `tarea list [--etapa][--estado][--padre][--limite]` | lectura | Lista tareas del proyecto |
| `tarea crear --nombre "…" [--descripcion][--horas][--padre][--fecha][--etapa]` | escritura | Crea tarea (dry-run → `--confirm`) |
| `tarea editar <ID> --set CAMPO=VALOR [--padre]` | escritura | Edita campos de la whitelist |
| `tarea etapa <ID> --etapa NOMBRE` | escritura | Mueve de etapa |
| `tarea estado <ID> --estado ALIAS` | escritura | Estado de workflow |
| `chatter post <ID> [--desde-archivo][--mensaje][--link URL]` | escritura | Publica en el chatter (URLs → clicables) |
| `chatter adjuntar <ID> --archivo RUTA [--archivo …][--mensaje]` | escritura | Sube imágenes (PNG/JPG/GIF/WEBP/BMP/SVG, ≤20 MB) |
| `horas registrar <ID> --horas X --nota "…" [--fecha ISO]` | escritura | Parte de horas (con fecha real si se usa `--fecha`) |
| `horas list <ID>` | lectura | Líneas de timesheet de la tarea |
| `horas ajustar <ID> --horas X [--nota]` | escritura | Ajusta una línea (whitelist `name`/`unit_amount`) |
| `ticket vincular <ID> --ticket N [--campo]` | escritura | Vincula ticket a la tarea |
| `calibracion registrar --modelo M --tipo T --ref R --estimado --real …` | local | Aporta una entrada de calibración |
| `calibracion stats --modelo M` | local | Ratios de desviación por tipo y global |
| `raw --modelo M --domain JSON [--metodo] [--campos]` | **solo lectura** | Consulta libre (prohibido `write`/`create`/`unlink`) |

Todos los subcomandos aceptan además las opciones robustas
`--robusto`, `--reintentos N|ilimitado`, `--tiempo-total SEG|ilimitado` y
`--espera SEG` para conexiones intermitentes (ver §7).

---

## 4. Qué leer primero (y en qué orden)

1. **`SKILL.md` completo** — es la ley. Léelo y vuelve a él ante cualquier duda de comportamiento.
2. **`how_to_use_for_agents.md`** (este archivo) — orientación operativa.
3. **`CHANGELOG.md`** — qué cambió en la última versión (para no usar funciones a medias).
4. **`docs/ARQUITECTURA.md`** — modelo mental del sistema (comandos, whitelists, fases).
5. **`docs/ROADMAP.md`** — para entender qué fases hay y qué se validó.
6. **`docs/PAUTAS.md`** — solo si vas a **desarrollar/modificar** la skill.

Si solo vas a *usar* la skill en un repo, con 1–3 te basta para arrancar.

---

## 5. Los 8 datos que necesitas para empezar (cómo conseguirlos)

El script trabaja contra un proyecto Odoo mapeado en el **repo del usuario**
(no en la skill). Ese repo tiene una carpeta privada `.ia/` (gitignored) con:

| Archivo | Contenido | Se crea con |
|---|---|---|
| `.ia/config.json` | Proyecto Odoo, etapas, roles, modo horas, estados, convención | `doctor --proyecto <ID>` |
| `.ia/.env` | **Credenciales**: `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` | El usuario (nunca tú) |
| `.ia/FOCO.md` | Foco/estado de la sesión (tarea activa, timestamps, estimación) | Tú (copia de `plantillas/FOCO.md`) |
| `.ia/actividad.log` | Historial de operaciones (incluye la `AUTORIZACION`) | El script |
| `.ia/calibracion/<modelo>.md` | Entradas de tiempo por modelo | El script |
| `.ia/tmp/` | Trabajo temporal (p. ej. `resumen.md`) | Tú |

`config.json` (sin secretos) se parece a esto; lo genera `doctor`:

```json
{
  "proyecto_id": 7,
  "modo_horas": "timesheet",
  "etapas": { "Backlog": 27, "Especificaciones": 28, "En desarrollo": 29,
              "En pruebas": 30, "Revisión": 31, "Entregado": 32, "Cancelado": 33 },
  "roles": { "inicio": "Backlog", "fin": "Entregado", "cancelado": "Cancelado" },
  "estados": { "en-progreso": "01_in_progress", ... },
  "umbral_desviacion_pct": 25,
  "convencion": { "formato": "[TIPO] titulo ejecutivo", "tipos": ["FEAT", ...] }
}
```

**Lo que debes pedir al usuario en la primera sesión (si no está):**

1. **Autorización de uso** — regla dura: pregunta si puedes usar la skill y
   registra `AUTORIZACION` en `.ia/actividad.log` (no vuelvas a preguntar).
2. **Credenciales** — que el usuario garantice `.ia/.env` (o lo dé de alta el
   técnico). **Tú nunca lees ni editas `.env`**: el script las usa.
3. **ID del proyecto Odoo** de este repo (si no está en `config.json`) y
   ejecuta `doctor --proyecto <ID>` para generarlo.
4. **Usuario técnico con empleado vinculado** — `doctor` te lo dirá si falta:
   la IA escribe timesheets como empleado (`user_id` ↔ `hr.employee`).
5. **Tu modelo de IA** — para identificar la calibración (anótalo en `FOCO.md`).
6. **FOCO inicial** — si no existe, créalo desde la plantilla y que el usuario
   confirme qué tarea se retoma.

Sugerencia de config rápida del primer día:

```
doctor --proyecto 7            # configura el repo → .ia/config.json
now                            # comprobar conexión y hora
calibracion stats --modelo <tu-modelo>   # ver ratios (vacío es normal)
```

---

## 6. Arranque de sesión (orden obligatorio)

Cada sesión comienza así (reglas duras 1–8 de `SKILL.md`):

0. **Primera vez** sin `AUTORIZACION` en el log → pide permiso y regístralo.
1. `now` — hora exacta.
2. Lee `.ia/FOCO.md` completo (qué se estaba haciendo).
3. `calibracion stats --modelo <tu modelo>` — identifícate y mira ratios.
4. Lee las últimas 5 líneas de `.ia/actividad.log`.
5. Resume en 3 líneas al usuario y confirma qué tarea se retoma.

---

## 7. Qué DEBES hacer en el día a día

- **Escrituras siempre en dos fases:** ejecuta sin `--confirm` → la propuesta
  sale con salida `exit 2` y JSON `dry_run: true` → **muéstrala al usuario** →
  espera su OK → repite con `--confirm`. Nunca escribas sin OK.
- **Salida JSON:** lee `{ "ok": true, "data": … }`. Errores: `{ "ok": false, "error": … }`.
- **Hora real** con `now` al empezar, en cada hito y al terminar; anota los
  timestamps y la estimación en `FOCO.md`.
- **Estimación** = cruda × ratio de calibración (del tipo o global; ×1.0 si no
  hay histórico), redondeo al alza en cuartos de hora.
- **Desviación > 25%** en cualquier dirección → pregunta por interrupciones,
  pausas y retomas; anota el tiempo invertido real y `calibracion registrar`.
- **Ciclo de tarea** con las etapas reales del kanban (las ve `doctor` en
  `roles`): Backlog → Especificaciones → En desarrollo → En pruebas → Revisión →
  Entregado (el final solo con OK explícito). Usa `tarea estado espera` para
  bloqueos con motivo; `cancelado` solo lo decide el usuario.
- **Resumen al chatter** al cerrar cada bloque, con el formato obligatorio de
  `SKILL.md` (`📊 Resumen — <ref>`: hecho, archivos, commits, pruebas, tiempo,
  siguiente). Redacta en `.ia/tmp/resumen.md` y publica con
  `chatter post ID --desde-archivo .ia/tmp/resumen.md`.
- **Nombres** de tareas `[TIPO] título ejecutivo` (TIPOS: FEAT FIX REF DOC OPS
  SEC TST CHK), ≤70 caracteres. Si el usuario da otro nombre, advierte y sigue.
- **Anti-invención:** toda afirmación trazable (archivo, commit, test, algo
  dicho por el usuario); sin dato → «no disponible».
- **Conexión intermitente:** ante fallos de red usa `--robusto` (3 reintentos /
  3 s). Si no basta: `--robusto --reintentos ilimitado --tiempo-total 60`.
  Nunca `--reintentos ilimitado` sin tiempo total (ni al revés). Solo se
  reintentan fallos de conexión, nunca los rechazos lógicos de Odoo.
- **Fechar trabajo real:** si se trabajó otro día, `tarea crear --fecha
  YYYY-MM-DD` (→ `date_deadline`) y `horas registrar --fecha YYYY-MM-DD` (→
  `date` del parte). No intentes retro-fechar `create_date` (imposible en Odoo).
- **Ajustar horas:** primero `horas list <ID>`; si hay **varias** líneas,
  muestra cuáles y **pregunta cuál ajustar**; si hay una sola, propones dry-run.
- **Enlaces/images:** si dejas un enlace como referencia en un campo, publícalo
  también en el chatter con `--link`. Adjunta capturas **solo si aportan**
  (revisión visual/pruebas), acordando qué y dónde.

---

## 8. Qué NO DEBES hacer (anti-patterns)

- ❌ **No escribas XML-RPC directo** ni pases de `odoo_sync.py`: regla dura 1.
- ❌ **No toques ni leas credenciales** (`.env`, API keys): el script las usa.
- ❌ **No inventes** datos: IDs de tareas, nombres de etapas, horas, ratios,
  versiones, commits. Anti-invención (regla dura 5).
- ❌ **No afirmes horas de memoria** sin pasar por `now` (regla dura 3).
- ❌ **No uses `raw` para escribir**: método prohibido (solo lectura).
- ❌ **No fuerces campos fuera de whitelist**: `EDITABLES` (name, description,
  date_deadline, planned_hours), `HORAS_EDITABLES` (name, unit_amount),
  `ADJUNTOS_EDITABLES` (name, datas, type, res_model, res_id, mimetype).
- ❌ **No escribas con `--confirm` directo** sin mostrar la propuesta antes.
- ❌ **No gestiones otro repo/proyecto**: si el usuario habla de otro repo,
  rechaza y pide cambiar de sesión (identidad de la skill).
- ❌ **No declares algo imposible** sin intentarlo en dry-run. Ejecuta y muestra
  la salida real.
- ❌ **No elijas tú la línea de horas** si hay varias ni cambies etapas a tu
  antojo (aplica dos fases + pregunta).
- ❌ **No publiques un resumen** sin el formato obligatorio.
- ❌ **No sugieras adjuntar imágenes** sin claro valor (revisión/pruebas).
- ❌ **No commitees** en ningún repo sin que el usuario lo pida explícitamente.
- ❌ **No edites `.env` ni `.ia/config.json` a mano**: `doctor` escribe el config.

---

## 9. Errores típicos y qué significan

| Error | Interpretación / acción |
|---|---|
| `exit 2` + `dry_run: true` | Propuesta lista: muéstrala y espera OK antes de `--confirm` |
| `exit 1` + `error` | Fallo real; reporta el error **tal cual** y la traza del contexto |
| `No se pudo contactar con Odoo…` | Host caído/lento → usa `--robusto`; si persiste, repórtalo (no afirmes imposible) |
| `Autenticación fallida…` | Revisar credenciales/API key (el usuario; tú no tocas `.env`) |
| `Esta instancia no expone state` | Filtra por `--etapa`, no por `--estado` |
| `El usuario IA Sync no tiene empleado vinculado` | Crear `hr.employee` ligado al usuario técnico (RRHH) |
| `modo «solo-registro»` | `hr_timesheet` no instalado: registrar horas en el resumen + calibración |
| `--fecha … ISO` | Formato/calendario inválido (p. ej. `2026-02-30`); usa `YYYY-MM-DD` |
| `--reintentos ilimitado … ilimitados a la vez` | Modo robusto mal configurado: añade `--tiempo-total` |

Si el script **no cubre** una necesidad: propón ampliarlo por TDD en este repo
(PAUTAS.md) — es el flujo previsto, no improvises soluciones.

---

## 10. Mini-cheat de diagnóstico

```
python ~/.config/opencode/skill/odoo-gestor/odoo_sync.py now
python … odoo_sync.py doctor --proyecto 7          # ¿qué detecta la instancia?
python … odoo_sync.py proyecto info                # etapas + roles reales
python … odoo_sync.py tarea list --limite 10       # ¿qué hay abierto?
python … odoo_sync.py tarea get <ID>               # detalles + chatter
python … odoo_sync.py horas list <ID>              # partes existentes
python … odoo_sync.py calibracion stats --modelo <tu-modelo>
```

Con esto estás orientado. **La fuente de verdad del comportamiento siempre es
`SKILL.md`; este archivo solo te acerca a ella.**