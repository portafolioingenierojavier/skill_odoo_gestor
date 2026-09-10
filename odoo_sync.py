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

# ------------------------------------------------------------------ constantes

CREDENCIALES = ("ODOO_URL", "ODOO_DB", "ODOO_USER", "ODOO_API_KEY")

UMBRAL_DESVIACION_PCT = 25  # aviso de desviación en `doctor` (config.json)

ESTADOS = {  # alias amigable → valor del campo state (Odoo 16+)
    "en-progreso": "01_in_progress",
    "espera": "02_waiting_normal",
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

    def ejec(self, modelo, metodo, *args, **kws):
        # Los callers pasan el dict de params (fields, attributes, valores de
        # write...) como ÚLTIMO argumento posicional. Se extrae como kwargs de
        # execute_kw para respetar la semántica XML-RPC.
        if args and isinstance(args[-1], dict):
            params = args[-1]
            args = args[:-1]
        else:
            params = {}
        params.update(kws)
        try:
            return self.models.execute_kw(self.db, self.uid, self._key,
                                          modelo, metodo, list(args), params)
        except xmlrpc.client.Fault as fault:
            error(f"Odoo rechazó {modelo}.{metodo}: "
                  f"{str(fault.faultString)[:300].strip()}")

    def buscar(self, modelo, dominio, campos, limite=100, orden=None):
        kwargs = {"fields": campos, "limit": limite}
        if orden:
            kwargs["order"] = orden
        return self.ejec(modelo, "search_read", dominio, kwargs)


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
                       {"attributes": ["type", "relation"]})
    deteccion = {
        "asignacion": "user_ids" if "user_ids" in campos
                      else ("user_id" if "user_id" in campos else None),
        "planned_hours": "planned_hours" in campos,
        "state": "state" in campos,
        "tickets": sorted(c for c in campos if "ticket" in c.lower()),
    }
    modulos = odoo.buscar("ir.module.module",
                          [["name", "in", ["hr_timesheet"]],
                           ["state", "=", "installed"]], ["name"])
    modo_horas = "timesheet" if modulos else "solo-registro"
    usuario = odoo.ejec("res.users", "read", [odoo.uid],
                        {"fields": ["name"]})[0]
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
                      {"fields": ["name", "date_start", "date", "active"]})[0]
    etapas = odoo.buscar("project.task.type", [["project_ids", "in", [pid]]],
                         ["id", "name", "fold", "sequence"], orden="sequence")
    ok({"proyecto": datos, "etapas": etapas})


def cmd_tarea_get(args):
    odoo, cfg = conexion_y_config()
    tareas = odoo.ejec("project.task", "read", [args.id],
                       {"fields": campos_tarea(cfg)})
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
        {"get": cmd_tarea_get, "list": cmd_tarea_list}[args.accion](args)


if __name__ == "__main__":
    main()