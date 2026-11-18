# -*- coding: utf-8 -*-
# ============================================================================
# assistente_edital.py — Assistente de leitura de editais de leilão com LLM (N2)
# ----------------------------------------------------------------------------
# Projeto: Assistente de Leitura de Editais de Leilão de Imóveis com LLM
#          (Disciplina de Inteligência Artificial, FCI Mackenzie)
# Integrantes:
#   Luiz Eduardo Bacha dos Santos (RA 10425296) - 10425296@mackenzista.com.br
#   Guilherme Haddad Borro        (RA 10427699) - 10427699@mackenzista.com.br
# Conteúdo: para cada lote da amostra, baixa o edital (PDF), extrai o texto com
#           PyMuPDF, monta o prompt (papel de sistema + esquema JSON), chama um
#           LLM por uma API no padrão OpenAI (Gemini, OpenAI, Groq, OpenRouter...),
#           valida/normaliza o JSON devolvido e gera:
#             resultados/saidas_llm/<lote>.json  (resposta estruturada do modelo)
#             resultados/dossies/<lote>.md       (dossiê em linguagem simples)
#             resultados/execucao_llm.csv        (log: tempo, tokens, status)
#
# Configuração (variáveis de ambiente):
#   LLM_API_KEY   chave do provedor (obrigatória)
#   LLM_BASE_URL  padrão: endpoint OpenAI-compatível do Google Gemini
#   LLM_MODEL     padrão: gemini-2.5-flash
#
# Uso:
#   python src/assistente_edital.py --amostra 30         # amostra estratificada
#   python src/assistente_edital.py --lote 128917         # um lote específico
#   python src/assistente_edital.py --pdf meu_edital.pdf  # um PDF local (demo)
#
# Histórico de alterações:
#   2026-11-17 | Luiz Eduardo Bacha dos Santos  | criação do pipeline LLM (N2)
#   2026-11-17 | Luiz Eduardo Bacha dos Santos  | evidências literais + retry 429
# ============================================================================
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import pymupdf as fitz  # PyMuPDF (nome novo)
except ImportError:
    import fitz  # PyMuPDF (nome antigo)
import pandas as pd
import requests

try:  # console do Windows: evita UnicodeEncodeError com acentos
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
DATASET = RAIZ / "dataset"
PDFS = DATASET / "pdfs"                     # cache local (gitignored)
TEXTOS = DATASET / "textos_editais"         # cache local (gitignored)
RESULT = RAIZ / "resultados"
SAIDAS = RESULT / "saidas_llm"
DOSSIES = RESULT / "dossies"

BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
MODELO = os.getenv("LLM_MODEL", "gemini-flash-lite-latest")
# se o modelo pedido não estiver liberado (404) ou travar (timeout), tenta estes, na ordem
MODELOS_RESERVA = ["gemini-flash-lite-latest", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash-lite",
                   "gemini-flash-latest", "gemini-3-flash-preview", "gemini-2.5-flash"]
TIMEOUT_S = int(os.getenv("LLM_TIMEOUT", "120"))
MAX_CHARS = 120_000      # corte do texto do edital (limite prático de contexto/custo)
PAUSA_S = float(os.getenv("LLM_PAUSA", "6"))  # respeita limite gratuito (~10 req/min)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}

