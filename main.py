import streamlit as st
import pandas as pd
import conexao
import plotly.express as px

# Aplicando css na página
def apply_custom_css(css_file):
    with open(css_file) as f:
        css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

apply_custom_css("style.css")

# Título da página
st.title("texto subti", text_alignment="center")

# Criando o menu principal com os itens
mainContainer = st.container()

with mainContainer:
    st.markdown('<div class="mainContainer"></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3, gap="large")

    with col1:
        st.image("static/dash-op.jpg")
        st.link_button("Dash. Operacional", "www.google.com", type="secondary")

    with col2:
        st.image("static/dash-ia.jpg")
        st.link_button("Dash. de IA", "www.google.com", type="secondary")
    
    with col3:
        st.image("static/dash-resumo.jpg")
        st.link_button("Dash. de Resumo", "www.google.com", type="secondary") 
