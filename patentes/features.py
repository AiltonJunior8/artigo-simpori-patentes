"""Transformação e indicadores: data/raw -> data/interim -> data/processed.

interim/   uma série por arquivo, em formato longo (codigo, nome, [tipo|campo], ano, valor)
processed/ indicadores da seção 7.3 do CLAUDE.md:
    total_mundial.csv            total mundial de pedidos por ano e de onde ele vem
    participacao_escritorio.csv  participação no total mundial (WD) por escritório e região
    participacao_origem.csv      participação no total mundial (WD) por país de origem
    participacao_pct.csv         participação no total do PCT (ZZ) por país de origem
    concentracao.csv             CR5 e HHI por série e ano
    vtr_decada.csv               vantagem tecnológica revelada por país, campo e década

Uso:
    python -m patentes.features
"""

import re

from loguru import logger
import pandas as pd
import typer

from patentes.config import (
    ANO_FINAL,
    CAMPO_DESCONHECIDO,
    CODIGO_LESTE_ASIATICO,
    CODIGO_MUNDO_ESCRITORIO,
    CODIGO_TOTAL_PCT,
    CODIGOS_AGREGADOS,
    DECADAS_VTR,
    INTERIM_DATA_DIR,
    LESTE_ASIATICO,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
)

app = typer.Typer()

PADRAO_ANO = re.compile(r"^\d{4}$")
PADRAO_MILHAR = re.compile(r"^\d{1,3}(,\d{3})+$")

COLUNAS_OMPI = {
    "Office (Code)": "codigo",
    "Office": "nome",
    "Origin (Code)": "codigo",
    "Origin(Code)": "codigo",
    "Origin": "nome",
    "Type": "tipo",
    "Field of technology": "campo",
}


# ---------------------------------------------------------------------------
# Leitura dos CSVs da OMPI
# ---------------------------------------------------------------------------
def localizar_cabecalho(linhas: list[str]) -> int:
    """Índice da linha de cabeçalho: a primeira que tem colunas de ano."""
    for indice, linha in enumerate(linhas):
        campos = [campo.strip('"') for campo in linha.split(",")]
        if sum(bool(PADRAO_ANO.match(campo)) for campo in campos) >= 2:
            return indice
    raise ValueError("Cabeçalho com colunas de ano não encontrado no CSV da OMPI")


def converter_valor(texto: str, aceita_milhar: bool) -> float | None:
    """Converte uma célula da OMPI em número; vazio vira ausente.

    A série PCT usa vírgula de milhar ("1,730"). Nas demais, vírgula numa célula indica que a
    API concatenou componentes (faltou filtrar o tipo) e o valor não é interpretável.
    """
    texto = texto.strip()
    if texto == "":
        return None
    if "," in texto:
        if aceita_milhar and PADRAO_MILHAR.match(texto):
            return float(texto.replace(",", ""))
        raise ValueError(f"Célula com valores concatenados: {texto!r}. Filtre o tipo na API.")
    return float(texto)


def ler_csv_ompi(caminho, aceita_milhar: bool = False) -> pd.DataFrame:
    """Lê um CSV bruto da OMPI e devolve o formato longo (uma linha por unidade e ano)."""
    linhas = caminho.read_text(encoding="utf-8-sig").splitlines()
    inicio = localizar_cabecalho(linhas)

    df_larga = pd.read_csv(
        caminho,
        skiprows=inicio,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
        index_col=False,  # cada linha termina em vírgula; sem isso a 1ª coluna vira índice
    )
    df_larga = df_larga.loc[:, ~df_larga.columns.str.startswith("Unnamed")]

    # Na série PCT, a primeira dupla de colunas é o escritório receptor (sempre ZZ).
    df_larga = df_larga.drop(
        columns=[c for c in df_larga.columns if c.startswith("Receiving Office")]
    )
    colunas_ano = [c for c in df_larga.columns if PADRAO_ANO.match(c)]
    # Descarta a dimensão fixada em "Total" (Origin na série por escritório, Office na série por
    # origem), que só repete o filtro da consulta.
    colunas_constantes = [
        c for c in df_larga.columns if c not in colunas_ano and set(df_larga[c]) == {"Total"}
    ]
    df_larga = df_larga.drop(columns=colunas_constantes)
    colunas_id = [c for c in df_larga.columns if c not in colunas_ano]

    df_longa = df_larga.melt(id_vars=colunas_id, var_name="ano", value_name="texto")
    df_longa["valor"] = [converter_valor(t, aceita_milhar) for t in df_longa["texto"]]
    df_longa["ano"] = df_longa["ano"].astype(int)

    return (
        df_longa.drop(columns="texto")
        .rename(columns=COLUNAS_OMPI)
        .dropna(subset=["valor"])
        .reset_index(drop=True)
    )


