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
from sentence_transformers import util # Importante estar aqui no topo
from sentence_transformers import SentenceTransformer

# --- 1. CONFIGURAÇÃO INICIAL E ESTADO DA SESSÃO ---
st.set_page_config(page_title="IA GPU - CITSM Analyzer", layout="wide")

# Inicializa o estado para salvar as coisas entre os cliques
if "analise_concluida" not in st.session_state:
    st.session_state.analise_concluida = False
    st.session_state.info_topicos = None
    st.session_state.fig_bar = None
    st.session_state.df_resultados = None
    st.session_state.embeddings_docs = None # <--- NOVO: Para guardar os vetores

st.title("🚀 Análise de Tópicos (Modo Turbo GPU)")

# Verifica hardware
device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cuda":
    st.success(f"✅ GPU ATIVADA: {torch.cuda.get_device_name(0)}")
else:
    st.warning("⚠️ Rodando em CPU.")

# --- 2. CACHE DE RECURSOS ---
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
    vectorizer_model = CountVectorizer(stop_words=stop_words, min_df=5)
    return BERTopic(
        language="multilingual",
        vectorizer_model=vectorizer_model,
        verbose=True,
        calculate_probabilities=False,
        min_topic_size=10
    )

stop_words_pt = preparar_stopwords()

# --- 3. FUNÇÕES DE APOIO ---
def limpar_texto(texto):
    if not isinstance(texto, str): return ""
    texto = texto.lower()
    texto = re.sub(r'\S+@\S+', '', texto)
    texto = re.sub(r'http\S+|www\S+', '', texto)
    texto = re.sub(r'\d+', '', texto)
    texto = re.sub(r'[^\w\s]', ' ', texto)
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
                docs = df_analise['TEXTO_LIMPO'].tolist()

                # --- PASSO 1: GERAR EMBEDDINGS MANUALMENTE ---
                # Isso resolve o erro 'SentenceTransformerBackend object has no attribute encode'
                # Usamos um modelo multilingue leve e rápido
                st.text("Gerando vetores matemáticos...")
                sent_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device=device)
                embeddings = sent_model.encode(docs, show_progress_bar=False)

                # Salva IMEDIATAMENTE no cofre do Streamlit
                st.session_state.embeddings_docs = embeddings

                # --- PASSO 2: RODAR O BERTopic ---
                # Passamos os embeddings prontos para ele (embeddings=embeddings)
                topic_model = carregar_modelo_base(stop_words_pt)
                topics, _ = topic_model.fit_transform(docs, embeddings=embeddings)

                # Salva resultados visuais
                st.session_state.info_topicos = topic_model.get_topic_info()
                st.session_state.fig_bar = topic_model.visualize_barchart(top_n_topics=8, n_words=5)

                # Reassocia os tópicos ao dataframe
                df_analise['TOPICO_ID'] = topics
                st.session_state.df_resultados = df_analise
                st.session_state.analise_concluida = True

                # Limpeza de memória
                del sent_model
                del topic_model
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

        except Exception as e:
            st.error(f"Falha no processamento: {e}")
            # Mostra o erro completo para facilitar debug
            import traceback
            st.text(traceback.format_exc())

# --- 6. RENDERIZAÇÃO DOS RESULTADOS ---
if st.session_state.analise_concluida:
    st.divider()
    col1, col2 = st.columns([0.4, 0.6])

    with col1:
        st.subheader("📌 Tópicos Identificados")
        info = st.session_state.info_topicos.drop(columns=['Representative_Docs'], errors='ignore')
        info.loc[info['Topic'] == -1, 'Name'] = "-1_outros_ruido"
        st.dataframe(info.head(15), hide_index=True, use_container_width=True)

    with col2:
        st.subheader("📊 Relevância de Termos")
        st.plotly_chart(st.session_state.fig_bar, use_container_width=True, theme="streamlit")

    # --- SEÇÃO: DETECÇÃO DE DUPLICADOS CORRIGIDA ---
    st.divider()
    st.subheader("👯 Detecção de Tickets Duplicados")

    with st.expander("Clique para analisar duplicados semânticos (Acima de 90% de similaridade)"):
        try:
            # Recupera os embeddings que salvamos no passo 5
            embeddings = st.session_state.embeddings_docs

            if embeddings is None:
                st.error("Erro: Embeddings não encontrados. Rode a análise novamente.")
            else:
                # Calcula a similaridade (Matemática pesada feita na GPU/CPU)
                cosine_scores = util.cos_sim(embeddings, embeddings)

                duplicados = []
                # Varre a matriz de similaridade
                # Pegamos apenas índices onde i != j para não comparar o ticket com ele mesmo
                pares_encontrados = set()

                for i in range(len(cosine_scores)):
                    # Threshold 0.90 = 90% de similaridade
                    indices = (cosine_scores[i] > 0.90).nonzero(as_tuple=True)[0]

                    for idx in indices:
                        idx = idx.item()
                        if idx > i: # Evita duplicatas (A com B e B com A) e auto-comparação
                            duplicados.append({
                                "Ticket A": st.session_state.df_resultados.iloc[i].get('DEMANDANTE', 'Ticket A'),
                                "Texto A": st.session_state.df_resultados.iloc[i][coluna_texto][:150] + "...",
                                "Ticket B": st.session_state.df_resultados.iloc[idx].get('DEMANDANTE', 'Ticket B'),
                                "Texto B": st.session_state.df_resultados.iloc[idx][coluna_texto][:150] + "...",
                                "Similaridade": f"{cosine_scores[i][idx]:.2%}"
                            })

                if duplicados:
                    df_duplicados = pd.DataFrame(duplicados)
                    st.warning(f"Foram encontrados {len(df_duplicados)} pares suspeitos.")
                    st.dataframe(df_duplicados, use_container_width=True)
                else:
                    st.success("Nenhum duplicado óbvio encontrado (acima de 90%).")

        except Exception as e:
            st.error(f"Erro ao processar duplicados: {e}")
            st.write("Detalhe técnico:", str(e))

    st.divider()
    st.subheader("🕵️ Auditoria de Chamados")

    nomes_topicos = st.session_state.info_topicos['Name'].tolist()
    sel_topico = st.selectbox("Selecione um tópico:", options=nomes_topicos)
    id_sel = int(sel_topico.split("_")[0])

    view_df = st.session_state.df_resultados[st.session_state.df_resultados['TOPICO_ID'] == id_sel]
    st.dataframe(
        view_df[['DEMANDANTE', coluna_texto, 'TEXTO_LIMPO']].head(50),
        use_container_width=True
    )