import streamlit as st
import pandas as pd
import conexao
import plotly.express as px
from datetime import datetime

st.set_page_config(layout="wide", page_title="Dashboard CITSM")
st.title("Dashboard Operacional")

@st.cache_data(ttl=3600)
def carregar_dados():
    conn = conexao.conexao()
    # Query pode ser otimizada
    query = """
            SELECT * FROM ODS_ITSM
            WHERE TO_DATE(DTABERTURA, 'YYYY-MM-DD') >= TO_DATE('2024-01-01', 'YYYY-MM-DD') \
            """
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Erro ao conectar ou executar query: {e}")
        return pd.DataFrame()
df = carregar_dados()
if df.empty:
    st.warning("Nenhum dado retornado do banco.")
    st.stop()


cols_data = ['DTABERTURA', 'DTULTIMAMODIFICACAO', 'DTFIM']
for col in cols_data:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')
coluna_filtro_ano = 'DTABERTURA'

st.sidebar.header("Filtros")
filtrar_ano = st.sidebar.checkbox('📅 Apenas Ano Atual (filtrado por 2025 para melhorar performance em fase de teste)', value=True)

if filtrar_ano:
    ano_atual = datetime.now().year
    if coluna_filtro_ano in df.columns:
        df = df[df[coluna_filtro_ano].dt.year == ano_atual]
        st.toast(f"Filtrado: {len(df)} registros de {ano_atual}", icon="📆")

if 'NOMESERVICO' in df.columns:
    lista_servicos = df['NOMESERVICO'].unique()
else:
    st.error("Coluna NOMESERVICO não encontrada.")
    st.stop()

index_padrao = 0
for i, servico in enumerate(lista_servicos):
    if "Sustenta" in str(servico):
        index_padrao = i
        break

servico_selecionado = st.sidebar.selectbox(
    "Selecione o Serviço:",
    lista_servicos,
    index=index_padrao
)

df_servico = df[df['NOMESERVICO'] == servico_selecionado]

total_registros = len(df_servico)
top_demandantes = df_servico['DEMANDANTE'].value_counts().head(10).reset_index()
distribuicao_status = df_servico['STATUS'].value_counts().reset_index()

st.divider()
st.markdown(f"### 🎯 Visão Geral: **{servico_selecionado}**")

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Total de Tickets", total_registros)
kpi2.metric("Principal Demandante", top_demandantes.iloc[0]['DEMANDANTE'] if not top_demandantes.empty else "-")
kpi3.metric("Status Predominante", distribuicao_status.iloc[0]['STATUS'] if not distribuicao_status.empty else "-")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Quem mais solicita?")
    if not top_demandantes.empty:
        fig_bar = px.bar(top_demandantes, x='count', y='DEMANDANTE', orientation='h',
                         title="Top 10 Demandantes", text='count')
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sem dados.")

with col2:
    st.subheader("Situação Geral")
    if not distribuicao_status.empty:
        fig_pie = px.pie(distribuicao_status, values='count', names='STATUS', hole=0.4,
                         title="Distribuição por Status")
        fig_pie.update_traces(textinfo='percent+value')
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Sem dados.")

st.divider()
st.subheader("📋 Detalhamento dos Tickets")
st.markdown("Utilize os filtros abaixo para localizar tickets específicos dentro deste serviço.")

col_filtro1, col_filtro2 = st.columns(2)

lista_demandantes_servico = ['Todos'] + list(df_servico['DEMANDANTE'].unique())
with col_filtro1:
    filtro_demandante = st.selectbox("1. Filtrar Demandante:", lista_demandantes_servico)

lista_status = df_servico['STATUS'].unique()
padrao_status = [s for s in lista_status if 'Andamento' in str(s)]
with col_filtro2:
    filtro_status = st.multiselect(
        "2. Filtrar Status:",
        options=lista_status,
        default=padrao_status if padrao_status else lista_status
    )

df_tabela = df_servico.copy()

if filtro_demandante != 'Todos':
    df_tabela = df_tabela[df_tabela['DEMANDANTE'] == filtro_demandante]

if filtro_status:
    df_tabela = df_tabela[df_tabela['STATUS'].isin(filtro_status)]

st.info(f"Listando **{len(df_tabela)}** tickets de **{servico_selecionado}** para **{filtro_demandante}**.")

if len(df_tabela) > 1000:
    st.warning(f"A lista é muito grande. Mostrando os 1000 registros mais recentes.")
    if 'DTABERTURA' in df_tabela.columns:
        df_tabela = df_tabela.sort_values(by='DTABERTURA', ascending=False)
    st.dataframe(df_tabela.head(1000), use_container_width=True)
else:
    st.dataframe(df_tabela, use_container_width=True)

st.divider()
st.subheader("Ritmo de Trabalho")

frequencia = st.radio("Agrupar por:", ["Diário", "Semanal", "Mensal"], horizontal=True, index=1)
mapa_frequencia = {'Diário': 'D', 'Semanal': 'W-MON', 'Mensal': 'MS'}
regra = mapa_frequencia[frequencia]

df_time = df_servico.copy()

def processar_serie(dataframe, coluna_data, regra_resample):
    if coluna_data not in dataframe.columns: return pd.Series(dtype='float64')
    datas_validas = dataframe[coluna_data].dropna()
    serie = pd.Series(1, index=datas_validas)
    return serie.resample(regra_resample).sum().rename(coluna_data)

s_abertura = processar_serie(df_time, 'DTABERTURA', regra).rename("Abertos")
s_modificacao = processar_serie(df_time, 'DTULTIMAMODIFICACAO', regra).rename("Modificados")
s_fechamento = processar_serie(df_time, 'DTFIM', regra).rename("Fechados")

dados_timeline = pd.concat([s_abertura, s_modificacao, s_fechamento], axis=1).fillna(0)

if not dados_timeline.empty and dados_timeline.sum().sum() > 0:
    fig_timeline = px.line(dados_timeline, x=dados_timeline.index, y=dados_timeline.columns, markers=True)
    color_map = {'Abertos': '#1f77b4', 'Modificados': '#ff7f0e', 'Fechados': '#2ca02c'}
    for data_name, color in color_map.items():
        if data_name in dados_timeline.columns:
            fig_timeline.update_traces(selector={'name':data_name}, line_color=color)
    st.plotly_chart(fig_timeline, use_container_width=True)