# ---------------------------------------------------------------------------
# Prompt: papel de sistema + regras anti-alucinação + esquema de saída
# ---------------------------------------------------------------------------
PROMPT_SISTEMA = """Você é um consultor que explica editais de leilão de imóveis para pessoas \
LEIGAS, sem formação jurídica. Você recebe o texto de um edital e a identificação de UM lote.

REGRAS OBRIGATÓRIAS
1. Use SOMENTE informações que estão no texto do edital. Não use conhecimento externo para \
inventar valores, datas, dívidas ou ônus.
2. Se uma informação não aparece no edital, use null (ou lista vazia) e diga "não informado no edital".
3. Para cada campo factual, preencha "evidencia" com um trecho LITERAL e curto (até 200 \
caracteres), copiado exatamente do edital, que comprova a resposta. Se não houver trecho, use null.
4. Valores em reais devem ser números (ex.: 250000.0), sem "R$".
5. O edital pode trazer vários lotes: responda apenas sobre o lote indicado. Regras gerais \
(pagamento, comissão, débitos) que valem para todos os lotes também se aplicam a ele.
6. Explicações em português simples: frases curtas, sem juridiquês. Se precisar usar um termo \
técnico, explique o que ele significa.
7. Isto NÃO é aconselhamento jurídico: a recomendação deve sugerir conferir com um advogado \
quando houver risco.

Responda APENAS com um objeto JSON válido, exatamente neste esquema:
{
  "lote_encontrado": true | false,
  "descricao_imovel": "texto curto",
  "tipo_leilao": {"valor": "Judicial" | "Extrajudicial" | "Não informado", "explicacao": "...", "evidencia": "..." | null},
  "ocupacao": {"valor": "Ocupado" | "Desocupado" | "Não informado", "explicacao": "...", "evidencia": "..." | null},
  "valores": {"avaliacao": número | null, "lance_minimo_1": número | null, "lance_minimo_2": número | null, "evidencia": "..." | null},
  "comissao_leiloeiro_pct": {"valor": número | null, "evidencia": "..." | null},
  "dividas": [{"tipo": "IPTU | Condomínio | Outros", "valor": número | null, "responsavel": "Arrematante" | "Vendedor/Credor" | "Não informado", "explicacao": "...", "evidencia": "..."}],
  "onus": [{"tipo": "Hipoteca | Penhora | Alienação fiduciária | Usufruto | Outro", "explicacao": "...", "evidencia": "..."}],
  "pagamento": {"resumo": "...", "permite_parcelamento": true | false | null, "permite_financiamento": true | false | null, "evidencia": "..." | null},
  "risco": {"nivel": "Baixo" | "Médio" | "Alto", "motivos": ["..."]},
  "glossario": [{"termo": "...", "explicacao": "..."}],
  "resumo_leigo": "até 120 palavras, linguagem simples",
  "recomendacao": "1 a 3 frases"
}"""


def montar_mensagem_usuario(texto: str, lote: dict) -> str:
    ident = (f"Lote alvo: id {lote.get('lote_id')}, apartamento de {lote.get('area_m2')} m², "
             f"bairro/descrição '{lote.get('bairro')}'. Página do lote: {lote.get('url')}")
    return f"{ident}\n\nTEXTO DO EDITAL (extraído do PDF):\n<<<\n{texto[:MAX_CHARS]}\n>>>"


# ---------------------------------------------------------------------------
# Entrada: PDF -> texto (com cache por leilão, pois o edital é compartilhado)
# ---------------------------------------------------------------------------
def texto_do_pdf_bytes(data: bytes) -> tuple[int, str]:
    doc = fitz.open(stream=data, filetype="pdf")
    txt = re.sub(r"\s+", " ", " ".join(p.get_text() for p in doc)).strip()
    return doc.page_count, txt


def obter_texto_edital(leilao_id: str, url: str) -> str:
    TEXTOS.mkdir(parents=True, exist_ok=True)
    PDFS.mkdir(parents=True, exist_ok=True)
    cache_txt = TEXTOS / f"{leilao_id}.txt"
    if cache_txt.exists():
        return cache_txt.read_text(encoding="utf-8")
    cache_pdf = PDFS / f"{leilao_id}.pdf"
    if not cache_pdf.exists():
        r = requests.get(url, headers=HEADERS, timeout=120)
        r.raise_for_status()
        cache_pdf.write_bytes(r.content)
    _, txt = texto_do_pdf_bytes(cache_pdf.read_bytes())
    cache_txt.write_text(txt, encoding="utf-8")
    return txt


