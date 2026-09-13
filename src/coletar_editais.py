# -*- coding: utf-8 -*-
# ============================================================================
# coletar_editais.py — Coleta do corpus de editais de leilão de imóveis (SP)
# ----------------------------------------------------------------------------
# Projeto: Análise de Editais de Leilão com LLM (Disciplina de IA — FCI Mackenzie)
# Conteúdo: percorre a vitrine pública do Mega Leilões (apartamentos/SP/São Paulo),
#           coleta a página de cada lote, baixa o EDITAL (por leilão) e a MATRÍCULA
#           (por lote), extrai o texto (PyMuPDF) e monta um metadata.csv com os
#           atributos usados na análise exploratória.
#           Fonte 100% server-side: coleta via HTTP (requests), sem navegador.
#
# Histórico de alterações:
#   2026-09-13 | Guilherme Haddad Borro | criação do coletor (listagem+detalhe+PDF)
# ============================================================================
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import time
from pathlib import Path

import fitz  # PyMuPDF
import requests

BASE = "https://www.megaleiloes.com.br/imoveis/apartamentos/sp/sao-paulo"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}

RAIZ = Path(__file__).resolve().parents[1]
DATASET = RAIZ / "dataset"
TXT_EDITAL = DATASET / "textos_editais"
TXT_MATRIC = DATASET / "textos_matriculas"

# Termos jurídicos/técnicos relevantes para caracterizar o corpus (análise de risco)
TERMOS = {
    "hipoteca": r"\bhipotec",
    "penhora": r"\bpenhor",
    "usufruto": r"\busufrut",
    "alienacao_fiduciaria": r"aliena[çc][ãa]o fiduci",
    "iptu": r"\bIPTU\b",
    "condominio": r"condom[íi]nio",
    "divida_ativa": r"d[íi]vida ativa",
    "financiamento": r"financiament",
    "comissao_leiloeiro": r"comiss[ãa]o",
    "debito": r"\bd[ée]bito",
    "ocupado": r"\bocupad",
}


def get(url: str, timeout: int = 30) -> str:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def links_dos_lotes(pagina: int) -> list[str]:
    """URLs de detalhe (card-title) de uma página da vitrine."""
    url = BASE if pagina == 1 else f"{BASE}?pagina={pagina}"
    html = get(url)
    brutos = re.findall(r'class="card-title"[^>]*href="([^"]+)"', html)
    # remove querystring de tracking e deduplica preservando ordem
    limpos = [h.split("?")[0] for h in brutos]
    return list(dict.fromkeys(limpos))


def pdf_texto(url: str, cache: dict[str, tuple[int, str]]) -> tuple[int, str]:
    """Baixa um PDF e devolve (n_paginas, texto). Cacheia por URL (editais são
    compartilhados entre lotes do mesmo leilão)."""
    if url in cache:
        return cache[url]
    try:
        data = requests.get(url, headers=HEADERS, timeout=90).content
        doc = fitz.open(stream=data, filetype="pdf")
        n = doc.page_count
        txt = re.sub(r"\s+", " ", " ".join(p.get_text() for p in doc)).strip()
        cache[url] = (n, txt)
        return n, txt
    except Exception:
        cache[url] = (0, "")
        return 0, ""


def achar_pdfs(html: str) -> dict[str, str | None]:
    pdfs = list(dict.fromkeys(re.findall(r'https://[^\s"\'<>]+\.pdf', html)))
    out = {"edital": None, "matricula": None}
    for p in pdfs:
        low = p.lower()
        if "megaleiloes" not in low:
            continue
        if "edital" in low and not out["edital"]:
            out["edital"] = p
        elif "matricula" in low and not out["matricula"]:
            out["matricula"] = p
    return out


def campo_detalhe(html_text: str) -> dict:
    """Ocupação, avaliação e SQL cadastral a partir do texto da página."""
    flat = re.sub(r"\s+", " ", html_text)
    out = {"ocupacao": "Não informado", "valor_avaliacao": None, "tem_sql": False}
    m = re.search(r",\s*(Ocupad[oa]|Desocupad[oa]|Desabitad[oa]|Livre)\b", flat, re.I)
    if m:
        v = m.group(1).lower()
        out["ocupacao"] = "Desocupado" if v.startswith(("deso", "desa", "livr")) else "Ocupado"
    m = re.search(r"Valor de Avalia[çc][ãa]o\s*R\$\s*([\d.]+,\d{2})", flat)
    if m:
        val = float(m.group(1).replace(".", "").replace(",", "."))
        out["valor_avaliacao"] = val if val > 0 else None
    out["tem_sql"] = bool(re.search(r"\b\d{3}\.\d{3}\.\d{4}-\d\b", flat))
    return out


