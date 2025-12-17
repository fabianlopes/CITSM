import streamlit as st
import pandas as pd
import conexao
import plotly.express as px

st.title("Dashboard CITSM")

conn = conexao.conexao()

query = """
        SELECT *
          FROM DWITSM.DIM_TICKET
         WHERE SITUACAO = 'Em Andamento/Aberto'
        """

df = pd.read_sql(query, conn)

total_registros = len(df)
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
    st.metric("Total de Registros", total_registros)
    st.write("Top 10 Solicitantes:")
    st.dataframe(top_10)
#st.bar_chart(top_10)
#st.bar_chart(top_10, x="count", y="DEMANDANTE")
    fig = px.pie(top_10, values='count', names='DEMANDANTE', title='Distribuição por Demandante')
    st.plotly_chart(fig)
    st.dataframe(df)
with col2:
    st.subheader("Análise de Serviços")
    st.metric("Total de Registros", total_registros)
    st.write("Top 10 Serviços:")
    st.dataframe(top_10_serv)
    fig = px.pie(top_10_serv, values='count', names='SERVICO', title='Distribuição por Serviços')
    st.plotly_chart(fig)
    st.dataframe(df)