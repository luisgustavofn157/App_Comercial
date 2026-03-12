import streamlit as st
import pandas as pd
import urllib
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from memoria.consultas_rapidas_benner import consultas_rapidas_benner
from modulos.exportador import exportar_consulta_sql

@st.cache_resource
def criar_engine_benner():
    db_host = st.secrets["BENNER_DB_HOST"]
    db_name = st.secrets["BENNER_DB_NAME"]
    
    driver = urllib.parse.quote_plus("SQL Server")
    url = f"mssql+pyodbc://@{db_host}/{db_name}?driver={driver}&Trusted_Connection=yes"

    return create_engine(url)

def executar_consulta_segura(query):
    query_upper = query.upper()
    palavras_proibidas = ["UPDATE ", "DELETE ", "INSERT ", "DROP ", "TRUNCATE ", "ALTER ", "EXEC "]
    if any(p in query_upper for p in palavras_proibidas):
        raise ValueError("Comando bloqueado: Apenas consultas (SELECT) são permitidas.")

    engine = criar_engine_benner()
    with engine.connect() as conexao:
        df = pd.read_sql(text(query), conexao)
        return df

#Remove quebras de linha internas e protege contra dados binários (imagens/arquivos).
def higienizar_para_exportacao(df):
    df_limpo = df.copy()
    
    # Proteção Anti-Binário
    for col in df_limpo.columns:
        df_limpo[col] = df_limpo[col].apply(lambda x: "<Dados Binários>" if isinstance(x, bytes) else x)
        
    df_limpo = df_limpo.fillna("")
    df_limpo = df_limpo.astype(str)
    df_limpo = df_limpo.replace(r'\n|\r|\t', ' ', regex=True)
    df_limpo = df_limpo.replace(r'[\x00-\x1F\x7F]', '', regex=True)
    return df_limpo

# ==========================================
# GERENCIAMENTO DE ESTADO E CALLBACKS
# ==========================================
if "query_input" not in st.session_state:
    st.session_state.query_input = ""

if "acionar_execucao_automatica" not in st.session_state:
    st.session_state.acionar_execucao_automatica = False

def aplicar_consulta_pronta():
    escolha = st.session_state.combo_biblioteca
    if escolha == "Selecione uma consulta pronta...":
        limpar_tela() 
    else:
        st.session_state.query_input = consultas_rapidas_benner[escolha]
        st.session_state.acionar_execucao_automatica = True 

def limpar_tela():
    """Reseta absolutamente tudo da memória e da tela."""
    st.session_state.query_input = ""
    st.session_state.combo_biblioteca = "Selecione uma consulta pronta..."
    # Apaga as chaves, incluindo o novo timer
    for chave in ["ultimo_resultado_sql", "df_seguro", "excel_bytes", "tempo_execucao"]:
        if chave in st.session_state:
            del st.session_state[chave]

# ==========================================
# INTERFACE DO USUÁRIO
# ==========================================
st.title("🗄️ Consultas ao Banco de Dados do Benner")

st.selectbox(
    "Consultas Rápidas:", 
    options=list(consultas_rapidas_benner.keys()), 
    key="combo_biblioteca",
    on_change=aplicar_consulta_pronta
)

query_usuario = st.text_area(
    "Comando SQL:", 
    key="query_input", 
    height=200, 
    placeholder="SELECT TOP 100 * FROM NOME_DA_TABELA"
)

# ==========================================
# 🧰 BARRA DE FERRAMENTAS (Toolbar)
# ==========================================
col1, col2, col3, col4 = st.columns(4)

btn_executar = col1.button("▶️ Executar Consulta", use_container_width=True)

# 🧠 Lógica do Botão Mutante (Limpar -> Cancelar)
vai_executar = btn_executar or st.session_state.acionar_execucao_automatica
label_btn_limpar = "🛑 Cancelar Consulta" if vai_executar else "🧹 Limpar Tela"
col2.button(label_btn_limpar, on_click=limpar_tela, use_container_width=True)

