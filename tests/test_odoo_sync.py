# tests/test_odoo_sync.py — Nivel 1: sin conexión a Odoo
"""Batería unitaria acumulada de odoo_sync.py.

Fase 2: utilidades locales (constantes, ok/error/dry_run, raiz_repo,
cargar_credenciales, texto_o_archivo, registrar_actividad).
Fase 3+: now, doctor y calibración se añaden en sus fases.
"""
import importlib.util
import json
import os
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
                          capture_output=True, text=True, encoding="utf-8", cwd=cwd)


def correr_codigo(codigo, cwd):
    """Ejecuta un snippet de python que importa odoo_sync y lo usa."""
    snippet = (f"import sys, json; sys.path.insert(0, {str(SCRIPT.parent)!r}); "
               f"import odoo_sync; {codigo}")
    return subprocess.run([sys.executable, "-c", snippet],
                          capture_output=True, text=True, encoding="utf-8", cwd=cwd)


def cargar_modulo():
    spec = importlib.util.spec_from_file_location("odoo_sync", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def repo_temporal():
    """Crea un repo temporal con .ia/."""
    tmp = tempfile.TemporaryDirectory()
    repo = Path(tmp.name)
    (repo / ".ia").mkdir()
    return tmp, repo


class TestConstantes(unittest.TestCase):
    """F2-T1: constantes del módulo."""

    def test_constantes_obligatorias(self):
        mod = cargar_modulo()
        self.assertEqual(sorted(mod.CREDENCIALES),
                         ["ODOO_API_KEY", "ODOO_DB", "ODOO_URL", "ODOO_USER"])
        self.assertIn("en-progreso", mod.ESTADOS)
        self.assertIn("hecho", mod.ESTADOS)
        self.assertIn("name", mod.EDITABLES)
        self.assertNotIn("project_id", mod.EDITABLES)
        self.assertIn("search_read", mod.LECTURA_CRUDA)
        self.assertNotIn("create", mod.LECTURA_CRUDA)
        self.assertIn("FEAT", mod.TIPOS_VALIDOS)


class TestSalida(unittest.TestCase):
    """F2-T2: ok(), error(), dry_run() — exit codes 0/1/2 y JSON."""

    def test_ok_exit0_y_json(self):
        r = correr_codigo("odoo_sync.ok({'clave': 'valor'})", tempfile.gettempdir())
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["clave"], "valor")

    def test_error_exit1_y_json(self):
        r = correr_codigo("odoo_sync.error('mensaje claro', 'detalle')",
                          tempfile.gettempdir())
        self.assertEqual(r.returncode, 1)
        data = json.loads(r.stdout)
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"], "mensaje claro")
        self.assertEqual(data["detalle"], "detalle")

    def test_dry_run_exit2_y_json(self):
        r = correr_codigo("odoo_sync.dry_run({'accion': 'crear tarea'})",
                          tempfile.gettempdir())
        self.assertEqual(r.returncode, 2)
        data = json.loads(r.stdout)
        self.assertTrue(data["dry_run"])
        self.assertEqual(data["propuesta"]["accion"], "crear tarea")
        self.assertIn("--confirm", data["siguiente_paso"])


