import logging
from banco_de_dados.inicializar_sqlite import conectar_banco
from banco_de_dados.conexao_benner import executar_consulta_benner

logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)

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
    
    try:
        resultado = executar_consulta_benner(QUERY_BENNER)
        marcas_benner = resultado.set_index('HANDLE')['MARCA'].to_dict()
        print(f"📥 Extração concluída: {len(marcas_benner)} marcas ativas encontradas no Benner.")
    except Exception as e:
        print(f"🚨 ERRO DE CONEXÃO COM BENNER: {e}")
        return

    # Análise de alterações
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

    # Atualizar banco local
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