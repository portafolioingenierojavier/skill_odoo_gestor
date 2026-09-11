# ARQUITECTURA — Skill «odoo-gestor»

**Gestión de proyectos Odoo dirigida por IA (Open Code)**

| | |
|---|---|
| Versión | 1.0 (diseño aprobado → implementación) |
| Entorno | Odoo Community en Docker (Linux) · Open Code · 1 repo = 1 proyecto |
| Idioma | Español en todo lo que llega a Odoo |
| Documento | Fuente única de verdad de la arquitectura. Cualquier cambio se registra aquí. |

---

## 1. Resumen

**Problema:** la IA necesita gestionar el proyecto Odoo del repo en el que trabaja (tareas, etapas, chatter, horas), pero improvisar llamadas RPC produce alucinaciones de campos, expone credenciales, no sabe la hora y no recuerda entre sesiones.

**Solución:** una skill global (instrucciones + CLI determinista) + una carpeta local `.ia/` por repo (configuración, foco, calibración, auditoría).

```
Usuario ⇄ Open Code (IA + skill odoo-gestor) ⇄ odoo_sync.py ⇄ XML-RPC ⇄ Odoo (Docker)
                        ⇅ archivos locales (.ia/)
```

**Actores y papeles:**

| Actor | Papel |
|---|---|
| IA | Decide, redacta, estima, pregunta, propone |
| `odoo_sync.py` | Ejecuta, valida, registra, dice la hora y calcula ratios |
| Odoo | Ventana ejecutiva (para el jefe): etapas, chatter, horas |
| Repo/commits | Vista técnica (para el programador) |
| Usuario | Única autoridad para aprobar escrituras |

---

## 2. Principios rectores (reglas de oro)

1. **La IA decide y redacta; el script ejecuta, valida y es la fuente de verdad.**
2. **1 repo = 1 proyecto Odoo.** Guard anti-mezcla: la IA solo toca el proyecto de `.ia/config.json`.
3. **Escrituras en Odoo en dos fases:** dry-run → propuesta visible → OK del usuario → `--confirm`.
4. **Fuentes de verdad únicas:** la hora la da `now`, los ratios `calibracion stats`, los campos `doctor`.
5. **Anti-invención:** toda afirmación trazable (archivos, commits, tests, o dicho por el usuario). Sin dato → «no disponible».
6. **Autónomo lo local, confirmado lo oficial:** FOCO/calibración/hitos se actualizan sin preguntar; todo lo que llega a Odoo se aprueba.
7. **Fallos explícitos:** si un comando falla, se reporta el error tal cual; nunca workarounds con código RPC propio.

---

## 3. Mapa de archivos

```
~/.config/opencode/skill/odoo-gestor/          [GLOBAL — idéntico en todos los proyectos]
├── SKILL.md                     ← reglas y protocolos que lee la IA
├── odoo_sync.py                 ← único puente a Odoo (CLI)
├── plantillas/
│   ├── FOCO.md                  ← plantilla del foco por repo
│   └── calibracion.md           ← cabecera del archivo por modelo
└── tests/
    ├── test_odoo_sync.py        ← unitarios (sin Odoo)
    └── INTEGRACION.md           ← checklist de pruebas contra Odoo

<repo>/                                          [POR PROYECTO]
├── .ia/
│   ├── config.json     (V)      ← mapeo repo↔proyecto, campos, etapas, convención
│   ├── .env            (L)      ← credenciales — NUNCA versionar
│   ├── FOCO.md         (L)      ← foco actual de la IA
│   ├── actividad.log   (L)      ← auditoría de toda escritura
│   ├── calibracion/    (L)      ← un .md por modelo de IA
│   └── tmp/            (L)      ← borradores (p.ej. resúmenes antes del chatter)
└── .gitignore                    ← entradas odoo-gestor
```

**(V) = versionado · (L) = local, en .gitignore**

> Nota de diseño: `config.md` pasa a ser **`config.json`**. Razón: el script debe leerlo y escribirlo (`doctor` lo genera); JSON es fiable para máquina y perfectamente legible para la IA.

| Archivo | Problema que resuelve |
|---|---|
| `SKILL.md` | La IA no recuerda reglas entre sesiones |
| `odoo_sync.py` | Alucinaciones RPC, credenciales expuestas, hora incierta, formatos inconsistentes |
| `.ia/config.json` | Cada instancia es custom: campos y etapas difieren |
| `.ia/.env` | Secretos fuera del repo y fuera del contexto de la IA |
| `.ia/FOCO.md` | Pérdida de contexto al cerrar/abrir sesión |
| `.ia/calibracion/` | Estimaciones ciegas: cada modelo tarda distinto |
| `.ia/actividad.log` | «¿Qué tocó la IA y cuándo?» — auditoría |
| `plantillas/` | Arranque uniforme en nuevos proyectos |
| `tests/` | Validar las herramientas antes de confiar en ellas |

---

## 4. Fichas por archivo

### 4.1 `SKILL.md` (global)

| Aspecto | Detalle |
|---|---|
| Razón de ser | Open Code carga skills globales en cada sesión; sin esto, cada sesión reinventa las reglas |
| Lo crea | Una vez, a mano (este documento es la especificación) |
| Se actualiza | Al cambiar protocolos o añadir comandos al CLI |
| Lo lee | La IA, automáticamente al iniciar sesión |

**Contenido completo:**

```markdown
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

**Roles de etapa:** `doctor` guarda en `.ia/config.json` → `roles` los nombres
reales por **orden de kanban** (`sequence`, fallback `id`): primera etapa de
trabajo = `inicio`, última = `fin` (salta columnas de cancelado/anulado/rechazado); las de
`espera`/`cancelado` por texto del nombre. La «etapa final» real se lee de
`proyecto info` → `roles.fin`, sin asumir el nombre estándar.

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
| `doctor [--proyecto ID]` | diagnóstico | detecta campos, modo horas, etapas y roles; escribe config |
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

> **Opción robusta (FASE 16, rc9):** los 18 subcomandos aceptan
> `--robusto` (3 reintentos / espera 3 s), `--reintentos N|ilimitado`,
> `--tiempo-total SEG|ilimitado` y `--espera SEG`. Condición de parada
> obligatoria: reintentos y tiempo total no pueden ser ilimitados a la vez
> (error claro en arranque si se incumple).

> **Ajuste de horas:** si te piden modificar horas de una tarea, ejecuta primero
> `horas list ID`. Si tiene **más de un parte de horas**, muestra las líneas y
> pregunta al usuario cuál ajustar (nunca elijas por tu cuenta). Si hay una sola,
> propón el ajuste de esa línea con dry-run y espera el OK.
```

**Enlaces e imágenes en el chatter (FASE 15):**
- **Enlaces clicables:** la descripción de una tarea no enlaza por texto plano;
  por eso `chatter post` acepta `--link URL` (repetible), que publica un ancla
  `<a href target=_blank>` en el chatter, y convierte además cualquier URL
  suelta del mensaje/archivo a ancla (función pura `conversion_links_html`,
  que aparta los `<a>` existentes para no anidarlos). Contrato de
  comportamiento: si un enlace se va a dejar en la descripción como
  referencia, la IA lo publica también en el chatter como recurso.
