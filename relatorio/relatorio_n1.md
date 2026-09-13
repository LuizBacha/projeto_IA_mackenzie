# Assistente de Leitura de Editais de Leilão de Imóveis com Grande Modelo de Linguagem (LLM)

**Disciplina:** Inteligência Artificial — 7ºK SI
**Instituição:** Faculdade de Computação e Informática (FCI) — Universidade Presbiteriana Mackenzie
**Professor:** Prof. Dr. Leandro Zerbinatti

## Integrantes

| Nome | RA | E-mail |
|------|----|--------|
| Guilherme Haddad Borro | _(RA)_ | _(e-mail @mackenzista)_ |
| _(integrante 2)_ | | |
| _(integrante 3)_ | | |

---

## Resumo

Editais de leilão de imóveis são documentos jurídicos extensos e densos em
terminologia técnica, o que impede que o comprador comum compreenda os riscos do
lote antes de dar um lance. Este projeto propõe um assistente que lê o edital (e a
matrícula) de um imóvel e, por meio de um Grande Modelo de Linguagem (LLM), produz
um dossiê em linguagem acessível: tipo de leilão, situação de ocupação, débitos que
passam ao arrematante, ônus e gravames, nível de risco, um glossário dos termos
técnicos presentes no documento e uma recomendação final. Para fundamentar a
proposta, foi coletado um corpus de 87 lotes de apartamentos em São Paulo (66
editais distintos) diretamente de uma plataforma pública de leilões, com extração
de texto dos PDFs e construção de um conjunto de dados estruturado. A análise
exploratória confirma o problema: o edital mediano tem cerca de 16 mil caracteres
de texto jurídico e termos como "comissão", "débito", "condomínio", "IPTU" e
"penhora" aparecem na quase totalidade dos documentos, enquanto informações críticas
como ocupação e avaliação raramente estão disponíveis em campos estruturados — elas
estão dispersas no texto do edital. Espera-se, na fase de desenvolvimento, avaliar a
capacidade do LLM de extrair esses fatos corretamente e de traduzi-los para uma
linguagem que um leigo entenda, reduzindo a assimetria de informação nesse mercado.

**Palavras-chave:** grande modelo de linguagem; análise de documentos; leilão de
imóveis; extração de informação; processamento de linguagem natural.

## Abstract

Real-estate auction notices ("editais") are long, dense legal documents that prevent
ordinary buyers from understanding a lot's risks before bidding. This project proposes
an assistant that reads the auction notice (and the property record) of a lot and, by
means of a Large Language Model (LLM), produces a dossier in plain language: auction
type, occupancy status, debts transferred to the buyer, liens and encumbrances, risk
level, a glossary of the technical terms found in the document, and a final
recommendation. To ground the proposal, a corpus of 87 apartment lots in São Paulo (66
distinct notices) was collected from a public auction platform, with text extracted
from the PDFs and organized into a structured dataset. Exploratory analysis confirms
the problem: the median notice has around 16,000 characters of legal text, and terms
such as "commission", "debt", "condominium fee", "property tax" and "lien" appear in
almost every document, while critical information such as occupancy and appraisal is
rarely available as structured fields — it is scattered throughout the notice. In the
development phase, we expect to assess the LLM's ability to extract these facts
correctly and to translate them into language a layperson can understand, reducing the
information asymmetry in this market.

**Keywords:** large language model; document analysis; real-estate auction; information
extraction; natural language processing.

---

## 1. Introdução

### 1.1 Contextualização

Os leilões de imóveis tornaram-se uma via popular de aquisição de moradia e de
investimento no Brasil, impulsionados por leilões extrajudiciais de bancos (retomada
de garantias de financiamento) e por leilões judiciais (execuções de dívidas). Toda
oferta é regida por um **edital**: o documento jurídico que define as regras do
leilão, a descrição do bem, os valores, as condições de pagamento e — o mais
importante para o comprador — os encargos, dívidas e restrições que recaem sobre o
imóvel. Junto ao edital costuma vir a **matrícula** do imóvel, que registra os ônus
reais (hipoteca, penhora, usufruto, alienação fiduciária) incidentes sobre o bem.

### 1.2 Justificativa

O problema é que esses documentos são escritos para operadores do Direito, não para o
cidadão comum. Um erro de leitura pode custar caro: arrematar um imóvel ocupado (que
exige ação de desocupação), com dívidas de IPTU e condomínio que passam ao comprador,
ou com um ônus não percebido. A assimetria de informação entre quem redige o edital e
quem dá o lance é a lacuna que este projeto ataca. Um assistente capaz de ler o
documento e explicar seu conteúdo em linguagem simples democratiza o acesso a esse
mercado e reduz o risco de decisões mal informadas. A tarefa é adequada a um Grande
Modelo de Linguagem porque combina **compreensão de texto extenso**, **extração de
fatos específicos** em meio a cláusulas genéricas e **reescrita** para um público
leigo — capacidades centrais desses modelos.

