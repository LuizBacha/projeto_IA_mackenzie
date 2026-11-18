# -*- coding: utf-8 -*-
# ============================================================================
# app.py — Interface de demonstração (Streamlit) do assistente de editais
# ----------------------------------------------------------------------------
# Integrantes:
#   Luiz Eduardo Bacha dos Santos (RA 10425296) - 10425296@mackenzista.com.br
#   Guilherme Haddad Borro        (RA 10427699) - 10427699@mackenzista.com.br
# Conteúdo: o usuário envia o PDF de um edital e recebe o dossiê em linguagem
#           simples; também permite navegar pelos dossiês já gerados na amostra.
#           Uso:  pip install streamlit  &&  streamlit run app.py
#
# Histórico de alterações:
#   2026-11-17 | Luiz Eduardo Bacha dos Santos  | criação da interface
# ============================================================================
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
import assistente_edital as A  # noqa: E402

st.set_page_config(page_title="Assistente de Editais de Leilão", page_icon="🏠")
st.title("Assistente de Leitura de Editais de Leilão")
st.caption("Ferramenta de apoio à leitura. Não é aconselhamento jurídico.")

aba1, aba2 = st.tabs(["Analisar um edital (PDF)", "Dossiês da amostra"])
with aba1:
    pdf = st.file_uploader("Edital do leilão (PDF)", type="pdf")
    ident = st.text_input("Qual lote? (bairro, área, nº do lote — opcional)")
    if pdf and st.button("Analisar"):
        _, texto = A.texto_do_pdf_bytes(pdf.read())
        lote = {"lote_id": Path(pdf.name).stem, "bairro": ident or "-", "area_m2": "-", "url": "-"}
        with st.spinner("Lendo o edital com o LLM..."):
            saida, meta = A.analisar(texto, lote)
        st.markdown(A.gerar_dossie(saida, lote))
        st.caption(f"{len(texto):,} caracteres lidos | {meta['segundos']} s | modelo {meta['modelo']}")
        with st.expander("Resposta estruturada (JSON)"):
            st.json(saida)
with aba2:
    arquivos = sorted(A.DOSSIES.glob("*.md"))
    if not arquivos:
        st.info("Rode primeiro: python src/assistente_edital.py --amostra 30")
    else:
        esc = st.selectbox("Lote", arquivos, format_func=lambda p: p.stem)
        st.markdown(esc.read_text(encoding="utf-8"))