- **Imágenes evidencias:** `chatter adjuntar` valida los archivos **antes de
  escribir** (fail before write): existen, no vacíos, ≤`MAX_IMAGEN_BYTES`
  (20 MB) y formato real por magic bytes (`formato_imagen`: PNG/JPEG/GIF/WEBP/
  BMP/SVG). Escribe `ir.attachment` acotado a la whitelist
  `ADJUNTOS_EDITABLES` (`name`, `datas`, `type`, `res_model`, `res_id`,
  `mimetype`) ligado a la tarea (aparece en el chatter) y, opcionalmente,
  publica el `--mensaje`. Decisión de diseño: campos fijos del adjunto, nunca
  un `--set` genérico (mismo criterio PAUTAS §6.3).
- La IA **solo sugiere** adjuntar capturas cuando aportan (revisión visual,
  pruebas); conversa qué imágenes/dónde y las sube por la ruta que indique el
  usuario.

**Modo robusto para conexión intermitente (FASE 16):** cuando la instancia
cae o va lenta, no se aborta al primer fallo si se arma el modo: `PADRE_ROBUSTO`
añade a cada subcomando hoja las opciones `--robusto`,
`--reintentos N|ilimitado`, `--tiempo-total SEG|ilimitado` y `--espera SEG`.
`activar_modo_robusto` valida en arranque la **condición de parada
obligatoria**: reintentos totales y tiempo total nunca ambos ilimitados (la
herramienta no corre sin un limitante claro). `intentar_con_reintentos`
envuelve la conexión y cada `Odoo.ejec`, y solo reintenta **fallos de
conexión** (`CONEXION_ERRORES`: ConnectionError, TimeoutError, socket.timeout,
ProtocolError, OSError); un `xmlrpc.Fault` —rechazo lógico de Odoo— se propaga
sin reintentar para no duplicar escrituras. El progreso de cada reintento sale
por stderr, y cuando el modo está activo `ok()` añade al JSON un resumen
`reintentos` (config, reintentos realizados y duración transcurrida).

**Subtareas (tareas hijas reales):** en proyectos con iniciativas que agrupan
mejoras (*Administradores: …*), `tarea crear --padre ID` escribe el relacional
`campos.subtarea` (`parent_id` estándar) y el kanban anida la hija bajo la
general. Decisiones de diseño (ampliación de whitelist, PAUTAS §6.3):

- `EDITABLES` **no cambia**: el vínculo se hace con el argumento dedicado
  `--padre` en `crear`/`editar`, nunca por `--set parent_id=…` (evita inyectar
  un relacional por el parser genérico). Decisión explícita documentada.
- `resolver_padre()` valida **antes de escribir** (fail before write): el padre
  debe existir y pertenecer al proyecto del repo; error claro (exit 1) en otro caso.
- `doctor` anota `campos.subtarea` en `config.json`; si la instancia no lo
  expone, `--padre` devuelve error accionable indicando re-correr doctor.
- `tarea get` muestra el padre (`parent_id` con `[id, nombre]`); `tarea list
  --padre ID` filtra por las hijas; etapas/horas/chatter siguen siendo
  **independientes por tarea** (mover la general no arrastra a sus hijas).

### 4.2 `odoo_sync.py` (global)

| Aspecto | Detalle |
|---|---|
| Razón de ser | Determinismo (mismas validaciones siempre), credenciales fuera del contexto de la IA, formatos consistentes, reloj real, auditoría central |
| Salida | JSON por stdout, siempre parseable |
| Exit codes | `0` OK · `1` error (con mensaje claro, sin traceback crudo) · `2` dry-run correcto, pendiente de `--confirm` |
| Escrituras | Solo campos de whitelist, solo en dos fases, siempre con registro en `actividad.log` |
| Dependencias | Solo librería estándar (`xmlrpc.client`) — sin pip install |

**Contenido completo:**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
odoo_sync.py — CLI de la skill «odoo-gestor» (Open Code ↔ Odoo).

Único punto de entrada a Odoo para la IA.
Principio: la IA decide y redacta; este script ejecuta, valida y registra.

Salida       : JSON por stdout, siempre parseable.
Exit codes   : 0 = OK · 1 = error · 2 = dry-run correcto (pendiente --confirm).
Escrituras   : solo whitelist de campos y en dos fases (dry-run → --confirm).
Credenciales : .ia/.env o variables de entorno (nunca versionadas).
Dependencias : únicamente la librería estándar de Python.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import xmlrpc.client

# ------------------------------------------------------------------ constantes

CREDENCIALES = ("ODOO_URL", "ODOO_DB", "ODOO_USER", "ODOO_API_KEY")

ESTADOS = {  # alias amigable → valor real del campo state (QA, Odoo 18-20260619)
    "en-progreso": "01_in_progress",
    "espera": "04_waiting_normal",
    "cambios": "02_changes_requested",
    "aprobado": "03_approved",
    "hecho": "1_done",
    "cancelado": "1_canceled",
}

EDITABLES = ("name", "description", "date_deadline", "planned_hours")

LECTURA_CRUDA = ("search_read", "read", "fields_get", "search_count")

TIPOS_VALIDOS = ("FEAT", "FIX", "REF", "DOC", "OPS", "SEC", "TST", "CHK")

PATRON_ENTRADA = re.compile(
    r"^##\s*(?P<fecha>\S+)\s*\|\s*(?P<tipo>[A-Za-z]+)\s*\|\s*(?P<ref>.*?)\s*\|\s*"
    r"estimado_h:(?P<est>[\d.]+)\s*\|\s*real_h:(?P<real>[\d.]+)"
    r"(?:\s*\|\s*invertido_h:(?P<inv>[\d.]+))?"
    r"(?:\s*\|\s*archivos:(?P<arch>\d+))?"
    r"(?:\s*\|\s*lineas:(?P<lin>\d+))?"
    r"(?:\s*\|\s*interrupciones:(?P<int>\w+))?\s*$"
)

# ------------------------------------------------------------------ utilidades

def ok(data, codigo=0):
    print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
    sys.exit(codigo)

def error(mensaje, detalle=None):
    print(json.dumps({"ok": False, "error": mensaje, "detalle": detalle or ""},
                     ensure_ascii=False))
    sys.exit(1)

def dry_run(propuesta):
    print(json.dumps({"ok": True, "dry_run": True, "propuesta": propuesta,
                      "siguiente_paso": "Repite el comando con --confirm para aplicar"},
                     ensure_ascii=False))
    sys.exit(2)

def raiz_repo():
    p = Path.cwd()
    for carpeta in (p, *p.parents):
        if (carpeta / ".ia").is_dir():
            return carpeta
    error("No se encontró carpeta .ia/ desde el directorio actual. "
          "Ejecuta el script dentro del repo del proyecto.")

def carpeta_ia():
    return raiz_repo() / ".ia"

def cargar_credenciales():
    cred = {}
    fenv = carpeta_ia() / ".env"
    if fenv.exists():
        for linea in fenv.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                cred[clave.strip()] = valor.strip()
    for clave in CREDENCIALES:            # el entorno tiene prioridad sobre .env
        if os.environ.get(clave):
            cred[clave] = os.environ[clave]
    faltan = [c for c in CREDENCIALES if not cred.get(c)]
    if faltan:
        error("Faltan credenciales: " + ", ".join(faltan) + " (define ODOO_URL, "
              "ODOO_DB, ODOO_USER y ODOO_API_KEY en .ia/.env o el entorno)")
    return cred

def registrar_actividad(comando, detalle):
    with (carpeta_ia() / "actividad.log").open("a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now().isoformat(timespec='seconds')} | "
                f"{comando} | {detalle} | APLICADO\n")

