"""El veredicto del revisor de CI decide si un PR se puede mergear: se lee sin ambigüedad."""

import importlib.util
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[1] / "scripts" / "revisor_ci.py"
especificacion = importlib.util.spec_from_file_location("revisor_ci", RUTA)
assert especificacion and especificacion.loader
revisor_ci = importlib.util.module_from_spec(especificacion)
especificacion.loader.exec_module(revisor_ci)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Sin hallazgos.\nVEREDICTO: accept", "accept"),
        ("**VEREDICTO: accept**  \r\n", "accept"),
        ("VEREDICTO: **Revise**", "revise"),
        ("VEREDICTO: accept\n...\nVEREDICTO: block", "block"),  # manda el último
        ("VEREDICTO: accept\nAunque falta revisar X.", None),  # no es la última línea
        ("VEREDICTO: accept | revise | block", None),  # repetir la plantilla no aprueba
        ("Todo bien, acepto el cambio.", None),
    ],
)
def test_veredicto(texto: str, esperado: str | None) -> None:
    assert revisor_ci.veredicto(texto) == esperado


def test_features_solo_carpetas_de_feature() -> None:
    tocados = [
        "specs/features/02-login/requirements.md",
        "specs/features/02-login/plan.md",
        "specs/features/_plantilla/brief.md",
        "specs/features/README.md",  # archivo suelto: no es una feature
        "src/app.py",
    ]
    assert revisor_ci.features(tocados) == ["specs/features/02-login"]
