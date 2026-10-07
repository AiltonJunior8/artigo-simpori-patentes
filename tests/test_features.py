import pandas as pd
import pytest

from patentes.features import (
    calcular_concentracao,
    calcular_participacao,
    calcular_vtr,
    converter_valor,
    ler_csv_ompi,
    montar_total_mundial,
)

CSV_ORIGEM = """Intellectual property right :Patent

Indicator :1 - Total patent applications (direct and PCT national phase entries)

Source: WIPO statistics database. Last updated: May 2026

Origin,Origin (Code),Office,Type,2023,2024
"China","CN","Total","Total","1642643","1796738",
"China","CN","Total","Resident","1522292","",
"""

CSV_PCT = """Intellectual property right :PCT

Source: WIPO statistics database. Last updated: October 2026

"Receiving Office (RO)","Receiving Office (RO)(Code)","Origin","Origin(Code)",2023,2024,
"Total","ZZ","China","CN","69,584","69,932",
"Total","ZZ","Total","ZZ","272,481","273,946",
"""


def test_ler_csv_ompi_formato_longo(tmp_path):
    caminho = tmp_path / "origem.csv"
    caminho.write_text(CSV_ORIGEM, encoding="utf-8")

    df = ler_csv_ompi(caminho)

    assert list(df.columns) == ["nome", "codigo", "tipo", "ano", "valor"]
    assert len(df) == 3  # a célula vazia de 2024 (Resident) é descartada
    total_2024 = df.query("tipo == 'Total' and ano == 2024")["valor"].item()
    assert total_2024 == 1796738


def test_ler_csv_ompi_pct_com_milhar(tmp_path):
    caminho = tmp_path / "pct.csv"
    caminho.write_text(CSV_PCT, encoding="utf-8")

    df = ler_csv_ompi(caminho, aceita_milhar=True)

    assert set(df.columns) == {"nome", "codigo", "ano", "valor"}
    assert df.query("codigo == 'ZZ' and ano == 2024")["valor"].item() == 273946


def test_converter_valor_rejeita_celula_concatenada():
    # Sem filtro de tipo, a API junta os componentes em ordem lexicográfica.
    with pytest.raises(ValueError):
        converter_valor("124737,126837,1672001,1796738,1798838", aceita_milhar=False)
    assert converter_valor("", aceita_milhar=False) is None
    assert converter_valor("1,730", aceita_milhar=True) == 1730


def _serie(valores: dict[str, float], ano: int = 2024) -> pd.DataFrame:
    return pd.DataFrame(
        {"codigo": list(valores), "nome": list(valores), "ano": ano, "valor": list(valores.values())}
    )


def test_participacao_inclui_leste_asiatico():
    df = _serie({"WD": 200, "CN": 80, "JP": 20, "KR": 10, "US": 40})

    resultado = calcular_participacao(df, "WD").set_index("codigo")["participacao"]

    assert resultado["CN"] == pytest.approx(40)
    assert resultado["XEA"] == pytest.approx(55)
    assert "WD" not in resultado.index


def test_concentracao_ignora_agregados_e_leste_asiatico():
    df = _serie({"WD": 100, "CN": 50, "US": 30, "JP": 20, "R2": 70})
    participacao = calcular_participacao(df, "WD")

    linha = calcular_concentracao(participacao, "teste").iloc[0]

    assert linha["cr5"] == pytest.approx(100)
    assert linha["hhi"] == pytest.approx(50**2 + 30**2 + 20**2)
    assert linha["lider"] == "CN"


def test_vtr_igual_a_um_quando_perfis_sao_identicos():
    linhas = []
    for codigo, escala in [("CN", 1), ("US", 3)]:
        for campo, peso in [(6, 10), (16, 30)]:
            linhas.append(
                {"codigo": codigo, "nome": codigo, "campo": campo, "nome_campo": str(campo),
                 "ano": 2020, "valor": escala * peso}
            )
    df = pd.DataFrame(linhas)

    vtr = calcular_vtr(df, decadas=[(2014, 2023)])

    assert vtr["vtr"].tolist() == pytest.approx([1.0] * 4)


def test_total_mundial_completa_anos_sem_wd():
    df = pd.concat([_serie({"CN": 10, "US": 20}, 1984), _serie({"WD": 35, "CN": 15, "US": 20}, 1985)])

    total = montar_total_mundial(df).set_index("ano")

    assert total.loc[1984, "valor"] == 30
    assert total.loc[1984, "fonte"] == "soma dos escritórios"
    assert total.loc[1985, "valor"] == 35
