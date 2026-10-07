# artigo-simpori-patentes

ETL e análise das séries de patentes da OMPI para o artigo "Distribuição internacional de patentes e a
posição da China: participação e especialização tecnológica (1980–2024)", XIV SimpoRI (UERJ, 2026).
Estrutura [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/) v2.

## Como rodar

Python 3.12, a partir da raiz do projeto:

```bash
pip install -r requirements.txt     # instala também o pacote `patentes` em modo editável

python -m patentes.dataset          # 1. extração: API da OMPI -> data/raw/ (+ manifest.json)
python -m patentes.features         # 2. transformação: data/interim/ e indicadores em data/processed/
jupyter nbconvert --to notebook --execute --inplace notebooks/1.0-apj-analise-descritiva.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/2.0-apj-figuras-artigo.ipynb

python -m pytest tests              # testes do ETL (não acessam a rede)
ruff check patentes && ruff format patentes
```

Com `make` disponível: `make all` (ou `make data`, `make features`, `make notebooks`, `make test`).
Uma série isolada: `python -m patentes.dataset --serie pct_origem`.

## Fluxo

| Etapa | Código | Saída |
|---|---|---|
| Extração | `patentes/dataset.py` | `data/raw/*.csv` exatamente como a OMPI entrega; `data/raw/manifest.json` com URL, filtros, data de extração e versão da base; `data/external/codigos_*.json` |
| Transformação | `patentes/features.py` | `data/interim/*.csv` (formato longo) e `data/processed/*.csv` (participação, CR5, HHI, VTR) |
| Exploração | `notebooks/1.0-apj-analise-descritiva.ipynb` | conferência dos dados e padrões preliminares |
| Artigo | `notebooks/2.0-apj-figuras-artigo.ipynb` | `reports/figures/*.png|pdf`, `reports/tables/*.csv|xlsx`, `reports/figures/legendas.md` |

Toda figura e tabela do artigo sai do notebook 2.0. `patentes/plots.py` só define o estilo (Times New Roman,
formato numérico brasileiro, 16 cm de largura) e o salvamento.

## Fonte dos dados

API pública do [WIPO IP Statistics Data Center](https://www3.wipo.int/ipstats/)
(`https://api.ipstatsdc.deda.prd.web1.wipo.int/api/v1/public`), a mesma que o site usa. Não exige
autenticação, mas exige o cabeçalho `Accept-Language`. As séries, filtros e códigos estão em `patentes/config.py`.

| Série | Indicador OMPI | Período |
|---|---|---|
| `depositos_escritorio` | 1 – Total patent applications, por escritório (total, residente, não residente) | 1980–2024 |
| `depositos_origem` | 1 – Total patent applications, por origem (total, residente, exterior, contagem equivalente) | 1980–2024 |
| `publicacoes_campo_origem` | 4a – Patent publications by technology (35 campos), por origem | 1980–2024 (VTR até 2023) |
| `pct_origem` | PCT 1 – PCT applications by filing date, por origem | 1995–2024 |

## Ressalvas das séries

- **Origem antes de 1994:** a OMPI só cruza escritório e origem a partir de 1994. Até 1993, cerca de um terço
  dos pedidos aparece com origem desconhecida (`**`), o que subestima os países que depositam no exterior.
- **Total mundial:** o código `WD` só existe desde 1985; para 1980–1984 usa-se a soma dos escritórios
  (em 1985 a diferença é de 0,02%). Ver `data/processed/total_mundial.csv`.
- **Regiões de escritório** (R1–R6) só desde 1997. `W1`–`W4` são grupos de renda, não escritórios.
- **Leste Asiático** = CN + JP + KR, com o código `XEA` (`LA` é o código ISO do Laos).
- Taiwan não aparece nas séries; Hong Kong (`HK`) e Macau (`MO`) têm códigos próprios.
- A OMPI revisa valores antigos a cada edição: refaça a extração e registre a data antes de citar números.
