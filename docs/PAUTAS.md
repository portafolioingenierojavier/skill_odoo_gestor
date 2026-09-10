# PAUTAS.md — Reglas de desarrollo de la skill «odoo-gestor»

**Documento normativo de cumplimiento OBLIGATORIO durante el desarrollo y creación de la skill.**

| | |
|---|---|
| Versión | 1.0 |
| Ámbito | Todo commit, todo archivo, toda sesión de IA que toque este proyecto |
| Relación | Complementa `ARQUITECTURA.md` (qué se construye). Este documento define **cómo se construye y cuándo se integra** |
| Principio rector | Esta skill es infraestructura crítica: la IA de todos los proyectos depende de ella. Un bug aquí contamina todo lo que la IA toca en Odoo. Se prioriza correcto sobre rápido |

---

## 1. Reglas inviolables («si o si»)

1. **Puerta de commit verde:** se hace commit al terminar cada tarea **solo si toda la batería de tests y comprobaciones acumuladas hasta ese momento está en verde**. Sin excepciones: ni «es un cambio pequeño», ni «lo arreglo en el próximo commit», ni «el fallo es del entorno». Si algo está rojo, el commit espera.
2. **1 tarea = 1 commit = 1 rama `TIPO-<id>`:** el commit contiene la tarea completa (código + tests + documentación afectada). Atómico y revertible. Prohibido mezclar dos tareas en un commit.
3. **Test junto al código:** toda funcionalidad nueva llega con su test en el mismo commit. Código sin test no se commitea (ver matriz §7).
4. **Solo librería estándar de Python:** `odoo_sync.py` no gana dependencias externas. Sin `pip install`, sin requirements.txt. Si se cree necesaria una, es decisión de diseño documentada en `ARQUITECTURA.md` primero.
5. **UTF-8 explícito siempre:** toda lectura/escritura de archivo usa `encoding="utf-8"`. El contenido es español (acentos, ñ); omitirlo es bug latente. Inviolable incluso en código «de prueba».
6. **Solo la clase `Odoo` toca `xmlrpc`:** ningún otro punto del código construye clientes, URLs ni llamadas RPC. Toda excepción RPC se maneja en `Odoo.ejec` y sale como error JSON accionable.
7. **Salidas únicas:** solo `ok()`, `error()` y `dry_run()` llaman a `sys.exit()`. Prohibido esparcir exits por el código.
8. **Toda escritura en Odoo pasa por dry-run → `--confirm` y deja línea en `actividad.log`.** Toda capacidad de escritura nueva hereda este mecanismo sin discusión.
9. **Solo `doctor` escribe `.ia/config.json`.** Ningún otro comando ni la IA modifican la config por su cuenta.
10. **`raw` jamás gana escritura.** Si se necesita una escritura nueva, se crea un comando específico con whitelist, dry-run y test. Ampliar `raw` es un rechazo automático de revisión.
11. **Credenciales intocables:** solo `cargar_credenciales()` lee `.env`. Prohibido printear, loguear, cachear o pasar secretos como argumentos. Prohibido commitear `.env`, claves API o cualquier secreto.
12. **Bug → test primero:** todo bug encontrado se reproduce con un test (que falla), luego se corrige, luego se commitea con el test incluido. El test queda para siempre en la batería (regresión).

---

## 2. Flujo de trabajo por tarea (obligatorio)

```
1. ARRANQUE     leer FOCO · crear/retomar la tarea en Odoo (QA-SKILL durante el desarrollo)
                · marcar inicio con `odoo_sync.py now` en FOCO
2. PLAN        la IA (o tú) expone el plan de la tarea ANTES de codificar:
                archivos a tocar, comandos/protocolos afectados, tests previstos
3. CÓDIGO      desarrollar siguiendo §4 (código) y §5 (estructura)
                · marcar hitos con `now` en FOCO
                · si aparece un cambio de diseño: actualizar ARQUITECTURA.md
                  en el MISMO commit (doc-first)
4. TESTS       escribir los tests nuevos junto a la funcionalidad
5. BATERÍA     ejecutar TODA la batería acumulada (nivel 1 completo +
                niveles 0-2/3 que apliquen según la matriz §7)
6. ¿VERDE?     NO → arreglar y volver a 5.   SÍ → continuar
7. COMMIT      formato §8 · incluye código + tests + docs · evidencia de
                validación en el cuerpo del commit
8. CIERRE      actualizar FOCO · proponer transición de etapa en Odoo (dry-run
                → tu OK → confirm) · registrar entrada de calibración
```

