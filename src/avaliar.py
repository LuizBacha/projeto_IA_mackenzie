# -*- coding: utf-8 -*-
# ============================================================================
# avaliar.py — Avaliação do assistente LLM (N2)
# ----------------------------------------------------------------------------
# Projeto: Assistente de Leitura de Editais de Leilão de Imóveis com LLM
# Integrantes:
#   Luiz Eduardo Bacha dos Santos (RA 10425296) - 10425296@mackenzista.com.br
#   Guilherme Haddad Borro        (RA 10427699) - 10427699@mackenzista.com.br
# Conteúdo: compara as saídas do LLM com o texto do edital, com a linha de base
#           por regras e com os campos estruturados do site (referência
#           independente). Métricas:
#             1. Validade do JSON e tempo/tokens por chamada
#             2. Completude: % de campos preenchidos (LLM x regras)
#             3. Fidelidade (anti-alucinação): % de evidências literais achadas no
#                texto; % de valores em R$ que existem no texto; % de termos do
#                glossário presentes no edital
#             4. Concordância: tipo de leilão (LLM x regra da N1), avaliação
#                (LLM/regras x valor do site), comissão e ocupação (LLM x regras)
#             5. Legibilidade: Índice de Flesch adaptado ao português
#                (Martins et al., 1996) do edital x texto gerado
#           Gera resultados/metricas.json, tabelas CSV, figuras 08-11 e a
#           planilha de conferência manual (resultados/conferencia_manual.csv).
#
# Histórico de alterações:
#   2026-11-17 | Luiz Eduardo Bacha dos Santos  | criação da avaliação automática
#   2026-11-18 | Luiz Eduardo Bacha dos Santos  | Flesch: segmentação de frases corrigida
# ============================================================================
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
DATASET = RAIZ / "dataset"
TEXTOS = DATASET / "textos_editais"
RESULT = RAIZ / "resultados"
SAIDAS = RESULT / "saidas_llm"
FIG = RAIZ / "figuras"
AZUL, LARANJA, CINZA = "#2a6f97", "#e07a1f", "#8d99ae"


# ---------------------------------------------------------------- utilidades
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def evidencia_no_texto(evid: str | None, texto_norm: str) -> bool | None:
    """True se o trecho citado pelo modelo existe no edital (exato ou >=80% dos
    trigramas de palavras). None se o modelo não citou trecho."""
    if not evid or not str(evid).strip():
        return None
    q = norm(evid)
    if not q:
        return None
    if q in texto_norm:
        return True
    w = q.split()
    if len(w) < 4:
        return False
    tri = [" ".join(w[i:i + 3]) for i in range(len(w) - 2)]
    achados = sum(1 for t in tri if t in texto_norm)
    return achados / len(tri) >= 0.8


def valor_no_texto(v, texto: str) -> bool | None:
    """True se o número (em R$) aparece no edital em algum formato brasileiro."""
    if not isinstance(v, (int, float)) or v <= 0:
        return None
    br = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")  # 123.456,78
    inteiro = br.split(",")[0]
    cands = {br, br.replace(".", ""), inteiro + ",", f"{v:.2f}".replace(".", ",")}
    if v == int(v):
        cands.add(inteiro)
    sem_esp = texto.replace(" ", "")
    return any(c in sem_esp for c in cands)


def silabas(palavra: str) -> int:
    return max(1, len(re.findall(r"[aeiouáéíóúâêôãõàü]+", palavra.lower())))


def flesch_pt(texto: str) -> float | None:
    """Índice de Facilidade de Leitura de Flesch adaptado ao português
    (Martins et al., 1996): 248,835 - 1,015*(palavras/frase) - 84,6*(sílabas/palavra).
    Quanto MAIOR, mais fácil (75-100 muito fácil; 25-50 difícil; <25 muito difícil)."""
    # frase = trecho terminado em . ! ? seguido de maiúscula (";" e ":" não encerram frase:
    # contá-los como fim de frase inflava o índice dos editais, cheios de listas com ";")
    frases = [f for f in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý])", texto) if f.strip()]
    palavras = re.findall(r"[A-Za-zÀ-ÿ]+", texto)
    if not frases or len(palavras) < 20:
        return None
    asl = len(palavras) / len(frases)
    asw = sum(silabas(p) for p in palavras) / len(palavras)
    return round(248.835 - 1.015 * asl - 84.6 * asw, 1)


