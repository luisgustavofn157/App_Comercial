import pandas as pd
import numpy as np
import re
from modulos.config_erp import DICIONARIO_ERP # <--- IMPORTAMOS A FONTE DE VERDADE

def limpar_preco_br(valor):
    if pd.isna(valor) or str(valor).strip() == "": return np.nan
    if isinstance(valor, (int, float)): return float(valor)
    v = str(valor).strip()
    if ',' in v:
        v = v.replace('.', '')
        v = v.replace(',', '.')
    v = re.sub(r'[^\d.]', '', v)
    try: return float(v)
    except: return np.nan

def limpar_e_traduzir_dados(df_bruto, mapeamento_usuario):
    # --- 1. TRADUÇÃO E FILTRO DE COLUNAS ---
    colunas_para_manter = []
    renomeios = {}
    
    for col_excel, col_erp in mapeamento_usuario.items():
        if col_erp != DICIONARIO_ERP["IGNORAR"]:
            colunas_para_manter.append(col_excel)
            renomeios[col_excel] = col_erp
            
    df_traduzido = df_bruto[colunas_para_manter].copy()
    df_traduzido.rename(columns=renomeios, inplace=True)
    
    if df_traduzido.columns.duplicated().any():
        df_traduzido = df_traduzido.groupby(df_traduzido.columns, axis=1).first()
    
    # --- 2. REGRAS DE LIMPEZA REFERENCIANDO O DICIONÁRIO ---
    # Agora, se você mudar o emoji ou o texto lá no config_erp.py, o código não quebra!
    col_sku = DICIONARIO_ERP["SKU"]
    col_preco = DICIONARIO_ERP["PRECO_BASE"]
    col_desc = DICIONARIO_ERP["DESCRICAO"]
    
    if col_sku not in df_traduzido.columns or col_preco not in df_traduzido.columns:
        return df_traduzido, pd.DataFrame() 
        
    df_limpo = df_traduzido.copy()
    
    df_limpo[col_sku] = df_limpo[col_sku].replace(r'^\s*$', np.nan, regex=True)
    df_limpo[col_preco] = df_limpo[col_preco].apply(limpar_preco_br)
    
    mascara_vazios = df_limpo[col_sku].isna() | df_limpo[col_preco].isna()
    
    # --- 3. A MÁGICA DOS SUBTÍTULOS ---
    if col_desc in df_limpo.columns:
        mascara_subtitulo = mascara_vazios & df_limpo[col_desc].notna()
        df_limpo['🗂️ Categoria Extraída'] = np.where(mascara_subtitulo, df_limpo[col_desc], np.nan)
        df_limpo['🗂️ Categoria Extraída'] = df_limpo['🗂️ Categoria Extraída'].ffill()
        colunas_ordem = ['🗂️ Categoria Extraída'] + [c for c in df_limpo.columns if c != '🗂️ Categoria Extraída']
        df_limpo = df_limpo[colunas_ordem]
        
    # --- 4. SEPARAR O JOIO DO TRIGO ---
    df_lixo = df_limpo[mascara_vazios].copy()
    df_valido = df_limpo[~mascara_vazios].copy()
    
    if '🗂️ Categoria Extraída' in df_lixo.columns:
        df_lixo.drop(columns=['🗂️ Categoria Extraída'], inplace=True)
        
    df_lixo['Motivo_Descarte'] = "Falta Código (SKU) ou Preço (Possível Subtítulo)"
    
    return df_valido, df_lixo