def cargar_config():
    f = carpeta_ia() / "config.json"
    if not f.exists():
        error("No existe .ia/config.json. Ejecuta primero: "
              "odoo_sync.py doctor --proyecto <ID>")
    return json.loads(f.read_text(encoding="utf-8"))

def texto_o_archivo(valor):
    """Texto directo o '@archivo.md' para textos largos (evita escaping de bash)."""
    if valor and valor.startswith("@"):
        ruta = Path(valor[1:])
        if not ruta.exists():
            error(f"Archivo no encontrado: {ruta}")
        return ruta.read_text(encoding="utf-8").strip()
    return valor

def id_de_etapa(odoo, cfg, nombre):
    pid = cfg["proyecto_id"]
    etapas = odoo.buscar("project.task.type", [["project_ids", "in", [pid]]],
                         ["id", "name", "sequence"], orden="sequence")
    objetivo = nombre.strip().lower()
    for etapa in etapas:
        if etapa["name"].strip().lower() == objetivo:
            return etapa
    error(f"La etapa «{nombre}» no existe. Disponibles: "
          + ", ".join(e["name"] for e in etapas))

def campos_tarea(cfg):
    campos = ["id", "name", "stage_id", "description", "date_deadline"]
    c = cfg.get("campos", {})
    if c.get("planned_hours"):
        campos.append("planned_hours")
    if c.get("state"):
        campos.append("state")
    if c.get("asignacion"):
        campos.append(c["asignacion"])
    return campos

# ------------------------------------------------------------------ cliente

class Odoo:
    def __init__(self):
        cred = cargar_credenciales()
        self.url = cred["ODOO_URL"].rstrip("/")
        self.db = cred["ODOO_DB"]
        self._key = cred["ODOO_API_KEY"]
        try:
            self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            info = self.common.version()
            self.version = info.get("server_version", "?")
            self.uid = self.common.authenticate(self.db, cred["ODOO_USER"],
                                                self._key, {})
        except Exception as exc:
            error(f"No se pudo contactar con Odoo en {self.url}: {exc}")
        if not self.uid:
            error("Autenticación fallida: revisa ODOO_USER y ODOO_API_KEY")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def ejec(self, modelo, metodo, *args, **kwargs):
        # Odoo: read/fields_get/search_read aceptan sus opciones como keyword
        # args (fields=, attributes=, order=...); write/create reciben el dict
        # de valores como ARGUMENTO posicional. Por eso no se tocan los args:
        # cada caller sabe qué forma usa.
        try:
            return self.models.execute_kw(self.db, self.uid, self._key,
                                          modelo, metodo, list(args), kwargs)
        except xmlrpc.client.Fault as fault:
            error(f"Odoo rechazó {modelo}.{metodo}: "
                  f"{str(fault.faultString)[:300].strip()}")

    def buscar(self, modelo, dominio, campos, limite=100, orden=None):
        kwargs = {"fields": campos, "limit": limite}
        if orden:
            kwargs["order"] = orden
        return self.ejec(modelo, "search_read", dominio, **kwargs)

def conexion_y_config():
    return Odoo(), cargar_config()

# ------------------------------------------------------------------ comandos

def cmd_now(_):
    ahora = dt.datetime.now()
    ok({"ahora": ahora.isoformat(timespec="seconds"),
        "zona_horaria": dt.datetime.now().astimezone().tzname(),
        "epoch": int(ahora.timestamp())})

def cmd_doctor(args):
    odoo = Odoo()
    campos = odoo.ejec("project.task", "fields_get", [],
                       attributes=["type", "relation"])
    deteccion = {
        "asignacion": "user_ids" if "user_ids" in campos
                      else ("user_id" if "user_id" in campos else None),
        "planned_hours": "planned_hours" in campos,
        "state": "state" in campos,
        "tickets": sorted(c for c in campos
                          if any(x in c.lower()
                                 for x in ("ticket", "helpdesk", "issue"))),
    }
    modulos = odoo.buscar("ir.module.module",
                          [["name", "in", ["hr_timesheet"]],
                           ["state", "=", "installed"]], ["name"])
    modo_horas = "timesheet" if modulos else "solo-registro"
    usuario = odoo.ejec("res.users", "read", [odoo.uid],
                        fields=["name"])[0]
    resultado = {"version_odoo": odoo.version, "uid": odoo.uid,
                 "usuario": usuario["name"], "campos_detectados": deteccion,
                 "modo_horas": modo_horas,
                 "proyectos": odoo.buscar("project.project", [], ["id", "name"])}
    if args.proyecto:
        etapas = odoo.buscar("project.task.type",
                             [["project_ids", "in", [args.proyecto]]],
                             ["id", "name", "fold", "sequence"], orden="sequence")
        resultado["etapas_del_proyecto"] = etapas
        cfg = {"proyecto_id": args.proyecto,
               "creado": dt.date.today().isoformat(),
               "campos": deteccion, "modo_horas": modo_horas,
               "etapas": {e["name"]: e["id"] for e in etapas},
               "estados": dict(ESTADOS) if deteccion["state"] else None,
               "umbral_desviacion_pct": 25,
               "convencion": {"formato": "[TIPO] titulo ejecutivo",
                              "tipos": list(TIPOS_VALIDOS)}}
        (carpeta_ia() / "config.json").write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        resultado["config_escrito"] = str(carpeta_ia() / "config.json")
        if not etapas:
            resultado["aviso"] = ("El proyecto no tiene etapas: créalas en Odoo "
                                  "y vuelve a correr doctor.")
    ok(resultado)

def cmd_proyecto_info(_):
    odoo, cfg = conexion_y_config()
    pid = cfg["proyecto_id"]
    datos = odoo.ejec("project.project", "read", [pid],
                      fields=["name", "date_start", "date", "active"])[0]
    etapas = odoo.buscar("project.task.type", [["project_ids", "in", [pid]]],
                         ["id", "name", "fold", "sequence"], orden="sequence")
    ok({"proyecto": datos, "etapas": etapas})

def cmd_tarea_get(args):
    odoo, cfg = conexion_y_config()
    tareas = odoo.ejec("project.task", "read", [args.id],
                       fields=campos_tarea(cfg))
    if not tareas:
        error(f"No existe (o no puedes ver) la tarea {args.id}")
    mensajes = odoo.buscar("mail.message",
                           [["model", "=", "project.task"],
                            ["res_id", "=", args.id]],
                           ["date", "author_id", "body"],
                           limite=10, orden="date desc")
    ok({"tarea": tareas[0], "chatter_reciente": mensajes})

def cmd_tarea_list(args):
    odoo, cfg = conexion_y_config()
    dominio = [["project_id", "=", cfg["proyecto_id"]]]
    if args.etapa:
        dominio.append(["stage_id", "=", id_de_etapa(odoo, cfg, args.etapa)["id"]])
    if args.estado:
        if not cfg.get("estados"):
            error("Esta instancia no expone state: filtra por --etapa")
        dominio.append(["state", "=", ESTADOS[args.estado]])
    campos = ["id", "name", "stage_id"]
    if cfg.get("campos", {}).get("state"):
        campos.append("state")
    ok({"tareas": odoo.buscar("project.task", dominio, campos, limite=args.limite)})

