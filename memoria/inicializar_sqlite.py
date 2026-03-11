import sqlite3
from pathlib import Path
import streamlit as st

DIRETORIO_RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = DIRETORIO_RAIZ / 'memoria' / 'BD_App_Comercial.db'

def conectar_banco():
    """Cria e retorna a conexão com o banco SQLite."""
    try:
        conn = sqlite3.connect(CAMINHO_BANCO, check_same_thread=False)
        conn.row_factory = sqlite3.Row 
        return conn
    except Exception as e:
        st.error(f"🚨 ERRO DE CONEXÃO: Não foi possível conectar ao banco de dados local. Detalhes: {e}")
        st.stop()

def inicializar_banco():
    """Cria as tabelas estruturais caso seja a primeira vez rodando o sistema."""
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Tabela 1: Marcas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tb_marca (
            id_marca INTEGER PRIMARY KEY AUTOINCREMENT,
            handle_benner INTEGER UNIQUE,
            nome_marca TEXT NOT NULL
        )
    ''')
    
    # Tabela 2: Perfis (Criados pelo usuário)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tb_perfil (
            id_perfil INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_perfil TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Tabela 3: Relacionamento (Perfil x Marca)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tb_perfil_marca (
            id_perfil INTEGER,
            id_marca INTEGER,
            FOREIGN KEY(id_perfil) REFERENCES tb_perfil(id_perfil) ON DELETE CASCADE,
            FOREIGN KEY(id_marca) REFERENCES tb_marca(id_marca) ON DELETE CASCADE,
            PRIMARY KEY (id_perfil, id_marca)
        )
    ''')

    # Tabela 4: Memória de aprendizado de colunas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tb_memoria_coluna (
            id_mapeamento INTEGER PRIMARY KEY AUTOINCREMENT,
            id_perfil INTEGER,
            coluna_planilha TEXT NOT NULL,
            campo_sistema TEXT NOT NULL,
            pontuacao REAL NOT NULL,
            FOREIGN KEY(id_perfil) REFERENCES tb_perfil(id_perfil) ON DELETE CASCADE,
            UNIQUE(id_perfil, coluna_planilha, campo_sistema)
        )
    ''')

    # Tabela 5: Log de Sincronização (Auditoria)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tb_log_sincronizacao (
            id_log INTEGER PRIMARY KEY AUTOINCREMENT,
            tabela_destino TEXT NOT NULL,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
            linhas_inseridas INTEGER DEFAULT 0,
            linhas_atualizadas INTEGER DEFAULT 0,
            linhas_deletadas INTEGER DEFAULT 0,
            status TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

# Executa a inicialização ao importar este módulo
if __name__ == "__main__":
    inicializar_banco()
    print(f"✅ Banco de dados inicializado com sucesso em: {CAMINHO_BANCO}")