**Puntos del flujo que no se negocian:**

- El paso 5 usa la batería **acumulada**: los tests de todas las tareas anteriores siguen existiendo y siguen pasando. La batería solo crece.
- Si el rojo proviene del entorno (Odoo caído, Docker parado), el commit **espera**. No se salta la puerta por culpa ajena.
- Prohibido «amañar» tests: reducir su alcance, aflojar el criterio o marcarlos skip para conseguir verde. Un `skip` exige justificación escrita en el commit y visibilidad en la próxima sesión.
- La tarea no está «terminada» hasta el paso 8. «Terminada» = commiteada en verde + FOCO actualizado + etapa movida en Odoo.

---

## 3. La puerta de commit — definición exacta de «verde acumulado»

Se considera **verde acumulado** cuando, en el mismo momento del commit:

| Fuente | Condición |
|---|---|
| Nivel 1 (unitarios, `python3 -m unittest tests/test_odoo_sync.py -v`) | 100% pass, 0 skips sin justificar |
| Nivel 2 (integración contra QA-SKILL) | 100% de los casos **aplicables** según la matriz §7 |
| Nivel 0 (entorno) | Solo si la tarea tocó infraestructura (Docker, usuario, API key, red) |
| Nivel 3 (comportamiento IA) | Solo si la tarea tocó `SKILL.md`, plantillas o protocolos |
| Nuevo código | Llega con test propio; sin «lo testeo luego» |
| Formatos de datos (calibración, config, FOCO) | El parser actual lee las entradas viejas Y las nuevas |

**Regla de oro del repo:** si el historial de git muestra un commit, ese commit certifica que en ese instante todo estaba en verde. Ese es el estándar que hace posible confiar en cualquier `revert` y en cualquier bisect futuro.

---

## 4. Pautas de código (Python)

**Estilo:**
- PEP 8, relajado a **110 caracteres** por línea máximo.
- `f-strings` para interpolación; `pathlib` en lugar de `os.path` (salvo `os.environ`).
- Nombres de funciones/variables descriptivos; prohibidos `tmp2`, `datosAux`, `x`.
- Type hints en toda función **nueva** (no se reescribe el código viejo de golpe; se converge).
- Docstring de al menos una línea en toda función de nivel de comando.
- Constantes arriba del archivo; prohibidos números mágicos — umbrales y límites van a constantes o a `config.json`.

**Robustez:**
- **Fail before write:** validar TODA la entrada (ids, nombres de etapa, tipos, rangos) antes de la primera llamada que escriba en Odoo. Un comando nunca escribe a medias.
- Errores **accionables y en español**: el mensaje dice qué falló Y qué hacer («La etapa X no existe. Disponibles: …»). Prohibido el traceback crudo.
- Prohibido `except: pass` y `except Exception` silencioso. Las capturas son específicas; lo inesperado sube hasta `error()` con contexto.
- Idempotencia donde sea posible: reintentar un comando confirmado no debe duplicar efectos si es evitable (p. ej. vincular un ticket ya vinculado → ok informativo, no duplicado).
- Funciones puras separadas de efectos: parseo, cálculo de ratios y saneado no tocan red ni disco; se testean sin mocks.

**Dominio y idioma:**
- Mensajes de usuario, propuestas, errores y logs: **español**.
- Identificadores de código: español para dominio (`tarea`, `etapa`, `calibracion`), inglés solo para vocabulario técnico estándar.

**Métricas límite de mantenimiento (alerta, no bloqueo):**
- Función > 60 líneas → refactorizar en la misma tarea.
- `odoo_sync.py` > 800 líneas → NO se fragmenta improvisadamente: se redacta el plan de modularización en `ARQUITECTURA.md`, tarea aparte, con su propio commit.

---

## 5. Pautas de estructura

**Repo de desarrollo de la skill** (la skill se desarrolla con control de versiones; la instalación global es un symlink):