### 1.3 Objetivo

**Objetivo geral:** desenvolver um assistente baseado em LLM que analise o edital e a
matrícula de um lote de leilão de imóvel e produza um dossiê explicativo em linguagem
acessível a pessoas sem formação jurídica.

**Objetivos específicos:**
- coletar e caracterizar um corpus representativo de editais de leilão de imóveis;
- definir o conjunto de fatos a serem extraídos de cada documento (tipo de leilão,
  ocupação, débitos, ônus, condições de pagamento, nível de risco);
- projetar o prompt e o formato de saída estruturado (JSON) que orientam o LLM;
- avaliar a qualidade da extração e da explicação geradas pelo modelo.

### 1.4 Opção do projeto

Adotou-se a **Opção API de LLM** (uso de um grande modelo de linguagem para análise de
documentos de negócio), conforme previsto no enunciado da disciplina.

## 2. Descrição do Problema

Dado o edital (e, quando disponível, a matrícula) de um lote de leilão, o sistema deve
responder, em linguagem que um leigo entenda, a perguntas como: *o leilão é judicial
ou extrajudicial?*, *o imóvel está ocupado?*, *quais dívidas passam para mim?*,
*existem ônus na matrícula?*, *quais as condições de pagamento?* e *qual o nível de
risco deste lote?*. O desafio técnico é triplo: (i) o documento é **longo** e mistura
informações específicas do lote com **cláusulas genéricas** (boilerplate) que se
repetem; (ii) os fatos relevantes estão em **linguagem jurídica** que precisa ser
traduzida; e (iii) a saída precisa ser **estruturada e confiável** (sem inventar
valores) para ser útil e segura.

## 3. Aspectos Éticos e Responsabilidade no Uso da IA

O uso de IA neste domínio exige cuidados explícitos:

- **Não é aconselhamento jurídico.** A ferramenta é um apoio à leitura, não substitui
  advogado. A saída deve deixar isso claro ao usuário, evitando induzir decisões
  financeiras de alto valor com base apenas no modelo.
- **Alucinação em contexto sensível.** Um LLM pode "inventar" um valor de dívida ou um
  ônus inexistente. Mitigações previstas: instruir o modelo a usar `null` quando o dado
  não constar, temperatura zero, e ancorar a resposta no texto do documento.
- **Privacidade de terceiros.** Editais e matrículas contêm dados pessoais de devedores
  e ocupantes (nomes, às vezes CPF). Embora sejam documentos públicos, o projeto **não
  versiona os textos brutos** no repositório; o conjunto de dados publicado contém
  apenas atributos estruturados e agregados, sem identificar pessoas. Esse é o sentido
  de "dados anonimizados quando necessário".
- **Viés e cobertura.** O corpus é de uma única plataforma e de uma cidade; conclusões
  não devem ser generalizadas sem ressalvas.
- **Dependência excessiva.** O público-alvo é leigo e pode confiar cegamente na
  resposta; por isso a ferramenta apresenta o **porquê** de cada ponto e um glossário,
  favorecendo o entendimento em vez da mera obediência à recomendação.

## 4. Dataset

### 4.1 Origem e conteúdo

O corpus foi coletado da vitrine pública de apartamentos em São Paulo/SP de uma
plataforma de leilões (Mega Leilões). O script `src/coletar_editais.py` percorre as
páginas da vitrine (todas server-side, coletadas via HTTP, sem navegador), abre a
página de cada lote, localiza os PDFs do **edital** e da **matrícula**, extrai o texto
com a biblioteca PyMuPDF e monta um registro por lote. Como o edital é um documento por
*leilão* (compartilhado por vários lotes) e a matrícula é por *lote*, o download dos
editais é cacheado por URL para evitar redundância.

O conjunto final tem **87 lotes** e **66 editais distintos**. Cada linha do
`metadata.csv` contém: identificação do lote e do leilão, bairro, área, ocupação,
valor de avaliação, presença de inscrição cadastral, presença e tamanho (páginas e
caracteres) de edital e matrícula, tipo de leilão inferido e um conjunto de
indicadores binários de presença de termos jurídicos no edital (hipoteca, penhora,
usufruto, alienação fiduciária, IPTU, condomínio, dívida ativa, financiamento,
comissão, débito, ocupação).

### 4.2 Análise exploratória (Python)

A análise completa está em `notebooks/eda.ipynb` (pandas, matplotlib, seaborn).
Principais achados:

