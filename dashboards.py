import streamlit as st
import plotly.express as px

def renderizar_paineis_interativos(df_servico):
    """
    Exibe os gráficos de Demandante (Esq) e Status com Legenda (Dir).
    Retorna: (demandante_clicado, status_clicado)
    """
    st.divider()
    st.markdown(f"### 🎯 Visão Interativa")
    st.caption("Clique nas barras para filtrar a tabela no final.")

    demandante_clicado = None
    status_clicado = None

    col1, col2 = st.columns(2)

    # --- LADO ESQUERDO: DEMANDANTES ---
    with col1:
        st.subheader("1. Quem solicita?")
        # Conta e limpa nomes
        df_dem = df_servico['DEMANDANTE'].value_counts().head(10).reset_index()
        df_dem.columns = ['DEMANDANTE', 'count']

        if not df_dem.empty:
            fig = px.bar(df_dem, x='count', y='DEMANDANTE', orientation='h', text='count')
            fig.update_layout(yaxis={'categoryorder':'total ascending'})

            # Captura clique
            evt = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="v_dem")
            if len(evt['selection']['points']) > 0:
                demandante_clicado = evt['selection']['points'][0]['y']
        else:
            st.info("Sem dados de demandantes.")

    # Filtra dados para o gráfico da direita (Cascade Filter)
    df_filtered = df_servico[df_servico['DEMANDANTE'] == demandante_clicado] if demandante_clicado else df_servico

    # --- LADO DIREITO: PIZZA + LEGENDA LATERAL ---
    with col2:
        st.subheader("2. Situação")
        df_stat = df_filtered['STATUS'].value_counts().reset_index()
        df_stat.columns = ['STATUS', 'count']

        if not df_stat.empty:
            # Layout: Pizza (70%) | Legenda (30%)
            c_pizza, c_legenda = st.columns([0.7, 0.3], gap="small")

            # A) PIZZA (Visual)
            with c_pizza:
                fig_pie = px.pie(df_stat, values='count', names='STATUS', hole=0.6, color='STATUS')
                fig_pie.update_traces(textinfo='percent')
                fig_pie.update_layout(showlegend=False, margin=dict(t=0,b=0,l=0,r=0), height=320)
                st.plotly_chart(fig_pie, use_container_width=True)

            # B) LEGENDA DINÂMICA (Botões)
            with c_legenda:
                # Cria base fixa para barras iguais
                df_stat['base'] = 1
                # Altura dinâmica: min 100px ou cresce conforme itens
                altura = max(len(df_stat) * 35, 100)

                fig_leg = px.bar(df_stat, x='base', y='STATUS', text='count', orientation='h', color='STATUS')

                # Estilo visual de legenda
                fig_leg.update_traces(
                    textposition='inside', insidetextanchor='middle',
                    width=0.8, marker_line_width=0, textfont_size=12
                )

                # Layout para colar o texto na barra
                fig_leg.update_layout(
                    showlegend=False,
                    xaxis=dict(visible=False, fixedrange=True, range=[0, 2.5]), # Range alto encurta a barra
                    yaxis=dict(
                        title=None, fixedrange=True, side='right', # Texto na direita
                        automargin=True, anchor="free", position=0.45 # Cola o texto na barra
                    ),
                    margin=dict(t=10, b=0, l=0, r=0),
                    height=altura,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    bargap=0.1
                )

                # Captura clique na legenda
                evt_leg = st.plotly_chart(
                    fig_leg, use_container_width=True, on_select="rerun",
                    selection_mode="points", config={'displayModeBar':False}, key="v_stat"
                )

                if len(evt_leg['selection']['points']) > 0:
                    status_clicado = evt_leg['selection']['points'][0]['y']
        else:
            st.info("Sem dados de status.")

    # Feedback visual de filtros ativos
    if demandante_clicado or status_clicado:
        cols_info = st.columns([0.8, 0.2])
        msg = f"**Filtros Ativos:** "
        if demandante_clicado: msg += f"👤 {demandante_clicado}  "
        if status_clicado: msg += f"🏷️ {status_clicado}"

        cols_info[0].markdown(msg)
        if cols_info[1].button("❌ Limpar"):
            st.rerun()

    return demandante_clicado, status_clicado