class TestRaizRepo(unittest.TestCase):
    """F2-T3: raiz_repo() / carpeta_ia()."""

    def test_sin_ia_error_limpio(self):
        mod = cargar_modulo()
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            try:
                with self.assertRaises(SystemExit) as ctx:
                    mod.raiz_repo()
                self.assertEqual(ctx.exception.code, 1)
            finally:
                os.chdir(cwd)

    def test_detecta_carpeta_ia_en_ancestro(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        subdir = repo / "sub" / "nivel"
        subdir.mkdir(parents=True)
        cwd = os.getcwd()
        try:
            os.chdir(subdir)
            self.assertEqual(mod.raiz_repo(), repo)
            self.assertEqual(mod.carpeta_ia(), repo / ".ia")
        finally:
            os.chdir(cwd)


class TestCredenciales(unittest.TestCase):
    """F2-T4: cargar_credenciales()."""

    VALORES = {"ODOO_URL": "http://qa:8069", "ODOO_DB": "qa_skill",
               "ODOO_USER": "ia.sync", "ODOO_API_KEY": "clave-dummy"}

    def setUp(self):
        self._guardadas = {}
        for k in self.VALORES:
            self._guardadas[k] = os.environ.get(k)
        for k in self.VALORES:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._guardadas.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _env_dummy(self, repo):
        (repo / ".ia" / ".env").write_text(
            "\n".join(f"{k}={v}" for k, v in self.VALORES.items()) + "\n",
            encoding="utf-8")

    def test_parsea_env(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        self._env_dummy(repo)
        cwd = os.getcwd()
        try:
            os.chdir(repo)
            self.assertEqual(mod.cargar_credenciales(), self.VALORES)
        finally:
            os.chdir(cwd)

    def test_faltantes_error_lista_variables(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        (repo / ".ia" / ".env").write_text("# comentario\nODOO_URL=http://qa:8069\n",
                                           encoding="utf-8")
        captured = {}
        original = mod.error
        def fake_error(mensaje, detalle=""):
            captured["mensaje"] = mensaje
            raise SystemExit(1)
        mod.error = fake_error
        cwd = os.getcwd()
        try:
            os.chdir(repo)
            with self.assertRaises(SystemExit):
                mod.cargar_credenciales()
        finally:
            mod.error = original
            os.chdir(cwd)
        for k in self.VALORES:
            self.assertIn(k, captured["mensaje"])

    def test_env_prioridad_sobre_entorno(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        self._env_dummy(repo)
        os.environ["ODOO_USER"] = "otro.usuario"
        cwd = os.getcwd()
        try:
            os.chdir(repo)
            cred = mod.cargar_credenciales()
            self.assertEqual(cred["ODOO_USER"], "otro.usuario")
            self.assertEqual(cred["ODOO_URL"], self.VALORES["ODOO_URL"])
        finally:
            os.chdir(cwd)


class TestTextoOArchivo(unittest.TestCase):
    """F2-T5: texto_o_archivo()."""

    def test_texto_directo(self):
        mod = cargar_modulo()
        self.assertEqual(mod.texto_o_archivo("hola"), "hola")

    def test_archivo_existente_via_arroba_y_strip(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        f = repo / "notas.md"
        f.write_text("  línea con acentos y ñ  ", encoding="utf-8")
        self.assertEqual(mod.texto_o_archivo(f"@{f}"), "línea con acentos y ñ")

    def test_archivo_inexistente_error(self):
        mod = cargar_modulo()
        captured = {}
        original = mod.error
        def fake_error(mensaje, detalle=""):
            captured["mensaje"] = mensaje
            raise SystemExit(1)
        mod.error = fake_error
        try:
            with self.assertRaises(SystemExit):
                mod.texto_o_archivo("@no-existe.md")
        finally:
            mod.error = original
        self.assertIn("no-existe.md", captured["mensaje"])


class TestNow(unittest.TestCase):
    """F3-T2: comando now (caso 1.1)."""

    def test_now_formato_iso_y_campos(self):
        with tempfile.TemporaryDirectory() as d:     # no necesita .ia/
            r = correr(["now"], d)
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)["data"]
        datetime.fromisoformat(data["ahora"])   # falla si no es ISO
        self.assertIn("zona_horaria", data)
        self.assertGreater(data["epoch"], 0)
        # zona_horaria coincide con el reloj local
        self.assertEqual(data["zona_horaria"],
                         datetime.now().astimezone().tzname())


class TestConstruirConfig(unittest.TestCase):
    """F3-T3: estructura de .ia/config.json que genera doctor."""

    def test_claves_obligatorias_y_etapas_mapeadas(self):
        mod = cargar_modulo()
        etapas = [{"id": 27, "name": "Backlog"}, {"id": 31, "name": "Entregado"}]
        cfg = mod.construir_config(7,
                                   {"asignacion": "user_ids", "planned_hours": True,
                                    "state": True, "tickets": []},
                                   etapas, "timesheet")
        self.assertEqual(cfg["proyecto_id"], 7)
        self.assertEqual(cfg["campos"]["asignacion"], "user_ids")
        self.assertEqual(cfg["modo_horas"], "timesheet")
        self.assertEqual(cfg["etapas"], {"Backlog": 27, "Entregado": 31})
        self.assertEqual(cfg["umbral_desviacion_pct"], 25)
        self.assertIn("FEAT", cfg["convencion"]["tipos"])
        self.assertEqual(cfg["convencion"]["formato"], "[TIPO] titulo ejecutivo")

    def test_sin_state_estados_none(self):
        mod = cargar_modulo()
        cfg = mod.construir_config(7,
                                   {"asignacion": "user_id", "planned_hours": False,
                                    "state": False, "tickets": []},
                                   [], "solo-registro")
        self.assertIsNone(cfg["estados"])
        self.assertEqual(cfg["modo_horas"], "solo-registro")


class TestCoincidirEtapa(unittest.TestCase):
    """F4-T3: coincidir_etapa() pura e id_de_etapa()."""

    ETAPAS = [{"id": 27, "name": "Backlog", "sequence": 1},
              {"id": 31, "name": "Revisión", "sequence": 5}]

    def test_exacta(self):
        mod = cargar_modulo()
        self.assertEqual(mod.coincidir_etapa(self.ETAPAS, "Backlog")["id"], 27)

    def test_mayusculas_y_espacios(self):
        mod = cargar_modulo()
        self.assertEqual(mod.coincidir_etapa(self.ETAPAS, "  REVISIÓN " )["id"], 31)

    def test_no_existe_devuelve_none(self):
        mod = cargar_modulo()
        self.assertIsNone(mod.coincidir_etapa(self.ETAPAS, "NoExiste"))

    def test_id_de_etapa_devuelve_ficha(self):
        mod = cargar_modulo()
        class FakeOdoo:
            def buscar(self, modelo, dominio, campos, limite=100, orden=None):
                return TestCoincidirEtapa.ETAPAS
        ficha = mod.id_de_etapa(FakeOdoo(), {"proyecto_id": 7}, "revisión")
        self.assertEqual(ficha["id"], 31)

    def test_id_de_etapa_inexistente_error_con_lista(self):
        mod = cargar_modulo()
        class FakeOdoo:
            def buscar(self, modelo, dominio, campos, limite=100, orden=None):
                return TestCoincidirEtapa.ETAPAS
        captured = {}
        original = mod.error
        def fake_error(mensaje, detalle=""):
            captured["mensaje"] = mensaje
            raise SystemExit(1)
        mod.error = fake_error
        try:
            with self.assertRaises(SystemExit):
                mod.id_de_etapa(FakeOdoo(), {"proyecto_id": 7}, "NoExiste")
        finally:
            mod.error = original
        self.assertIn("NoExiste", captured["mensaje"])
        self.assertIn("Backlog", captured["mensaje"])
        self.assertIn("Revisión", captured["mensaje"])


class TestCamposTarea(unittest.TestCase):
    """F4-T1: campos_tarea()."""

    def test_base_y_condicionales(self):
        mod = cargar_modulo()
        cfg = {"campos": {"asignacion": "user_ids", "planned_hours": False,
                          "state": True, "tickets": []}}
        campos = mod.campos_tarea(cfg)
        for obligatorio in ("id", "name", "stage_id", "description",
                            "date_deadline", "state", "user_ids"):
            self.assertIn(obligatorio, campos)
        self.assertNotIn("planned_hours", campos)
        self.assertNotIn("project_id", campos)

    def test_campos_condicionales_presentes(self):
        mod = cargar_modulo()
        cfg = {"campos": {"asignacion": "user_id", "planned_hours": True,
                          "state": False, "tickets": []}}
        campos = mod.campos_tarea(cfg)
        self.assertIn("planned_hours", campos)
        self.assertIn("user_id", campos)
        self.assertNotIn("state", campos)


class TestValidarConvencion(unittest.TestCase):
    """F5-T1: validar_convencion() pura."""

    def test_valido(self):
        mod = cargar_modulo()
        self.assertTrue(mod.validar_convencion("[FEAT] Crear modulo de facturas"))
        self.assertTrue(mod.validar_convencion("[TST] Prueba N1"))

    def test_invalido(self):
        mod = cargar_modulo()
        self.assertFalse(mod.validar_convencion("sin prefijo"))
        self.assertFalse(mod.validar_convencion("[FEAT]"))
        self.assertFalse(mod.validar_convencion("[feat] minusculas"))


class TestParsearSet(unittest.TestCase):
    """F5-T2: parsear_set() pura."""

    def _capturar_error(self, mod):
        captured = {}
        original = mod.error
        def fake_error(mensaje, detalle=""):
            captured["mensaje"] = mensaje
            raise SystemExit(1)
        mod.error = fake_error
        return captured, original

    def test_valido_simple(self):
        mod = cargar_modulo()
        self.assertEqual(mod.parsear_set(["name=Hola"]), {"name": "Hola"})

    def test_campo_fuera_whitelist_error_con_permitidos(self):
        mod = cargar_modulo()
        captured, original = self._capturar_error(mod)
        try:
            with self.assertRaises(SystemExit):
                mod.parsear_set(["project_id=7"])
        finally:
            mod.error = original
        self.assertIn("project_id", captured["mensaje"])
        self.assertIn("name", captured["mensaje"])

    def test_planned_hours_numerico(self):
        mod = cargar_modulo()
        self.assertEqual(mod.parsear_set(["planned_hours=2.5"]),
                         {"planned_hours": 2.5})

    def test_planned_hours_no_numerico_error(self):
        mod = cargar_modulo()
        captured, original = self._capturar_error(mod)
        try:
            with self.assertRaises(SystemExit):
                mod.parsear_set(["planned_hours=abc"])
        finally:
            mod.error = original
        self.assertIn("numérico", captured["mensaje"])

    def test_formato_sin_igual_error(self):
        mod = cargar_modulo()
        captured, original = self._capturar_error(mod)
        try:
            with self.assertRaises(SystemExit):
                mod.parsear_set(["solo-texto"])
        finally:
            mod.error = original
        self.assertIn("CAMPO=VALOR", captured["mensaje"])


class TestRegistrarActividad(unittest.TestCase):
    """F2-T6: registrar_actividad()."""

    def test_formato_append_y_utf8(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        cwd = os.getcwd()
        try:
            os.chdir(repo)
            mod.registrar_actividad("tarea crear", "#10 «Prueba ñ»")
            mod.registrar_actividad("chatter post", "#10 (25 caracteres)")
            lineas = (repo / ".ia" / "actividad.log").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lineas), 2)
            for linea in lineas:
                partes = linea.split(" | ")
                self.assertEqual(len(partes), 4)
                datetime.fromisoformat(partes[0])   # falla si no es ISO
                self.assertEqual(partes[3], "APLICADO")
            self.assertIn("Prueba ñ", lineas[0])
            self.assertIn("#10 (25 caracteres)", lineas[1])
        finally:
            os.chdir(cwd)


class TestArchivoCalibracion(unittest.TestCase):
    """F7-T1: archivo_calibracion() sanea el modelo y crea la carpeta."""

    def _error_capturado(self, mod):
        capturado = {}
        original = mod.error

        def fake_error(mensaje, detalle=""):
            capturado["mensaje"] = mensaje
            raise SystemExit(1)
        mod.error = fake_error
        return capturado, original

    def test_nombre_saneado_y_carpeta(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        cwd = os.getcwd()
        try:
            os.chdir(repo)
            ruta = mod.archivo_calibracion("Claude Sonnet 4.5!")
            self.assertEqual(ruta.name, "claude-sonnet-4.5.md")
            self.assertTrue(ruta.parent.is_dir())
            self.assertTrue((repo / ".ia" / "calibracion").is_dir())
        finally:
            os.chdir(cwd)

    def test_modelo_vacio_error(self):
        mod = cargar_modulo()
        capturado, original = self._error_capturado(mod)
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        cwd = os.getcwd()
        try:
            os.chdir(repo)
            with self.assertRaises(SystemExit):
                mod.archivo_calibracion("   ")
        finally:
            mod.error = original
            os.chdir(cwd)
        self.assertIn("modelo", capturado["mensaje"])


class TestPatronEntrada(unittest.TestCase):
    """F7-T2: robustez de PATRON_ENTRADA."""

    def test_entrada_completa(self):
        mod = cargar_modulo()
        linea = ("## 2025-01-15T17:20 | FIX | T-123 | estimado_h:4.5 | real_h:5.2 "
                 "| invertido_h:4.5 | archivos:4 | lineas:180 | interrupciones:si")
        m = mod.PATRON_ENTRADA.match(linea)
        self.assertIsNotNone(m)
        self.assertEqual(m.group("tipo"), "FIX")
        self.assertEqual(float(m.group("est")), 4.5)
        self.assertEqual(float(m.group("inv")), 4.5)
        self.assertEqual(int(m.group("arch")), 4)
        self.assertEqual(m.group("int"), "si")

    def test_entrada_minima(self):
        mod = cargar_modulo()
        linea = "## 2025-01-15T17:20 | FIX | T-123 | estimado_h:2 | real_h:3"
        m = mod.PATRON_ENTRADA.match(linea)
        self.assertIsNotNone(m)
        self.assertEqual(float(m.group("real")), 3)
        self.assertIsNone(m.group("inv"))

    def test_no_parsea_separadores_mal(self):
        mod = cargar_modulo()
        self.assertIsNone(mod.PATRON_ENTRADA.match(
            "## 2025-01-15 | FIX | T-1 estimado_h:2 | real_h:3"))

    def test_no_parsea_sin_estimado(self):
        mod = cargar_modulo()
        self.assertIsNone(mod.PATRON_ENTRADA.match(
            "## 2025-01-15 | FIX | T-1 | real_h:3"))

    def test_no_parsea_prefijo_distinto(self):
        mod = cargar_modulo()
        self.assertIsNone(mod.PATRON_ENTRADA.match(
            "#! 2025-01-15 | FIX | T-1 | estimado_h:2 | real_h:3"))


class TestCalRegistrar(unittest.TestCase):
    """F7-T3: calibracion registrar (test ANTES)."""

    def test_crea_cabecera_y_append(self):
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        r = correr(["calibracion", "registrar", "--modelo", "test-modelo",
                    "--tipo", "FIX", "--ref", "T-1",
                    "--estimado", "2", "--real", "3"], repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = correr(["calibracion", "registrar", "--modelo", "test-modelo",
                    "--tipo", "FIX", "--ref", "T-2",
                    "--estimado", "1", "--real", "1"], repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        ruta = repo / ".ia" / "calibracion" / "test-modelo.md"
        self.assertTrue(ruta.exists())
        lineas = ruta.read_text(encoding="utf-8").splitlines()
        self.assertTrue(lineas[0].startswith("# "))   # cabecera
        self.assertEqual(len([l for l in lineas if l.startswith("## ")]), 2)

    def test_formato_exacto_y_interrupciones_default(self):
        mod = cargar_modulo()
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        correr(["calibracion", "registrar", "--modelo", "test-modelo",
                "--tipo", "FIX", "--ref", "T-1",
                "--estimado", "2", "--real", "3"], repo)
        ruta = repo / ".ia" / "calibracion" / "test-modelo.md"
        linea = [l for l in ruta.read_text(encoding="utf-8").splitlines()
                 if l.startswith("## ")][0]
        m = mod.PATRON_ENTRADA.match(linea)
        self.assertIsNotNone(m, linea)
        self.assertEqual(m.group("tipo"), "FIX")
        self.assertEqual(m.group("ref"), "T-1")
        self.assertEqual(m.group("int"), "no")

    def test_interrupciones_si_y_campos_opcionales(self):
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        correr(["calibracion", "registrar", "--modelo", "test-modelo",
                "--tipo", "FEAT", "--ref", "T-3", "--estimado", "4",
                "--real", "5", "--invertido", "3.5", "--archivos", "3",
                "--lineas", "150", "--interrupciones"], repo)
        ruta = repo / ".ia" / "calibracion" / "test-modelo.md"
        linea = [l for l in ruta.read_text(encoding="utf-8").splitlines()
                 if l.startswith("## ")][0]
        self.assertIn("invertido_h:3.5", linea)
        self.assertIn("archivos:3", linea)
        self.assertIn("lineas:150", linea)
        self.assertIn("interrupciones:si", linea)

    def test_notas_desde_archivo(self):
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        notas = repo / "notas.md"
        notas.write_text("Entrevista: hubo 2 interrupciones y retoma al siguiente día.",
                         encoding="utf-8")
        correr(["calibracion", "registrar", "--modelo", "test-modelo",
                "--tipo", "FIX", "--ref", "T-4", "--estimado", "2",
                "--real", "4", "--notas", f"@{notas}"], repo)
        ruta = repo / ".ia" / "calibracion" / "test-modelo.md"
        contenido = ruta.read_text(encoding="utf-8")
        self.assertIn("Entrevista: hubo 2 interrupciones", contenido)


class TestCalStats(unittest.TestCase):
    """F7-T4: calibracion stats (test ANTES, el más importante)."""

    def test_sin_historico(self):
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        r = correr(["calibracion", "stats", "--modelo", "test-modelo"], repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)["data"]
        self.assertEqual(data["tareas"], 0)
        self.assertIsNone(data["ratio_global"])
        self.assertIn("Sin histórico", data["aviso"])

    def test_una_entrada_ratio_1_5(self):
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        correr(["calibracion", "registrar", "--modelo", "test-modelo",
                "--tipo", "FIX", "--ref", "T-1",
                "--estimado", "2", "--real", "3"], repo)
        r = correr(["calibracion", "stats", "--modelo", "test-modelo"], repo)
        data = json.loads(r.stdout)["data"]
        self.assertEqual(data["tareas"], 1)
        self.assertEqual(data["ratio_global"], 1.5)   # 3/2

    def test_invertido_tiene_prioridad(self):
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        correr(["calibracion", "registrar", "--modelo", "test-modelo",
                "--tipo", "FIX", "--ref", "T-1", "--estimado", "2",
                "--real", "10", "--invertido", "3"], repo)
        r = correr(["calibracion", "stats", "--modelo", "test-modelo"], repo)
        data = json.loads(r.stdout)["data"]
        self.assertEqual(data["ratio_global"], 1.5)   # 3/2, no 10/2

    def test_por_tipo_con_dos_tipos(self):
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        for tipo, est, real in (("FIX", 2, 3), ("FEAT", 4, 8)):
            correr(["calibracion", "registrar", "--modelo", "test-modelo",
                    "--tipo", tipo, "--ref", "T-x",
                    "--estimado", str(est), "--real", str(real)], repo)
        r = correr(["calibracion", "stats", "--modelo", "test-modelo"], repo)
        data = json.loads(r.stdout)["data"]
        self.assertEqual(data["por_tipo"]["FIX"]["ratio"], 1.5)
        self.assertEqual(data["por_tipo"]["FEAT"]["ratio"], 2.0)
        self.assertEqual(data["por_tipo"]["FEAT"]["tareas"], 1)  # para ">=3" (§6.4)
        self.assertEqual(data["ratio_global"], 1.75)   # (1.5+2.0)/2

    def test_aviso_historico_corto(self):
        tmp, repo = repo_temporal()
        self.addCleanup(tmp.cleanup)
        correr(["calibracion", "registrar", "--modelo", "test-modelo",
                "--tipo", "TST", "--ref", "T-1",
                "--estimado", "1", "--real", "1"], repo)
        r = correr(["calibracion", "stats", "--modelo", "test-modelo"], repo)
        data = json.loads(r.stdout)["data"]
        self.assertIn("Histórico corto", data["aviso"])


if __name__ == "__main__":
    unittest.main()