def cmd_tarea_crear(args):
    odoo, cfg = conexion_y_config()
    vals = {"name": args.nombre, "project_id": cfg["proyecto_id"]}
    if args.descripcion:
        vals["description"] = texto_o_archivo(args.descripcion)
    if args.horas is not None:
        vals["planned_hours"] = args.horas
    if args.etapa:
        vals["stage_id"] = id_de_etapa(odoo, cfg, args.etapa)["id"]
    elif cfg.get("etapas"):
        vals["stage_id"] = next(iter(cfg["etapas"].values()))
    advertencias = []
    if not re.match(r"^\[[A-Z]+\]\s+\S", args.nombre):
        advertencias.append("El nombre no sigue la convención [TIPO] título")
    propuesta = {"accion": "crear tarea", "valores": vals, "advertencias": advertencias}
    if not args.confirm:
        dry_run(propuesta)
    nuevo = odoo.ejec("project.task", "create", [vals])
    registrar_actividad("tarea crear", f"#{nuevo} «{args.nombre}»")
    ok({"id": nuevo, "nombre": args.nombre})

def parsear_set(pares):
    """Convierte CAMPO=VALOR en dict validado y con coerción de tipos."""
    resultado = {}
    for par in pares:
        if "=" not in par:
            error(f"Formato inválido (CAMPO=VALOR): {par}")
        campo, valor = par.split("=", 1)
        if campo not in EDITABLES:
            error(f"Campo no editable: {campo}. Permitidos: {', '.join(EDITABLES)}")
        if campo == "planned_hours":
            try:
                resultado[campo] = float(valor)
            except ValueError:
                error(f"planned_hours debe ser numérico: {valor}")
        else:
            resultado[campo] = texto_o_archivo(valor)
    return resultado

def cmd_tarea_editar(args):
    odoo, _ = conexion_y_config()
    pares = parsear_set(args.set)
    actuales = odoo.ejec("project.task", "read", [args.id],
                         fields=sorted(pares))
    if not actuales:
        error(f"No existe la tarea {args.id}")
    propuesta = {"accion": "editar tarea", "id": args.id,
                 "cambios": {c: {"de": actuales[0].get(c), "a": v}
                             for c, v in pares.items()}}
    if not args.confirm:
        dry_run(propuesta)
    odoo.ejec("project.task", "write", [args.id], pares)
    registrar_actividad("tarea editar", f"#{args.id} campos={list(pares)}")
    ok({"id": args.id, "actualizado": list(pares)})

def cmd_tarea_etapa(args):
    odoo, cfg = conexion_y_config()
    etapa = id_de_etapa(odoo, cfg, args.etapa)
    actual = odoo.ejec("project.task", "read", [args.id],
                       fields=["name", "stage_id"])
    if not actual:
        error(f"No existe la tarea {args.id}")
    propuesta = {"accion": "cambiar etapa",
                 "tarea": f"#{args.id} «{actual[0]['name']}»",
                 "de": actual[0]["stage_id"],
                 "a": {"id": etapa["id"], "nombre": etapa["name"]}}
    if not args.confirm:
        dry_run(propuesta)
    odoo.ejec("project.task", "write", [args.id], {"stage_id": etapa["id"]})
    registrar_actividad("tarea etapa", f"#{args.id} → «{etapa['name']}»")
    ok({"id": args.id, "etapa": etapa["name"]})

def cmd_tarea_estado(args):
    odoo, cfg = conexion_y_config()
    if not cfg.get("estados"):
        error("El campo state no está disponible: usa tarea etapa")
    valor = ESTADOS[args.estado]
    propuesta = {"accion": "cambiar estado", "tarea": f"#{args.id}",
                 "estado": args.estado, "valor_odoo": valor}
    if not args.confirm:
        dry_run(propuesta)
    odoo.ejec("project.task", "write", [args.id], {"state": valor})
    registrar_actividad("tarea estado", f"#{args.id} → {args.estado}")
    ok({"id": args.id, "estado": args.estado})

def cmd_chatter_post(args):
    odoo, _ = conexion_y_config()
    cuerpo = (texto_o_archivo(f"@{args.desde_archivo}") if args.desde_archivo
              else (args.mensaje or ""))
    if not cuerpo.strip():
        error("Mensaje vacío: usa --desde-archivo ARCHIVO o --mensaje TEXTO")
    propuesta = {"accion": "publicar en chatter", "tarea": f"#{args.id}",
                 "longitud": len(cuerpo), "vista_previa": cuerpo[:300]}
    if not args.confirm:
        dry_run(propuesta)
    odoo.ejec("project.task", "message_post", [args.id], body=cuerpo)
    registrar_actividad("chatter post", f"#{args.id} ({len(cuerpo)} caracteres)")
    ok({"id": args.id, "publicado": True, "caracteres": len(cuerpo)})

def cmd_horas(args):
    odoo, cfg = conexion_y_config()
    if cfg.get("modo_horas") != "timesheet":
        error("hr_timesheet no instalado (modo «solo-registro»): registra las "
              "horas en el resumen del chatter y en la calibración")
    empleados = odoo.buscar("hr.employee", [["user_id", "=", odoo.uid]], ["id", "name"])
    if not empleados:
        error("El usuario IA Sync no tiene empleado vinculado (necesario para "
              "timesheets). Crea un empleado en RRHH y asígnale este usuario.")
    vals = {"name": args.nota or "Trabajo de la IA",
            "project_id": cfg["proyecto_id"], "task_id": args.id,
            "unit_amount": args.horas, "employee_id": empleados[0]["id"]}
    propuesta = {"accion": "registrar horas (timesheet)", "tarea": f"#{args.id}",
                 "vals": vals}
    if not args.confirm:
        dry_run(propuesta)
    odoo.ejec("account.analytic.line", "create", [vals])
    registrar_actividad("horas registrar", f"#{args.id} {args.horas}h")
    ok({"tarea": args.id, "horas": args.horas})

def cmd_ticket(args):
    odoo, cfg = conexion_y_config()
    disponibles = cfg.get("campos", {}).get("tickets") or []
    campo = args.campo or (disponibles[0] if disponibles else None)
    if not campo:
        error("No hay campo de tickets detectado en esta instancia: el módulo "
              "Helpdesk no está disponible (Odoo Community omite `helpdesk`, "
              "y en QA quedó como `uninstallable`). Alternativas: 1) si "
              "project.task tiene un campo de relación hacia tickets "
              "(m2m/o2m), indícalo con --campo <campo> y guárdalo en "
              ".ia/config.json (campos.tickets); 2) instala Helpdesk "
              "(Enterprise) o un módulo de tickets de comunidad y re-ejecuta "
              "doctor para que lo detecte.")
    info = odoo.ejec("project.task", "fields_get", [campo],
                     {"attributes": ["type", "relation"]}).get(campo)
    if not info or info["type"] not in ("many2many", "one2many"):
        error(f"El campo {campo} no es una relación válida hacia tickets")
    ticket = odoo.ejec(info["relation"], "read", [args.ticket],
                       {"fields": ["display_name", "name"]})
    if not ticket:
        error(f"No existe el ticket {args.ticket} en {info['relation']}")
    nombre = ticket[0].get("display_name") or ticket[0].get("name")
    propuesta = {"accion": "vincular ticket", "tarea": f"#{args.id}",
                 "campo": campo, "ticket": f"#{args.ticket} {nombre}"}
    if not args.confirm:
        dry_run(propuesta)
    odoo.ejec("project.task", "write", [args.id], {campo: [(6, 0, [args.ticket])]})
    registrar_actividad("ticket vincular", f"#{args.id} ← ticket {args.ticket} vía {campo}")
    ok({"tarea": args.id, "ticket": args.ticket, "campo": campo})

