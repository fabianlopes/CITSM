import streamlit as st
import pandas as pd
import conexao
import dashboards
import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Dashboard Operacional", layout="wide")
st.title("📊 Painel Operacional")

# ========================================================
# ⚙️ CONFIGURAÇÃO ATUALIZADA
# ========================================================
NOME_COLUNA_CONTRATO = "NUMEROCONTRATO"
# ========================================================

# --- CARGA DE DADOS ---
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

# --- VERIFICAÇÃO DE SEGURANÇA ---
if NOME_COLUNA_CONTRATO not in df.columns:
    st.error(f"⚠️ A coluna '{NOME_COLUNA_CONTRATO}' não existe! Verifique se está escrita corretamente.")
    st.stop()

# --- TRATAMENTO ---
cols_data = ['DTABERTURA', 'DTULTIMAMODIFICACAO', 'DTFIM']
for col in cols_data:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

# Garante strings limpas (IMPORTANTE PARA O CONTRATO)
cols_texto = ['DEMANDANTE', 'STATUS', 'NOMESERVICO', NOME_COLUNA_CONTRATO]
for col in cols_texto:
    if col in df.columns:
        # Converte para string e remove espaços (.0 se for número)
        df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

# ==========================================
# 🔻 FILTROS EM CASCATA (LINHARES) 🔻
# ==========================================
st.sidebar.header("🔍 Filtros")

# --- 1. DATA (Primeiro filtro) ---
min_date = df['DTABERTURA'].min().date()
max_date = df['DTABERTURA'].max().date()

periodo = st.sidebar.date_input("1. Período:", (min_date, max_date), min_value=min_date, max_value=max_date)

if isinstance(periodo, tuple) and len(periodo) == 2:
    inicio, fim = periodo
    df_etapa1 = df[(df['DTABERTURA'].dt.date >= inicio) & (df['DTABERTURA'].dt.date <= fim)]
else:
    df_etapa1 = df.copy()

if df_etapa1.empty:
    st.warning("Sem dados neste período.")
    st.stop()

# --- 2. CONTRATO (Agora é Selectbox único) ---
# Pega apenas contratos que existem na data filtrada
opcoes_contratos = sorted(df_etapa1[NOME_COLUNA_CONTRATO].unique())

contrato_sel = st.sidebar.selectbox(
    "2. Contrato:",
    options=opcoes_contratos
)

# Filtra para o próximo passo
df_etapa2 = df_etapa1[df_etapa1[NOME_COLUNA_CONTRATO] == contrato_sel]

# --- 3. SERVIÇO (Depende do Contrato) ---
# Pega apenas serviços que existem no contrato selecionado
opcoes_servicos = sorted(df_etapa2['NOMESERVICO'].unique())

# Tenta deixar 'Sustenta' selecionado se existir na lista
idx_serv = next((i for i, s in enumerate(opcoes_servicos) if "Sustenta" in str(s)), 0)

servico_sel = st.sidebar.selectbox(
    "3. Serviço:",
    opcoes_servicos,
    index=idx_serv
)

# Filtro Final
df_final = df_etapa2[df_etapa2['NOMESERVICO'] == servico_sel]

# ==========================================
# 📊 VISUALIZAÇÃO
# ==========================================
st.markdown(f"**Contrato:** {contrato_sel} | **Serviço:** {servico_sel} | **Chamados:** {len(df_final)}")
st.divider()

if df_final.empty:
    st.warning("Nenhum registro encontrado.")
    st.stop()

# Gráficos
filtro_dem, filtro_stat = dashboards.renderizar_paineis_interativos(df_final)

# Tabela Detalhada
st.subheader("📋 Detalhamento")
df_tabela = df_final.copy()

# Cross-filtering dos gráficos
if filtro_dem: df_tabela = df_tabela[df_tabela['DEMANDANTE'] == filtro_dem]
if filtro_stat: df_tabela = df_tabela[df_tabela['STATUS'] == filtro_stat]

# Colunas para exibir
cols_view = [c for c in ['TICKET_PRINCIPAL', 'DTABERTURA', 'STATUS', 'DEMANDANTE', NOME_COLUNA_CONTRATO, 'SUMMARY'] if c in df_tabela.columns]

st.dataframe(df_tabela[cols_view].sort_values('DTABERTURA', ascending=False).head(500), use_container_width=True)