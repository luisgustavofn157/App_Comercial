import pandas as pd
import unicodedata
import re

def normalizar_cabecalho_extremo(texto):
    if pd.isna(texto): 
        return "COLUNA_VAZIA"
    else:
        texto = str(texto).upper().strip() # Deixar Maiúsculo
        texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn') # Remove acentos
        texto = re.sub(r'[\n\t\r]', ' ', texto) # Substitui quebras de linha ou tabulações por espaço
        texto = re.sub(r'[^A-Z0-9 ]', '', texto) # Remove caracteres especiais (deixa só letras, números e espaços)
        texto = re.sub(r'\b(DE|DO|DA|DOS|DAS|E|O|A|PARA|COM)\b', ' ', texto) # Remover preposições
        texto = re.sub(r'\s+', '_', texto.strip()) # Substitui múltiplos espaços por um único underline (snake_case)
        return texto
    
def deduplicar_colunas(colunas):
    nomes_vistos = {}
    novas_colunas = []
    
    for i, col in enumerate(colunas):
        if not col or str(col).strip() == "":
            col = f"col_vazia_{i}"
            
        if col in nomes_vistos:
            nomes_vistos[col] += 1
            nova_col = f"{col}_{nomes_vistos[col]}"
            novas_colunas.append(nova_col)
        else:
            nomes_vistos[col] = 0
            novas_colunas.append(col)
            
    return novas_colunas

def consolidar_dataframes(lista_tabelas_aprovadas):
    dfs_para_empilhar = []
    
    for tbl in lista_tabelas_aprovadas:
        df = tbl['dados'].copy()
        
        df['__ARQUIVO_ORIGEM__'] = tbl['arquivo']
        df['__ABA_ORIGEM__'] = tbl['aba']
        
        dfs_para_empilhar.append(df)
        
    if not dfs_para_empilhar:
        return pd.DataFrame()
    
    df_consolidado = pd.concat(dfs_para_empilhar, ignore_index=True, sort=False)
    
    colunas_linhagem = ['__ARQUIVO_ORIGEM__', '__ABA_ORIGEM__']
    outras_colunas = [c for c in df_consolidado.columns if c not in colunas_linhagem]
    df_consolidado = df_consolidado[colunas_linhagem + outras_colunas]
    
    return df_consolidado