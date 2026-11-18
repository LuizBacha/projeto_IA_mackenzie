# -*- coding: utf-8 -*-
# ============================================================================
# baseline_regras.py — Linha de base (sem IA) com regras/expressões regulares
# ----------------------------------------------------------------------------
# Projeto: Assistente de Leitura de Editais de Leilão de Imóveis com LLM
# Integrantes:
#   Luiz Eduardo Bacha dos Santos (RA 10425296) - 10425296@mackenzista.com.br
#   Guilherme Haddad Borro        (RA 10427699) - 10427699@mackenzista.com.br
# Conteúdo: extrai do texto do edital os MESMOS campos do assistente LLM usando
#           apenas regras fixas (regex). Serve de comparação: mostra o que dá para
#           obter sem IA e onde as regras falham (texto variado, vários lotes no
#           mesmo edital, valores sem rótulo padronizado).
#           Saída: resultados/baseline_regras.csv
#
# Histórico de alterações:
#   2026-11-17 | Luiz Eduardo Bacha dos Santos  | criação da linha de base
# ============================================================================
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
TEXTOS = RAIZ / "dataset" / "textos_editais"
RESULT = RAIZ / "resultados"

# Mesmos termos do glossário que o LLM costuma explicar
GLOSSARIO_FIXO = {
    "alienação fiduciária": r"aliena[çc][ãa]o fiduci",
    "arrematante": r"arrematante",
    "hipoteca": r"hipotec",
    "penhora": r"\bpenhor",
    "usufruto": r"usufrut",
    "IPTU": r"\bIPTU\b",
    "condomínio": r"condom[íi]nio",
    "dívida ativa": r"d[íi]vida ativa",
    "comissão do leiloeiro": r"comiss[ãa]o",
    "praça/leilão": r"\b(pra[çc]a|1º leil[ãa]o|primeiro leil[ãa]o)",
    "imissão na posse": r"imiss[ãa]o (na|de) posse",
    "ITBI": r"\bITBI\b",
    "matrícula": r"matr[íi]cula",
    "ônus": r"[ôo]nus",
}


def br_para_float(s: str) -> float | None:
    try:
        return float(s.replace(".", "").replace(",", "."))
    except Exception:
        return None


def extrair(texto: str) -> dict:
    t = texto
    low = t.lower()
    out: dict = {}
    # tipo de leilão (mesma regra da N1)
    if "extrajudicial" in low or re.search(r"lei\s*n?[ºo.]*\s*9\.?514", low):
        out["tipo_leilao"] = "Extrajudicial"
    elif any(k in low for k in ("judicial", "processo n", "vara ", "exequente", "executad")):
        out["tipo_leilao"] = "Judicial"
    else:
        out["tipo_leilao"] = "Não informado"
    # ocupação: procura frases explícitas
    if re.search(r"\b(encontra-se|est[áa]|im[óo]vel)\s+(desocupad|livre)", low):
        out["ocupacao"] = "Desocupado"
    elif re.search(r"\b(encontra-se|est[áa]|im[óo]vel)\s+ocupad", low):
        out["ocupacao"] = "Ocupado"
    else:
        out["ocupacao"] = "Não informado"
    # avaliação: "avaliação ... R$ 123.456,78"
    m = re.search(r"avalia[çc][ãa]o[^R]{0,80}R\$\s*([\d.]+,\d{2})", t, re.I)
    out["avaliacao"] = br_para_float(m.group(1)) if m else None
    # lance mínimo: primeira ocorrência de "lance mínimo ... R$"
    m = re.search(r"lance m[íi]nimo[^R]{0,80}R\$\s*([\d.]+,\d{2})", t, re.I)
    out["lance_minimo_1"] = br_para_float(m.group(1)) if m else None
    # comissão do leiloeiro em %
    m = re.search(r"comiss[ãa]o[^%]{0,120}?(\d{1,2}(?:,\d+)?)\s*%", t, re.I)
    out["comissao_pct"] = br_para_float(m.group(1)) if m else None
    # débitos por conta do arrematante (só detecta a cláusula, não o valor)
    out["debitos_arrematante"] = bool(re.search(
        r"(por conta|[àa] cargo|responsabilidade)\s+(exclusiva\s+)?do\s+arrematante", low))
    # ônus mencionados
    onus = [n for n, p in {"Hipoteca": r"hipotec", "Penhora": r"\bpenhor",
                           "Alienação fiduciária": r"aliena[çc][ãa]o fiduci",
                           "Usufruto": r"usufrut"}.items() if re.search(p, low)]
    out["onus"] = ";".join(onus)
    out["n_onus"] = len(onus)
    out["parcelamento"] = bool(re.search(r"parcelad|parcelament", low))
    out["glossario"] = ";".join(k for k, p in GLOSSARIO_FIXO.items() if re.search(p, t, re.I))
    return out


def main() -> None:
    amostra = pd.read_csv(RESULT / "amostra.csv", dtype=str)
    linhas = []
    for r in amostra.to_dict("records"):
        f = TEXTOS / f"{r['leilao_id']}.txt"
        if not f.exists():
            continue
        linhas.append({"lote_id": r["lote_id"], "leilao_id": r["leilao_id"],
                       **extrair(f.read_text(encoding="utf-8"))})
    df = pd.DataFrame(linhas)
    df.to_csv(RESULT / "baseline_regras.csv", index=False)
    print(f"Baseline: {len(df)} lotes -> {RESULT / 'baseline_regras.csv'}")


if __name__ == "__main__":
    main()