def limpar_series() -> dict[str, pd.DataFrame]:
    """Lê os quatro CSVs brutos e grava as versões longas em data/interim/."""
    INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    series = {}

    df = ler_csv_ompi(RAW_DATA_DIR / "depositos_escritorio.csv")
    df["tipo"] = df["tipo"].map(
        {"Total": "Total", "Resident": "Residente", "Non-resident": "Não residente"}
    )
    series["depositos_escritorio"] = df

    df = ler_csv_ompi(RAW_DATA_DIR / "depositos_origem.csv")
    df["tipo"] = df["tipo"].map(
        {
            "Total": "Total",
            "Resident": "Residente",
            "Abroad": "Exterior",
            "Total (equivalent count)": "Total (contagem equivalente)",
            "Abroad (equivalent count)": "Exterior (contagem equivalente)",
        }
    )
    series["depositos_origem"] = df

    df = ler_csv_ompi(RAW_DATA_DIR / "publicacoes_campo_origem.csv")
    df["nome_campo"] = df["campo"].str.replace(r"^\s*\d+\s*-\s*", "", regex=True)
    df["campo"] = df["campo"].str.extract(r"^\s*(\d+)")[0].fillna(CAMPO_DESCONHECIDO).astype(int)
    series["publicacoes_campo_origem"] = df

    df = ler_csv_ompi(RAW_DATA_DIR / "pct_origem.csv", aceita_milhar=True)
    series["pct_origem"] = df

    for nome, df in series.items():
        if df.get("tipo") is not None and df["tipo"].isna().any():
            raise ValueError(f"{nome}: tipo da OMPI sem tradução no mapeamento")
        df.to_csv(INTERIM_DATA_DIR / f"{nome}.csv", index=False)
        logger.info(f"interim/{nome}.csv: {len(df):,} linhas")
    return series


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------
def eh_unidade(codigo: pd.Series) -> pd.Series:
    """True para países e escritórios; False para totais, regiões e origem desconhecida."""
    return ~codigo.isin(CODIGOS_AGREGADOS)


def montar_total_mundial(escritorio_total: pd.DataFrame) -> pd.DataFrame:
    """Total mundial de pedidos por ano: o WD da OMPI e, nos anos sem WD, a soma dos escritórios."""
    soma_escritorios = (
        escritorio_total.loc[eh_unidade(escritorio_total["codigo"])]
        .groupby("ano", as_index=False)["valor"]
        .sum()
        .assign(fonte="soma dos escritórios")
    )
    wd = escritorio_total.loc[
        escritorio_total["codigo"] == CODIGO_MUNDO_ESCRITORIO, ["ano", "valor"]
    ].assign(fonte="WD (OMPI)")
    return (
        pd.concat([wd, soma_escritorios.loc[~soma_escritorios["ano"].isin(wd["ano"])]])
        .assign(codigo=CODIGO_MUNDO_ESCRITORIO, nome="World")
        .sort_values("ano")
        .reset_index(drop=True)
    )


def calcular_participacao(df: pd.DataFrame, codigo_total: str) -> pd.DataFrame:
    """Participação (%) de cada linha no total do ano dado pelo código agregado.

    Acrescenta o Leste Asiático (CN + JP + KR) como linha própria (CODIGO_LESTE_ASIATICO).
    """
    totais = df.loc[df["codigo"] == codigo_total, ["ano", "valor"]].rename(
        columns={"valor": "total_mundial"}
    )
    leste_asiatico = (
        df.loc[df["codigo"].isin(LESTE_ASIATICO)]
        .groupby("ano", as_index=False)["valor"]
        .sum()
        .assign(codigo=CODIGO_LESTE_ASIATICO, nome="Leste Asiático (CN+JP+KR)")
    )
    return (
        pd.concat([df.loc[df["codigo"] != codigo_total], leste_asiatico], ignore_index=True)
        .merge(totais, on="ano", how="inner")
        .assign(participacao=lambda d: 100 * d["valor"] / d["total_mundial"])
        .sort_values(["codigo", "ano"])
        .reset_index(drop=True)
    )