def preenchido(v) -> bool:
    if v is None or v == "" or v == [] or (isinstance(v, float) and pd.isna(v)):
        return False
    return str(v) not in ("Não informado", "nan", "None")


def texto_gerado(s: dict) -> str:
    partes = [s.get("resumo_leigo", ""), s.get("recomendacao", "")]
    for k in ("tipo_leilao", "ocupacao"):
        partes.append((s.get(k) or {}).get("explicacao", ""))
    partes += [d.get("explicacao", "") for d in s.get("dividas") or []]
    partes += [o.get("explicacao", "") for o in s.get("onus") or []]
    partes.append((s.get("pagamento") or {}).get("resumo", ""))
    return " ".join(p for p in partes if p)


# ---------------------------------------------------------------- avaliação
def main() -> None:
    FIG.mkdir(exist_ok=True)
    meta = pd.read_csv(DATASET / "dataset_preparado.csv", dtype={"lote_id": str})
    meta = meta.set_index("lote_id")
    base = (pd.read_csv(RESULT / "baseline_regras.csv", dtype={"lote_id": str}).set_index("lote_id")
            if (RESULT / "baseline_regras.csv").exists()
            and (RESULT / "baseline_regras.csv").stat().st_size > 20 else pd.DataFrame())
    log = (pd.read_csv(RESULT / "execucao_llm.csv", dtype={"lote_id": str})
           if (RESULT / "execucao_llm.csv").exists() else pd.DataFrame())
    amostra = pd.read_csv(RESULT / "amostra.csv", dtype=str)

    linhas, evid_reg, valor_reg, gloss_reg, conf = [], [], [], [], []
    for r in amostra.to_dict("records"):
        lid, leid = r["lote_id"], r["leilao_id"]
        fj, ft = SAIDAS / f"{lid}.json", TEXTOS / f"{leid}.txt"
        if not (fj.exists() and ft.exists()):
            continue
        s = json.loads(fj.read_text(encoding="utf-8"))
        if "_bruto" in s:
            linhas.append({"lote_id": lid, "json_valido": False})
            continue
        texto = ft.read_text(encoding="utf-8")
        tn = norm(texto)
        tl, oc = s.get("tipo_leilao") or {}, s.get("ocupacao") or {}
        va, co = s.get("valores") or {}, s.get("comissao_leiloeiro_pct") or {}
        pg, ri = s.get("pagamento") or {}, s.get("risco") or {}

        # --- fidelidade das evidências literais
        evids = [("tipo_leilao", tl.get("evidencia")), ("ocupacao", oc.get("evidencia")),
                 ("valores", va.get("evidencia")), ("comissao", co.get("evidencia")),
                 ("pagamento", pg.get("evidencia"))]
        evids += [("divida", d.get("evidencia")) for d in s.get("dividas") or []]
        evids += [("onus", o.get("evidencia")) for o in s.get("onus") or []]
        for campo, e in evids:
            ok = evidencia_no_texto(e, tn)
            if ok is not None:
                evid_reg.append({"lote_id": lid, "campo": campo, "encontrada": ok, "evidencia": e})
        # --- valores monetários existem no texto?
        vals = [("avaliacao", va.get("avaliacao")), ("lance_minimo_1", va.get("lance_minimo_1")),
                ("lance_minimo_2", va.get("lance_minimo_2"))]
        vals += [("divida", d.get("valor")) for d in s.get("dividas") or []]
        for campo, v in vals:
            ok = valor_no_texto(v, texto)
            if ok is not None:
                valor_reg.append({"lote_id": lid, "campo": campo, "valor": v, "encontrado": ok})
        # --- glossário ancorado no documento
        for g in s.get("glossario") or []:
            termo = norm(g.get("termo", ""))
            if termo:
                raiz = termo[: max(5, int(len(termo) * 0.7))]  # tolera plural/flexão
                gloss_reg.append({"lote_id": lid, "termo": g.get("termo"), "no_texto": raiz in tn})

        m = meta.loc[lid] if lid in meta.index else {}
        b = base.loc[lid] if lid in base.index else {}
        linha = {
            "lote_id": lid, "leilao_id": leid, "json_valido": True,
            "chars_edital": len(texto),
            "llm_tipo": tl.get("valor"), "n1_tipo": m.get("tipo_leilao") if len(m) else None,
            "llm_ocupacao": oc.get("valor"), "regra_ocupacao": b.get("ocupacao") if len(b) else None,
            "site_ocupacao": m.get("ocupacao") if len(m) else None,
            "llm_avaliacao": va.get("avaliacao"), "regra_avaliacao": b.get("avaliacao") if len(b) else None,
            "site_avaliacao": m.get("valor_avaliacao") if len(m) else None,
            "llm_lance1": va.get("lance_minimo_1"), "regra_lance1": b.get("lance_minimo_1") if len(b) else None,
            "llm_comissao": co.get("valor"), "regra_comissao": b.get("comissao_pct") if len(b) else None,
            "llm_n_dividas": len(s.get("dividas") or []),
            "llm_total_dividas_arrematante": s.get("_total_dividas_arrematante"),
            "llm_n_onus": len(s.get("onus") or []), "regra_n_onus": b.get("n_onus") if len(b) else None,
            "llm_parcelamento": pg.get("permite_parcelamento"),
            "llm_risco": ri.get("nivel"), "llm_n_glossario": len(s.get("glossario") or []),
            "regra_n_glossario": len(str(b.get("glossario", "")).split(";")) if len(b) and preenchido(b.get("glossario")) else 0,
            "flesch_edital": flesch_pt(texto[:30000]), "flesch_gerado": flesch_pt(texto_gerado(s)),
            "palavras_resumo": len(str(s.get("resumo_leigo", "")).split()),
        }
        linhas.append(linha)
        # --- planilha de conferência manual (o grupo marca S/N)
        for campo, valor, evid in [("tipo_leilao", tl.get("valor"), tl.get("evidencia")),
                                   ("ocupacao", oc.get("valor"), oc.get("evidencia")),
                                   ("avaliacao", va.get("avaliacao"), va.get("evidencia")),
                                   ("lance_minimo_1", va.get("lance_minimo_1"), va.get("evidencia")),
                                   ("comissao_pct", co.get("valor"), co.get("evidencia")),
                                   ("total_dividas_arrematante", s.get("_total_dividas_arrematante"), ""),
                                   ("risco", ri.get("nivel"), "; ".join(ri.get("motivos") or []))]:
            conf.append({"lote_id": lid, "campo": campo, "valor_llm": valor, "evidencia": evid,
                         "correto_S_N": "", "observacao": ""})

    df = pd.DataFrame(linhas)
    if df.empty:
        print("Nenhuma saída do LLM encontrada em resultados/saidas_llm. Rode antes o assistente.")
        return
    ok = df[df["json_valido"]].copy()
    ev, vr, gl = pd.DataFrame(evid_reg), pd.DataFrame(valor_reg), pd.DataFrame(gloss_reg)
    df.to_csv(RESULT / "tabela_lotes_llm.csv", index=False)
    ev.to_csv(RESULT / "fidelidade_evidencias.csv", index=False)
    vr.to_csv(RESULT / "fidelidade_valores.csv", index=False)
    pd.DataFrame(conf).to_csv(RESULT / "conferencia_manual.csv", index=False, encoding="utf-8-sig")

    # ---------------- métricas agregadas
    def pct(x):
        return round(100 * float(x), 1) if pd.notna(x) else None

    campos = {"Tipo de leilão": ("llm_tipo", "n1_tipo"), "Ocupação": ("llm_ocupacao", "regra_ocupacao"),
              "Avaliação (R$)": ("llm_avaliacao", "regra_avaliacao"),
              "Lance mínimo (R$)": ("llm_lance1", "regra_lance1"),
              "Comissão (%)": ("llm_comissao", "regra_comissao")}
    completude = {k: {"llm": pct(ok[a].map(preenchido).mean()), "regras": pct(ok[b].map(preenchido).mean())}
                  for k, (a, b) in campos.items()}

    def concord(a, b, tol=None):
        sub = ok[ok[a].map(preenchido) & ok[b].map(preenchido)]
        if sub.empty:
            return {"n": 0, "pct": None}
        if tol is None:
            iguais = (sub[a].astype(str) == sub[b].astype(str))
        else:
            iguais = ((sub[a].astype(float) - sub[b].astype(float)).abs()
                      <= tol * sub[b].astype(float).abs().clip(lower=1))
        return {"n": int(len(sub)), "pct": pct(iguais.mean())}

    site_ocup = ok[ok["site_ocupacao"].isin(["Ocupado", "Desocupado"])]
    met = {
        "modelo": str(log["modelo"].dropna().iloc[-1]) if not log.empty and log["modelo"].notna().any() else None,
        "lotes_processados": int(len(df)),
        "json_valido_pct": pct(df["json_valido"].mean()) if len(df) else None,
        "erros_execucao": int(log["erro"].notna().sum()) if "erro" in log else 0,
        "tempo_medio_s": round(float(log["segundos"].mean()), 1) if "segundos" in log and log["segundos"].notna().any() else None,
        "tokens_entrada_medio": int(log["tokens_entrada"].mean()) if "tokens_entrada" in log and log["tokens_entrada"].notna().any() else None,
        "tokens_saida_medio": int(log["tokens_saida"].mean()) if "tokens_saida" in log and log["tokens_saida"].notna().any() else None,
        "completude": completude,
        "fidelidade": {
            "evidencias_citadas": int(len(ev)),
            "evidencias_encontradas_pct": pct(ev["encontrada"].mean()) if len(ev) else None,
            "evidencias_por_campo_pct": (ev.groupby("campo")["encontrada"].mean().mul(100).round(1).to_dict() if len(ev) else {}),
            "valores_rs_citados": int(len(vr)),
            "valores_rs_encontrados_pct": pct(vr["encontrado"].mean()) if len(vr) else None,
            "glossario_termos": int(len(gl)),
            "glossario_no_texto_pct": pct(gl["no_texto"].mean()) if len(gl) else None,
        },
        "concordancia": {
            "tipo_llm_x_regra_n1": concord("llm_tipo", "n1_tipo"),
            "avaliacao_llm_x_site_1pct": concord("llm_avaliacao", "site_avaliacao", 0.01),
            "avaliacao_regras_x_site_1pct": concord("regra_avaliacao", "site_avaliacao", 0.01),
            "comissao_llm_x_regras": concord("llm_comissao", "regra_comissao", 0.001),
            "ocupacao_llm_x_regras": concord("llm_ocupacao", "regra_ocupacao"),
            "ocupacao_llm_x_site": {"n": int(len(site_ocup)),
                                    "pct": pct((site_ocup["llm_ocupacao"] == site_ocup["site_ocupacao"]).mean()) if len(site_ocup) else None},
        },
        "legibilidade_flesch": {
            "edital_mediana": float(ok["flesch_edital"].median()) if ok["flesch_edital"].notna().any() else None,
            "gerado_mediana": float(ok["flesch_gerado"].median()) if ok["flesch_gerado"].notna().any() else None,
        },
        "resumo_palavras_mediana": float(ok["palavras_resumo"].median()) if len(ok) else None,
        "risco": ok["llm_risco"].value_counts().to_dict(),
        "risco_por_tipo": pd.crosstab(ok["llm_tipo"], ok["llm_risco"]).to_dict() if len(ok) else {},
        "ocupacao_llm": ok["llm_ocupacao"].value_counts().to_dict(),
        "dividas_media_por_lote": round(float(ok["llm_n_dividas"].mean()), 2) if len(ok) else None,
        "onus_media_por_lote": round(float(ok["llm_n_onus"].mean()), 2) if len(ok) else None,
        "glossario_media_termos": round(float(ok["llm_n_glossario"].mean()), 1) if len(ok) else None,
    }
    (RESULT / "metricas.json").write_text(json.dumps(met, ensure_ascii=False, indent=2, default=str),
                                          encoding="utf-8")
    print(json.dumps(met, ensure_ascii=False, indent=2, default=str))

    if ok.empty:
        return
    # ---------------- figuras
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    # 08 completude
    fig, ax = plt.subplots(figsize=(7, 3.8))
    nomes = list(completude)
    y = range(len(nomes))
    ax.barh([i + 0.2 for i in y], [completude[n]["llm"] for n in nomes], 0.4, color=AZUL, label="LLM")
    ax.barh([i - 0.2 for i in y], [completude[n]["regras"] for n in nomes], 0.4, color=CINZA, label="Regras (regex)")
    ax.set_yticks(list(y), nomes)
    ax.set_xlabel("% dos lotes com o campo preenchido")
    ax.set_xlim(0, 105)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    ax.set_title("Completude da extração: LLM x linha de base por regras")
    fig.tight_layout()
    fig.savefig(FIG / "08_completude_llm_x_regras.png", dpi=150)
    plt.close(fig)
    # 09 fidelidade
    f = met["fidelidade"]
    rot = ["Evidências literais\nencontradas no edital", "Valores em R$\nencontrados no edital",
           "Termos do glossário\npresentes no edital"]
    vals = [f["evidencias_encontradas_pct"] or 0, f["valores_rs_encontrados_pct"] or 0,
            f["glossario_no_texto_pct"] or 0]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    b = ax.bar(rot, vals, color=[AZUL, AZUL, AZUL], width=0.55)
    ax.bar_label(b, fmt="%.1f%%")
    ax.set_ylim(0, 110)
    ax.set_ylabel("%")
    ax.set_title("Fidelidade ao documento (verificação automática anti-alucinação)")
    fig.tight_layout()
    fig.savefig(FIG / "09_fidelidade.png", dpi=150)
    plt.close(fig)
    # 10 legibilidade
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    dados = [ok["flesch_edital"].dropna(), ok["flesch_gerado"].dropna()]
    try:
        ax.boxplot(dados, orientation="horizontal", widths=0.5)
    except TypeError:  # matplotlib < 3.10
        ax.boxplot(dados, vert=False, widths=0.5)
    ax.set_yticks([1, 2], ["Texto do edital", "Explicação gerada"])
    ax.axvspan(50, 75, color=LARANJA, alpha=0.08)
    ax.set_xlabel("Índice de Flesch (PT) — maior = mais fácil")
    ax.set_title("Legibilidade: edital original x explicação do assistente")
    fig.tight_layout()
    fig.savefig(FIG / "10_legibilidade.png", dpi=150)
    plt.close(fig)
    # 11 risco
    ct = pd.crosstab(ok["llm_tipo"], ok["llm_risco"]).reindex(columns=["Baixo", "Médio", "Alto"], fill_value=0)
    fig, ax = plt.subplots(figsize=(6.5, 3))
    ct.plot(kind="barh", stacked=True, ax=ax, color=["#6a994e", "#f2c14e", "#bc4749"])
    ax.set_xlabel("nº de lotes")
    ax.set_ylabel("")
    ax.legend(title="Risco (LLM)", frameon=False, bbox_to_anchor=(1, 1))
    ax.set_title("Nível de risco atribuído pelo assistente, por tipo de leilão")
    fig.tight_layout()
    fig.savefig(FIG / "11_risco_por_tipo.png", dpi=150)
    plt.close(fig)
    print(f"\nFiguras 08-11 salvas em {FIG}")


if __name__ == "__main__":
    main()
