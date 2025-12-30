import streamlit as st
import pandas as pd
import conexao
import torch
from sentence_transformers import SentenceTransformer, util

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Busca Semântica", layout="wide")
st.title("🔍 Busca por Sentido (Semantic Search)")
st.markdown("Encontre tickets pelo **significado**, mesmo que não usem as palavras exatas.")

# Verifica GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cuda":
    st.success(f"✅ GPU Ativada: {torch.cuda.get_device_name(0)}")
else:
    st.warning("⚠️ Rodando em CPU.")

# --- 1. CARGA DE DADOS ---
@st.cache_data(ttl=3600)
def carregar_dados():
    conn = conexao.conexao()
    # Trazemos uma amostra de 2000 a 5000 linhas
    return pd.read_sql("SELECT * FROM ODS_ITSM FETCH FIRST 3000 ROWS ONLY", conn)

df = carregar_dados()
if df.empty: st.stop()

# --- 2. PREPARAÇÃO NA BARRA LATERAL ---
st.sidebar.header("Configuração")

# Seleção de Coluna Automática
cols = df.columns.tolist()
idx_desc = next((i for i, c in enumerate(cols) if any(x in c.upper() for x in ['DESC', 'TEXT', 'RESUMO'])), 0)
col_texto = st.sidebar.selectbox("Coluna para analisar:", cols, index=idx_desc)

# Limpeza Básica (importante remover vazios)
df = df.dropna(subset=[col_texto])
df = df[df[col_texto].astype(str).str.len() > 10]
df.reset_index(drop=True, inplace=True) # Reseta index para alinhar com os vetores

# --- 3. CARREGAR MODELO (NA GPU) ---
@st.cache_resource
def carregar_modelo_semantico():
    # TROCAMOS O MODELO AQUI
    # Sai o MiniLM, entra o E5-Large (Requer ~2GB de VRAM, sua placa sobra)
    return SentenceTransformer('intfloat/multilingual-e5-large', device=device)

model = carregar_modelo_semantico()

# --- 4. GERAR VETORES (EMBEDDINGS) ---
# Isso transforma os textos dos tickets em números.
# Cacheamos isso porque é a parte "pesada".
# MUDANÇA: Adicionei o nome do modelo no argumento para o cache saber diferenciar
@st.cache_data
def gerar_embeddings_banco(_model, textos_lista, model_name="e5-large"):
    return _model.encode(textos_lista, convert_to_tensor=True, show_progress_bar=True)

# ...

# Na chamada da função:
with st.spinner("Gerando mapa semântico (Recalculando para E5-Large)..."):
    lista_textos = df[col_texto].astype(str).tolist()
    # Passamos o nome para forçar o Python a entender que é novo
    embeddings_banco = gerar_embeddings_banco(model, lista_textos, "e5-large")

st.divider()

# --- 5. A BUSCA INTELIGENTE ---
col_search, col_btn = st.columns([0.8, 0.2])

with col_search:
    query = st.text_input(
        "Descreva o SENTIDO que você procura:",
        placeholder="Ex: Testes de validação de sistema antes de subir para produção"
    )

with col_btn:
    st.write("") # Espaço para alinhar
    st.write("")
    buscar = st.button("🔎 Buscar", type="primary")

if query:
    # 1. Transforma sua busca em vetor
    query_embedding = model.encode(query, convert_to_tensor=True)

    # 2. Calcula a similaridade (Matemática de Cosseno)
    # Compara o vetor da sua busca contra TODOS os vetores do banco instantaneamente
    scores = util.cos_sim(query_embedding, embeddings_banco)[0]

    # 3. Organiza os resultados (Top Hits)
    # Pega os índices dos top 20 mais parecidos
    top_results = torch.topk(scores, k=50)

    st.subheader("Resultados por Similaridade")

    resultados = []
    for score, idx in zip(top_results[0], top_results[1]):
        idx = idx.item() # Converte tensor para int
        score = score.item() # Converte tensor para float

        # Filtra apenas o que tiver o mínimo de sentido (> 0.3 de similaridade)
        if score > 0.3:
            row = df.iloc[idx]
            resultados.append({
                "Similaridade (%)": f"{score*100:.1f}%",
                "Demandante": row.get('DEMANDANTE', '-'),
                "Texto Original": row[col_texto]
            })

    if resultados:
        df_result = pd.DataFrame(resultados)
        st.dataframe(df_result, use_container_width=True)
    else:
        st.warning("Nenhum ticket com sentido parecido encontrado.")