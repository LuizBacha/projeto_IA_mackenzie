# Assistente de Leitura de Editais de Leilão com LLM

Projeto da disciplina de **Inteligência Artificial** — Faculdade de Computação e
Informática (FCI), Universidade Presbiteriana Mackenzie.

**Opção do projeto:** API de LLM (análise de documentos de negócio).

**Professor:** Prof. Dr. Leandro Zerbinatti (Inteligência Artificial, 7ºK SI). **Orientador:** Prof. Gustavo Scalabrini Sampaio.

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
src/coletar_editais.py        # N1: coleta o corpus (HTTP + PyMuPDF) -> dataset/metadata.csv
src/assistente_edital.py      # N2: assistente LLM (PDF -> prompt -> JSON -> dossiê)
src/baseline_regras.py        # N2: linha de base sem IA (regex) para comparação
src/avaliar.py                # N2: métricas (completude, fidelidade, concordância, legibilidade) + figuras 08-11
app.py                        # N2: interface Streamlit (envia um PDF e mostra o dossiê)
rodar_n2.bat                  # N2: executa tudo no Windows (pede a chave da API)
notebooks/eda.ipynb           # N1: análise exploratória e preparação dos dados
notebooks/n2_assistente.ipynb # N2: execução comentada do assistente e dos resultados
dataset/metadata.csv          # dataset estruturado (1 linha por lote)
dataset/dataset_preparado.csv # dataset limpo usado na N2
resultados/                   # N2: saídas JSON do LLM, dossiês, métricas e planilha de conferência
figuras/                      # gráficos da EDA (01-07) e dos resultados (08-11)
relatorio/                    # relatórios N1 e N2 (template FCI)
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

## N2: rodar o assistente

O assistente usa qualquer API no padrão OpenAI. O padrão é o **Google Gemini** (chave grátis em
https://aistudio.google.com/apikey).

```bash
pip install -r requirements.txt
# Windows (cmd):  set LLM_API_KEY=sua_chave      | Linux/macOS: export LLM_API_KEY=sua_chave
python src/assistente_edital.py --amostra 30   # baixa editais, chama o LLM, gera JSON + dossiês
python src/baseline_regras.py                  # linha de base sem IA
python src/avaliar.py                          # métricas + figuras 08-11
```

No Windows basta dar duplo clique em `rodar_n2.bat`. Para outro provedor, defina também
`LLM_BASE_URL` e `LLM_MODEL` (ex.: `https://api.openai.com/v1` e `gpt-4o-mini`).

Demonstração interativa: `pip install streamlit` e `streamlit run app.py`.

Principais saídas: `resultados/metricas.json`, `resultados/dossies/*.md` (um dossiê por lote),
`resultados/conferencia_manual.csv` (planilha para conferência humana).

## Entregas

- **Relatório N2 (final):** [`relatorio/relatorio_n2.pdf`](relatorio/relatorio_n2.pdf) ([.docx](relatorio/relatorio_n2.docx))
- **Relatório N1:** [`relatorio/relatorio_n1.docx`](relatorio/relatorio_n1.docx)
- **Vídeo de apresentação (YouTube):** https://youtu.be/3hR9aPqte-c
- **Principais resultados (29 editais):** JSON válido em 96,6%; 99,1% das evidências citadas pelo LLM existem no edital;
  lance mínimo extraído em 100% dos lotes (regras: 0%); legibilidade (Flesch) de 40,7 no edital para 51,3 nas explicações.
  Detalhes em [`resultados/metricas.json`](resultados/metricas.json) e no [notebook da N2](notebooks/n2_assistente.ipynb).

A N1 foi publicada originalmente em https://github.com/guihborro/projeto_IA_mackenzie; este repositório reúne N1 e N2
com o histórico completo de commits.

## Fonte dos dados

Vitrine pública do Mega Leilões — apartamentos em São Paulo/SP. Os documentos
(editais e matrículas) são públicos e disponibilizados pela própria plataforma.

## Integrantes

- Luiz Eduardo Bacha dos Santos — RA 10425296
- Guilherme Haddad Borro — RA 10427699
