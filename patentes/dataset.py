"""Extração: baixa as séries da API pública da OMPI para data/raw/.

Os CSVs são gravados byte a byte como a OMPI os entrega. Cada extração fica registrada em
data/raw/manifest.json (URL, parâmetros, data de extração e "Last updated" da OMPI), que
alimenta o dados/README exigido pela seção 7.2 do CLAUDE.md.

Uso:
    python -m patentes.dataset                 # todas as séries
    python -m patentes.dataset --serie pct_origem
"""

from datetime import datetime, timezone
import json
import re

from loguru import logger
import requests
import typer

from patentes.config import (
    API_BASE_URL,
    API_HEADERS,
    API_TIMEOUT_SEGUNDOS,
    EXTERNAL_DATA_DIR,
    MANIFEST_PATH,
    RAW_DATA_DIR,
    SERIES,
    TODOS,
)

app = typer.Typer()


# Parâmetro de seleção -> chave da lista correspondente na resposta de loadOffOrg*List.
LISTA_POR_PARAMETRO = {
    "ipsTechSelValues": "ipsTechList",
    "ipsOriSelValues": "ipsOriginList",
    "ipsOffSelValues": "ipsOffList",
    "pmhOriSelValues": "pmhOriginList",
    "pmhOffSelValues": "pmhOffList",
}


def carregar_lista_de_codigos(aba: str, params: dict) -> dict:
    """Devolve as listas de códigos (países, escritórios, campos) válidas para um indicador."""
    if aba == "ips-search":
        endpoint = "loadOffOrgTechList"
        consulta = {"indicator": params["indicator"], "rpType": params["reportType"]}
    else:
        endpoint = "loadOffOrgClassList"
        consulta = {"indicator": params["indicator"]}
    resposta = requests.get(
        f"{API_BASE_URL}/{aba}/{endpoint}",
        params=consulta,
        headers=API_HEADERS,
        timeout=API_TIMEOUT_SEGUNDOS,
    )
    resposta.raise_for_status()
    return resposta.json()


def resolver_selecao_todos(aba: str, params: dict) -> dict:
    """Troca o marcador TODOS pela lista completa de códigos daquele seletor."""
    if TODOS not in params.values():
        return params
    listas = carregar_lista_de_codigos(aba, params)
    return {
        chave: sorted(listas[LISTA_POR_PARAMETRO[chave]]) if valor == TODOS else valor
        for chave, valor in params.items()
    }


def baixar_csv(aba: str, params: dict) -> tuple[bytes, str]:
    """Chama o endpoint downloadCsv e devolve o conteúdo bruto e a URL efetiva."""
    resposta = requests.get(
        f"{API_BASE_URL}/{aba}/downloadCsv",
        params=params,
        headers=API_HEADERS,
        timeout=API_TIMEOUT_SEGUNDOS,
    )
    resposta.raise_for_status()
    if b"," not in resposta.content[:2000]:
        raise ValueError(f"Resposta inesperada da OMPI: {resposta.content[:300]!r}")
    return resposta.content, resposta.url


def ler_ultima_atualizacao(conteudo: bytes) -> str | None:
    """Extrai o 'Last updated: <mês ano>' do cabeçalho do CSV da OMPI."""
    achado = re.search(rb"Last updated:\s*([^\r\n,]+)", conteudo)
    return achado.group(1).decode().strip() if achado else None


def baixar_listas_de_codigos() -> None:
    """Guarda as listas de países, escritórios e campos usadas pela OMPI (referência)."""
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for nome, especificacao in SERIES.items():
        listas = carregar_lista_de_codigos(especificacao["aba"], especificacao["params"])
        nome_arquivo = f"codigos_{nome}.json"
        (EXTERNAL_DATA_DIR / nome_arquivo).write_text(
            json.dumps(listas, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"Lista de códigos salva em {EXTERNAL_DATA_DIR / nome_arquivo}")


@app.command()
def main(serie: str = typer.Option(None, help="Nome de uma série de config.SERIES")):
    nomes_series = [serie] if serie else list(SERIES)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    manifesto = (
        json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
    )

    for nome in nomes_series:
        especificacao = SERIES[nome]
        logger.info(f"Baixando {nome}: {especificacao['descricao']}")
        params = resolver_selecao_todos(especificacao["aba"], especificacao["params"])
        conteudo, url = baixar_csv(especificacao["aba"], params)

        caminho = RAW_DATA_DIR / f"{nome}.csv"
        caminho.write_bytes(conteudo)

        manifesto[nome] = {
            "arquivo": caminho.name,
            "descricao": especificacao["descricao"],
            "url": url,
            "params": especificacao["params"],
            "extraido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "ompi_last_updated": ler_ultima_atualizacao(conteudo),
            "bytes": len(conteudo),
        }
        logger.success(f"{caminho.name}: {len(conteudo):,} bytes")

    MANIFEST_PATH.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    if not serie:
        baixar_listas_de_codigos()
    logger.success(f"Manifesto atualizado em {MANIFEST_PATH}")


if __name__ == "__main__":
    app()
