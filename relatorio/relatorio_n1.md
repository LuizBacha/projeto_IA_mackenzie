# Assistente de Leitura de Editais de Leilão de Imóveis com Grande Modelo de Linguagem (LLM)

**Disciplina:** Inteligência Artificial (7ºK SI)
**Instituição:** Faculdade de Computação e Informática (FCI), Universidade Presbiteriana Mackenzie
**Orientador:** Prof. Gustavo Scalabrini Sampaio (gustavo.sampaio@mackenzie.br)

## Integrantes

| Nome | RA | E-mail |
|------|----|--------|
| Luiz Eduardo Bacha dos Santos | 10425296 | 10425296@mackenzista.com.br |
| Guilherme Haddad Borro | 10427699 | 10427699@mackenzista.com.br |

---

## Resumo

Comprar um imóvel em leilão pode ser um ótimo negócio, mas exige ler o edital, um
documento jurídico longo e cheio de termos técnicos que a maioria das pessoas não
entende. Quem não consegue interpretá-lo corre o risco de arrematar um imóvel com
dívidas, ocupado ou com restrições que não percebeu. Este projeto propõe um assistente
que lê o edital (e a matrícula) de um lote e usa um Grande Modelo de Linguagem (LLM)
para explicar tudo em linguagem simples: se o leilão é judicial ou extrajudicial, se o
imóvel está ocupado, quais dívidas passam para o comprador, quais são os ônus, o nível
de risco e um glossário dos termos que aparecem no documento. Para embasar a proposta,
coletamos 87 lotes de apartamentos em São Paulo (66 editais diferentes) de uma
plataforma pública de leilões, extraímos o texto dos PDFs e organizamos tudo em uma base
estruturada. A análise exploratória confirma o problema: o edital mediano tem cerca de
16 mil caracteres de texto jurídico, e termos como comissão, débito, condomínio, IPTU e
penhora aparecem em quase todos os documentos. Informações importantes, como ocupação e
avaliação, quase nunca vêm em campos prontos: estão escondidas no meio do texto. Na
próxima fase, vamos avaliar se o LLM consegue extrair esses dados corretamente e
traduzi-los para uma linguagem que qualquer pessoa entenda.

**Palavras-chave:** grande modelo de linguagem; análise de documentos; leilão de
imóveis; extração de informação; processamento de linguagem natural.

> Observação: no documento oficial (`relatorio_n1.docx`) há também o Abstract e as
> Keywords em inglês, exigidos pelo template ABNT da FCI.

---

## 1. Introdução

### 1.1 Contextualização

Comprar imóveis em leilão virou uma opção popular no Brasil, tanto para quem procura
moradia quanto para quem investe. Boa parte dessas oportunidades vem de leilões
extrajudiciais (quando o banco retoma um imóvel financiado que não foi pago) e de
leilões judiciais (quando um imóvel é usado para quitar uma dívida em processo). Todo
leilão é regido por um **edital**: o documento que traz as regras, descreve o imóvel,
informa os valores e, o que mais importa para quem compra, lista as dívidas, encargos e
restrições que pesam sobre o bem. Junto com o edital costuma vir a **matrícula** do
imóvel, onde ficam registrados os ônus, como hipoteca, penhora e alienação fiduciária.

### 1.2 Justificativa

O problema é que o edital é escrito para advogados, não para o cidadão comum. E um erro
de leitura sai caro: dá para arrematar um imóvel que ainda está ocupado (e vai exigir
uma ação para desocupar), com dívidas de IPTU e condomínio que passam para o comprador,
ou com um ônus que ninguém percebeu. Existe, portanto, um desequilíbrio: quem escreve o
edital entende tudo, quem dá o lance quase nunca. É essa lacuna que o projeto quer
resolver. Um assistente que lê o documento e explica em português claro torna o leilão
mais acessível e reduz o risco de decisões mal informadas. E essa é uma tarefa em que os
modelos de linguagem se saem bem: eles leem textos longos, encontram a informação que
importa no meio de cláusulas repetidas e reescrevem tudo de um jeito que o leigo entende.

