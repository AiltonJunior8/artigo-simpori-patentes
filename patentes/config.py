"""Configuração central do projeto: caminhos, API da OMPI e recortes da análise.

Este é o único arquivo a editar para mudar período, séries coletadas ou grupos de países.
"""

from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ---------------------------------------------------------------------------
# Caminhos (estrutura Cookiecutter Data Science)
# ---------------------------------------------------------------------------
PROJ_ROOT = Path(__file__).resolve().parents[1]
logger.info(f"PROJ_ROOT path is: {PROJ_ROOT}")

DATA_DIR = PROJ_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"  # CSVs exatamente como a OMPI os entrega (nunca editar)
INTERIM_DATA_DIR = DATA_DIR / "interim"  # séries em formato longo, limpas
PROCESSED_DATA_DIR = DATA_DIR / "processed"  # indicadores prontos para análise
EXTERNAL_DATA_DIR = DATA_DIR / "external"  # listas de códigos (países, campos) da OMPI

REPORTS_DIR = PROJ_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"  # figuras do artigo, geradas só pelo notebook de figuras
TABLES_DIR = REPORTS_DIR / "tables"  # tabelas do artigo, idem

MANIFEST_PATH = RAW_DATA_DIR / "manifest.json"  # parâmetros, URL e data de cada extração

# ---------------------------------------------------------------------------
# API pública do WIPO IP Statistics Data Center
# ---------------------------------------------------------------------------
# A mesma API que o site https://www3.wipo.int/ipstats/ usa. Sem autenticação, mas exige o
# cabeçalho Accept-Language (sem ele, responde 400).
API_BASE_URL = "https://api.ipstatsdc.deda.prd.web1.wipo.int/api/v1/public"
API_HEADERS = {"Accept-Language": "en", "User-Agent": "Mozilla/5.0 (pesquisa academica)"}
API_TIMEOUT_SEGUNDOS = 180

ANO_INICIAL = 1980
ANO_FINAL = 2024
ANO_FINAL_CAMPOS = 2023  # último ano completo das publicações por campo tecnológico
ANO_INICIAL_PCT = 1995  # primeiro ano disponível na API do PCT

# Códigos de "Type" da OMPI. Cada célula do CSV só traz um número quando o tipo é filtrado;
# sem filtro, a API concatena os componentes em ordem lexicográfica (ilegível).
TIPOS_ESCRITORIO = {"900": "Total", "901": "Residente", "902": "Não residente"}
TIPOS_ORIGEM = {
    "910": "Total",
    "911": "Residente",
    "912": "Exterior",
    "913": "Total (contagem equivalente)",
    "914": "Exterior (contagem equivalente)",
}

# Marcador resolvido em dataset.py: seleciona todos os códigos da lista oficial da OMPI.
TODOS = "TODOS"

# Séries coletadas (seção 7.2 do CLAUDE.md). Cada chave vira data/raw/<chave>.csv.
# "aba" escolhe o endpoint: "ips-search" (estatísticas de PI) ou "pmh-search" (PCT).
SERIES = {
    "depositos_escritorio": {
        "descricao": "Pedidos de patente (diretos + fase nacional PCT) por escritório",
        "aba": "ips-search",
        "params": {
            "selectedTab": "patent",
            "indicator": "10",
            "reportType": "11",  # Total count by filing office
            "fromYear": ANO_INICIAL,
            "toYear": ANO_FINAL,
            "ipsTechSelValues": list(TIPOS_ESCRITORIO),
        },
    },
    "depositos_origem": {
        "descricao": "Pedidos de patente (diretos + fase nacional PCT) por país de origem",
        "aba": "ips-search",
        "params": {
            "selectedTab": "patent",
            "indicator": "10",
            "reportType": "13",  # Total count by applicant's origin
            "fromYear": ANO_INICIAL,
            "toYear": ANO_FINAL,
            "ipsTechSelValues": list(TIPOS_ORIGEM),
        },
    },
    "publicacoes_campo_origem": {
        "descricao": "Publicações de patente por campo tecnológico (35 campos) e país de origem",
        "aba": "ips-search",
        "params": {
            "selectedTab": "patent",
            "indicator": "17",
            "reportType": "13",
            "fromYear": ANO_INICIAL,
            "toYear": ANO_FINAL,
            "ipsTechSelValues": TODOS,  # sem seleção explícita, a API soma os campos
        },
    },
    "pct_origem": {
        "descricao": "Pedidos PCT por data de depósito e país de origem (todos os escritórios receptores)",
        "aba": "pmh-search",
        "params": {
            "selectedTab": "pct",
            "indicator": "1001",
            "reportType": "4001",  # Yearly statistics
            "fromYear": ANO_INICIAL_PCT,
            "toYear": ANO_FINAL,
            "pmhOffSelValues": ["ZZ"],  # ZZ = total dos escritórios receptores
            "pmhOriSelValues": TODOS,  # sem seleção explícita, a API devolve só o total
        },
    },
}

