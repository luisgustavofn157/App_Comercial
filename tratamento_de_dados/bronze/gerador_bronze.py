import pandas as pd

# Filtra as tabela aprovadas pelo usuário e as consolida
def gerar_camada_bronze(tabelas_extraidas, decisoes_usuario):
    dfs_aprovados = []
    
    for tbl in tabelas_extraidas:
        id_tbl = tbl['id_unico']
        decisao = decisoes_usuario.get(id_tbl, "❓ Pendente")
        
        if "Consolidar" in decisao:
            df_aprovado = tbl['dados'].copy()
            
            df_aprovado['SYS_ORIGEM_ARQUIVO'] = tbl['arquivo']
            df_aprovado['SYS_ORIGEM_ABA'] = tbl['aba']
            
            dfs_aprovados.append(df_aprovado)
            
    if not dfs_aprovados:
        return None
        
    df_bronze = pd.concat(dfs_aprovados, ignore_index=True, sort=False)
    
    return df_bronze