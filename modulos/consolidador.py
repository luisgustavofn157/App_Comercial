import pandas as pd
import unicodedata
import re

def normalizar_cabecalho_extremo(texto):
    """
    Aplica regras rígidas para padronizar nomes de colunas e forçar o 'match' automático.
    Ex: ' Cód.   Produto \n' vira 'COD_PRODUTO'
    """
    if pd.isna(texto): 
        return "COLUNA_VAZIA"
    
    texto = str(texto).upper().strip()
    
    # Remove acentos
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    
    # Substitui quebras de linha ou tabulações por espaço
    texto = re.sub(r'[\n\t\r]', ' ', texto)
    
    # Remove caracteres especiais (deixa só letras, números e espaços)
    texto = re.sub(r'[^A-Z0-9 ]', '', texto)
    
    # Remover preposições
    texto = re.sub(r'\b(DE|DO|DA|DOS|DAS|E|O|A|PARA|COM)\b', ' ', texto)

    # Substitui múltiplos espaços por um único underline (snake_case)
    texto = re.sub(r'\s+', '_', texto.strip())

    return texto

def consolidar_dataframes(lista_tabelas_aprovadas):
    """
    Recebe as tabelas aprovadas, normaliza os cabeçalhos agressivamente e 
    empilha tudo (UNION) num único DataFrame bruto.
    """
    dfs_normalizados = []
    
    for tbl in lista_tabelas_aprovadas:
        df = tbl['dados'].copy()
        
        # 1. Normaliza as colunas
        novas_colunas = [normalizar_cabecalho_extremo(c) for c in df.columns]
        
        # 2. Desduplica nomes caso a normalização tenha gerado nomes iguais (ex: duas colunas 'PRECO')
        colunas_finais = []
        vistos = {}
        for col in novas_colunas:
            if col in vistos:
                vistos[col] += 1
                colunas_finais.append(f"{col}_{vistos[col]}")
            else:
                vistos[col] = 0
                colunas_finais.append(col)
                
        df.columns = colunas_finais
        
        # 3. Adiciona a Linhagem de Dados (Rastreabilidade de onde veio cada linha)
        df['__ARQUIVO_ORIGEM__'] = tbl['arquivo']
        df['__ABA_ORIGEM__'] = tbl['aba']
        
        dfs_normalizados.append(df)
    
    # O pd.concat faz a mágica: se o nome da coluna bate 100%, ele põe embaixo. Se não, cria coluna nova.
    df_consolidado = pd.concat(dfs_normalizados, ignore_index=True)
    
    # Joga as colunas de linhagem para o começo do dataframe para ficar bonito de ler
    colunas_linhagem = ['__ARQUIVO_ORIGEM__', '__ABA_ORIGEM__']
    outras_colunas = [c for c in df_consolidado.columns if c not in colunas_linhagem]
    df_consolidado = df_consolidado[colunas_linhagem + outras_colunas]
    
    return df_consolidado