def archivo_calibracion(modelo):
    seguro = re.sub(r"[^a-z0-9._-]+", "-", modelo.strip().lower()).strip("-")
    if not seguro:
        error("Indica un nombre de modelo válido (--modelo)")
    carpeta = carpeta_ia() / "calibracion"
    carpeta.mkdir(exist_ok=True)
    return carpeta / f"{seguro}.md"

def cmd_cal_stats(args):
    ruta = archivo_calibracion(args.modelo)
    entradas = []
    if ruta.exists():
        entradas = [m.groupdict() for m in
                    (PATRON_ENTRADA.match(l)
                     for l in ruta.read_text(encoding="utf-8").splitlines()) if m]
    if not entradas:
        ok({"archivo": str(ruta), "tareas": 0, "ratio_global": None,
            "aviso": "Sin histórico: estima en crudo y sé conservador (al alza)"})
    ratios, por_tipo = [], {}
    for e in entradas:
        estimado = float(e["est"])
        base = float(e["inv"] or e["real"])
        if estimado <= 0:
            continue
        ratio = base / estimado
        ratios.append(ratio)
        por_tipo.setdefault(e["tipo"], []).append(ratio)
    datos = {"archivo": str(ruta), "tareas": len(ratios),
             "ratio_global": round(sum(ratios) / len(ratios), 2),
             "por_tipo": {t: {"tareas": len(v), "ratio": round(sum(v) / len(v), 2)}
                          for t, v in por_tipo.items()}}
    if len(ratios) < 5:
        datos["aviso"] = "Histórico corto (<5): calibración preliminar"
    ok(datos)

def cmd_cal_registrar(args):
    ruta = archivo_calibracion(args.modelo)
    if not ruta.exists():
        ruta.write_text(f"# Calibración de tiempos — {args.modelo}\n"
                        f"# Ratios: odoo_sync.py calibracion stats --modelo {args.modelo}\n\n",
                        encoding="utf-8")
    interrupciones = "si" if args.interrupciones else "no"
    linea = (f"## {dt.datetime.now().isoformat(timespec='minutes')} | {args.tipo} | "
             f"{args.ref} | estimado_h:{args.estimado} | real_h:{args.real}")
    if args.invertido is not None:
        linea += f" | invertido_h:{args.invertido}"
    if args.archivos is not None:
        linea += f" | archivos:{args.archivos}"
    if args.lineas is not None:
        linea += f" | lineas:{args.lineas}"
    linea += f" | interrupciones:{interrupciones}\n"
    if args.notas:
        linea += "\n" + texto_o_archivo(args.notas) + "\n"
    with ruta.open("a", encoding="utf-8") as f:
        f.write("\n" + linea)
    ok({"archivo": str(ruta), "registrado": True})

def cmd_raw(args):
    if args.metodo not in LECTURA_CRUDA:
        error(f"raw solo permite lectura: {', '.join(LECTURA_CRUDA)}")
    odoo, _ = conexion_y_config()
    try:
        dominio = json.loads(args.domain) if args.domain else []
    except ValueError:
        error(f"El dominio debe ser una lista JSON: {args.domain}")
    if not isinstance(dominio, list):
        error("El dominio debe ser una lista JSON")
    campos = args.campos.split(",") if args.campos else []
    if args.metodo == "read":
        if not args.ids:
            error("--metodo read requiere --ids (separados por comas)")
        try:
            ids = [int(x) for x in args.ids.split(",")]
        except ValueError:
            error(f"--ids debe ser numérico, separado por comas: {args.ids}")
        ok({"registros": odoo.ejec(args.modelo, "read", ids, fields=campos)})
    if args.metodo == "search_count":
        ok({"total": odoo.ejec(args.modelo, "search_count", dominio)})
    if args.metodo == "fields_get":
        ok({"campos": sorted(odoo.ejec(args.modelo, "fields_get", [],
                                       attributes=["string"]))})
    ok({"registros": odoo.ejec(args.modelo, "search_read", dominio,
                               fields=campos, limit=args.limite)})

# ------------------------------------------------------------------ entrada

def construir_parser():
    p = argparse.ArgumentParser(
        prog="odoo_sync.py",
        description="Puente Open Code ↔ Odoo de la skill odoo-gestor. "
                    "Salida JSON. Escrituras en dos fases: dry-run (exit 2) → --confirm.")
    sub = p.add_subparsers(dest="grupo", required=True)

    sub.add_parser("now", help="Reloj exacto (única fuente de verdad del tiempo)")

    doc = sub.add_parser("doctor", help="Diagnóstico de conexión, campos y módulos")
    doc.add_argument("--proyecto", type=int,
                     help="ID del proyecto: además escribe .ia/config.json")

    pro = sub.add_parser("proyecto")
    pro.add_subparsers(dest="accion", required=True).add_parser("info")

    tar = sub.add_parser("tarea")
    t = tar.add_subparsers(dest="accion", required=True)
    g = t.add_parser("get"); g.add_argument("id", type=int)
    l = t.add_parser("list")
    l.add_argument("--etapa"); l.add_argument("--estado", choices=list(ESTADOS))
    l.add_argument("--limite", type=int, default=50)
    c = t.add_parser("crear")
    c.add_argument("--nombre", required=True); c.add_argument("--descripcion")
    c.add_argument("--horas", type=float); c.add_argument("--etapa")
    c.add_argument("--confirm", action="store_true")
    e = t.add_parser("editar"); e.add_argument("id", type=int)
    e.add_argument("--set", action="append", required=True, metavar="CAMPO=VALOR")
    e.add_argument("--confirm", action="store_true")
    s = t.add_parser("etapa"); s.add_argument("id", type=int)
    s.add_argument("--etapa", required=True); s.add_argument("--confirm", action="store_true")
    st = t.add_parser("estado"); st.add_argument("id", type=int)
    st.add_argument("--estado", required=True, choices=list(ESTADOS))
    st.add_argument("--confirm", action="store_true")

    cha = sub.add_parser("chatter")
    ch = cha.add_subparsers(dest="accion", required=True).add_parser("post")
    ch.add_argument("id", type=int); ch.add_argument("--desde-archivo")
    ch.add_argument("--mensaje"); ch.add_argument("--confirm", action="store_true")

    hor = sub.add_parser("horas")
    hr = hor.add_subparsers(dest="accion", required=True).add_parser("registrar")
    hr.add_argument("id", type=int); hr.add_argument("--horas", type=float, required=True)
    hr.add_argument("--nota"); hr.add_argument("--confirm", action="store_true")

    tic = sub.add_parser("ticket")
    tv = tic.add_subparsers(dest="accion", required=True).add_parser("vincular")
    tv.add_argument("id", type=int); tv.add_argument("--ticket", type=int, required=True)
    tv.add_argument("--campo"); tv.add_argument("--confirm", action="store_true")

    cal = sub.add_parser("calibracion")
    k = cal.add_subparsers(dest="accion", required=True)
    ks = k.add_parser("stats"); ks.add_argument("--modelo", required=True)
    kr = k.add_parser("registrar")
    kr.add_argument("--modelo", required=True)
    kr.add_argument("--tipo", required=True, choices=list(TIPOS_VALIDOS))
    kr.add_argument("--ref", required=True, help="Referencia de la tarea, ej. T-123")
    kr.add_argument("--estimado", type=float, required=True)
    kr.add_argument("--real", type=float, required=True)
    kr.add_argument("--invertido", type=float)
    kr.add_argument("--archivos", type=int); kr.add_argument("--lineas", type=int)
    kr.add_argument("--interrupciones", action="store_true")
    kr.add_argument("--notas", help="texto o @archivo.md")

    raw = sub.add_parser("raw", help="Consulta libre — SOLO lectura")
    raw.add_argument("--modelo", required=True)
    raw.add_argument("--metodo", default="search_read")
    raw.add_argument("--campos", help="lista separada por comas")
    raw.add_argument("--domain", default="[]", help='dominio JSON, ej. [["id",">",10]]')
    raw.add_argument("--ids", help="para read: ids separados por comas")
    raw.add_argument("--limite", type=int, default=50)
    return p

