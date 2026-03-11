import streamlit as st
from memoria.inicializar_sqlite import conectar_banco, inicializar_banco

# Garante que as tabelas sempre existam quando o gerenciador for acionado
inicializar_banco()

def obter_perfis():
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("SELECT nome_perfil FROM tb_perfil ORDER BY nome_perfil")
    perfis = [linha['nome_perfil'] for linha in cursor.fetchall()]
    
    conn.close()
    return perfis

def obter_marcas_por_perfil(perfil):

    if not perfil or perfil == "Selecione...":
        return []
        
    conn = conectar_banco()
    cursor = conn.cursor()
    
    query = '''
        SELECT m.nome_marca
        FROM tb_perfil_marca pm
        JOIN tb_perfil p ON pm.id_perfil = p.id_perfil
        JOIN tb_marca m ON pm.id_marca = m.id_marca
        WHERE p.nome_perfil = ?
    '''
    cursor.execute(query, (perfil.strip(),))
    marcas = [linha['nome_marca'] for linha in cursor.fetchall()]
    
    conn.close()
    return marcas

def atualizar_marcas_do_perfil(nome_perfil, novas_marcas):
    nome_perfil = nome_perfil.strip()
    conn = conectar_banco()
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT OR IGNORE INTO tb_perfil (nome_perfil) VALUES (?)", (nome_perfil,))
        cursor.execute("SELECT id_perfil FROM tb_perfil WHERE nome_perfil = ?", (nome_perfil,))
        id_perfil = cursor.fetchone()['id_perfil']
        cursor.execute("DELETE FROM tb_perfil_marca WHERE id_perfil = ?", (id_perfil,))
        
        for marca in novas_marcas:
            cursor.execute("INSERT OR IGNORE INTO tb_marca (nome_marca) VALUES (?)", (marca,))
            cursor.execute("SELECT id_marca FROM tb_marca WHERE nome_marca = ?", (marca,))
            id_marca = cursor.fetchone()['id_marca']
            cursor.execute("INSERT INTO tb_perfil_marca (id_perfil, id_marca) VALUES (?, ?)", (id_perfil, id_marca))
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"🚨 ERRO: Falha ao salvar vínculos. Detalhes: {e}")
        st.stop()
    finally:
        conn.close()

def obter_marcas():
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("SELECT nome_marca FROM tb_marca ORDER BY nome_marca")
    marcas = [linha['nome_marca'] for linha in cursor.fetchall()]

    conn.close()
    return marcas

def obter_pesos_coluna(nome_perfil, coluna_planilha):
    conn = conectar_banco()
    cursor = conn.cursor()
    
    query = '''
        SELECT mc.campo_sistema, mc.pontuacao
        FROM tb_memoria_coluna mc
        INNER JOIN tb_perfil p ON mc.id_perfil = p.id_perfil
        WHERE p.nome_perfil = ? AND mc.coluna_planilha = ?
    '''
    cursor.execute(query, (nome_perfil, coluna_planilha))
    
    pesos = {linha['campo_sistema']: linha['pontuacao'] for linha in cursor.fetchall()}
    
    conn.close()
    return pesos

def salvar_pesos_coluna(nome_perfil, coluna_planilha, dicionario_pesos):
    conn = conectar_banco()
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT OR IGNORE INTO tb_perfil (nome_perfil) VALUES (?)", (nome_perfil,))
        cursor.execute("SELECT id_perfil FROM tb_perfil WHERE nome_perfil = ?", (nome_perfil,))
        id_perfil = cursor.fetchone()['id_perfil']
        
        for campo_sistema, pontuacao in dicionario_pesos.items():
            cursor.execute('''
                INSERT OR REPLACE INTO tb_memoria_coluna 
                (id_perfil, coluna_planilha, campo_sistema, pontuacao)
                VALUES (?, ?, ?, ?)
            ''', (id_perfil, coluna_planilha, campo_sistema, pontuacao))
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"🚨 ERRO: Falha ao gravar o aprendizado no banco. Detalhes: {e}")
    finally:
        conn.close()