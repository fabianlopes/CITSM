import streamlit as st
import pandas as pd
import conexao
import plotly.express as px

from datetime import datetime

st.title("Dashboard CITSM")

conn = conexao.conexao()

query = """
        SELECT *
          FROM DWITSM.DIM_TICKET
         WHERE SITUACAO = 'Em Andamento/Aberto'
        """

df = pd.read_sql(query, conn)

coluna_filtro_ano = 'DATA_ABERTURA'
df[coluna_filtro_ano] = pd.to_datetime(df[coluna_filtro_ano], errors='coerce')
filtrar_ano = st.sidebar.checkbox('📅 Apenas Ano Atual', value=True)
if filtrar_ano:
    ano_atual = datetime.now().year
    df = df[df[coluna_filtro_ano].dt.year == ano_atual]
    st.toast(f"Mostrando dados de {ano_atual}", icon="📆") # Aviso visual legal


total_demandantes = len(df['DEMANDANTE'].value_counts())
total_servicos = len(df['SERVICO'].value_counts())

#top_10 = df['DEMANDANTE'].value_counts().head(10)
top_10 = df['DEMANDANTE'].value_counts().head(10).reset_index()
top_10_serv = df['SERVICO'].value_counts().head(10).reset_index()
lista_demandantes = ['Todos'] + list(df['DEMANDANTE'].unique())
demandante_selecionado = st.sidebar.selectbox("Título do Filtro", lista_demandantes)

if demandante_selecionado == 'Todos':
    top_10_serv = df['SERVICO'].value_counts().head(10).reset_index()
    df_filtrado = df
else:
    df_filtrado = df[df['DEMANDANTE'] == demandante_selecionado]
    top_10_serv = df_filtrado['SERVICO'].value_counts().head(10).reset_index()

top_10 = df['DEMANDANTE'].value_counts().head(10).reset_index()
#df_filtrado = df[df['DEMANDANTE'] == demandante_selecionado]
#top_10 = df['DEMANDANTE'].value_counts().head(10).reset_index()
#top_10_serv = df_filtrado['SERVICO'].value_counts().head(10).reset_index()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Análise de Demandantes")
    st.metric("Total de Registros", total_demandantes)
    st.write("Top 10 Solicitantes:")
    #st.dataframe(top_10)
#st.bar_chart(top_10)
#st.bar_chart(top_10, x="count", y="DEMANDANTE")
    fig = px.pie(top_10, values='count', names='DEMANDANTE', title='Distribuição por Demandante')
    st.plotly_chart(fig)
    #st.dataframe(df)
with col2:
    st.subheader("Análise de Serviços")
    st.metric("Total de Registros", total_servicos)
    st.write("Top 10 Serviços:")
    #st.dataframe(top_10_serv)
    fig = px.pie(top_10_serv, values='count', names='SERVICO', title='Distribuição por Serviços')
    st.plotly_chart(fig)
    #st.dataframe(df)

st.divider()
st.subheader("Evolução Temporal dos Chamados")
frequencia = st.radio("Agrupar por:", ["Diário", "Semanal", "Mensal"], horizontal=True)
mapa_frequencia = {'Diário': 'D', 'Semanal': 'W-MON', 'Mensal': 'MS'}
regra_agrupamento = mapa_frequencia[frequencia]
col_abertura = 'DATA_ABERTURA'
col_modificacao = 'DATA_ULTIMA_MODIFICACAO'
col_fechamento = 'DATA_FECHAMENTO'

df_time = df_filtrado.copy()

for col in [col_abertura, col_modificacao, col_fechamento]:
    df_time[col] = pd.to_datetime(df_time[col], errors='coerce')

def processar_serie(dataframe, coluna_data, regra):
    """Pega uma coluna de data, define como índice e agrupa pela regra escolhida"""
    # Filtra datas vazias para não dar erro
    datas_validas = dataframe[coluna_data].dropna()
    # Cria uma série temporal onde cada data vale 1
    serie = pd.Series(1, index=datas_validas)
    # Agrupa e soma (Resample é a mágica aqui)
    return serie.resample(regra).sum().rename(coluna_data)

s_abertura = processar_serie(df_time, col_abertura, regra_agrupamento).rename("Abertos")
s_modificacao = processar_serie(df_time, col_modificacao, regra_agrupamento).rename("Modificados")
s_fechamento = processar_serie(df_time, col_fechamento, regra_agrupamento).rename("Fechados")

# Juntamos tudo numa tabela só para o gráfico
dados_timeline = pd.concat([s_abertura, s_modificacao, s_fechamento], axis=1).fillna(0)

fig_timeline = px.line(dados_timeline, x=dados_timeline.index, y=dados_timeline.columns,
                       title=f"Fluxo de Trabalho ({frequencia})",
                       labels={'index': 'Período', 'value': 'Quantidade', 'variable': 'Tipo'},
                       markers=True)

color_map = {'Abertos': '#1f77b4', 'Modificados': '#ff7f0e', 'Fechados': '#2ca02c'} # Azul, Laranja, Verde
for data_name, color in color_map.items():
    if data_name in dados_timeline.columns:
        fig_timeline.update_traces(selector={'name':data_name}, line_color=color)

st.plotly_chart(fig_timeline, use_container_width=True)