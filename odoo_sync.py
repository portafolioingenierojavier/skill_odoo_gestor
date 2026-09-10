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
import xmlrpc.client
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ------------------------------------------------------------------ constantes

CREDENCIALES = ("ODOO_URL", "ODOO_DB", "ODOO_USER", "ODOO_API_KEY")

UMBRAL_DESVIACION_PCT = 25  # aviso de desviación en `doctor` (config.json)

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


def coincidir_etapa(etapas, nombre):
    """Empareja un nombre de etapa contra una lista (case-insensitive, strip)."""
    objetivo = nombre.strip().lower()
    for etapa in etapas:
        if etapa["name"].strip().lower() == objetivo:
            return etapa
    return None


def id_de_etapa(odoo, cfg, nombre):
    pid = cfg["proyecto_id"]
    etapas = odoo.buscar("project.task.type", [["project_ids", "in", [pid]]],
                         ["id", "name", "sequence"], orden="sequence")
    etapa = coincidir_etapa(etapas, nombre)
    if etapa:
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


def validar_convencion(nombre):
    """True si el nombre sigue la convención `[TIPO] titulo ejecutivo`."""
    return re.match(r"^\[[A-Z]+\]\s+\S", nombre) is not None


def parsear_set(pares):
    """Convierte CAMPO=VALOR en dict validado y coerción de tipos."""
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


def archivo_calibracion(modelo):
    seguro = re.sub(r"[^a-z0-9._-]+", "-", modelo.strip().lower()).strip("-")
    if not seguro:
        error("Indica un nombre de modelo válido (--modelo)")
    carpeta = carpeta_ia() / "calibracion"
    carpeta.mkdir(exist_ok=True)
    return carpeta / f"{seguro}.md"


def texto_o_archivo(valor):
    """Texto directo o '@archivo.md' para textos largos (evita escaping de bash)."""
    if valor and valor.startswith("@"):
        ruta = Path(valor[1:])
        if not ruta.exists():
            error(f"Archivo no encontrado: {ruta}")
        return ruta.read_text(encoding="utf-8").strip()
    return valor


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
        # de valores como ARGUMENTO posicional. Por eso aquí no se tocan los
        # args: cada caller sabe qué forma usa.
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


# ------------------------------------------------------------------ comandos

def cmd_now(_):
    ahora = dt.datetime.now()
    ok({"ahora": ahora.isoformat(timespec="seconds"),
        "zona_horaria": dt.datetime.now().astimezone().tzname(),
        "epoch": int(ahora.timestamp())})


def construir_config(pid, deteccion, etapas, modo_horas):
    """Versión pura del config: permitir test N1 sin conexión a Odoo."""
    return {"proyecto_id": pid,
            "creado": dt.date.today().isoformat(),
            "campos": deteccion,
            "modo_horas": modo_horas,
            "etapas": {e["name"]: e["id"] for e in etapas},
            "estados": dict(ESTADOS) if deteccion["state"] else None,
            "umbral_desviacion_pct": UMBRAL_DESVIACION_PCT,
            "convencion": {"formato": "[TIPO] titulo ejecutivo",
                           "tipos": list(TIPOS_VALIDOS)}}


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
        cfg = construir_config(args.proyecto, deteccion, etapas, modo_horas)
        (carpeta_ia() / "config.json").write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        resultado["config_escrito"] = str(carpeta_ia() / "config.json")
        if not etapas:
            resultado["aviso"] = ("El proyecto no tiene etapas: créalas en Odoo "
                                  "y vuelve a correr doctor.")
    ok(resultado)


def conexion_y_config():
    return Odoo(), cargar_config()


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
    if not validar_convencion(args.nombre):
        advertencias.append("El nombre no sigue la convención [TIPO] título")
    propuesta = {"accion": "crear tarea", "valores": vals, "advertencias": advertencias}
    if not args.confirm:
        dry_run(propuesta)
    nuevo = odoo.ejec("project.task", "create", [vals])
    registrar_actividad("tarea crear", f"#{nuevo} «{args.nombre}»")
    ok({"id": nuevo, "nombre": args.nombre})


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