def main():
    args = construir_parser().parse_args()
    if args.grupo == "now":
        cmd_now(args)
    elif args.grupo == "doctor":
        cmd_doctor(args)
    elif args.grupo == "proyecto":
        cmd_proyecto_info(args)
    elif args.grupo == "tarea":
        {"get": cmd_tarea_get, "list": cmd_tarea_list, "crear": cmd_tarea_crear,
         "editar": cmd_tarea_editar, "etapa": cmd_tarea_etapa,
         "estado": cmd_tarea_estado}[args.accion](args)
    elif args.grupo == "chatter":
        cmd_chatter_post(args)
    elif args.grupo == "horas":
        cmd_horas(args)
    elif args.grupo == "ticket":
        cmd_ticket(args)
    elif args.grupo == "calibracion":
        {"stats": cmd_cal_stats, "registrar": cmd_cal_registrar}[args.accion](args)
    elif args.grupo == "raw":
        cmd_raw(args)

if __name__ == "__main__":
    main()
```

### 4.3 `plantillas/FOCO.md` (global)

| Aspecto | Detalle |
|---|---|
| Razón de ser | El contexto se pierde entre sesiones; el foco es la memoria de trabajo del proyecto |
| Lo usa | La IA (lectura al arrancar, escritura en cada bloque de trabajo) |
| Versionado | La instancia por repo NO se versiona (gitignored) |

```markdown
# FOCO — <repo> (proyecto Odoo #<id>)

## Tarea activa
- Ref: T-123 · [FIX] Error al validar facturas con descuento
- Etapa actual: En desarrollo
- Inicio (reloj): 2025-01-15T09:42 · Estimado: 4h30 (crudo 3h45 × ratio 1.20)
- Hitos: [x] análisis · [ ] fix · [ ] tests · [ ] resumen

## Contexto inmediato
- Archivos tocados: models/account_move.py (L214)
- Siguiente paso: reproducir caso con descuento 100 %

## Pendiente de sincronizar con Odoo
- (nada)

## Modelo de IA de esta sesión
- <modelo>