```
odoo-gestor/                      ← repo de desarrollo (git)
├── SKILL.md
├── odoo_sync.py
├── plantillas/
│   ├── FOCO.md
│   └── calibracion.md
├── tests/
│   ├── test_odoo_sync.py         ← N1
│   └── INTEGRACION.md            ← N2 (checklist ejecutable)
├── docs/
│   ├── ARQUITECTURA.md
│   └── PAUTAS.md                 ← este archivo
├── CHANGELOG.md
└── instalar.sh                   ← crea el symlink en ~/.config/opencode/skill/
```

Instalación: `symlink` de `~/.config/opencode/skill/odoo-gestor` → este repo. Así el desarrollo y la instalación son lo mismo; no hay copias divergentes. Prohibido editar directamente en `~/.config`.

**Reglas de coherencia estructural:**

- **Cambio de formato = cambio atómico triple:** si cambia el formato de FOCO, calibración o config.json, el MISMO commit actualiza: (1) el código que lo escribe/lee, (2) la plantilla correspondiente, (3) el test que valida el parseo. Desincronizar plantilla y código es el bug clásico de este sistema.
- **Doc-first:** cualquier cambio de diseño (nuevo comando, cambio de protocolo, nuevo archivo) se refleja en `ARQUITECTURA.md` en el mismo commit que lo implementa. El documento nunca queda atrás del código.
- Orden interno de `odoo_sync.py` (ya establecido, se respeta): constantes → utilidades → cliente `Odoo` → comandos → parser → `main`.
- Un archivo, una responsabilidad. Si un archivo empieza a hacer dos cosas, se documenta y se divide (tarea propia).

---

## 6. Pautas de seguridad

1. `cargar_credenciales()` es el único lector de `.env`. Ningún test, comando o log imprime valores de credenciales (los tests de N2 usan el `.env` real del repo de pruebas, jamás secretos hardcodeados).
2. `actividad.log` no contiene secretos: se revisa al añadir cualquier detalle nuevo a los logs.
3. Toda ampliación de `EDITABLES` (campos editables de tarea) o de cualquier whitelist de escritura exige: decisión explícita documentada + dry-run/confirm + test. Nunca «ya que estoy tocando esto».
4. `raw` permanece de solo lectura (regla 10 de §1).
5. Al compartir el repo o pantallazos: revisar que `.env`, `actividad.log`, `FOCO.md` y `calibracion/` no viajen (están en `.gitignore`, pero se verifica con `git status` antes de cada push).

---

## 7. Matriz de cambio → validación exigida

Qué batería hay que re-ejecutar (y qué test nuevo exige) cada tipo de cambio. Esta matriz es la que decide qué cuenta como «verde acumulado» en cada commit:

| Tipo de cambio | Test nuevo obligatorio | Re-ejecutar N1 | N2 | N3 | Actualizar docs |
|---|---|---|---|---|---|
| Lógica pura local (calibración, parseo, saneado, `now`) | Unitario | ✅ | — | — | Si cambia formato |
| Comando Odoo nuevo o modificado | Unitario + caso N2 | ✅ | ✅ | Si cambia flujo | ✅ ARQUITECTURA + índice SKILL.md |
| Cambio en dry-run/confirm de un comando | Unitario del exit code + N2 | ✅ | ✅ | — | ✅ |
| `SKILL.md` (reglas/protocolos) | — | — | — | ✅ (checklist 3.x) | ✅ |
| Plantillas (FOCO, calibración) | Parseo del formato | ✅ | — | ✅ | ✅ |
| `instalar.sh` / estructura de repo | Ejecución en seco | — | ✅ (0.x) | — | ✅ |
| Infraestructura (Docker, usuario, API key) | — | ✅ | ✅ completa | — | — |
| Corrección de bug | Test de regresión (falla primero) | ✅ | Según área | Según área | Commit explica causa |

**Nivel 3 solo se puede ejecutar con la skill instalada (symlink) y Odoo arriba.** Sus escenarios (3.1–3.10 de ARQUITECTURA §7.4) son el contrato de comportamiento de la IA: cambiar `SKILL.md` sin re-validar N3 rompe el contrato silenciosamente.

---

## 8. Commits y ramas

**Rama por tarea:** `TIPO-<id_odoo>` — ej. `FIX-142`, `FEAT-156`, `TST-160`. Merge a `main` solo con la puerta de commit en verde.

**Formato de commit (obligatorio):**

```
[T-<id>] <verbo en imperativo> <qué hace>

- <detalle relevante 1>
- <detalle relevante 2>

Validación: N1 ✅ (14/14) · N2 ✅ (2.1–2.13) · N3 — no aplica
```

