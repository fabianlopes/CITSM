import streamlit as st
import pandas as pd
import dashboards # Importa seus gráficos reais
import conexao

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Apresentação CITSM", layout="wide", initial_sidebar_state="collapsed")

# --- CSS PARA DEIXAR COM CARA DE SLIDE ---
st.markdown("""
<style>
    .main { background-color: #0e1117; color: white; }
    h1 { font-size: 3.5rem !important; color: #4facfe; text-align: center; }
    h2 { font-size: 2.5rem !important; border-bottom: 2px solid #4facfe; padding-bottom: 10px; }
    p, li { font-size: 1.5rem !important; }
    .stButton>button { width: 100%; border-radius: 20px; font-size: 1.2rem; }
    /* Esconde elementos padrão do Streamlit para ficar limpo */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- CONTROLE DE NAVEGAÇÃO (Session State) ---
if 'slide' not in st.session_state:
    st.session_state.slide = 0

def proximo():
    st.session_state.slide += 1

def anterior():
    st.session_state.slide -= 1

# --- FUNÇÕES DOS SLIDES ---

def slide_0_capa():
    st.write("")
    st.write("")
    st.write("")
    st.title("🤖 CITSM Analyzer")
    st.markdown("<h3 style='text-align: center; color: gray;'>Inteligência Artificial Aplicada à Gestão de Serviços de TI</h3>", unsafe_allow_html=True)
    st.write("")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("**Apresentador:** Seu Nome | **Tecnologia:** Python + GPU Computing")

def slide_1_problema():
    st.header("1. O Desafio: Dados Não Estruturados")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        * **Volume:** Milhares de tickets mensais.
        * **Caos:** Dados em texto livre ("PC lento", "Travou tudo").
        * **Cegueira:** O SQL tradicional (`LIKE %palavra%`) falha em entender contexto.
        * **Desperdício:** Redundância e re-trabalho em tickets duplicados.
        """)
    with col2:
        st.warning("⚠️ **Exemplo Real:**\n\nTicket A: 'Impressora parou'\nTicket B: 'Atolamento de papel'\n\nPara o Banco de Dados, são diferentes.\nPara a IA, são a mesma coisa.")

def slide_2_solucao_arquitetura():
    st.header("2. Nossa Stack Tecnológica (On-Premise)")

    # Exemplo de código bonito no slide
    codigo = '''
    # O Cérebro da Operação
    Model: "intfloat/multilingual-e5-large"
    Hardware: NVIDIA RTX 3060 (12GB VRAM)
    Framework: PyTorch + Streamlit
    Database: Oracle (ODS_ITSM)
    '''
    st.code(codigo, language='yaml')

    st.success("💡 **Diferencial:** Tudo roda localmente. Custo ZERO de API e privacidade total dos dados.")

def slide_3_demo_dashboard():
    st.header("3. Demonstração: Analytics em Tempo Real")
    st.markdown("Neste slide, trazemos o **painel real** para dentro da apresentação.")
    st.divider()

    # --- MÁGICA: RODANDO SEU CÓDIGO DE DASHBOARD DENTRO DO SLIDE ---
    # Simulando carga de dados rápida
    conn = conexao.conexao()
    df = pd.read_sql("SELECT * FROM ODS_ITSM FETCH FIRST 1000 ROWS ONLY", conn)

    # Tratamento básico rápido
    for col in ['DTABERTURA', 'DTULTIMAMODIFICACAO']:
        if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce')

    # Chama sua função de gráficos (do arquivo dashboards.py)
    dashboards.renderizar_paineis_interativos(df)

def slide_4_demo_ia():
    st.header("4. Demonstração: Busca Semântica (IA)")
    st.markdown("A IA entende a **intenção**, não apenas a palavra.")

    col1, col2 = st.columns([3, 1])
    with col1:
        termo = st.text_input("Teste a IA agora:", "Problema de lentidão no sistema SAP")
    with col2:
        st.write("")
        st.write("")
        st.button("🔍 Buscar (Simulado)")

    if termo:
        st.write(f"🤖 **O Modelo E5-Large interpretou:** Buscando vetores próximos a '{termo}'...")
        st.write("✅ *Encontrado:* Chamado #9923 - 'ERP demorando para carregar telas financeiras' (Similaridade: 89%)")
        st.progress(89)

def slide_5_futuro():
    st.header("5. Próximos Passos & Roadmap")
    st.markdown("""
    1. **Validação (QA):** Implementação de "Golden Set" para medir precisão da IA.
    2. **Feedback Loop:** Botão de 👍/👎 para o usuário treinar o modelo.
    3. **LLM Local:** Rodar um Llama-3 para *gerar respostas* e não apenas classificar.
    """)
    st.balloons()

# --- LISTA DE SLIDES ---
slides = [
    slide_0_capa,
    slide_1_problema,
    slide_2_solucao_arquitetura,
    slide_3_demo_dashboard, # AQUI ESTÁ A MÁGICA
    slide_4_demo_ia,
    slide_5_futuro
]

# --- RENDERIZAÇÃO ---
# Barra de progresso no topo
progresso = (st.session_state.slide + 1) / len(slides)
st.progress(progresso)

# Executa a função do slide atual
slides[st.session_state.slide]()

# --- RODAPÉ DE NAVEGAÇÃO ---
st.write("---")
col_nav1, col_nav2, col_nav3 = st.columns([1, 8, 1])

with col_nav1:
    if st.session_state.slide > 0:
        st.button("⬅️ Anterior", on_click=anterior)

with col_nav3:
    if st.session_state.slide < len(slides) - 1:
        st.button("Próximo ➡️", on_click=proximo)