import pandas as pd
import streamlit as st

def gerar_camada_bronze(tabelas_extraidas, decisoes_usuario):
    """
    Filtra as tabelas aprovadas pelo usuário e empilha (concatena) verticalmente.
    O resultado é a Camada Bronze (Bruta Consolidada), o ponto de partida seguro do ETL.
    """
    dfs_aprovados = []
    
    for tbl in tabelas_extraidas:
        id_tbl = tbl['id_unico']
        decisao = decisoes_usuario.get(id_tbl, "❓ Pendente")
        
        if "Consolidar" in decisao:
            # Pega o dataframe que já foi recortado pelo identificador
            df_aprovado = tbl['dados'].copy()
            
            # (Opcional) Adiciona uma coluna de rastreabilidade (Lineage)
            df_aprovado['SYS_ORIGEM_ARQUIVO'] = tbl['arquivo']
            df_aprovado['SYS_ORIGEM_ABA'] = tbl['aba']
            
            dfs_aprovados.append(df_aprovado)
            
    if not dfs_aprovados:
        return None
        
    # Empilha verticalmente ignorando o index original
    df_bronze = pd.concat(dfs_aprovados, ignore_index=True, sort=False)
    
    return df_bronze