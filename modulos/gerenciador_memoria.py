import sqlite3
import streamlit as st
from modulos.setup_sqlite import conectar_banco, inicializar_banco

# Garante que as tabelas existam sempre que o gerenciador for acionado
inicializar_banco()

# ==========================================
# FUNÇÕES PÚBLICAS (A interface chama essas)
# ==========================================

def obter_todas_marcas_cadastradas():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT nome_marca FROM tb_marca ORDER BY nome_marca")
    marcas = [linha['nome_marca'] for linha in cursor.fetchall()]
    conn.close()
    return marcas

def obter_perfis_salvos():
    """Retorna a lista de perfis existentes direto da tabela de perfis."""
    conn = conectar_banco()
    cursor = conn.cursor()
    
    cursor.execute("SELECT nome_perfil FROM tb_perfil ORDER BY nome_perfil")
    perfis = [linha['nome_perfil'] for linha in cursor.fetchall()]
    
    conn.close()
    return perfis

def obter_marcas_por_perfil(perfil):
    """
    Faz um JOIN estruturado para trazer apenas as marcas vinculadas ao perfil.
    """
    if not perfil or perfil == "Selecione...":
        return []
        
    conn = conectar_banco()
    cursor = conn.cursor()
    
    query = '''
        SELECT m.nome_marca
        FROM tb_perfil_marca pm
        INNER JOIN tb_perfil p ON pm.id_perfil = p.id_perfil
        INNER JOIN tb_marca m ON pm.id_marca = m.id_marca
        WHERE p.nome_perfil = ?
    '''
    cursor.execute(query, (perfil.strip(),))
    marcas = [linha['nome_marca'] for linha in cursor.fetchall()]
    
    conn.close()
    return marcas

def atualizar_marcas_do_perfil(nome_perfil, novas_marcas):
    """
    Rotina transacional: Garante que o perfil existe, limpa vínculos antigos e cria novos.
    Se algo der errado no meio, o ROLLBACK desfaz tudo para evitar banco corrompido.
    """
    nome_perfil = nome_perfil.strip()
    conn = conectar_banco()
    cursor = conn.cursor()
    
    
    
    try:
        # 1. Insere o perfil (INSERT OR IGNORE pula se já existir por causa do UNIQUE)
        cursor.execute("INSERT OR IGNORE INTO tb_perfil (nome_perfil) VALUES (?)", (nome_perfil,))
        
        # Coleta o ID do perfil
        cursor.execute("SELECT id_perfil FROM tb_perfil WHERE nome_perfil = ?", (nome_perfil,))
        id_perfil = cursor.fetchone()['id_perfil']
        
        # 2. Deleta os vínculos antigos deste perfil (Limpeza para o novo multiselect)
        cursor.execute("DELETE FROM tb_perfil_marca WHERE id_perfil = ?", (id_perfil,))
        
        # 3. Insere os novos vínculos
        for marca in novas_marcas:
            # Trava de segurança: Garante que a marca existe na tabela mestre
            cursor.execute("INSERT OR IGNORE INTO tb_marca (nome_marca) VALUES (?)", (marca,))
            
            # Coleta o ID da marca
            cursor.execute("SELECT id_marca FROM tb_marca WHERE nome_marca = ?", (marca,))
            id_marca = cursor.fetchone()['id_marca']
            
            # Cria a ponte na tabela de junção
            cursor.execute('''
                INSERT INTO tb_perfil_marca (id_perfil, id_marca) 
                VALUES (?, ?)
            ''', (id_perfil, id_marca))
            
        # Tudo certo? Grava no disco!
        conn.commit()
    except Exception as e:
        conn.rollback() # Deu erro? Descarta tudo e protege a integridade
        st.error(f"🚨 ERRO DE BANCO DE DADOS: Falha ao salvar vínculos. Detalhes: {e}")
        st.stop()
    finally:
        conn.close()

def obter_pesos_coluna(nome_perfil, coluna_planilha):
    """Busca os pesos de uma coluna específica no banco local."""
    conn = conectar_banco()
    cursor = conn.cursor()
    
    query = '''
        SELECT mc.campo_sistema, mc.pontuacao
        FROM tb_memoria_coluna mc
        INNER JOIN tb_perfil p ON mc.id_perfil = p.id_perfil
        WHERE p.nome_perfil = ? AND mc.coluna_planilha = ?
    '''
    cursor.execute(query, (nome_perfil, coluna_planilha))
    
    # Converte as linhas do banco para um dicionário idêntico ao que o sistema já espera
    pesos = {linha['campo_sistema']: linha['pontuacao'] for linha in cursor.fetchall()}
    
    conn.close()
    return pesos

def salvar_pesos_coluna(nome_perfil, coluna_planilha, dicionario_pesos):
    """Salva ou atualiza os pesos de aprendizado no banco."""
    conn = conectar_banco()
    cursor = conn.cursor()
    
    try:
        # Garante que o perfil existe (vital para salvar a memória do perfil genérico "")
        cursor.execute("INSERT OR IGNORE INTO tb_perfil (nome_perfil) VALUES (?)", (nome_perfil,))
        cursor.execute("SELECT id_perfil FROM tb_perfil WHERE nome_perfil = ?", (nome_perfil,))
        id_perfil = cursor.fetchone()['id_perfil']
        
        for campo_sistema, pontuacao in dicionario_pesos.items():
            # INSERT OR REPLACE atualiza a nota se já existir, ou cria se for nova
            cursor.execute('''
                INSERT OR REPLACE INTO tb_memoria_coluna 
                (id_perfil, coluna_planilha, campo_sistema, pontuacao)
                VALUES (?, ?, ?, ?)
            ''', (id_perfil, coluna_planilha, campo_sistema, pontuacao))
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"🚨 ERRO DE APRENDIZADO: Falha ao gravar no banco. Detalhes: {e}")
    finally:
        conn.close()