# ---------------------------------------------------------------------------
# Recortes analíticos
# ---------------------------------------------------------------------------
CODIGO_MUNDO_ESCRITORIO = "WD"  # total mundial na série por escritório (existe só desde 1985;
# antes disso, features.py usa a soma dos escritórios, que em 1985 difere do WD em 0,02%)
CODIGO_TOTAL_PCT = "ZZ"  # total mundial na série PCT
CODIGO_ORIGEM_DESCONHECIDA = "**"

# Regiões da OMPI (só existem na série por escritório). R7 (países menos desenvolvidos) não é
# região geográfica e fica de fora.
REGIOES_OMPI = {
    "R1": "África",
    "R2": "Ásia",
    "R3": "Europa",
    "R4": "América Latina e Caribe",
    "R5": "América do Norte",
    "R6": "Oceania",
}

LESTE_ASIATICO = ["CN", "JP", "KR"]  # glossário do artigo: China, Japão e Coreia do Sul
# Código da linha agregada do Leste Asiático. "LA" não serve: é o código ISO do Laos.
CODIGO_LESTE_ASIATICO = "XEA"

# Grupos de renda do Banco Mundial (só na série por escritório): alta, média-alta, média-baixa
# e baixa renda. Não são escritórios.
GRUPOS_RENDA = {"W1", "W2", "W3", "W4"}

# Códigos que agregam países e não podem entrar em rankings, CR5, HHI ou VTR.
# Escritórios regionais (EP, EA, OA, AP, GC) contam como escritórios e ficam de fora daqui.
CODIGOS_AGREGADOS = {
    CODIGO_MUNDO_ESCRITORIO,
    CODIGO_TOTAL_PCT,
    CODIGO_ORIGEM_DESCONHECIDA,
    "EU",
    *REGIOES_OMPI,
    "R7",
    *GRUPOS_RENDA,
    CODIGO_LESTE_ASIATICO,
}

PAISES_DESTAQUE = ["CN", "US", "JP", "KR", "DE"]
ESCRITORIOS_DESTAQUE = ["CN", "US", "JP", "KR", "EP"]

NOMES_PT = {
    "CN": "China",
    "US": "Estados Unidos",
    "JP": "Japão",
    "KR": "Coreia do Sul",
    "DE": "Alemanha",
    "EP": "EPO",
    "FR": "França",
    "GB": "Reino Unido",
    "WD": "Mundo",
    "XEA": "Leste Asiático",
    **REGIOES_OMPI,
}

# Décadas da VTR (seção 7.3): soma dos depósitos do decênio.
DECADAS_VTR = [(1984, 1993), (1994, 2003), (2004, 2013), (2014, 2023)]
CAMPO_DESCONHECIDO = 0  # campo "Unknown", excluído da VTR

# A OMPI só passa a cruzar escritório x origem em 1994. Antes disso, quase todo depósito
# feito no exterior aparece como origem desconhecida ("**").
ANO_INICIO_ORIGEM_COMPLETA = 1994


# Nomes dos 35 campos tecnológicos da OMPI (Schmoch, 2008) em português. Tradução do projeto,
# não oficial: revisar antes de publicar.
CAMPOS_PT = {
    1: "Máquinas, aparelhos e energia elétrica",
    2: "Tecnologia audiovisual",
    3: "Telecomunicações",
    4: "Comunicação digital",
    5: "Processos básicos de comunicação",
    6: "Tecnologia da computação",
    7: "Métodos de TI para gestão",
    8: "Semicondutores",
    9: "Óptica",
    10: "Medição",
    11: "Análise de materiais biológicos",
    12: "Controle",
    13: "Tecnologia médica",
    14: "Química fina orgânica",
    15: "Biotecnologia",
    16: "Produtos farmacêuticos",
    17: "Química macromolecular, polímeros",
    18: "Química de alimentos",
    19: "Química de materiais básicos",
    20: "Materiais, metalurgia",
    21: "Tecnologia de superfícies, revestimentos",
    22: "Tecnologia microestrutural e nanotecnologia",
    23: "Engenharia química",
    24: "Tecnologia ambiental",
    25: "Manuseio",
    26: "Máquinas-ferramenta",
    27: "Motores, bombas, turbinas",
    28: "Máquinas têxteis e de papel",
    29: "Outras máquinas especiais",
    30: "Processos e aparelhos térmicos",
    31: "Elementos mecânicos",
    32: "Transporte",
    33: "Móveis, jogos",
    34: "Outros bens de consumo",
    35: "Engenharia civil",
}

try:
    from tqdm import tqdm

    logger.remove(0)
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
except ModuleNotFoundError:
    pass
