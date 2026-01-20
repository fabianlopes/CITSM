import streamlit as st
import pandas as pd
import conexao
import torch
import re
import nltk
import gc
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
from nltk.corpus import stopwords

# --- 1. CONFIGURAÇÃO INICIAL E ESTADO DA SESSÃO ---
st.set_page_config(page_title="IA GPU - CITSM Analyzer", layout="wide")

# Inicializa o estado para evitar loops infinitos
if "analise_concluida" not in st.session_state:
    st.session_state.analise_concluida = False
    st.session_state.info_topicos = None
    st.session_state.fig_bar = None
    st.session_state.df_resultados = None

st.title("🚀 Análise de Tópicos (Modo Turbo GPU)")

# Verifica hardware
device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cuda":
    st.success(f"✅ GPU ATIVADA: {torch.cuda.get_device_name(0)}")
else:
    st.warning("⚠️ Rodando em CPU.")

# --- 2. CACHE DE RECURSOS (STOPWORDS E MODELO) ---
@st.cache_resource
def preparar_stopwords():
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')

    lista = stopwords.words('portuguese')
    lixo_helpdesk = [
        'manaus', 'amazonas', 'am', 'br', 'gov', 'com', 'org', 'http', 'https', 'www',
        'atenciosamente', 'grato', 'obrigado', 'bom', 'dia', 'tarde', 'noite',
        'semef', 'prefeitura', 'secretaria', 'assunto', 'encaminhado', 'mensagem',
        'chamado', 'ticket', 'solicitacao', 'solicito', 'favor', 'gentileza',
        'analise', 'verificar', 'analisar', 'tratar', 'conforme', 'segue', 'anexo',
        'sistema', 'erro', 'falha', 'problema', 'abertura', 'fechamento',
        'json', 'html', 'div', 'span', 'class', 'id', 'width', 'height', 'style'
    ]
    lista.extend(lixo_helpdesk)
    return lista

@st.cache_resource
def carregar_modelo_base(stop_words):
    # O vectorizer é o que remove as stopwords na saída dos tópicos
    vectorizer_model = CountVectorizer(stop_words=stop_words, min_df=5)
    return BERTopic(
        language="multilingual",
        vectorizer_model=vectorizer_model,
        verbose=True,
        calculate_probabilities=False, # Crucial para não travar o navegador
        min_topic_size=10
    )

stop_words_pt = preparar_stopwords()

# --- 3. FUNÇÕES DE APOIO ---
def limpar_texto(texto):
    if not isinstance(texto, str): return ""
    texto = texto.lower()
    texto = re.sub(r'\S+@\S+', '', texto) # E-mails
    texto = re.sub(r'http\S+|www\S+', '', texto) # URLs
    texto = re.sub(r'\d+', '', texto) # Números
    texto = re.sub(r'[^\w\s]', ' ', texto) # Pontuação
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

@st.cache_data(ttl=3600)
def carregar_dados():
    try:
        conn = conexao.conexao()
        return pd.read_sql("SELECT * FROM ODS_ITSM FETCH FIRST 5000 ROWS ONLY", conn)
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return pd.DataFrame()

# --- 4. CARGA E BARRA LATERAL ---
df = carregar_dados()
if df.empty: st.stop()

st.sidebar.header("⚙️ Configurações")
lista_servicos = df['NOMESERVICO'].unique()
idx_serv = next((i for i, s in enumerate(lista_servicos) if "Sustenta" in str(s)), 0)
servico_sel = st.sidebar.selectbox("1. Selecione o Serviço:", lista_servicos, index=idx_serv)

df_analise = df[df['NOMESERVICO'] == servico_sel].copy()

cols_disponiveis = df_analise.columns.tolist()
idx_desc = next((i for i, c in enumerate(cols_disponiveis) if any(x in c.upper() for x in ['DESC', 'TEXT', 'RESUMO'])), 0)
coluna_texto = st.sidebar.selectbox("2. Coluna para IA:", cols_disponiveis, index=idx_desc)

# --- 5. BOTÃO DE EXECUÇÃO ---
if st.button("🚀 Iniciar Processamento na GPU", type="primary"):
    with st.spinner("🧹 Limpando dados e preparando GPU..."):
        df_analise = df_analise.dropna(subset=[coluna_texto])
        df_analise['TEXTO_LIMPO'] = df_analise[coluna_texto].astype(str).apply(limpar_texto)
        df_analise = df_analise[df_analise['TEXTO_LIMPO'].str.len() > 10]

    if len(df_analise) < 15:
        st.warning("Dados insuficientes para criar tópicos.")
    else:
        try:
            with st.spinner(f"🧠 A IA está analisando {len(df_analise)} tickets..."):
                # Carrega modelo e executa
                model = carregar_modelo_base(stop_words_pt)
                docs = df_analise['TEXTO_LIMPO'].tolist()
                topics, _ = model.fit_transform(docs)

                # Salva no Session State para persistência
                st.session_state.info_topicos = model.get_topic_info()
                st.session_state.fig_bar = model.visualize_barchart(top_n_topics=8, n_words=5)

                # Reassocia os tópicos ao dataframe
                df_analise['TOPICO_ID'] = topics
                st.session_state.df_resultados = df_analise
                st.session_state.analise_concluida = True

                # Limpeza de memória GPU
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

        except Exception as e:
            st.error(f"Falha no processamento: {e}")

# --- 6. RENDERIZAÇÃO DOS RESULTADOS (FORA DO BOTÃO) ---
if st.session_state.analise_concluida:
    st.divider()
    col1, col2 = st.columns([0.4, 0.6])

    with col1:
        st.subheader("📌 Tópicos Identificados")
        info = st.session_state.info_topicos.drop(columns=['Representative_Docs'], errors='ignore')
        info.loc[info['Topic'] == -1, 'Name'] = "-1_outros_ruido"
        st.dataframe(info.head(15), hide_index=True, width="stretch")

    with col2:
        st.subheader("📊 Relevância de Termos")
        st.plotly_chart(st.session_state.fig_bar, width="stretch", theme="streamlit")

    st.divider()
    st.subheader("🕵️ Auditoria de Chamados")

    nomes_topicos = st.session_state.info_topicos['Name'].tolist()
    sel_topico = st.selectbox("Selecione um tópico para ver os tickets:", options=nomes_topicos)
    id_sel = int(sel_topico.split("_")[0])

    # Filtra e exibe os tickets reais
    view_df = st.session_state.df_resultados[st.session_state.df_resultados['TOPICO_ID'] == id_sel]
    st.dataframe(
        view_df[['DEMANDANTE', coluna_texto, 'TEXTO_LIMPO']].head(50),
        width="stretch"
    )