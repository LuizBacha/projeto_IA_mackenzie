# Assistente de Leitura de Editais de Leilão com LLM

Projeto da disciplina de **Inteligência Artificial** — Faculdade de Computação e
Informática (FCI), Universidade Presbiteriana Mackenzie.

**Opção do projeto:** API de LLM (análise de documentos de negócio).

## Problema

Editais de leilão de imóveis são documentos jurídicos longos (dezenas de páginas)
e cheios de termos técnicos (*alienação fiduciária*, *ônus*, *penhora*, *praça*…).
O arrematante leigo não consegue ler nem entender esses documentos e corre o risco
de arrematar um imóvel com dívidas, ocupação ou restrições que não percebeu.

## Solução

Um assistente que recebe o edital (e a matrícula) de um lote, extrai o texto do PDF
e usa um **Grande Modelo de Linguagem (LLM)** para produzir um dossiê em **linguagem
simples**: tipo de leilão, ocupação, débitos por conta do arrematante, ônus/gravames,
nível de risco, um **glossário** dos termos que aparecem no documento e uma
recomendação final — tudo explicado para uma pessoa sem conhecimento jurídico.

## Estrutura do repositório

```
src/coletar_editais.py        # coleta o corpus (HTTP + PyMuPDF) -> dataset/metadata.csv
notebooks/eda.ipynb           # análise exploratória e preparação dos dados
dataset/metadata.csv          # dataset estruturado (1 linha por lote)
dataset/dataset_preparado.csv # dataset limpo para a fase de desenvolvimento
figuras/                      # gráficos gerados pela EDA
relatorio/                    # relatório do projeto (template FCI/ABNT)
```

> **Privacidade:** os textos brutos dos editais/matrículas contêm dados pessoais de
> terceiros (devedores, ocupantes) e **não são versionados**. São reproduzíveis com
> `python src/coletar_editais.py --salvar-textos`. O `metadata.csv` guarda apenas
> atributos estruturados e agregados, sem identificar pessoas.

## Como reproduzir

```bash
uv sync
# 1) Coletar o corpus (páginas da vitrine de apartamentos/SP)
uv run python src/coletar_editais.py --paginas 5 --max-lotes 250
# 2) Rodar a análise exploratória
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/eda.ipynb
```

## Fonte dos dados

Vitrine pública do Mega Leilões — apartamentos em São Paulo/SP. Os documentos
(editais e matrículas) são públicos e disponibilizados pela própria plataforma.

## Integrantes

- _(nome — RA — e-mail)_
