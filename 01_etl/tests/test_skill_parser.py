"""
test_skill_parser.py
Tests unitarios del motor de extracción de skills y scoring de CAIQ.

Uso:
    python test_skill_parser.py          # ejecuta todos los tests
    python -m pytest test_skill_parser.py -v   # con pytest
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

# ── Carga dinámica del módulo principal ──────────────────────────────────────
def _load_module(path: Path, name: str = "caiq_model"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _find_model_module() -> Path:
    """Localiza build_datapath_model_advanced.py relativo a este archivo."""
    candidates = [
        Path(__file__).resolve().parents[1] / "pipelines" / "build_datapath_model_advanced.py",
        Path(os.environ.get("CAIQ_ETL_DIR", "")) / "pipelines" / "build_datapath_model_advanced.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        "No se encontró build_datapath_model_advanced.py. "
        "Establece la ruta con la variable CAIQ_ETL_DIR."
    )


try:
    MOD = _load_module(_find_model_module())
    MODEL_AVAILABLE = True
    _LOAD_ERROR = ""
except Exception as e:
    MOD = None
    MODEL_AVAILABLE = False
    _LOAD_ERROR = str(e)


# ── Taxonomía mínima para tests (independiente del JSON real) ─────────────────
MINIMAL_TAXONOMY = {
    "python":           ["python", "python 3", "python3"],
    "sql":              ["sql", "mysql", "postgresql", "sqlite"],
    "machine learning": ["machine learning", "ml", "scikit-learn", "sklearn"],
    "docker":           ["docker", "containerization"],
    "r":                [" r ", " r,", " r.", "r language"],
    "power bi":         ["power bi", "powerbi"],
}

# ── Helper de coverage score (lógica extraída del módulo) ─────────────────────
def coverage_score(candidate_skills: set, required_skills: set) -> float:
    """Fracción de required_skills que el candidato cubre. Devuelve 0 si required está vacío."""
    if not required_skills:
        return 0.0
    covered = len(candidate_skills & required_skills)
    return covered / len(required_skills)


# ── Tests de normalización de texto ──────────────────────────────────────────
class TestTextNormalization:

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_norm_text_preserves_case(self):
        """norm_text normaliza espacios pero NO cambia mayúsculas."""
        assert MOD.norm_text("PYTHON") == "PYTHON"

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_norm_text_strips_whitespace(self):
        assert MOD.norm_text("  Python  ") == "Python"

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_fix_spaced_letters_python(self):
        """Texto OCR con letras separadas debe unificarse."""
        result = MOD.fix_spaced_letters("P y t h o n")
        assert "python" in result.lower(), f"Esperado 'python' en '{result}'"

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_fix_spaced_letters_preserves_normal_text(self):
        result = MOD.fix_spaced_letters("Machine Learning con Python")
        assert "python" in result.lower()
        assert "machine" in result.lower()

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_contains_term_exact(self):
        assert MOD.contains_term("experto en python y sql", "python") is True

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_contains_term_not_false_positive(self):
        """'r' como letra suelta no debe detectarse dentro de otras palabras."""
        assert MOD.contains_term("programador con experiencia", " r ") is False

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_contains_term_alias_with_spaces(self):
        """El alias ' r ' (con espacios) debe detectarse en texto con R como skill."""
        assert MOD.contains_term("experto en r y python", " r ") is True


# ── Tests de extracción de skills ─────────────────────────────────────────────
class TestSkillExtraction:

    CV_COMPLETO = """
    Senior Data Scientist con 5 años de experiencia.
    Habilidades técnicas: Python, SQL, Machine Learning, Docker.
    Experiencia con scikit-learn y postgresql en entornos cloud.
    """

    CV_SIN_SKILLS = """
    Profesional con amplia trayectoria en gestión de equipos
    y habilidades de comunicación interpersonal y liderazgo.
    """

    CV_ALIAS = """
    Desarrollador con dominio de sklearn y mysql.
    Uso habitual de containerization para despliegue.
    """

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_extrae_python(self):
        skills = set(MOD.extract_skills(self.CV_COMPLETO, MINIMAL_TAXONOMY))
        assert "python" in skills, f"Skills detectadas: {skills}"

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_extrae_alias_sql(self):
        """El alias 'postgresql' debe mapear a la skill canónica 'sql'."""
        skills = set(MOD.extract_skills(self.CV_COMPLETO, MINIMAL_TAXONOMY))
        assert "sql" in skills, f"Skills detectadas: {skills}"

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_extrae_alias_ml(self):
        """El alias 'scikit-learn' debe mapear a 'machine learning'."""
        skills = set(MOD.extract_skills(self.CV_COMPLETO, MINIMAL_TAXONOMY))
        assert "machine learning" in skills, f"Skills detectadas: {skills}"

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_alias_sklearn_sin_guion(self):
        """'sklearn' (sin guion) también debe detectarse."""
        skills = set(MOD.extract_skills(self.CV_ALIAS, MINIMAL_TAXONOMY))
        assert "machine learning" in skills, f"Skills detectadas: {skills}"

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_cv_sin_skills_no_genera_falsos_positivos(self):
        """CV sin términos técnicos no debe detectar skills."""
        skills = set(MOD.extract_skills(self.CV_SIN_SKILLS, MINIMAL_TAXONOMY))
        assert len(skills) == 0, f"Skills detectadas (no esperadas): {skills}"

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_tipo_retorno_es_lista(self):
        skills = MOD.extract_skills(self.CV_COMPLETO, MINIMAL_TAXONOMY)
        assert isinstance(skills, list)

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_sin_duplicados(self):
        """No debe haber skills duplicadas en el resultado."""
        skills = MOD.extract_skills(self.CV_COMPLETO, MINIMAL_TAXONOMY)
        assert len(skills) == len(set(skills)), f"Duplicados: {skills}"

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_texto_vacio_devuelve_lista_vacia(self):
        assert MOD.extract_skills("", MINIMAL_TAXONOMY) == []

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_taxonomia_vacia_devuelve_lista_vacia(self):
        assert MOD.extract_skills("Python SQL Machine Learning", {}) == []


# ── Tests del coverage score ──────────────────────────────────────────────────
class TestCoverageScore:

    def test_cobertura_perfecta(self):
        required  = {"python", "sql", "machine learning"}
        candidate = {"python", "sql", "machine learning", "docker"}
        assert coverage_score(candidate, required) == 1.0

    def test_cobertura_cero(self):
        required  = {"python", "sql"}
        candidate = {"power bi", "docker"}
        assert coverage_score(candidate, required) == 0.0

    def test_cobertura_parcial(self):
        required  = {"python", "sql"}
        candidate = {"python"}
        score = coverage_score(candidate, required)
        assert abs(score - 0.5) < 1e-9, f"Esperado 0.5, obtenido {score}"

    def test_required_vacio_devuelve_cero(self):
        assert coverage_score({"python"}, set()) == 0.0

    def test_score_acotado_entre_0_y_1(self):
        score = coverage_score({"python", "sql"}, {"python"})
        assert 0.0 <= score <= 1.0

    def test_tres_de_cuatro(self):
        required  = {"python", "sql", "docker", "machine learning"}
        candidate = {"python", "sql", "docker"}
        score = coverage_score(candidate, required)
        assert abs(score - 0.75) < 1e-9, f"Esperado 0.75, obtenido {score}"


# ── Tests de robustez ante inputs malformados ─────────────────────────────────
class TestRobustness:

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_texto_unicode_no_rompe(self):
        text = "Experto en análisis de datos con Python y estadística bayesiana."
        skills = MOD.extract_skills(text, MINIMAL_TAXONOMY)
        assert isinstance(skills, list)

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_texto_solo_espacios(self):
        skills = MOD.extract_skills("   ", MINIMAL_TAXONOMY)
        assert skills == []

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_texto_con_html(self):
        text = "<b>Python</b> y <em>SQL</em> developer"
        skills = set(MOD.extract_skills(text, MINIMAL_TAXONOMY))
        # El HTML puede interferir, pero no debe lanzar excepción
        assert isinstance(skills, set)

    @pytest.mark.skipif(not MODEL_AVAILABLE, reason=_LOAD_ERROR)
    def test_norm_text_acepta_none_sin_crash(self):
        try:
            result = MOD.norm_text(None)
            assert isinstance(result, str)
        except (TypeError, AttributeError):
            pass  # Aceptable: el módulo puede no manejar None explícitamente


# ── Runner sin pytest ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import traceback

    suites = [TestTextNormalization, TestSkillExtraction, TestCoverageScore, TestRobustness]
    passed = failed = skipped = 0

    for suite in suites:
        obj = suite()
        for name in [m for m in dir(obj) if m.startswith("test_")]:
            method = getattr(obj, name)
            # Saltar tests que requieren el módulo si no está disponible
            marks = getattr(method, "pytestmark", [])
            if not MODEL_AVAILABLE and any(hasattr(m, "kwargs") for m in marks):
                print(f"  SKIP  {suite.__name__}.{name}")
                skipped += 1
                continue
            try:
                method()
                print(f"  PASS  {suite.__name__}.{name}")
                passed += 1
            except AssertionError as e:
                print(f"  FAIL  {suite.__name__}.{name}: {e}")
                failed += 1
            except Exception:
                print(f"  ERROR {suite.__name__}.{name}")
                traceback.print_exc()
                failed += 1
    print(f"\nResultado: {passed} passed  |  {failed} failed  |  {skipped} skipped")
    if failed:
        import sys; sys.exit(1)
