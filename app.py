import streamlit as st
import pandas as pd
import os
import urllib
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sshtunnel import SSHTunnelForwarder

# Carrega os segredos
load_dotenv()

st.set_page_config(page_title="Cliente SQL - Rede Âncora", layout="wide")
st.title("🗄️ Cliente SQL Web - Consultas Rápidas")
st.write("Selecione o banco de dados, digite sua query e analise os resultados diretamente no navegador.")
st.divider()

# ==========================================
# FUNÇÕES DE CONEXÃO E CONSULTA
# ==========================================
def consultar_wms(query_sql):
    # (O código do WMS continua intacto aqui)
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
            df_resultado = pd.read_sql(text(query_sql), conexao)
            return df_resultado

def consultar_benner(query_sql):
    """Conecta nativamente ao SQL Server e retorna um DataFrame Pandas"""
    DB_USER = os.getenv("BENNER_DB_USER")
    DB_PASS = os.getenv("BENNER_DB_PASS")
    DB_HOST = os.getenv("BENNER_DB_HOST") 
    DB_NAME = os.getenv("BENNER_DB_NAME")
    
    # O seu driver exato
    NOME_DO_DRIVER = "ODBC Driver 18 for SQL Server" 
    driver_formatado = urllib.parse.quote_plus(NOME_DO_DRIVER)
    
    # Adicionamos &Encrypt=yes&TrustServerCertificate=yes no final da URL
    conexao_url = f"mssql+pyodbc://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?driver={driver_formatado}&Encrypt=yes&TrustServerCertificate=yes"
    
    engine = create_engine(conexao_url)
    with engine.connect() as conexao:
        df_resultado = pd.read_sql(text(query_sql), conexao)
        return df_resultado

# ==========================================
# INTERFACE DO USUÁRIO (FRONTEND)
# ==========================================
banco_escolhido = st.selectbox(
    "Selecione o Banco de Dados:",
    ["WMS Coletores (PostgreSQL)", "Benner ERP (SQL Server)"]
)

query_usuario = st.text_area("Digite seu comando SQL (SELECT):", height=150)

if st.button("Executar Query ▶️"):
    if not query_usuario.strip():
        st.warning("Por favor, digite uma query SQL antes de executar.")
    else:
        with st.spinner("Conectando ao banco e executando a query..."):
            try:
                if banco_escolhido == "WMS Coletores (PostgreSQL)":
                    df = consultar_wms(query_usuario)
                    st.success(f"Query WMS executada com sucesso! Linhas retornadas: {len(df)}")
                    st.dataframe(df, use_container_width=True)
                    
                elif banco_escolhido == "Benner ERP (SQL Server)":
                    df = consultar_benner(query_usuario)
                    st.success(f"Query Benner executada com sucesso! Linhas retornadas: {len(df)}")
                    st.dataframe(df, use_container_width=True)
                    
            except Exception as erro:
                st.error("Erro ao executar a query.")
                with st.expander("Ver detalhes técnicos do erro"):
                    st.code(erro)