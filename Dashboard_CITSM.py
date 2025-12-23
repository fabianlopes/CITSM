import streamlit as st
import pandas as pd
import conexao
import dashboards # Importa o módulo de gráficos interativos

# Configuração da Página Principal
st.set_page_config(page_title="Dashboard Operacional", layout="wide")

st.title("📊 Painel Operacional")
st.markdown("Use o menu lateral para ver as **Timelines** em outra página.")

# --- CARGA DE DADOS (Cacheada) ---
@st.cache_data(ttl=3600)
def carregar_dados():
    conn = conexao.conexao()
    try:
        return pd.read_sql("SELECT * FROM ODS_ITSM", conn)
    except Exception as e:
        st.error(f"Erro SQL: {e}")
        return pd.DataFrame()

df = carregar_dados()
if df.empty: st.stop()

# --- TRATAMENTO ---
for col in ['DTABERTURA', 'DTULTIMAMODIFICACAO', 'DTFIM']:
    if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce')

if 'DEMANDANTE' in df.columns: df['DEMANDANTE'] = df['DEMANDANTE'].astype(str).str.strip()
if 'STATUS' in df.columns: df['STATUS'] = df['STATUS'].astype(str).str.strip()

# --- FILTROS ---
st.sidebar.header("Filtros Dashboard")
lista_servicos = df['NOMESERVICO'].unique()
idx = next((i for i, s in enumerate(lista_servicos) if "Sustenta" in str(s)), 0)
servico_sel = st.sidebar.selectbox("Serviço:", lista_servicos, index=idx)

df_servico = df[df['NOMESERVICO'] == servico_sel]

# --- 1. CHAMADA DOS GRÁFICOS INTERATIVOS ---
filtro_dem, filtro_stat = dashboards.renderizar_paineis_interativos(df_servico)

# --- 2. TABELA FINAL ---
st.divider()
st.subheader("📋 Detalhamento dos Tickets")

df_final = df_servico.copy()

if filtro_dem:
    df_final = df_final[df_final['DEMANDANTE'] == filtro_dem]
if filtro_stat:
    df_final = df_final[df_final['STATUS'] == filtro_stat]

st.dataframe(df_final.sort_values('DTABERTURA', ascending=False).head(1000), use_container_width=True)