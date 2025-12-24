import streamlit as st
import pandas as pd
import conexao
import timelines
import timelines

st.set_page_config(page_title="Timelines", layout="wide")

st.title("⏳ Análise Temporal e Backlog")

# --- REUTILIZAÇÃO DA CARGA DE DADOS ---
# O cache faz com que o Python não precise ir no banco de novo
@st.cache_data(ttl=3600)
def carregar_dados():
    conn = conexao.conexao()
    try:
        return pd.read_sql("SELECT * FROM ODS_ITSM", conn)
    except Exception as e:
        return pd.DataFrame()

df = carregar_dados()
if df.empty: st.stop()

# --- TRATAMENTO ---
for col in ['DTABERTURA', 'DTULTIMAMODIFICACAO', 'DTFIM']:
    if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce')
if 'DEMANDANTE' in df.columns: df['DEMANDANTE'] = df['DEMANDANTE'].astype(str).str.strip()

# --- FILTROS (Independente da outra página) ---
st.sidebar.header("Filtros Timelines")
lista_servicos = df['NOMESERVICO'].unique()
idx = next((i for i, s in enumerate(lista_servicos) if "Sustenta" in str(s)), 0)
servico_sel = st.sidebar.selectbox("Serviço Analisado:", lista_servicos, index=idx)

df_servico = df[df['NOMESERVICO'] == servico_sel]

# --- CHAMADA DO MÓDULO DE TIMELINES ---
timelines.renderizar_timelines(df_servico)