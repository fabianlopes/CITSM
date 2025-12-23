import streamlit as st
import pandas as pd
import conexao
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="Dashboard CITSM")

st.title("Dashboard Operacional - Tickets")

# --- 2. CONEXÃO E DADOS ---
@st.cache_data(ttl=3600)
def carregar_dados():
    conn = conexao.conexao()
    query = "SELECT * FROM ODS_ITSM"
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Erro na query: {e}")
        return pd.DataFrame()

df = carregar_dados()

if df.empty:
    st.warning("Sem dados.")
    st.stop()

# --- 3. TRATAMENTO ---
for col in ['DTABERTURA', 'DTULTIMAMODIFICACAO', 'DTFIM']:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

# Limpeza
if 'DEMANDANTE' in df.columns:
    df['DEMANDANTE'] = df['DEMANDANTE'].astype(str).str.strip()
if 'STATUS' in df.columns:
    df['STATUS'] = df['STATUS'].astype(str).str.strip()

# --- 4. FILTROS GLOBAIS ---
st.sidebar.header("Filtros")
if st.sidebar.checkbox('📅 Apenas Ano Atual', value=True):
    if 'DTABERTURA' in df.columns:
        df = df[df['DTABERTURA'].dt.year == datetime.now().year]

if 'NOMESERVICO' in df.columns:
    lista = df['NOMESERVICO'].unique()
    idx = next((i for i, s in enumerate(lista) if "Sustenta" in str(s)), 0)
    servico_sel = st.sidebar.selectbox("Serviço:", lista, index=idx)
    df_servico = df[df['NOMESERVICO'] == servico_sel]
else:
    st.error("Coluna NOMESERVICO ausente.")
    st.stop()

# --- 5. VISUALIZAÇÃO ---
st.divider()
st.markdown(f"### 🎯 Visão Geral: **{servico_sel}**")
st.caption("💡 **Interatividade:** Clique na barra de **Demandante** e depois na legenda de **Status**.")

demandante_clicado = None
status_clicado = None

col_esquerda, col_direita = st.columns(2)

# === ESQUERDA: DEMANDANTES ===
with col_esquerda:
    st.subheader("1. Quem solicita?")
    df_dem = df_servico['DEMANDANTE'].value_counts().head(10).reset_index()
    df_dem.columns = ['DEMANDANTE', 'count']

    if not df_dem.empty:
        fig_bar = px.bar(df_dem, x='count', y='DEMANDANTE', orientation='h', text='count')
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})

        evt_dem = st.plotly_chart(fig_bar, use_container_width=True, on_select="rerun", selection_mode="points", key="chart_dem")
        if len(evt_dem['selection']['points']) > 0:
            demandante_clicado = evt_dem['selection']['points'][0]['y']

if demandante_clicado:
    df_chart2 = df_servico[df_servico['DEMANDANTE'] == demandante_clicado]
    st.toast(f"Filtro: {demandante_clicado}", icon="👤")
else:
    df_chart2 = df_servico

# === DIREITA: STATUS (PIZZA + LEGENDA GRUDADA) ===
with col_direita:
    st.subheader("2. Situação")

    df_stat = df_chart2['STATUS'].value_counts().reset_index()
    df_stat.columns = ['STATUS', 'count']

    if not df_stat.empty:
        # Coluna 1 (Pizza) | Coluna 2 (Legenda)
        sub_c1, sub_c2 = st.columns([0.7, 0.3], gap="small")

        # A) PIZZA
        with sub_c1:
            fig_pie = px.pie(df_stat, values='count', names='STATUS', hole=0.6, color='STATUS')
            fig_pie.update_traces(textinfo='percent')
            fig_pie.update_layout(
                showlegend=False,
                margin=dict(t=0, b=0, l=0, r=0),
                height=320
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # B) LEGENDA (TEXTO COLADO NA BARRA)
        with sub_c2:
            df_stat['tamanho_fixo'] = 1

            # Altura Dinâmica (calcula para ficar compacto no topo)
            qtd_itens = len(df_stat)
            altura_legenda = max(qtd_itens * 35, 100)

            fig_buttons = px.bar(
                df_stat,
                x='tamanho_fixo',
                y='STATUS',
                text='count',
                orientation='h',
                color='STATUS'
            )

            fig_buttons.update_traces(
                textposition='inside',
                insidetextanchor='middle',
                textfont_size=12,
                width=0.8,
                marker_line_width=0
            )

            # O SEGREDO DO POSICIONAMENTO ESTÁ AQUI EMBAIXO:
            fig_buttons.update_layout(
                showlegend=False,

                # 1. Definimos que o gráfico vai de 0 a 2.5
                xaxis=dict(visible=False, fixedrange=True, range=[0, 2.5]),

                yaxis=dict(
                    title=None,
                    fixedrange=True,
                    side='right',
                    tickfont=dict(size=11),
                    automargin=True,

                    # 2. TRUQUE DE GEOMETRIA:
                    # 'anchor="free"' libera o eixo da borda.
                    # 'position=0.45' move o texto para 45% da largura da tela.
                    # Como a barra vai de 0 a 1 e o total é 2.5 -> 1/2.5 = 0.4.
                    # Ou seja, colocamos o texto logo depois que a barra acaba!
                    anchor="free",
                    position=0.45
                ),

                margin=dict(t=10, b=0, l=0, r=0),
                height=altura_legenda,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                bargap=0.1
            )

            evt_stat = st.plotly_chart(
                fig_buttons,
                use_container_width=True,
                on_select="rerun",
                selection_mode="points",
                config={'displayModeBar': False},
                key="chart_buttons_legend"
            )

            if len(evt_stat['selection']['points']) > 0:
                status_clicado = evt_stat['selection']['points'][0]['y']
                st.toast(f"Status: {status_clicado}", icon="🏷️")
    else:
        st.info("Sem dados.")

# Limpar Filtros
if demandante_clicado or status_clicado:
    if st.button("🔄 Limpar Filtros"):
        st.rerun()

# --- 6. TIMELINE ---
st.divider()
st.subheader("Ritmo de Trabalho")
df_time = df_servico.copy()
cols_t = {'DTABERTURA':'Abertos', 'DTULTIMAMODIFICACAO':'Modificados', 'DTFIM':'Fechados'}
dados_t = pd.DataFrame()

for col_db, nome_legenda in cols_t.items():
    if col_db in df_time.columns:
        s = df_time.set_index(col_db).resample('W-MON').size()
        dados_t[nome_legenda] = s

if not dados_t.empty:
    st.plotly_chart(px.line(dados_t, markers=True), use_container_width=True)

# --- 7. TABELA ---
st.divider()
st.subheader("📋 Lista de Tickets")

df_final = df_servico.copy()
filtros = []

if demandante_clicado:
    df_final = df_final[df_final['DEMANDANTE'] == demandante_clicado]
    filtros.append(f"👤 {demandante_clicado}")

if status_clicado:
    df_final = df_final[df_final['STATUS'] == status_clicado]
    filtros.append(f"🏷️ {status_clicado}")

if filtros:
    st.info(f"Filtro: {' + '.join(filtros)}")

if 'DTABERTURA' in df_final.columns:
    df_final = df_final.sort_values('DTABERTURA', ascending=False)

st.dataframe(df_final.head(1000), use_container_width=True)