def tipo_leilao(texto_edital: str) -> str:
    t = texto_edital.lower()
    if "extrajudicial" in t or re.search(r"lei\s*n?[ºo.]*\s*9\.?514", t):
        return "Extrajudicial"
    if any(k in t for k in ("judicial", "processo n", "vara ", "exequente", "executad")):
        return "Judicial"
    return "Não informado"


def area_do_titulo(url: str) -> float | None:
    m = re.search(r"apartamento-(\d+)-m2", url)
    return float(m.group(1)) if m else None


def bairro_do_titulo(url: str) -> str:
    # .../sp/sao-paulo/apartamento-75-m2-na-av-paulista-bela-vista-sao-paulo-sp-x128917
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"-sao-paulo-sp-x\d+$", "", slug)
    m = re.search(r"-([a-z]+(?:-[a-z]+){0,2})$", slug)
    return m.group(1).replace("-", " ").title() if m else "São Paulo"


def id_lote(url: str) -> str:
    m = re.search(r"x(\d+)$", url)
    return m.group(1) if m else hashlib.md5(url.encode()).hexdigest()[:8]


def id_leilao(edital_url: str | None) -> str | None:
    if not edital_url:
        return None
    m = re.search(r"/auctions/(\d+)/", edital_url) or re.search(r"ML(\d+)", edital_url)
    return m.group(1) if m else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paginas", type=int, default=4, help="nº de páginas da vitrine")
    ap.add_argument("--max-lotes", type=int, default=200)
    ap.add_argument("--salvar-textos", action="store_true",
                    help="grava os textos extraídos em dataset/textos_* (gitignored)")
    args = ap.parse_args()

    TXT_EDITAL.mkdir(parents=True, exist_ok=True)
    TXT_MATRIC.mkdir(parents=True, exist_ok=True)

    detalhe_urls: list[str] = []
    for pg in range(1, args.paginas + 1):
        try:
            novos = links_dos_lotes(pg)
        except Exception as e:
            print(f"  página {pg}: erro {e}")
            break
        antes = len(detalhe_urls)
        detalhe_urls += [u for u in novos if u not in detalhe_urls]
        print(f"  página {pg}: +{len(detalhe_urls) - antes} lotes (total {len(detalhe_urls)})")
        if not novos or len(detalhe_urls) >= args.max_lotes:
            break
        time.sleep(0.8)
    detalhe_urls = detalhe_urls[: args.max_lotes]

    cache_pdf: dict[str, tuple[int, str]] = {}
    linhas: list[dict] = []
    for i, url in enumerate(detalhe_urls, 1):
        try:
            html = get(url)
        except Exception as e:
            print(f"  [{i}] falha ao abrir lote: {e}")
            continue

        pdfs = achar_pdfs(html)
        det = campo_detalhe(html)
        e_pag, e_txt = pdf_texto(pdfs["edital"], cache_pdf) if pdfs["edital"] else (0, "")
        m_pag, m_txt = pdf_texto(pdfs["matricula"], cache_pdf) if pdfs["matricula"] else (0, "")

        lid = id_lote(url)
        linha = {
            "lote_id": lid,
            "leilao_id": id_leilao(pdfs["edital"]),
            "bairro": bairro_do_titulo(url),
            "area_m2": area_do_titulo(url),
            "ocupacao": det["ocupacao"],
            "valor_avaliacao": det["valor_avaliacao"],
            "tem_sql_cadastral": det["tem_sql"],
            "tem_edital": bool(pdfs["edital"]),
            "tem_matricula": bool(pdfs["matricula"]),
            "edital_paginas": e_pag,
            "edital_chars": len(e_txt),
            "matricula_paginas": m_pag,
            "matricula_chars": len(m_txt),
            "tipo_leilao": tipo_leilao(e_txt) if e_txt else "Não informado",
            "url": url,
            "edital_url": pdfs["edital"],
        }
        # flags de termos jurídicos no edital (corpus de risco)
        for nome, pat in TERMOS.items():
            linha[f"termo_{nome}"] = bool(re.search(pat, e_txt, re.I)) if e_txt else False
        linhas.append(linha)

        if args.salvar_textos:
            if e_txt:
                (TXT_EDITAL / f"{lid}.txt").write_text(e_txt, encoding="utf-8")
            if m_txt:
                (TXT_MATRIC / f"{lid}.txt").write_text(m_txt, encoding="utf-8")

        print(f"  [{i}/{len(detalhe_urls)}] lote {lid} | edital={e_pag}p "
              f"matricula={m_pag}p | {linha['tipo_leilao']}")
        time.sleep(0.4)

    saida = DATASET / "metadata.csv"
    if linhas:
        campos = list(linhas[0].keys())
        with saida.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos)
            w.writeheader()
            w.writerows(linhas)
    print(f"\nOK: {len(linhas)} lotes | {len({l['edital_url'] for l in linhas if l['edital_url']})} "
          f"editais únicos -> {saida}")


if __name__ == "__main__":
    main()