# ---------------------------------------------------------------------------
# Chamada ao LLM (API padrão OpenAI: /chat/completions)
# ---------------------------------------------------------------------------
def obter_chave() -> str:
    """Lê a chave da API do ambiente; se não houver, pede no terminal (não é salva em disco)."""
    chave = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not chave:
        chave = input("Cole a chave da API do LLM (Google AI Studio) e tecle Enter: ").strip()
        os.environ["LLM_API_KEY"] = chave
    if not chave:
        sys.exit("ERRO: nenhuma chave informada (variável LLM_API_KEY).")
    return chave


def chamar_llm(mensagens: list[dict], modelo: str = MODELO, tentativas: int = 5) -> dict:
    chave = obter_chave()
    global MODELO
    corpo = {"model": MODELO, "messages": mensagens, "temperature": 0,
             "response_format": {"type": "json_object"}, "reasoning_effort": "low"}
    url = BASE_URL.rstrip("/") + "/chat/completions"
    espera = 10.0
    for i in range(tentativas + 3):
        try:
            r = requests.post(url, json=corpo, timeout=TIMEOUT_S,
                              headers={"Authorization": f"Bearer {chave}"})
        except requests.exceptions.Timeout:
            reserva = [m for m in MODELOS_RESERVA if m != corpo["model"]]
            if not reserva:
                raise
            print(f"    '{corpo['model']}' demorou mais de {TIMEOUT_S}s; trocando para '{reserva[0]}'")
            MODELOS_RESERVA.remove(reserva[0])
            corpo["model"] = MODELO = reserva[0]
            continue
        if r.status_code == 200:
            MODELO = corpo["model"]
            return r.json()
        if r.status_code == 400 and "reasoning" in r.text and "reasoning_effort" in corpo:
            corpo.pop("reasoning_effort")         # modelo sem controle de raciocínio
            continue
        if r.status_code == 400 and "response_format" in r.text and "response_format" in corpo:
            corpo.pop("response_format")          # provedor sem modo JSON nativo
            continue
        if r.status_code in (429, 500, 502, 503, 504):  # limite/instabilidade: espera e tenta
            print(f"    HTTP {r.status_code}; nova tentativa em {espera:.0f}s")
            time.sleep(espera)
            espera *= 2
            continue
        if r.status_code == 404:
            disponiveis = [m.removeprefix("models/") for m in listar_modelos(chave)]
            reserva = [m for m in MODELOS_RESERVA if m != corpo["model"] and m in disponiveis]
            if reserva:
                print(f"    modelo '{corpo['model']}' indisponível; usando '{reserva[0]}'")
                corpo["model"] = MODELO = reserva[0]
                MODELOS_RESERVA.remove(reserva[0])
                continue
            raise RuntimeError(f"Modelo '{corpo['model']}' não encontrado. Modelos disponíveis: "
                               f"{disponiveis[:15]}  -> defina LLM_MODEL")
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
    raise RuntimeError("Falha após várias tentativas (limite de requisições).")


def listar_modelos(chave: str) -> list[str]:
    try:
        r = requests.get(BASE_URL.rstrip("/") + "/models", timeout=30,
                         headers={"Authorization": f"Bearer {chave}"})
        return [m.get("id", "") for m in r.json().get("data", [])]
    except Exception:
        return []


def extrair_json(conteudo: str) -> dict:
    """Aceita JSON puro ou dentro de ```json ... ``` (alguns modelos cercam a saída)."""
    s = conteudo.strip()
    m = re.search(r"\{.*\}", s, re.S)
    return json.loads(m.group(0) if m else s)


# ---------------------------------------------------------------------------
# Pós-processamento: totais e dossiê em Markdown
# ---------------------------------------------------------------------------
def total_dividas_arrematante(saida: dict) -> float | None:
    vals = [d.get("valor") for d in saida.get("dividas") or []
            if (d.get("responsavel") == "Arrematante" and isinstance(d.get("valor"), (int, float)))]
    return round(sum(vals), 2) if vals else None