Ejemplo real:

```
[T-142] añadir comando ticket vincular con detección de campo

- doctor ya detecta campos con "ticket" en project.task
- vinculación vía many2many/one2many con dry-run y --confirm
- si no hay campo detectado, error accionable pidiendo --campo

Validación: N1 ✅ (16/16) · N2 ✅ (2.1–2.15) · N3 — no aplica
```

**Reglas de commit:**

- La línea de **Validación es obligatoria**: el commit certifica el verde (§3). Un commit sin línea de validación está mal formado.
- Prohibidos: `wip`, `cambios`, `fix` a secas, commits vacíos de contexto, y commits que mezclan tareas.
- Si el commit arregla un bug, el cuerpo menciona la causa raíz (no solo el síntoma).
- `revert` de un commit es legítimo y debe dejar la batería en verde por sí mismo (consecuencia de la atomicidad de la regla 2).

---

## 9. Versionado y compatibilidad de la skill

- **SemVer** en `CHANGELOG.md`:
  - `MAJOR`: cambia protocolos o formatos de datos de forma incompatible (entrada de calibración, `config.json`, FOCO, reglas duras de SKILL.md).
  - `MINOR`: comando o capacidad nueva.
  - `PATCH`: corrección sin cambio de contrato.
- **Compatibilidad hacia atrás obligatoria en formatos:** el parser de calibración/config debe seguir leyendo entradas viejas tras un cambio de formato (con test que lo pruebe, ver matriz §7). Si no es posible, es MAJOR y se escribe el paso de migración en el CHANGELOG.
- Todo cambio de versión se registra en `CHANGELOG.md` en el mismo commit del cambio.

**Dogfooding:** la skill empieza a gestionar su propio desarrollo (sus tareas en Odoo) solo después de alcanzar el Definition of Done de nivel 2 (ARQUITECTURA §7.5). Hasta entonces, el desarrollo se gestiona manualmente o contra QA-SKILL.

---

## 10. Prohibiciones explícitas (chuleta rápida)

| ❌ Prohibido | Regla |
|---|---|
| Commitear con algo en rojo | §1.1 |
| Commit «wip» o sin línea de Validación | §8 |
| Desactivar/aflojar un test para pasar | §1.12, §2 |
| Dependencia externa en `odoo_sync.py` | §1.4 |
| `open()` sin `encoding="utf-8"` | §1.5 |
| `xmlrpc` fuera de la clase `Odoo` | §1.6 |
| `sys.exit` fuera de ok/error/dry_run | §1.7 |
| Escritura en Odoo sin dry-run/confirm ni log | §1.8 |
| Escribir `config.json` fuera de `doctor` | §1.9 |
| Dar escritura a `raw` | §1.10 |
| Printear/loguear credenciales | §1.11 |
| Commitear secretos o archivos locales | §1.11, §6.5 |
| Cambiar plantilla sin cambiar código+test en el mismo commit | §5 |
| Cambiar diseño sin actualizar ARQUITECTURA.md | §5 |
| Editar la skill directamente en `~/.config` | §5 |
| Fragmentar `odoo_sync.py` sin plan documentado | §4 |
| Código nuevo sin test cuando la matriz lo exige | §7 |

---

## 11. Checklist de fin de tarea (imprimible)

```
TAREA: ______  RAMA: TIPO-____  T-ODOO: ____

[ ] Plan expuesto antes de codificar
[ ] Código conforme a §4 (valida entrada, errores accionables, UTF-8, sin mágicos)
[ ] Tests nuevos escritos y pasando
[ ] Batería N1 completa: ___/___ en verde, 0 skips injustificados
[ ] N2/N3/N0 según matriz §7: ____________
[ ] Formatos: parser lee entradas viejas y nuevas (si aplica)
[ ] Docs actualizadas en este commit (ARQUITECTURA / CHANGELOG / SKILL.md)
[ ] git status limpio (sin secretos, sin locales)
[ ] COMMIT con formato §8 + línea de Validación
[ ] FOCO actualizado · etapa propuesta en Odoo · calibración registrada
```

---

**Fin del documento.** Si una pauta choca con la realidad del desarrollo, se cambia ESTE documento primero (commit propio, con validación), y después el código. Nunca al revés.

---