import streamlit as st
import pandas as pd
import conexao
import torch
import re
import nltk
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
from nltk.corpus import stopwords

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="IA GPU - BERTopic Limpo", layout="wide")
st.title("🚀 Análise de Tópicos (Limpeza Avançada + GPU)")

# Verifica GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cuda":
    st.success(f"✅ GPU ATIVADA: {torch.cuda.get_device_name(0)} - Modo Turbo")
else:
    st.warning("⚠️ GPU não detectada. Rodando em CPU (pode demorar).")

# --- 0. PREPARAÇÃO DE STOPWORDS (O FILTRO) ---
@st.cache_resource
def preparar_stopwords():
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')

    lista_pt = stopwords.words('portuguese')

    # AQUI ESTÁ O SEGREDO: Adicionamos o "lixo" específico do seu negócio
    lixo_helpdesk = [
        # Assinaturas e Locais
        'manaus', 'amazonas', 'am', 'br', 'gov', 'com', 'org', 'http', 'https', 'www',
        'atenciosamente', 'grato', 'obrigado', 'bom', 'dia', 'tarde', 'noite',
        'semef', 'prefeitura', 'secretaria', 'assunto', 'encaminhado', 'mensagem',
        # Palavras vazias de chamado
        'chamado', 'ticket', 'solicitacao', 'solicito', 'favor', 'gentileza',
        'analise', 'verificar', 'analisar', 'tratar', 'conforme', 'segue', 'anexo',
        'sistema', 'erro', 'falha', 'problema', 'abertura', 'fechamento',
        # Lixo técnico
        'json', 'html', 'div', 'span', 'class', 'id', 'width', 'height', 'style',
        'null', 'undefined', 'true', 'false', 'date', 'time'
    ]
    lista_pt.extend(lixo_helpdesk)
    return lista_pt

stop_words_pt = preparar_stopwords()

# --- 1. FUNÇÃO DE LIMPEZA DE TEXTO (REGEX) ---
def limpar_texto(texto):
    if not isinstance(texto, str): return ""

    # 1. Converte para minúsculas
    texto = texto.lower()

    # 2. Remove E-mails (ex: fulano@manaus.am.gov.br)
    texto = re.sub(r'\S+@\S+', '', texto)

    # 3. Remove URLs (http://...)
    texto = re.sub(r'http\S+|www\S+', '', texto)

    # 4. Remove Números e Anos (Remove 2024, 2025, 123)
    texto = re.sub(r'\d+', '', texto)

    # 5. Remove Pontuação e Caracteres Especiais (Mantém apenas letras e espaços)
    texto = re.sub(r'[^\w\s]', ' ', texto)

    # 6. Remove espaços extras
    texto = re.sub(r'\s+', ' ', texto).strip()

    return texto

# --- CARGA DE DADOS ---
@st.cache_data(ttl=3600)
def carregar_dados():
    conn = conexao.conexao()
    # Traz 5000 linhas
    return pd.read_sql("SELECT * FROM ODS_ITSM FETCH FIRST 5000 ROWS ONLY", conn)

df = carregar_dados()
if df.empty: st.stop()

# --- BARRA LATERAL ---
st.sidebar.header("Configuração")

if 'NOMESERVICO' in df.columns:
    lista_servicos = df['NOMESERVICO'].unique()
    idx_serv = next((i for i, s in enumerate(lista_servicos) if "Sustenta" in str(s)), 0)
    servico_sel = st.sidebar.selectbox("1. Serviço:", lista_servicos, index=idx_serv)
    df_analise = df[df['NOMESERVICO'] == servico_sel].copy()
else:
    st.error("Coluna NOMESERVICO não encontrada.")
    st.stop()

# Seleção de Coluna Inteligente
cols_disponiveis = df_analise.columns.tolist()
idx_desc = next((i for i, c in enumerate(cols_disponiveis) if any(x in c.upper() for x in ['DESC', 'TEXT', 'RESUMO'])), 0)
coluna_texto = st.sidebar.selectbox("2. Coluna de Texto:", cols_disponiveis, index=idx_desc)

# --- PRÉ-PROCESSAMENTO ---
if st.button("🚀 Iniciar Análise Limpa (GPU)", type="primary"):

    # 1. Aplica a limpeza pesada
    with st.spinner("🧹 Limpando sujeira (Emails, HTML, Datas, Assinaturas)..."):
        # Remove nulos e converte para string
        df_analise = df_analise.dropna(subset=[coluna_texto])
        df_analise['TEXTO_LIMPO'] = df_analise[coluna_texto].astype(str).apply(limpar_texto)

        # Filtra textos que ficaram vazios ou muito curtos após a limpeza
        df_analise = df_analise[df_analise['TEXTO_LIMPO'].str.len() > 10]

    if len(df_analise) < 10:
        st.warning("Após a limpeza, sobraram poucos dados. Tente outro serviço.")
    else:
        with st.spinner(f"🧠 A RTX 3060 está processando {len(df_analise)} tickets..."):
            try:
                # --- CONFIGURAÇÃO DO BERTOPIC ---
                # Usamos CountVectorizer para forçar o BERTopic a ignorar as stopwords
                # min_df=5: A palavra precisa aparecer em pelo menos 5 tickets para ser relevante
                vectorizer_model = CountVectorizer(stop_words=stop_words_pt, min_df=5)

                # Instancia o modelo com o vectorizer customizado
                topic_model = BERTopic(
                    language="multilingual",
                    vectorizer_model=vectorizer_model, # <--- AQUI ESTÁ A MÁGICA
                    verbose=True,
                    calculate_probabilities=False,
                    min_topic_size=10 # Tópicos precisam ter no mínimo 10 tickets
                )

                # Treina
                docs = df_analise['TEXTO_LIMPO'].tolist()
                topics, probs = topic_model.fit_transform(docs)

                # Resultados
                info_topicos = topic_model.get_topic_info()

                # --- VISUALIZAÇÃO ---
                col1, col2 = st.columns([0.4, 0.6])

                with col1:
                    st.subheader("📌 Tópicos Limpos")
                    # Remove coluna 'Representative_Docs' e o Tópico -1 (Ruído) se quiser
                    display = info_topicos.drop(columns=['Representative_Docs'], errors='ignore')

                    # Renomeia o tópico -1 para "Outros/Ruído"
                    display.loc[display['Topic'] == -1, 'Name'] = "-1_outros_ruido_diverso"

                    st.dataframe(display.head(20), hide_index=True, use_container_width=True)

                with col2:
                    st.subheader("📊 Palavras-Chave por Tópico")
                    fig_bar = topic_model.visualize_barchart(top_n_topics=8, n_words=5)
                    st.plotly_chart(fig_bar, use_container_width=True)

                st.divider()
                st.subheader("🕵️ Ver Tickets Reais do Tópico")

                # Cria um selectbox para escolher o tópico
                opcoes_topicos = info_topicos['Name'].tolist()
                topico_selecionado = st.selectbox("Escolha um tópico para auditar:", options=opcoes_topicos)

                # Pega o ID do tópico (o número antes do _)
                id_topico = int(topico_selecionado.split("_")[0])

                # Filtra o dataframe original (mas mostra o texto limpo para conferência)
                # Precisamos reassociar os tópicos ao DF. O BERTopic retorna na ordem.
                df_analise['TOPICO_ID'] = topics

                tickets_do_topico = df_analise[df_analise['TOPICO_ID'] == id_topico]

                st.dataframe(
                    tickets_do_topico[['DEMANDANTE', coluna_texto, 'TEXTO_LIMPO']].head(50),
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"Erro: {e}")