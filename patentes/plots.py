"""Estilo e gravação das figuras do artigo.

Só define a aparência (fonte, cores, formato numérico) e o salvamento. Cada figura é desenhada
no notebook notebooks/2.0-apj-figuras-artigo.ipynb, que é a única origem das imagens do artigo.
"""

import matplotlib as mpl
from matplotlib.ticker import FuncFormatter

from patentes.config import FIGURES_DIR

# Paleta legível em impressão em tons de cinza: cores com luminâncias distintas e, nas séries
# de linha, estilos de traço diferentes.
CORES_PAISES = {
    "CN": "#b2182b",
    "US": "#2166ac",
    "JP": "#1b1b1b",
    "KR": "#7f7f7f",
    "DE": "#4d9221",
    "EP": "#4d9221",
    "XEA": "#b2182b",
}
TRACOS_PAISES = {
    "CN": "-",
    "US": "--",
    "JP": "-.",
    "KR": ":",
    "DE": (0, (5, 1, 1, 1)),
    "EP": (0, (5, 1, 1, 1)),
}

FONTE_PADRAO = "Fonte: elaboração própria com base em WIPO Statistics Database"


def aplicar_estilo_artigo() -> None:
    """Times New Roman 10 pt, sem moldura superior/direita, grade horizontal leve."""
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.alpha": 0.3,
            "figure.dpi": 110,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "axes.formatter.use_locale": False,
        }
    )


def formatar_br(valor: float, casas: int = 1) -> str:
    """Número no padrão brasileiro: ponto de milhar e vírgula decimal."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def eixo_percentual(ax, casas: int = 0) -> None:
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{formatar_br(v, casas)}%"))


def eixo_milhar(ax) -> None:
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: formatar_br(v, 0)))


def salvar_figura(fig, nome: str) -> None:
    """Grava PNG (300 dpi, para o Word) e PDF (vetorial) em reports/figures/."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for extensao in ("png", "pdf"):
        fig.savefig(FIGURES_DIR / f"{nome}.{extensao}")