### 1.3 Objetivo

**Objetivo geral:** criar um assistente baseado em LLM que leia o edital e a matrícula de
um lote de leilão e gere um resumo explicativo em linguagem acessível a quem não é da
área jurídica.

**Objetivos específicos:**
- coletar e caracterizar um conjunto representativo de editais de leilão de imóveis;
- definir quais informações extrair de cada documento (tipo de leilão, ocupação, dívidas,
  ônus, condições de pagamento e nível de risco);
- projetar o prompt e o formato de saída em JSON que orientam o modelo;
- avaliar a qualidade da extração e das explicações geradas.

### 1.4 Opção do projeto

O projeto segue a **Opção API de LLM** (uso de um grande modelo de linguagem para
análise de documentos de negócio), prevista no enunciado da disciplina.

## 2. Descrição do Problema

A partir do edital (e da matrícula, quando existe) de um lote, o sistema precisa
responder, em linguagem simples, perguntas como: *o leilão é judicial ou extrajudicial?*,
*o imóvel está ocupado?*, *que dívidas passam para mim?*, *há algum ônus na matrícula?*,
*como é o pagamento?* e, no fim, *qual o risco desse lote?*. O desafio tem três lados: o
documento é longo e mistura o que é específico do imóvel com cláusulas genéricas que se
repetem; a informação vem em linguagem jurídica e precisa ser traduzida; e a resposta tem
de ser organizada e confiável, sem inventar valores, para ser realmente útil.

## 3. Aspectos Éticos e Responsabilidade no Uso da IA

Usar IA nesse contexto pede alguns cuidados claros:

- **Não é aconselhamento jurídico.** A ferramenta ajuda a ler o edital, mas não substitui
  um advogado, e deixa isso explícito, para ninguém tomar uma decisão de compra confiando
  só no modelo.
- **Risco de o modelo inventar.** Um LLM pode chutar um valor de dívida ou um ônus que não
  existe. Para reduzir isso, ele é instruído a deixar o campo em branco quando o dado não
  aparece, roda com temperatura zero e sempre se baseia no texto do documento.
- **Privacidade de terceiros.** Editais e matrículas trazem nomes de devedores e
  ocupantes. Mesmo sendo públicos, não colocamos os textos originais no repositório:
  publicamos apenas os dados estruturados, sem identificar ninguém.
- **Limite dos dados.** O material vem de uma só plataforma e de uma só cidade, então as
  conclusões não valem para o Brasil inteiro.
- **Dependência da ferramenta.** Como o público é leigo, o assistente explica o porquê de
  cada ponto e traz um glossário. A ideia é ajudar a entender, não mandar obedecer.

## 4. Dataset

### 4.1 Origem e conteúdo

O material foi coletado da vitrine pública de apartamentos em São Paulo/SP de uma
plataforma de leilões (Mega Leilões). O script `src/coletar_editais.py` percorre as
páginas da vitrine (que já vêm prontas no HTML, então nem precisamos de navegador), abre
a página de cada lote, encontra os PDFs do edital e da matrícula, lê o texto com a
biblioteca PyMuPDF e monta uma linha por lote. Como um mesmo edital vale para vários lotes
do mesmo leilão, o download é reaproveitado (cache) para não baixar o mesmo arquivo várias
vezes.

No total são **87 lotes** e **66 editais diferentes**. Para cada lote, o `metadata.csv`
guarda: identificação do lote e do leilão, bairro, área, ocupação, valor de avaliação, se
tem inscrição cadastral, se tem edital e matrícula (com o tamanho de cada um, em páginas e
caracteres), o tipo de leilão e um conjunto de marcações indicando quais termos jurídicos
aparecem no edital.

### 4.2 Análise exploratória (Python)

A análise completa está em `notebooks/eda.ipynb` (pandas, matplotlib e seaborn). Os
principais achados:

- **Tamanho dos documentos.** O edital mediano tem cerca de 5 páginas, mas isso engana: a
  média sobe para 15 e o maior chega a **58 páginas**. Em texto, a mediana é de cerca de
  **16.300 caracteres** por edital. É muita leitura jurídica para o comprador comum encarar.