def calcular_concentracao(df_participacao: pd.DataFrame, serie: str) -> pd.DataFrame:
    """CR5 e HHI por ano, sobre países/escritórios (participações no total mundial)."""
    unidades = df_participacao.loc[eh_unidade(df_participacao["codigo"])]
    linhas = []
    for ano, grupo in unidades.groupby("ano"):
        ordenado = grupo.sort_values("participacao", ascending=False)
        linhas.append(
            {
                "serie": serie,
                "ano": ano,
                "cr5": ordenado["participacao"].head(5).sum(),
                "hhi": (ordenado["participacao"] ** 2).sum(),
                "n_unidades": len(ordenado),
                "lider": ordenado["codigo"].iloc[0],
                "participacao_lider": ordenado["participacao"].iloc[0],
            }
        )
    return pd.DataFrame(linhas)


def calcular_vtr(df_campos: pd.DataFrame, decadas=DECADAS_VTR) -> pd.DataFrame:
    """VTR_ij = (P_ij / P_i) / (P_j / P), com P somado no decênio (seção 7.3).

    Exclui o campo desconhecido e os códigos agregados (inclusive a origem desconhecida).
    """
    base = df_campos.loc[
        eh_unidade(df_campos["codigo"]) & (df_campos["campo"] != CAMPO_DESCONHECIDO)
    ]
    resultados = []
    for inicio, fim in decadas:
        soma = (
            base.loc[base["ano"].between(inicio, fim)]
            .groupby(["codigo", "nome", "campo", "nome_campo"], as_index=False)["valor"]
            .sum()
        )
        total_pais = soma.groupby("codigo")["valor"].transform("sum")
        total_campo = soma.groupby("campo")["valor"].transform("sum")
        total_geral = soma["valor"].sum()
        soma["decada"] = f"{inicio}–{fim}"
        soma["participacao_campo_no_pais"] = 100 * soma["valor"] / total_pais
        soma["participacao_campo_no_mundo"] = 100 * total_campo / total_geral
        soma["vtr"] = (soma["valor"] / total_pais) / (total_campo / total_geral)
        resultados.append(soma)
    return pd.concat(resultados, ignore_index=True)


@app.command()
def main():
    series = limpar_series()
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    escritorio_total = series["depositos_escritorio"].query("tipo == 'Total'").drop(columns="tipo")
    total_mundial = montar_total_mundial(escritorio_total)
    escritorio_total = pd.concat(
        [
            escritorio_total.loc[escritorio_total["codigo"] != CODIGO_MUNDO_ESCRITORIO],
            total_mundial.drop(columns="fonte"),
        ]
    )
    participacao_escritorio = calcular_participacao(escritorio_total, CODIGO_MUNDO_ESCRITORIO)

    # Origem: o denominador é o mesmo total mundial de pedidos, como faz a OMPI. A origem
    # desconhecida ('**') fica na tabela para medir a cobertura da série por origem.
    origem_total = series["depositos_origem"].query("tipo == 'Total'").drop(columns="tipo")
    participacao_origem = calcular_participacao(
        pd.concat([origem_total, total_mundial.drop(columns="fonte")]),
        CODIGO_MUNDO_ESCRITORIO,
    )

    pct = series["pct_origem"].loc[lambda d: d["ano"] <= ANO_FINAL]
    participacao_pct = calcular_participacao(pct, CODIGO_TOTAL_PCT)

    concentracao = pd.concat(
        [
            calcular_concentracao(participacao_escritorio, "escritorio"),
            calcular_concentracao(participacao_origem, "origem"),
            calcular_concentracao(participacao_pct, "pct"),
        ],
        ignore_index=True,
    )
    vtr = calcular_vtr(series["publicacoes_campo_origem"])

    saidas = {
        "total_mundial": total_mundial,
        "participacao_escritorio": participacao_escritorio,
        "participacao_origem": participacao_origem,
        "participacao_pct": participacao_pct,
        "concentracao": concentracao,
        "vtr_decada": vtr,
    }
    for nome, df in saidas.items():
        df.to_csv(PROCESSED_DATA_DIR / f"{nome}.csv", index=False)
        logger.success(f"processed/{nome}.csv: {len(df):,} linhas")


if __name__ == "__main__":
    app()
