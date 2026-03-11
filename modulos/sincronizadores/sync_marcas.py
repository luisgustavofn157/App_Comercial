import urllib
import streamlit as st
import sqlalchemy as sa
from sqlalchemy import text
from memoria.inicializar_sqlite import conectar_banco

# ==========================================
# MOTOR DE CONEXÃO (Extraído do banco_dados.py)
# ==========================================
AMBIENTE_DEV_LOCAL = True

def criar_engine_benner():
    """Cria a conexão segura com o SQL Server do ERP."""
    db_host = st.secrets["BENNER_DB_HOST"]
    db_name = st.secrets["BENNER_DB_NAME"]
    
    if AMBIENTE_DEV_LOCAL:
        driver = urllib.parse.quote_plus("SQL Server")
        url = f"mssql+pyodbc://@{db_host}/{db_name}?driver={driver}&Trusted_Connection=yes"
    else:
        driver = urllib.parse.quote_plus("ODBC Driver 18 for SQL Server")
        db_user = st.secrets["BENNER_DB_USER"]
        db_pass = st.secrets["BENNER_DB_PASS"]
        url = f"mssql+pyodbc://{db_user}:{db_pass}@{db_host}/{db_name}?driver={driver}&Encrypt=yes&TrustServerCertificate=yes"
        
    return sa.create_engine(url)

# ==========================================
# A EXTRAÇÃO
# ==========================================
QUERY_BENNER = """
SELECT DISTINCT M.HANDLE,
M.NOME AS MARCA
FROM PD_PRODUTOSPAI P
JOIN PD_MARCASPRODUTOS M ON M.HANDLE = P.MARCAPRODUTO
JOIN PD_PRODUTOS PP ON P.CODIGO = PP.CODIGO
JOIN FILIAIS F ON PP.FILIAL = F.HANDLE
WHERE 1 =1
    AND P.ATIVO = 'S'
    AND P.K_DESCONTINUADO = 'N'
    AND M.EHITEM = 'S'
    AND F.HANDLE IN (3, 8, 10, 11, 12, 14, 16, 18, 19, 20, 38, 322)
GROUP BY M.HANDLE, M.NOME
"""

def sincronizar_marcas():
    print("🔄 Iniciando sincronização de Marcas com o Benner...")
    
    # ---------------------------------------------------------
    # 1. EXTRAÇÃO (Trazendo a verdade do Benner)
    # ---------------------------------------------------------
    try:
        engine = criar_engine_benner()
        with engine.connect() as conn_benner:
            resultado = conn_benner.execute(text(QUERY_BENNER))
            marcas_benner = {linha.HANDLE: linha.MARCA for linha in resultado}
        print(f"📥 Extração concluída: {len(marcas_benner)} marcas ativas encontradas no ERP.")
    except Exception as e:
        print(f"🚨 ERRO DE CONEXÃO COM BENNER: {e}")
        return

    # ---------------------------------------------------------
    # 2. LEITURA LOCAL E COMPARAÇÃO DELTA
    # ---------------------------------------------------------
    conn_sqlite = conectar_banco()
    cursor = conn_sqlite.cursor()
    
    cursor.execute("SELECT handle_benner, nome_marca FROM tb_marca WHERE handle_benner IS NOT NULL")
    marcas_sqlite = {linha['handle_benner']: linha['nome_marca'] for linha in cursor.fetchall()}
    
    handles_benner = set(marcas_benner.keys())
    handles_sqlite = set(marcas_sqlite.keys())
    
    inserir = handles_benner - handles_sqlite
    deletar = handles_sqlite - handles_benner
    manter = handles_benner & handles_sqlite
    atualizar = {h for h in manter if marcas_benner[h] != marcas_sqlite[h]}
    
    print(f"📊 Análise de Alterações: Inserir ({len(inserir)}) | Atualizar ({len(atualizar)}) | Deletar ({len(deletar)})")

    # ---------------------------------------------------------
    # 3. APLICAÇÃO NO SQLITE
    # ---------------------------------------------------------
    try:
        for h in inserir:
            cursor.execute("INSERT INTO tb_marca (handle_benner, nome_marca) VALUES (?, ?)", (h, marcas_benner[h]))
        for h in atualizar:
            cursor.execute("UPDATE tb_marca SET nome_marca = ? WHERE handle_benner = ?", (marcas_benner[h], h))
        for h in deletar:
            cursor.execute("DELETE FROM tb_marca WHERE handle_benner = ?", (h,))
            
        cursor.execute('''
            INSERT INTO tb_log_sincronizacao 
            (tabela_destino, linhas_inseridas, linhas_atualizadas, linhas_deletadas, status)
            VALUES (?, ?, ?, ?, ?)
        ''', ('tb_marca', len(inserir), len(atualizar), len(deletar), 'SUCESSO'))
        
        conn_sqlite.commit()
        print("✅ Sincronização finalizada e gravada com sucesso!")
        
    except Exception as e:
        conn_sqlite.rollback()
        print(f"🚨 ERRO AO GRAVAR NO SQLITE: {e}")
    finally:
        conn_sqlite.close()

if __name__ == "__main__":
    sincronizar_marcas()