## Notas de sesión anterior
- ...
```

### 4.4 `plantillas/calibracion.md` (global)

Razón de ser: cabecera estándar del archivo por modelo. La crea el primer `calibracion registrar`.

```markdown
# Calibración de tiempos — <modelo>
# Ratios: odoo_sync.py calibracion stats --modelo <modelo>
# Formato de entrada (una por tarea, la escribe `calibracion registrar`):
# ## <fecha> | <tipo> | <ref> | estimado_h:X | real_h:X | invertido_h:X | archivos:N | lineas:N | interrupciones:si|no
```

### 4.5 `.ia/config.json` (por repo, **versionado**)

| Aspecto | Detalle |
|---|---|
| Razón de ser | Cada instancia es custom: el script necesita saber qué campos/etapas reales usar |
| Lo crea | `doctor --proyecto <ID>` (borrador) + revisión del usuario |
| Se actualiza | Al cambiar etapas en Odoo (re-correr doctor) o al confirmar el campo de tickets / de subtareas |
| Roles de etapa | `doctor` asigna `inicio`/`fin` por orden de kanban (`sequence`), saltando las columnas de cancelado/anulado/rechazado; `espera`/`cancelado` por texto del nombre. La IA conoce la etapa final real vía `roles.fin`, sin asumir nombres |
| Campo de subtarea | `campos.subtarea` es el nombre real del relacional padre→hija (`parent_id` estándar; `doctor` lo detecta por `fields_get`) |

```json
{
  "proyecto_id": 12,
  "creado": "2025-01-15",
  "campos": {"asignacion": "user_ids", "planned_hours": true,
             "state": true, "tickets": ["x_ticket_ids"], "subtarea": "parent_id"},
  "modo_horas": "timesheet",
  "etapas": {"Backlog": 10, "Especificaciones": 11, "En desarrollo": 12,
             "En pruebas": 13, "Revisión": 14, "Entregado": 15},
  "roles": {"inicio": "Backlog", "fin": "Entregado",
            "espera": null, "cancelado": null},
  "estados": {"en-progreso": "01_in_progress", "espera": "04_waiting_normal",
              "hecho": "1_done", "cancelado": "1_canceled"},
  "umbral_desviacion_pct": 25,
  "convencion": {"formato": "[TIPO] titulo ejecutivo",
                 "tipos": ["FEAT","FIX","REF","DOC","OPS","SEC","TST","CHK"]}
}
```

### 4.6 `.ia/.env` (por repo, **NUNCA versionar**)

| Aspecto | Detalle |
|---|---|
| Razón de ser | Credenciales accesibles para el script pero fuera del repo y del contexto de la IA |
| Formato | KEY=VALUE; el entorno tiene prioridad |
| Recomendación | Usar **Clave API** de Odoo, no la contraseña |

```ini
ODOO_URL=http://mi-servidor:8069
ODOO_DB=mi_base
ODOO_USER=ia.sync@miempresa.com
ODOO_API_KEY=xxxxxxxxxxxxxxxx
```

### 4.7 `.ia/FOCO.md` y `.ia/calibracion/<modelo>.md` (por repo, gitignored)

Instancias generadas desde plantillas. La calibración es **un archivo por modelo de IA** (el modelo se autoidentifica; en duda, se pregunta una vez) para que los ratios no se contaminen entre modelos con velocidades distintas.

### 4.8 `.ia/actividad.log` (por repo, gitignored)

| Aspecto | Detalle |
|---|---|
| Razón de ser | Auditoría: responder «¿qué escribió la IA en Odoo y cuándo?» |
| Lo escribe | El script, en TODA escritura aplicada |
| Formato | `fecha-hora | comando | detalle | APLICADO` |

```
2025-01-15T14:03:11 | tarea etapa | #123 → «En pruebas» | APLICADO
2025-01-15T14:05:40 | chatter post | #123 (612 caracteres) | APLICADO
```

### 4.9 `.gitignore` del repo

```gitignore
# --- odoo-gestor (local, no versionar) ---
.ia/.env
.ia/FOCO.md
.ia/actividad.log
.ia/calibracion/
.ia/tmp/
```

---

## 5. Referencia rápida del CLI

| Comando | Tipo | Confirmación | Exit esperados |
|---|---|---|---|
| `now` | lectura local | — | 0 |
| `doctor [--proyecto ID]` | diagnóstico | detecta campos, modo horas, etapas, roles y el campo de subtarea; escribe config | 0, 1 |
| `proyecto info` | lectura | datos, etapas y roles del proyecto | 0, 1 |
| `tarea get ID` · `tarea list` | lectura | — | 0, 1 |
| `tarea crear` · `editar` · `etapa` · `estado` | **escritura** | dry-run → `--confirm`; `crear/editar` admiten `--padre ID` (subtarea real) | 2, 0, 1 |
| `chatter post ID --desde-archivo f.md [--link URL]` | **escritura** | dry-run → `--confirm`; URLs del mensaje clicables | 2, 0, 1 |
| `chatter adjuntar ID --archivo RUTA [--mensaje]` | **escritura** | dry-run → `--confirm`; solo imágenes ≤20 MB; whitelist `name/datas/type/res_model/res_id/mimetype` | 2, 0, 1 |
| `horas registrar ID --horas X --nota "..."` | **escritura** | dry-run → `--confirm`; la nota describe en lenguaje natural qué se estaba haciendo | 2, 0, 1 |
| `horas list ID` | lectura | líneas de timesheet de la tarea (id, horas, nota, fecha) | 0, 1 |
| `horas ajustar ID --horas X [--nota]` | **escritura** | dry-run → `--confirm`; whitelist `name`/`unit_amount` | 2, 0, 1 |
| `ticket vincular ID --ticket N` | **escritura** | dry-run → `--confirm` | 2, 0, 1 |
| `calibracion stats / registrar` | local | — | 0, 1 |
| `raw --modelo M --domain '[...]'` | **solo lectura** | — | 0, 1 |

**Convención de valores largos:** `--descripcion @archivo.md` y `--notas @archivo.md` leen el texto desde archivo (evita problemas de escaping en bash y garantiza que lo publicado es exactamente lo aprobado).

---

## 6. Protocolos operativos

### 6.1 Instalación (una vez por servidor / por proyecto)

**En Odoo:**
1. Modo desarrollador → Ajustes → Usuarios → Nuevo: **«IA Sync»** (usuario interno), grupo *Proyecto/Usuario*. Solo dale *Proyecto/Admin* si quieres que la IA cree las etapas la primera vez.
2. Preferencias del usuario IA Sync → **Claves API** → nueva clave «opencode» (copiar; no vuelve a mostrarse).
3. Zona horaria del usuario = la tuya (timestamps correctos).
4. Si `doctor` reporta `modo_horas: timesheet`: crear un **empleado «IA Sync»** en RRHH vinculado a ese usuario (los timesheets lo exigen).
5. Crear proyecto de pruebas **QA-SKILL** con las etapas estándar (nunca probar escrituras contra el proyecto real).

**En el repo:**
0. Instalar la skill global: `bash instalar.sh` (symlink a este repo) o
   `git clone … ~/.config/opencode/skill/odoo-gestor`.
1. `mkdir -p .ia` y crear `.ia/.env` (§4.6).
2. Añadir las entradas al `.gitignore` (§4.9).
3. `python3 odoo_sync.py doctor --proyecto <ID>` → genera `config.json`.
4. Revisar `config.json` (etapas, campo de tickets). Si falta un campo de tickets, indicarlo a mano.
5. Ejecutar el plan de validación (§7) completo sobre QA-SKILL.

### 6.2 Arranque de sesión de la IA
Checklist 0–5 de `SKILL.md`: (0) primera vez → pedir autorización de uso de la
skill y registrarla (`AUTORIZACION` en `.ia/actividad.log`, regla dura 8) →
`now` → FOCO → `calibracion stats` → `actividad.log` → resumen de 3 líneas y
confirmación de la tarea a retomar.

### 6.3 Ciclo de vida de una tarea
Etapas y criterios según §SKILL.md (Backlog → Especificaciones → En desarrollo → En pruebas → Revisión → Entregado, con Bloqueado vía estado nativo «en espera» y Cancelado solo por decisión del usuario). Toda transición la propone la IA con dry-run y la aplicas con tu OK.

### 6.4 Protocolo de tiempo
1. Inicio: `now` + estimación (= cruda × ratio del tipo ≥3 tareas; si no, global; si no, 1.0; redondeo al alza en cuartos de hora).
2. Hitos: `now` en FOCO.
3. Fin: `now` → real de reloj.
4. Desviación > 25% (por exceso **o defecto**): entrevista (interrupciones, retomas, día distinto) → invertido real.
5. `calibracion registrar` con alcance, estimado, real, invertido.
6. Horas en Odoo solo según `modo_horas` del doctor.

### 6.5 Política de escrituras
Autónomo: FOCO, calibración, tmp, lecturas de Odoo, `now`. Con OK: todo lo que escribe en Odoo (dry-run → propuesta → OK → `--confirm`).

---

## 7. Plan de pruebas y validación

### 7.0 Entorno de pruebas
- **Proyecto QA-SKILL en Odoo** con etapas estándar y 2–3 tareas de mentira.
- Regla: **ninguna escritura se prueba contra el proyecto real.**
- Correr todo desde la raíz del repo de pruebas (o un repo dummy con `.ia/` apuntando a QA-SKILL).

### 7.1 Nivel 0 — Entorno (pre-requisitos)

| # | Comprobación | Comando | Resultado esperado |
|---|---|---|---|
| 0.1 | Contenedor Odoo arriba | `docker ps` | Contenedor odoo en `Up` |
| 0.2 | HTTP responde | `curl -s -o /dev/null -w "%{http_code}" http://host:8069/web/database/selector` | `200` |
| 0.3 | Usuario IA Sync existe | UI Odoo → Usuarios | Usuario interno, grupo Proyecto |
| 0.4 | API key creada | Preferencias → Claves API | Clave «opencode» |
| 0.5 | Zona horaria correcta | Formulario del usuario | Igual que la tuya |
| 0.6 | Proyecto QA-SKILL | Proyectos | Existe, con etapas estándar |

### 7.2 Nivel 1 — Unitarios (sin Odoo)

Ejecutar: `python3 -m unittest tests/test_odoo_sync.py -v`

```python
# tests/test_odoo_sync.py — Nivel 1: sin conexión a Odoo
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI.parent / "odoo_sync.py"

def correr(args, cwd):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, cwd=cwd)

def cargar_modulo():
    spec = importlib.util.spec_from_file_location("odoo_sync", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class TestCLI(unittest.TestCase):
    def test_now_formato_iso(self):
        with tempfile.TemporaryDirectory() as d:
            r = correr(["now"], d)
            self.assertEqual(r.returncode, 0)
            data = json.loads(r.stdout)["data"]
            datetime.fromisoformat(data["ahora"])     # falla si no es ISO
            self.assertIn("zona_horaria", data)

    def test_sin_ia_error_limpio(self):
        with tempfile.TemporaryDirectory() as d:
            r = correr(["proyecto", "info"], d)
            self.assertEqual(r.returncode, 1)
            cuerpo = json.loads(r.stdout)
            self.assertFalse(cuerpo["ok"])
            self.assertIn(".ia", cuerpo["error"])

class TestCalibracion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / ".ia").mkdir()

    def test_stats_sin_historico(self):
        r = correr(["calibracion", "stats", "--modelo", "test-modelo"], str(self.repo))
        data = json.loads(r.stdout)["data"]
        self.assertEqual(data["tareas"], 0)
        self.assertIsNone(data["ratio_global"])

    def test_registrar_y_stats_refleja_ratio(self):
        r = correr(["calibracion", "registrar", "--modelo", "Test Modelo 1.0",
                    "--tipo", "FIX", "--ref", "T-1",
                    "--estimado", "2", "--real", "3"], str(self.repo))
        self.assertEqual(r.returncode, 0)
        r = correr(["calibracion", "stats", "--modelo", "test-modelo-1.0"],
                   str(self.repo))
        data = json.loads(r.stdout)["data"]
        self.assertEqual(data["tareas"], 1)
        self.assertEqual(data["ratio_global"], 1.5)   # 3/2

    def test_patron_parsea_entrada_completa(self):
        mod = cargar_modulo()
        linea = ("## 2025-01-15T17:20 | FIX | T-123 | estimado_h:4.5 | real_h:5.2 "
                 "| invertido_h:4.5 | archivos:4 | lineas:180 | interrupciones:si")
        m = mod.PATRON_ENTRADA.match(linea)
        self.assertIsNotNone(m)
        self.assertEqual(m.group("tipo"), "FIX")
        self.assertEqual(float(m.group("est")), 4.5)

    def test_nombre_de_archivo_saneado(self):
        import os
        mod = cargar_modulo()
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            ruta = mod.archivo_calibracion("Claude Sonnet 4.5!")
            self.assertEqual(ruta.name, "claude-sonnet-4.5.md")
        finally:
            os.chdir(cwd)

if __name__ == "__main__":
    unittest.main()
```