- **Tipo de leilão.** A maioria é **extrajudicial** (63) contra 24 judiciais, o que bate
  com o volume de imóveis retomados por bancos.
- **Termos jurídicos.** Eles aparecem com frequência alta: **comissão (100%)**, **débito
  (98%)**, **condomínio (95%)**, **IPTU (92%)**, **penhora (83%)**, dívida ativa (69%),
  alienação fiduciária (49%) e hipoteca (48%). São justamente esses termos que motivam o
  glossário automático e a extração de dívidas e ônus.
- **As informações não vêm prontas.** Ocupação e valor de avaliação quase nunca aparecem
  num campo separado: estão diluídas no texto do edital. Por isso faz mais sentido usar um
  modelo de linguagem para achá-las do que criar regras fixas.
- **Cobertura.** 100% dos lotes têm edital e 99% têm matrícula, então há material para
  analisar em praticamente todo o conjunto.

### 4.3 Preparação dos dados

Na preparação (seção 9 do notebook), tiramos os lotes sem edital ou sem texto legível,
criamos uma faixa de porte do edital (curto, médio, longo, muito longo) e salvamos a base
limpa em `dataset/dataset_preparado.csv`. Quando falta algum dado (avaliação ou
matrícula), ele fica em branco e o sistema continua funcionando mesmo assim.

## 5. Metodologia e Resultados Esperados

### 5.1 Metodologia proposta

A pesquisa é aplicada e combina análise quantitativa e qualitativa. Para a fase de
desenvolvimento (N2), o caminho é:

1. **Ler o PDF.** Converter o edital em texto com o PyMuPDF, cortando o que passar do
   limite que o modelo consegue processar de uma vez.
2. **Montar o prompt.** Um comando de sistema pede ao modelo para agir como um consultor
   que explica tudo para leigos, e um formato de saída em JSON fixa exatamente quais campos
   ele deve preencher (tipo de leilão, ocupação, dívidas, ônus, condições, risco, glossário
   e recomendação).
3. **Chamar o modelo.** Usamos uma API no padrão OpenAI (que funciona com vários
   provedores), com temperatura zero e a instrução de deixar em branco o que não estiver no
   documento.
4. **Tratar a resposta.** Somamos as dívidas que passam para o comprador e organizamos o
   JSON.
5. **Avaliar.** Conferimos à mão, numa amostra, se o que o modelo extraiu bate com o
   documento e se as explicações ficaram claras.

### 5.2 Resultados esperados

A expectativa é mostrar que o modelo consegue, na maioria dos casos, identificar o tipo de
leilão, a ocupação e as dívidas/ônus do edital; montar um glossário coerente com os termos
de cada documento; e escrever explicações que uma pessoa leiga entenda. Também queremos
deixar claras as limitações, ou seja, os tipos de cláusula em que o modelo erra ou inventa,
para ser honesto sobre até onde a ferramenta vai.

## 6. Referências

BROWN, T. et al. Language models are few-shot learners. **Advances in Neural Information
Processing Systems**, v. 33, p. 1877-1901, 2020.

OPENAI. **How can I access the ChatGPT API?** 2024. Disponível em:
https://help.openai.com/en/articles/7039783-how-can-i-access-the-chatgpt-api. Acesso em:
13 set. 2026.

RUSSELL, S.; NORVIG, P. **Inteligência Artificial**. Rio de Janeiro: LTC, 2021.

VASWANI, A. et al. Attention is all you need. **Advances in Neural Information Processing
Systems**, v. 30, 2017.

## 7. Bibliografia

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 6023**: informação e documentação:
referências: elaboração. Rio de Janeiro: ABNT, 2018.

JURAFSKY, D.; MARTIN, J. H. **Speech and Language Processing**. 3. ed. (rascunho), 2024.

MEGA LEILÕES. **Leilões de imóveis: apartamentos em São Paulo/SP.** Disponível em:
https://www.megaleiloes.com.br/imoveis/apartamentos/sp/sao-paulo. Acesso em: 13 set. 2026.
