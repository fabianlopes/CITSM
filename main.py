import streamlit as st
import conexao

# Aplicando css na página
def apply_custom_css(css_file):
    with open(css_file) as f:
        css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

apply_custom_css("style.css")

logoImg = st.image("assets/logo_pmm.png")

# Título da página
st.title("Dashboard CITSM", text_alignment="center")

# Botão Iniciar
st.page_link("pages/Dashboard_CITSM.py", label="Acessar Dashboard")