def brl(v) -> str:
    if not isinstance(v, (int, float)):
        return "não informado"
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_dossie(saida: dict, lote: dict) -> str:
    g = lambda k: saida.get(k) or {}
    L = [f"# Dossiê do lote {lote.get('lote_id')} — {lote.get('bairro')} ({lote.get('area_m2')} m²)",
         "", "> Ferramenta de apoio à leitura. **Não é aconselhamento jurídico.**", "",
         f"**Resumo:** {saida.get('resumo_leigo', '')}", "",
         f"- **Tipo de leilão:** {g('tipo_leilao').get('valor')} — {g('tipo_leilao').get('explicacao', '')}",
         f"- **Ocupação:** {g('ocupacao').get('valor')} — {g('ocupacao').get('explicacao', '')}",
         f"- **Avaliação:** {brl(g('valores').get('avaliacao'))} | **1º lance mínimo:** "
         f"{brl(g('valores').get('lance_minimo_1'))} | **2º lance mínimo:** {brl(g('valores').get('lance_minimo_2'))}",
         f"- **Comissão do leiloeiro:** {g('comissao_leiloeiro_pct').get('valor') or 'não informado'}%",
         f"- **Dívidas por conta do comprador (soma):** {brl(total_dividas_arrematante(saida))}",
         f"- **Nível de risco:** {g('risco').get('nivel')}", ""]
    if saida.get("dividas"):
        L += ["## Dívidas e encargos", ""]
        L += [f"- {d.get('tipo')}: {brl(d.get('valor'))} — responsável: {d.get('responsavel')}. "
              f"{d.get('explicacao', '')}" for d in saida["dividas"]]
        L.append("")
    if saida.get("onus"):
        L += ["## Ônus (restrições no imóvel)", ""]
        L += [f"- **{o.get('tipo')}**: {o.get('explicacao', '')}" for o in saida["onus"]]
        L.append("")
    L += ["## Pagamento", "", g("pagamento").get("resumo", "não informado"), "",
          "## Por que esse risco?", ""]
    L += [f"- {m}" for m in g("risco").get("motivos", [])]
    L += ["", "## Glossário", ""]
    L += [f"- **{t.get('termo')}**: {t.get('explicacao')}" for t in saida.get("glossario") or []]
    L += ["", f"**Recomendação:** {saida.get('recomendacao', '')}", ""]
    return "\n".join(L)


def analisar(texto: str, lote: dict) -> tuple[dict, dict]:
    """Executa o assistente para um lote. Devolve (saida_json, metadados_da_chamada)."""
    msgs = [{"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": montar_mensagem_usuario(texto, lote)}]
    t0 = time.time()
    resp = chamar_llm(msgs)
    dt = time.time() - t0
    conteudo = resp["choices"][0]["message"]["content"]
    uso = resp.get("usage") or {}
    meta = {"segundos": round(dt, 1), "tokens_entrada": uso.get("prompt_tokens"),
            "tokens_saida": uso.get("completion_tokens"), "modelo": MODELO}
    try:
        saida = extrair_json(conteudo)
        meta["json_valido"] = True
    except Exception:
        saida = {"_bruto": conteudo}
        meta["json_valido"] = False
    saida["_total_dividas_arrematante"] = total_dividas_arrematante(saida) if meta["json_valido"] else None
    return saida, meta


# ---------------------------------------------------------------------------
# Seleção da amostra: 1 lote por edital, estratificada por tipo de leilão
# ---------------------------------------------------------------------------
def carregar_lotes() -> pd.DataFrame:
    """Lê o dataset preparado na N1. Como nem todo edital tem nº de leilão na URL,
    a chave do edital (usada no cache) é o nº do leilão ou um hash da URL do PDF."""
    df = pd.read_csv(DATASET / "dataset_preparado.csv", dtype={"lote_id": str})
    df = df.dropna(subset=["edital_url"]).copy()
    df["leilao_id"] = [str(int(x)) if pd.notna(x) else "e" + hashlib.md5(u.encode()).hexdigest()[:8]
                       for x, u in zip(df["leilao_id"], df["edital_url"])]
    return df


