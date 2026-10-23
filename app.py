"""
Versão web do Prospector (Streamlit), pensada para uso no celular.
Precisa estar na mesma pasta que o prospector.py.
"""

import os
from urllib.parse import quote

import anthropic
import streamlit as st

# Copia as chaves dos "Secrets" do Streamlit para variáveis de ambiente
try:
    for chave in ("GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "APP_PASSWORD"):
        if chave in st.secrets:
            os.environ[chave] = st.secrets[chave]
except Exception:
    pass

import prospector as p  # noqa: E402

st.set_page_config(page_title="Prospector de sites", page_icon="🔎", layout="centered")
st.title("🔎 Prospector de sites")
st.caption("Acha comércios sem site e gera o prompt do site + mensagem de WhatsApp.")

# Trava simples por senha, para ninguém gastar suas APIs
senha_correta = os.environ.get("APP_PASSWORD")
if senha_correta:
    senha = st.text_input("Senha de acesso", type="password")
    if senha != senha_correta:
        st.stop()

faltando = [v for v in ("GOOGLE_API_KEY", "ANTHROPIC_API_KEY") if v not in os.environ]
if faltando:
    st.error("Faltam chaves nos Secrets: " + ", ".join(faltando))
    st.stop()

categoria = st.text_input("Categoria", placeholder="padaria, barbearia, oficina...")
cidade = st.text_input("Cidade", placeholder="Marília SP")
maximo = st.slider("Quantos leads gerar", min_value=1, max_value=10, value=3)

if st.button("Buscar e gerar", type="primary", use_container_width=True):
    if not categoria.strip() or not cidade.strip():
        st.warning("Preencha categoria e cidade.")
    else:
        with st.spinner("Buscando no Google..."):
            lugares = p.buscar_lugares(categoria.strip(), cidade.strip(), 1)
        leads = [l for l in lugares if p.sem_site_proprio(l)][:maximo]
        st.write(f"{len(lugares)} encontrados, {len(leads)} sem site próprio.")

        cliente = anthropic.Anthropic()
        resultados = []
        barra = st.progress(0.0)
        for i, lugar in enumerate(leads, start=1):
            nome = lugar.get("displayName", {}).get("text", "")
            try:
                prompt = p.gerar_prompt_site(cliente, lugar, cidade.strip())
                mensagem = p.gerar_mensagem_whatsapp(cliente, lugar, cidade.strip())
            except Exception as erro:
                prompt, mensagem = "", f"Falhou: {erro}"
            resultados.append({
                "nome": nome,
                "telefone": lugar.get("nationalPhoneNumber", ""),
                "whatsapp": p.link_whatsapp(lugar.get("internationalPhoneNumber", "")),
                "nota": lugar.get("rating", "-"),
                "avaliacoes": lugar.get("userRatingCount", 0),
                "maps": lugar.get("googleMapsUri", ""),
                "prompt": prompt,
                "mensagem": mensagem,
            })
            barra.progress(i / max(len(leads), 1))
        st.session_state["resultados"] = resultados

for r in st.session_state.get("resultados", []):
    with st.expander(f"{r['nome']}  ⭐ {r['nota']} ({r['avaliacoes']})"):
        st.write(f"📞 {r['telefone'] or 'sem telefone'}")
        if r["maps"]:
            st.link_button("Ver no Google Maps", r["maps"])
        st.markdown("**Mensagem de WhatsApp**")
        st.code(r["mensagem"], language=None, wrap_lines=True)
        if r["whatsapp"] and r["mensagem"]:
            st.link_button(
                "Abrir conversa no WhatsApp",
                f"{r['whatsapp']}?text={quote(r['mensagem'])}",
            )
        st.markdown("**Prompt para criar o site**")
        st.code(r["prompt"], language=None, wrap_lines=True)
