#!/usr/bin/env python3
"""Bootstrap idempotente del entorno QA-SKILL (Fase 0 del roadmap).

Crea:
- base de datos qa_skill (si no existe)
- usuario interno "IA Sync" con grupos Proyecto/Usuario
- empleado IA Sync vinculado (requiere hr_timesheet)
- proyecto QA-SKILL con las etapas estándar
- tareas de prueba
- API key "opencode" para IA Sync (con --api-key)

Credenciales por variables de entorno (ver README.md). Nunca escribir
secretos aquí.
"""
import argparse
import http.cookiejar
import json
import os
import sys
import urllib.parse
import urllib.request
from pprint import pprint

import xmlrpc.client

URL = os.environ.get("ODOO_URL", "http://localhost:8069")
DB = os.environ.get("ODOO_DB", "qa_skill")
ADMIN_LOGIN = os.environ.get("ODOO_ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.environ.get("ODOO_ADMIN_PASSWORD", "admin_qa_2026")
IA_LOGIN = os.environ.get("ODOO_IA_LOGIN", "ia.sync")
IA_PASSWORD = os.environ.get("ODOO_IA_PASSWORD", "ia_sync_qa_2026")
MASTER_PASSWORD = os.environ.get("ODOO_MASTER_PASSWORD", "admin_master_qa")

ETAPAS_ESTANDAR = [
    ("Backlog", 1, False),
    ("Especificaciones", 2, False),
    ("En desarrollo", 3, False),
    ("En pruebas", 4, False),
    ("Revisión", 5, False),
    ("Entregado", 6, True),
    ("Cancelado", 7, True),
]

TAREAS_PRUEBA = [
    ("[TST] Tarea de prueba Alpha", "Backlog", "Tarea basura para pruebas de lectura y escritura."),
    ("[TST] Tarea de prueba Beta", "Especificaciones", "Segunda tarea de prueba."),
    ("[TST] Tarea de prueba Gamma", "Backlog", "Tercera tarea de prueba."),
]


def crear_base_datos():
    data = urllib.parse.urlencode({
        "master_pwd": MASTER_PASSWORD,
        "name": DB,
        "login": ADMIN_LOGIN,
        "password": ADMIN_PASSWORD,
        "lang": "es_ES",
        "country_code": "EC",
        "phone": "",
        "demo": "true",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{URL}/web/database/create", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        urllib.request.urlopen(req, timeout=300)
        print(f"[OK] Base de datos '{DB}' creada")
    except urllib.error.HTTPError as e:
        print(f"[WARN] no se pudo crear la DB ({e.code}) — ¿ya existe?")
        return False
    return True


def conectar():
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
    uid = common.authenticate(DB, ADMIN_LOGIN, ADMIN_PASSWORD, {})
    if not uid:
        print("ERROR: autentificacion admin fallida", file=sys.stderr)
        sys.exit(1)
    return common, xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object"), uid


def ejec(models, uid, modelo, metodo, *args, **kwargs):
    return models.execute_kw(DB, uid, ADMIN_PASSWORD, modelo, metodo, list(args), kwargs)


def inspeccionar_entorno(models, uid):
    modulos = ejec(models, uid, "ir.module.module", "search_read",
                   [["name", "in", ["project", "hr_timesheet", "auth_api_key"]],
                    ["state", "=", "installed"]],
                   fields=["name"])
    print(f"[INFO] Modulos instalados: {[m['name'] for m in modulos]}")
    return {m["name"] for m in modulos}


def crear_usuario_ia(models, uid):
    ids_grupos = [g["id"] for g in ejec(models, uid, "res.groups", "search_read",
                                        [["name", "=", "Internal User"]],
                                        fields=["id"])]
    ids_grupos += [g["id"] for g in ejec(models, uid, "res.groups", "search_read",
                                         [["name", "like", "Project/User"]],
                                         fields=["id"])]
    existente = ejec(models, uid, "res.users", "search_read",
                     [["login", "=", IA_LOGIN]], fields=["id"])
    if existente:
        print(f"[SKIP] Usuario '{IA_LOGIN}' ya existe (uid={existente[0]['id']})")
        return existente[0]["id"]
    nuevo = ejec(models, uid, "res.users", "create", {
        "name": "IA Sync", "login": IA_LOGIN, "password": IA_PASSWORD,
        "email": "ia.sync@qaskill.local",
        "groups_id": [(6, 0, ids_grupos)],
        "tz": "America/Guayaquil", "company_id": 1,
    })
    print(f"[OK] Usuario IA Sync creado, uid={nuevo}")
    return nuevo


def crear_empleado(models, uid, uid_ia):
    existente = ejec(models, uid, "hr.employee", "search_read",
                     [["user_id", "=", uid_ia]], fields=["id"])
    if existente:
        print(f"[SKIP] Empleado IA Sync ya existe (id={existente[0]['id']})")
        return existente[0]["id"]
    nuevo = ejec(models, uid, "hr.employee", "create",
                 {"name": "IA Sync", "user_id": uid_ia})
    print(f"[OK] Empleado IA Sync creado, id={nuevo}")
    return nuevo


def crear_proyecto_y_etapas(models, uid):
    proyectos = ejec(models, uid, "project.project", "search_read",
                     [["name", "=", "QA-SKILL"]], fields=["id", "name"])
    if proyectos:
        pid = proyectos[0]["id"]
        print(f"[SKIP] Proyecto QA-SKILL ya existe (id={pid})")
    else:
        pid = ejec(models, uid, "project.project", "create",
                   {"name": "QA-SKILL",
                    "description": "Proyecto de pruebas para la skill odoo-gestor."})
        print(f"[OK] Proyecto QA-SKILL creado, id={pid}")

    existentes = ejec(models, uid, "project.task.type", "search_read",
                      [["project_ids", "in", [pid]]],
                      fields=["id", "name", "sequence"])
    mapa = {e["name"]: e["id"] for e in existentes}
    for nombre, seq, fold in ETAPAS_ESTANDAR:
        if nombre in mapa:
            print(f"[SKIP] Etapa '{nombre}' ya existe")
            continue
        eid = ejec(models, uid, "project.task.type", "create",
                   {"name": nombre, "sequence": seq, "fold": fold,
                    "project_ids": [(6, 0, [pid])]})
        mapa[nombre] = eid
        print(f"[OK] Etapa '{nombre}' creada, id={eid}")
    return pid, mapa


def crear_tareas(models, uid, pid, etapas):
    for nombre, etapa, desc in TAREAS_PRUEBA:
        existentes = ejec(models, uid, "project.task", "search_read",
                          [["name", "=", nombre], ["project_id", "=", pid]],
                          fields=["id"])
        if existentes:
            print(f"[SKIP] Tarea '{nombre}' ya existe")
            continue
        tid = ejec(models, uid, "project.task", "create",
                   {"name": nombre, "project_id": pid, "description": desc,
                    "stage_id": etapas.get(etapa)})
        print(f"[OK] Tarea '{nombre}' creada, id={tid}")


def generar_apikey():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def json_call(path, params, timeout=30):
        data = json.dumps({"jsonrpc": "2.0", "method": "call",
                           "params": params}).encode()
        req = urllib.request.Request(f"{URL}{path}", data=data,
                                     headers={"Content-Type": "application/json"})
        with opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    r = json_call("/web/session/authenticate", {"db": DB, "login": IA_LOGIN,
                                                "password": IA_PASSWORD})
    if not r.get("result", {}).get("uid"):
        print("ERROR: no se pudo autenticar la sesion web de IA Sync", file=sys.stderr)
        sys.exit(1)
    print("[OK] Sesion web de IA Sync iniciada")

    r = json_call("/web/dataset/call_kw", {
        "model": "res.users.apikeys.description", "method": "create",
        "args": [{"name": "opencode", "duration": "90"}],
        "kwargs": {"context": {"lang": "es_ES"}}})
    wiz_id = r.get("result")
    if not wiz_id:
        print(f"[INFO] Ya existe key 'opencode'? Respuesta: {r}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] Wizard creado, id={wiz_id}")

    r = json_call("/web/dataset/call_kw", {
        "model": "res.users.apikeys.description", "method": "make_key",
        "args": [wiz_id], "kwargs": {}})
    action = r.get("result", {})
    ident = (action.get("res_model") == "res.users.identitycheck")
    if ident:
        res_id = action.get("res_id")
        json_call("/web/dataset/call_kw", {
            "model": "res.users.identitycheck", "method": "write",
            "args": [res_id, {"password": IA_PASSWORD}], "kwargs": {}})
        r = json_call("/web/dataset/call_kw", {
            "model": "res.users.identitycheck", "method": "run_check",
            "args": [res_id], "kwargs": {}})
        action = r.get("result", {})

    key = action.get("context", {}).get("default_key")
    if not key:
        print("ADVERTENCIA: no se pudo leer la key desde la accion", file=sys.stderr)
        pprint(action)
        sys.exit(1)
    print(f"\nAPI_KEY_IA_SYNC: {key}")
    print("Guardala en el gestor de contrasenas. No se volvera a mostrar.")


def main():
    parser = argparse.ArgumentParser(description="Bootstrap del entorno QA-SKILL (Fase 0).")
    parser.add_argument("--api-key", action="store_true",
                        help="Generar la API key 'opencode' para IA Sync")
    parser.add_argument("--solo-db", action="store_true",
                        help="Solo crear la base de datos")
    args = parser.parse_args()

    crear_base_datos()

    if args.solo_db:
        return

    common, models, uid = conectar()
    print(f"[OK] Admin autenticado, uid={uid}")

    modulos = inspeccionar_entorno(models, uid)
    uid_ia = crear_usuario_ia(models, uid)
    if "hr_timesheet" in modulos:
        crear_empleado(models, uid, uid_ia)
    else:
        print("[INFO] hr_timesheet no instalado: sin empleado (modo solo-registro)")

    pid, etapas = crear_proyecto_y_etapas(models, uid)
    crear_tareas(models, uid, pid, etapas)

    uid_check = common.authenticate(DB, IA_LOGIN, IA_PASSWORD, {})
    print(f"[OK] Autenticacion de IA Sync verificada, uid={uid_check}")

    if args.api_key:
        generar_apikey()

    print(f"\n[OK] Entorno QA listo: {URL} · DB {DB} · proyecto QA-SKILL id {pid}")

if __name__ == "__main__":
    main()