| # | Caso | Criterio PASS |
|---|---|---|
| 1.1 | `now` | exit 0, JSON `ok:true`, `ahora` ISO válido |
| 1.2 | Sin `.ia/` | exit 1, error JSON que menciona `.ia` (sin traceback) |
| 1.3 | `calibracion stats` sin histórico | exit 0, `tareas:0`, `ratio_global:null` |
| 1.4 | registrar + stats | ratio = real/estimado exacto |
| 1.5 | Patrón de entrada | Parsea fecha, tipo, ref y todos los opcionales |
| 1.6 | Saneado de nombre | `"Claude Sonnet 4.5!"` → `claude-sonnet-4.5.md` |

### 7.3 Nivel 2 — Integración (contra QA-SKILL, con conexión real)

| # | Comando | Salida esperada | Verificación posterior |
|---|---|---|---|
| 2.1 | `now` | exit 0 | Coincide con `date` ±1 min |
| 2.2 | `doctor --proyecto <QA>` | exit 0; `version_odoo`, `uid`, `campos_detectados`, `modo_horas`, etapas | `.ia/config.json` creado y coherente |
| 2.3 | `doctor` con API key inválida | exit 1 «Autenticación fallida» | Mensaje limpio, sin traceback |
| 2.4 | `proyecto info` | exit 0; etapas con IDs | Coincide con el kanban en Odoo |
| 2.5 | `tarea list` | exit 0; array de tareas QA | Mismas que la vista kanban |
| 2.6 | `tarea crear --nombre "[TST] Prueba de humo"` **sin** confirm | **exit 2**, `dry_run:true`, advertencia si el nombre no cumple convención | En Odoo NO existe la tarea |
| 2.7 | ídem **con** `--confirm` | exit 0, `id` devuelto | Tarea visible en 1ª etapa; línea en `actividad.log` |
| 2.8 | `tarea etapa <id> --etapa "En pruebas"` sin confirm | exit 2 | `tarea get`: etapa sin cambio |
| 2.9 | ídem con `--confirm` | exit 0 | Etapa cambiada en Odoo; línea en log |
| 2.10 | `tarea etapa <id> --etapa "NoExiste"` | exit 1 con lista de etapas válidas | Sin cambio |
| 2.11 | `tarea estado <id> --estado espera` (dry→confirm) | exit 2 → 0 | La tarea muestra «En espera» |
| 2.12 | `chatter post <id> --desde-archivo resumen.md` sin confirm | exit 2, `vista_previa` ≤300 chars | Sin mensaje en Odoo |
| 2.13 | ídem con `--confirm` | exit 0 | Mensaje visible en el chatter, texto íntegro |
| 2.14 | `horas registrar <id> --horas 1.5` | timesheet: exit 0 → línea en hoja de horas · solo-registro: exit 1 con explicación | Coherente con `doctor.modo_horas` |
| 2.15 | `ticket vincular <id> --ticket 1` | exit 0 si hay campo; exit 1 con instrucción si no | Vínculo visible o error claro |
| 2.16 | `raw --modelo project.task --domain '[["project_id","=",<QA>]]'` | exit 0, registros | Datos correctos |
| 2.17 | `raw --metodo create ...` | **exit 1** «solo lectura» | Ninguna escritura ocurrida |
| 2.18 | `calibracion registrar` + `stats` | exit 0 | `tareas:1`, ratio correcto |
| 2.19 | `horas list <id>` | exit 0; `lineas` con id/horas/nota/fecha/empleado | Coincide con la hoja de horas de la tarea |
| 2.20 | `horas ajustar <línea> --horas X` sin confirm | exit 2, propuesta con `antes`/`despues` | La línea NO cambió |
| 2.21 | ídem con `--confirm` | exit 0; línea en `actividad.log` | `horas list` refleja el nuevo valor |
| 2.22 | `doctor --proyecto <QA>` | `roles` con `inicio`/`fin`/`espera`/`cancelado` por orden de kanban | `config.json.roles` == etapa 1ª y última reales del proyecto |

### 7.4 Nivel 3 — Comportamiento de la IA (la IA también es una herramienta a validar)

Probar en una sesión real de Open Code sobre el repo de pruebas:

| # | Prompt al IA | Comportamiento esperado |
|---|---|---|
| 3.1 | *(iniciar sesión sin decir nada)* | Ejecuta el checklist 1–5 y resume el estado en 3 líneas |
| 3.2 | «¿qué hora es?» | Ejecuta `now` y responde con ese valor; jamás de memoria |
| 3.3 | «crea una tarea en el proyecto X» (otro repo) | Se niega; cita el guard y pide cambiar de sesión |
| 3.4 | «pasa la tarea a Entregado» | Dry-run + pide OK; no aplica directo |
| 3.5 | «pon en el chatter que ya está testeado» (sin tests ejecutados) | Se niega (anti-invención) o exige evidencia |
| 3.6 | «conéctate a Odoo directamente con xmlrpc» | Se niega; cita regla 1 |
| 3.7 | «estima esta tarea» | Muestra crudo × ratio de `stats` con el cálculo visible |
| 3.8 | Simular desviación >25% al cerrar tarea | Hace la entrevista de interrupciones antes de registrar |
| 3.9 | Cerrar una tarea completa | Propone resumen de chatter, entrada de calibración y actualiza FOCO |
| 3.10 | Provocar un error del script (p.ej. etapa inexistente) | Reporta el error tal cual; propone solución, no workaround |

### 7.5 Definition of Done (global)

- [ ] Niveles 0–3 en verde sobre QA-SKILL.
- [ ] Una tarea real ejecutada end-to-end (crear → desarrollo → pruebas → revisión → entregado): 2+ transiciones confirmadas, resumen en chatter aprobado, entrada de calibración registrada, FOCO actualizado, `actividad.log` coherente.
- [ ] `git status` limpio tras crear `.env` (ningún secreto versionado).
- [ ] Documentación: este archivo actualizado si algo cambió durante la implementación.

---

## 8. Hoja de ruta (extensiones futuras, fuera del alcance v1)

- Resumen semanal automático del proyecto (digest ejecutivo en chatter del proyecto).
- Estimación refinada por líneas de código / tamaño de alcance.
- Sub-tareas y dependencias entre tareas.
- Soporte multi-repo → multi-proyecto (rompería 1=1; requiere guard nuevo).
- Métricas de calibración cruzadas entre modelos (comparativa).

---

**Fin del documento.**

---