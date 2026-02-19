import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sshtunnel import SSHTunnelForwarder

# Carrega os segredos
load_dotenv()

# Configuração visual da página
st.set_page_config(page_title="Cliente SQL - Rede Âncora", layout="wide")

st.title("🗄️ Cliente SQL Web - Consultas Rápidas")
st.write("Selecione o banco de dados, digite sua query e analise os resultados diretamente no navegador.")
st.divider()

# ==========================================
# FUNÇÕES DE CONEXÃO E CONSULTA
# ==========================================
def consultar_wms(query_sql):
    """Abre o túnel, conecta no Postgres, executa a query e retorna um DataFrame Pandas"""
    DB_USER = os.getenv("WMS_DB_USER")
    DB_PASS = os.getenv("WMS_DB_PASS")
    DB_HOST = os.getenv("WMS_DB_HOST")
    DB_NAME = os.getenv("WMS_DB_NAME")
    DB_PORT = 25060
    
    SSH_HOST = os.getenv("SSH_HOST")
    SSH_USER = os.getenv("SSH_USER")
    SSH_PASS = os.getenv("SSH_PASS")
    SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")

    ssh_kwargs = {}
    if SSH_KEY_PATH:
        ssh_kwargs['ssh_pkey'] = SSH_KEY_PATH
    else:
        ssh_kwargs['ssh_password'] = SSH_PASS

    # Inicia a conexão
    with SSHTunnelForwarder(
        (SSH_HOST, 22),
        ssh_username=SSH_USER,
        remote_bind_address=(DB_HOST, DB_PORT),
        **ssh_kwargs
    ) as tunnel:
        
        porta_local = tunnel.local_bind_port
        conexao_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@127.0.0.1:{porta_local}/{DB_NAME}"
        engine = create_engine(conexao_url)
        
        with engine.connect() as conexao:
            # O Pandas faz a mágica: executa a query e já transforma em tabela
            df_resultado = pd.read_sql(text(query_sql), conexao)
            return df_resultado

# ==========================================
# INTERFACE DO USUÁRIO (FRONTEND)
# ==========================================

# 1. Escolha do Banco
banco_escolhido = st.selectbox(
    "Selecione o Banco de Dados:",
    ["WMS Coletores (PostgreSQL)", "Benner ERP (SQL Server)"]
)

# 2. Área para digitar a Query
query_usuario = st.text_area(
    "Digite seu comando SQL (SELECT):", 
    height=150, 
    placeholder="Ex: SELECT * FROM sua_tabela LIMIT 10"
)

# 3. Botão de Execução
if st.button("Executar Query ▶️"):
    
    # Validação básica para não rodar vazio
    if not query_usuario.strip():
        st.warning("Por favor, digite uma query SQL antes de executar.")
    
    else:
        # Mostra um "spinner" de carregamento enquanto o Python vai até o banco
        with st.spinner("Conectando ao banco e executando a query..."):
            
            try:
                if banco_escolhido == "WMS Coletores (PostgreSQL)":
                    # Chama a nossa função e guarda a tabela na variável 'df'
                    df = consultar_wms(query_usuario)
                    
                    st.success(f"Query executada com sucesso! Linhas retornadas: {len(df)}")
                    
                    # Exibe a tabela interativa na tela
                    st.dataframe(df, use_container_width=True)
                    
                elif banco_escolhido == "Benner ERP (SQL Server)":
                    st.info("A conexão com o Benner ERP será implementada no próximo passo! 🚧")
            
            except Exception as erro:
                st.error("Erro ao executar a query. Verifique a sintaxe ou a conexão.")
                # Exibe o erro técnico em uma caixa "sanfonada" para não poluir a tela
                with st.expander("Ver detalhes técnicos do erro"):
                    st.code(erro)