def cmd_horas(args):
    odoo, cfg = conexion_y_config()
    if cfg.get("modo_horas") != "timesheet":
        error("hr_timesheet no instalado (modo «solo-registro»): registra las "
              "horas en el resumen del chatter y en la calibración")
    empleados = odoo.buscar("hr.employee", [["user_id", "=", odoo.uid]],
                            ["id", "name"])
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
                     attributes=["type", "relation"]).get(campo)
    if not info or info["type"] not in ("many2many", "one2many"):
        error(f"El campo {campo} no es una relación válida hacia tickets")
    ticket = odoo.ejec(info["relation"], "read", [args.ticket],
                       fields=["display_name", "name"])
    if not ticket:
        error(f"No existe el ticket {args.ticket} en {info['relation']}")
    nombre = ticket[0].get("display_name") or ticket[0].get("name")
    propuesta = {"accion": "vincular ticket", "tarea": f"#{args.id}",
                 "campo": campo, "ticket": f"#{args.ticket} {nombre}"}
    if not args.confirm:
        dry_run(propuesta)
    odoo.ejec("project.task", "write", [args.id],
              {campo: [(6, 0, [args.ticket])]})
    registrar_actividad("ticket vincular",
                        f"#{args.id} ← ticket {args.ticket} vía {campo}")
    ok({"tarea": args.id, "ticket": args.ticket, "campo": campo})


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
    g = t.add_parser("get")
    g.add_argument("id", type=int)
    l = t.add_parser("list")
    l.add_argument("--etapa")
    l.add_argument("--estado", choices=list(ESTADOS))
    l.add_argument("--limite", type=int, default=50)
    c = t.add_parser("crear")
    c.add_argument("--nombre", required=True)
    c.add_argument("--descripcion")
    c.add_argument("--horas", type=float)
    c.add_argument("--etapa")
    c.add_argument("--confirm", action="store_true")
    e = t.add_parser("editar")
    e.add_argument("id", type=int)
    e.add_argument("--set", action="append", required=True, metavar="CAMPO=VALOR")
    e.add_argument("--confirm", action="store_true")
    s = t.add_parser("etapa")
    s.add_argument("id", type=int)
    s.add_argument("--etapa", required=True)
    s.add_argument("--confirm", action="store_true")
    st = t.add_parser("estado")
    st.add_argument("id", type=int)
    st.add_argument("--estado", required=True, choices=list(ESTADOS))
    st.add_argument("--confirm", action="store_true")

    cha = sub.add_parser("chatter")
    ch = cha.add_subparsers(dest="accion", required=True).add_parser("post")
    ch.add_argument("id", type=int)
    ch.add_argument("--desde-archivo")
    ch.add_argument("--mensaje")
    ch.add_argument("--confirm", action="store_true")

    hor = sub.add_parser("horas")
    hr = hor.add_subparsers(dest="accion", required=True).add_parser("registrar")
    hr.add_argument("id", type=int)
    hr.add_argument("--horas", type=float, required=True)
    hr.add_argument("--nota")
    hr.add_argument("--confirm", action="store_true")

    tic = sub.add_parser("ticket")
    tv = tic.add_subparsers(dest="accion", required=True).add_parser("vincular")
    tv.add_argument("id", type=int)
    tv.add_argument("--ticket", type=int, required=True)
    tv.add_argument("--campo")
    tv.add_argument("--confirm", action="store_true")

    cal = sub.add_parser("calibracion")
    k = cal.add_subparsers(dest="accion", required=True)
    ks = k.add_parser("stats")
    ks.add_argument("--modelo", required=True)
    kr = k.add_parser("registrar")
    kr.add_argument("--modelo", required=True)
    kr.add_argument("--tipo", required=True, choices=list(TIPOS_VALIDOS))
    kr.add_argument("--ref", required=True)
    kr.add_argument("--estimado", type=float, required=True)
    kr.add_argument("--real", type=float, required=True)
    kr.add_argument("--invertido", type=float)
    kr.add_argument("--archivos", type=int)
    kr.add_argument("--lineas", type=int)
    kr.add_argument("--interrupciones", action="store_true")
    kr.add_argument("--notas", help="texto o @archivo.md")

    raw = sub.add_parser("raw", help="Consulta libre — SOLO lectura")
    raw.add_argument("--modelo", required=True)
    raw.add_argument("--metodo", default="search_read")
    raw.add_argument("--campos", help="lista separada por comas")
    raw.add_argument("--domain", default="[]",
                     help='dominio JSON, ej. [["id",">",10]]')
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