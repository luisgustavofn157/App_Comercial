import urllib
import pandas as pd
import re
from sqlalchemy import create_engine, text
import streamlit as st

@st.cache_resource
def criar_engine_benner():
    db_host = st.secrets["BENNER_DB_HOST"]
    db_name = st.secrets["BENNER_DB_NAME"]
    
    driver = urllib.parse.quote_plus("SQL Server")
    url = f"mssql+pyodbc://@{db_host}/{db_name}?driver={driver}&Trusted_Connection=yes"
    return create_engine(url)

def validar_query_segura(query: str) -> bool:
    """Permite apenas comandos DQL (SELECT/WITH) e barra DML/DDL."""
    if not query.strip(): return False
    
    # Remove comentários para avaliação
    query_clean = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    query_clean = re.sub(r'/\*.*?\*/', '', query_clean, flags=re.DOTALL)
    query_upper = query_clean.strip().upper()
    
    if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH"):
        return False
        
    # \b exige limites de palavra (ex: barra 'UPDATE', mas permite 'TB_UPDATE')
    palavras_proibidas = [r"\bUPDATE\b", r"\bDELETE\b", r"\bINSERT\b", r"\bDROP\b", r"\bTRUNCATE\b", r"\bALTER\b", r"\bEXEC\b"]
    for p in palavras_proibidas:
        if re.search(p, query_upper):
            return False
            
    return True

def executar_consulta_benner(query: str) -> pd.DataFrame:
    if not validar_query_segura(query):
        raise ValueError("Comando bloqueado: Apenas consultas seguras (SELECT/WITH) são permitidas.")

    engine = criar_engine_benner()
    with engine.connect() as conexao:
        df = pd.read_sql(text(query), conexao)
        return df