# Lemos direto da memória para acender os botões instantaneamente
if "df_seguro" in st.session_state and "excel_bytes" in st.session_state:
    df_seguro = st.session_state.df_seguro
    
    # Botão 3: Baixar XLSX Seguro
    col3.download_button(
        label="📄 Baixar (.XLSX)", 
        data=st.session_state.excel_bytes, 
        file_name="extracao.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        use_container_width=True
    )
    
    # Botão 4: Copiar
    if len(df_seguro) <= 5000:
        with col4.popover("📋 Copiar Dados", use_container_width=True):
            st.caption("Clique no ícone 📋 para copiar:")
            st.code(df_seguro.to_csv(index=False, sep='\t'), language="text")
    else:
        col4.button("🚫 Cópia Bloqueada", disabled=True, use_container_width=True, help="Limite excedido (> 5000 linhas). Baixe o arquivo XLSX.")

# ==========================================
# MOTOR DE EXECUÇÃO E TRATAMENTO DE ERROS
# ==========================================
if vai_executar:
    st.session_state.acionar_execucao_automatica = False 
    query = st.session_state.query_input.strip()
    
    if not query:
        st.warning("Digite uma query válida.")
    else:
        # Spinner com texto amigável já prevendo lentidão
        with st.spinner("Consultando o banco do Benner..."):
            try:
                # ⏱️ Inicia o cronômetro
                start_time = time.time()
                
                df_resultado = executar_consulta_segura(query)
                df_seguro = higienizar_para_exportacao(df_resultado)
                excel_bytes = exportar_consulta_sql(df_seguro)
                
                # ⏱️ Para o cronômetro
                end_time = time.time()
                
                st.session_state.tempo_execucao = end_time - start_time
                st.session_state.ultimo_resultado_sql = df_resultado
                st.session_state.df_seguro = df_seguro
                st.session_state.excel_bytes = excel_bytes
                
                st.rerun() 
                
            except ValueError as ve:
                st.error("🛡️ Ação não permitida")
                st.warning(str(ve))
                
            except ProgrammingError as pe:
                st.error("❌ Erro de Sintaxe SQL")
                st.warning("O banco de dados não entendeu o comando. Verifique se o nome da tabela ou das colunas estão corretos.")
                with st.expander("Ver Detalhes Técnicos (Para Analistas)"):
                    st.code(str(pe))
                    
            except OperationalError as oe:
                erro_str = str(oe)
                if "08001" in erro_str or "08S01" in erro_str:
                    st.error("🔌 Falha de Conexão com o Servidor (Tempo Excedido)")
                    st.info("""
                    **O que fazer:**
                    1. Verifique se sua internet está funcionando.
                    2. Se não estiver no escritório, verifique se a sua **VPN** está conectada.
                    3. Se a internet e a VPN estiverem OK, o acesso ao banco do Benner pode estar com problemas, acione o TI.
                    """)
                elif "28000" in erro_str or "Login failed" in erro_str:
                    st.error("🔐 Acesso Negado (Autenticação Falhou)")
                    st.info("""
                    **O que fazer:**
                    1. Solicite ao TI que a sua máquina seja colocada no domínio da empresa.
                    """)
                else:
                    st.error("⚠️ Erro Operacional de Banco de Dados")
                    with st.expander("Ver Detalhes Técnicos"):
                        st.code(erro_str)
                        
            except Exception as e:
                st.error("🚨 Erro Inesperado na Execução")
                with st.expander("Ver Detalhes Técnicos"):
                    st.code(str(e))

# ==========================================
# VISUALIZAÇÃO NA TELA
# ==========================================
if "ultimo_resultado_sql" in st.session_state:
    df = st.session_state.ultimo_resultado_sql
    tempo_segundos = st.session_state.get("tempo_execucao", 0.0)
    
    if len(df) > 10:
        st.info("Exibindo apenas as 10 primeiras linhas na tela por performance. Baixe ou copie para obter a extração completa.")
        
    # Mensagem final elegante com o cronômetro embutido
    st.caption(f"🔍 Pré-visualização dos Dados (Retornou **{len(df)} linhas** em **{tempo_segundos:.2f} segundos**)")
    st.dataframe(df.head(10), use_container_width=True)