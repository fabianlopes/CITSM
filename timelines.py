import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def renderizar_timelines(df_servico):
    """
    Renderiza Timeline de Fluxo e Aging (Backlog).
    """
    st.divider()

    # --- 1. Fluxo (Linha do Tempo) ---
    st.subheader("📈 Ritmo de Trabalho")

    # Seletor local de frequência
    freq = st.radio("Agrupar por:", ["Semanal", "Mensal"], horizontal=True, key="freq_time")
    regra = 'W-MON' if freq == "Semanal" else 'MS'

    df_time = df_servico.copy()
    cols_t = {'DTABERTURA':'Abertos', 'DTULTIMAMODIFICACAO':'Modificados', 'DTFIM':'Fechados'}
    dados_t = pd.DataFrame()

    for col_db, nome_legenda in cols_t.items():
        if col_db in df_time.columns:
            s = df_time.set_index(col_db).resample(regra).size()
            dados_t[nome_legenda] = s

    if not dados_t.empty:
        fig_t = px.line(dados_t, markers=True)
        fig_t.update_layout(xaxis_title="", yaxis_title="Quantidade Tickets", legend_title="Ação")
        st.plotly_chart(fig_t, use_container_width=True)
    else:
        st.info("Dados temporais insuficientes.")

    st.divider()

    # --- 2. Backlog Aging (Gantt) ---
    st.subheader("🐢 Tickets Pendentes Antigos (Top 15)")
    st.caption("Visualização de chamados abertos há mais tempo.")

    # Filtra o que não tem data de fim
    df_abertos = df_servico[df_servico['DTFIM'].isna()].copy()

    if not df_abertos.empty:
        agora = datetime.now()
        df_abertos['DIAS_ABERTO'] = (agora - df_abertos['DTABERTURA']).dt.days

        # Pega os 15 piores
        df_top = df_abertos.sort_values('DIAS_ABERTO', ascending=False).head(15)

        # Cria rótulo para o eixo Y
        df_top['ROTULO'] = df_top['DEMANDANTE'] + " (" + df_top['DIAS_ABERTO'].astype(str) + "d)"

        fig_gantt = px.timeline(
            df_top,
            x_start="DTABERTURA",
            x_end=[agora] * len(df_top),
            y="ROTULO",
            color="STATUS",
            title="Duração dos chamados em aberto"
        )
        fig_gantt.update_yaxes(autorange="reversed", title="") # Inverte para o mais velho ficar no topo
        fig_gantt.update_layout(height=max(len(df_top)*30, 300)) # Altura dinâmica
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.success("Nenhum ticket pendente!")