def selecionar_amostra(df: pd.DataFrame, n: int, semente: int = 42) -> pd.DataFrame:
    uni = df.dropna(subset=["edital_url"]).drop_duplicates("edital_url")
    if n >= len(uni):
        return uni
    frac = n / len(uni)
    partes = [g.sample(max(1, round(len(g) * frac)), random_state=semente)
              for _, g in uni.groupby("tipo_leilao")]
    return pd.concat(partes).head(n)


def main() -> None:
    ap = argparse.ArgumentParser(description="Assistente de editais de leilão (LLM)")
    ap.add_argument("--amostra", type=int, default=30, help="nº de editais distintos")
    ap.add_argument("--lote", help="processa só este lote_id")
    ap.add_argument("--pdf", help="processa um PDF local (demonstração)")
    ap.add_argument("--refazer", action="store_true", help="ignora saídas já existentes")
    args = ap.parse_args()

    SAIDAS.mkdir(parents=True, exist_ok=True)
    DOSSIES.mkdir(parents=True, exist_ok=True)
    obter_chave()

    if args.pdf:  # modo demonstração: um PDF qualquer
        _, txt = texto_do_pdf_bytes(Path(args.pdf).read_bytes())
        lote = {"lote_id": Path(args.pdf).stem, "bairro": "-", "area_m2": "-", "url": "-"}
        saida, meta = analisar(txt, lote)
        (SAIDAS / f"{lote['lote_id']}.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
        (DOSSIES / f"{lote['lote_id']}.md").write_text(gerar_dossie(saida, lote), encoding="utf-8")
        print(gerar_dossie(saida, lote))
        return

    df = carregar_lotes()
    amostra = df[df["lote_id"] == args.lote] if args.lote else selecionar_amostra(df, args.amostra)
    amostra[["lote_id", "leilao_id", "tipo_leilao"]].to_csv(RESULT / "amostra.csv", index=False)
    print(f"Modelo inicial: {MODELO} | endpoint: {BASE_URL} | {len(amostra)} lotes")

    log_path = RESULT / "execucao_llm.csv"
    novo_log = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as flog:
        w = csv.DictWriter(flog, fieldnames=["lote_id", "leilao_id", "chars_edital", "segundos",
                                             "tokens_entrada", "tokens_saida", "modelo",
                                             "json_valido", "erro"])
        if novo_log:
            w.writeheader()
        for i, lote in enumerate(amostra.to_dict("records"), 1):
            lid = lote["lote_id"]
            destino = SAIDAS / f"{lid}.json"
            if destino.exists() and not args.refazer:
                print(f"[{i}/{len(amostra)}] {lid}: já processado (pulando)")
                continue
            linha = {"lote_id": lid, "leilao_id": lote["leilao_id"]}
            try:
                txt = obter_texto_edital(lote["leilao_id"], lote["edital_url"])
                linha["chars_edital"] = len(txt)
                saida, meta = analisar(txt, lote)
                linha.update(meta)
                destino.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
                if meta["json_valido"]:
                    (DOSSIES / f"{lid}.md").write_text(gerar_dossie(saida, lote), encoding="utf-8")
                print(f"[{i}/{len(amostra)}] {lid}: ok ({meta['segundos']}s, risco="
                      f"{(saida.get('risco') or {}).get('nivel')})")
            except Exception as e:  # registra e segue para o próximo lote
                linha["erro"] = str(e)[:300]
                print(f"[{i}/{len(amostra)}] {lid}: ERRO {e}")
                if "LLM_MODEL" in str(e):
                    w.writerow(linha)
                    break
            w.writerow(linha)
            flog.flush()
            time.sleep(PAUSA_S)
    print(f"\nPronto. Saídas em {SAIDAS} e dossiês em {DOSSIES}")


if __name__ == "__main__":
    main()