- **Tamanho dos documentos.** O edital mediano tem ~5 páginas, mas a distribuição é
  fortemente assimétrica: a média é de ~15 páginas e o maior chega a **58 páginas**;
  em caracteres, a mediana é de **~16.300 caracteres** de texto jurídico por edital.
  Isso quantifica o problema de leitura enfrentado pelo leigo (Figura 3).
- **Tipo de leilão.** Predominam leilões **extrajudiciais** (63) sobre **judiciais**
  (24), coerente com o volume de retomadas bancárias no mercado (Figura 4).
- **Termos jurídicos.** A prevalência de termos no corpus é alta: **comissão (100%)**,
  **débito (98%)**, **condomínio (95%)**, **IPTU (92%)**, **penhora (83%)**, dívida
  ativa (69%), alienação fiduciária (49%) e hipoteca (48%) (Figura 6). Isso justifica
  diretamente o **glossário automático** e a **extração de débitos/ônus** como saídas
  do sistema.
- **Campos estruturados são esparsos.** A ocupação só foi identificável no resumo
  estruturado da listagem em uma minoria dos lotes e o valor de avaliação não aparece
  de forma estruturada — ou seja, **essas informações estão dispersas no texto do
  edital**, o que reforça a necessidade de um modelo de linguagem para extraí-las, em
  vez de regras fixas (Figura 1).
- **Cobertura documental.** 100% dos lotes têm edital e 99% têm matrícula anexada,
  garantindo material para análise em praticamente todo o corpus.

### 4.3 Preparação dos dados

Na preparação (seção 9 do notebook): removem-se lotes sem edital ou sem texto
extraível; deriva-se a faixa de porte do edital (curto/médio/longo/muito longo); e
persiste-se o conjunto limpo em `dataset/dataset_preparado.csv`. Valores ausentes
(avaliação, matrícula) são mantidos como nulos e tratados pelo pipeline, que degrada
com elegância quando um documento não está presente.

## 5. Metodologia e Resultados Esperados

### 5.1 Metodologia proposta

A pesquisa é **aplicada e quali-quantitativa**. A abordagem para a fase de
desenvolvimento (N2) compreende:

1. **Extração de texto:** PDF → texto com PyMuPDF, com truncamento controlado para
   respeitar a janela de contexto do modelo.
2. **Engenharia de prompt:** um *prompt* de sistema que instrui o modelo a atuar como
   consultor para leigos, e um *schema* JSON que fixa os campos de saída (tipo de
   leilão, ocupação, débitos, ônus, condições, risco, glossário, recomendação).
3. **Chamada ao LLM** via API compatível com o padrão OpenAI (provider-agnóstica),
   com temperatura zero para reduzir variabilidade e instrução de usar `null` quando
   um dado não constar.
4. **Pós-processamento:** cálculo do total de débitos que passam ao arrematante e
   normalização do JSON.
5. **Avaliação:** conferência manual, em uma amostra do corpus, da correção dos fatos
   extraídos (precisão/erro por campo) e da clareza das explicações, comparando a
   saída do modelo com a leitura humana do documento.

### 5.2 Resultados esperados

Espera-se demonstrar que o LLM é capaz de (i) identificar corretamente, na maioria dos
casos, o tipo de leilão, a ocupação e os débitos/ônus presentes no edital; (ii)
produzir um glossário pertinente aos termos efetivamente presentes em cada documento;
e (iii) gerar explicações que um leitor leigo considere compreensíveis. Espera-se
também mapear as **limitações** — tipos de cláusula em que o modelo erra ou alucina —
de modo a delimitar com honestidade o alcance da ferramenta.

## 6. Referências

BROWN, T. et al. Language models are few-shot learners. **Advances in Neural
Information Processing Systems**, v. 33, p. 1877–1901, 2020.

OPENAI. **How can I access the ChatGPT API?** 2024. Disponível em:
https://help.openai.com/en/articles/7039783-how-can-i-access-the-chatgpt-api. Acesso
em: 13 set. 2026.

RUSSELL, S.; NORVIG, P. **Inteligência Artificial**. Rio de Janeiro: LTC, 2021.

VASWANI, A. et al. Attention is all you need. **Advances in Neural Information
Processing Systems**, v. 30, 2017.

## 7. Bibliografia

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 6023**: informação e documentação:
referências: elaboração. Rio de Janeiro: ABNT, 2018.

JURAFSKY, D.; MARTIN, J. H. **Speech and Language Processing**. 3. ed. (rascunho),
2024.

MEGA LEILÕES. **Leilões de imóveis — apartamentos em São Paulo/SP.** Disponível em:
https://www.megaleiloes.com.br/imoveis/apartamentos/sp/sao-paulo. Acesso em: 13 set.
2026.
