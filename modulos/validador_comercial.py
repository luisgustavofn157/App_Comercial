import pandas as pd
import numpy as np

def higienizar_dados(df_mapeado):
    """
    FASE 1: Tratamento de Tipagem e Limpeza Visual.
    Transforma strings em floats, limpa caracteres especiais.
    """
    df = df_mapeado.copy()
    colunas = df.columns.tolist()
    
    col_ncm = next((c for c in colunas if "NCM" in c.upper()), None)
    col_ean = next((c for c in colunas if "EAN" in c.upper() or "BARRAS" in c.upper()), None)
    col_ipi = next((c for c in colunas if "IPI" in c.upper()), None)
    
    # Pega todas as colunas que envolvem dinheiro/percentual para converter
    cols_financeiras = [c for c in colunas if any(palavra in c.upper() for palavra in ["PREÇO", "PRECO", "CUSTO", "DESCONTO", "POLÍTICA"])]

    # Limpeza de NCM e EAN
    if col_ncm:
        df[col_ncm] = df[col_ncm].astype(str).str.replace(r'[\.\-\s]', '', regex=True)
        df[col_ncm] = df[col_ncm].replace(['nan', 'NaN', 'None', '<NA>'], '')
    if col_ean:
        df[col_ean] = df[col_ean].astype(str).str.replace(r'\D', '', regex=True)
        df[col_ean] = df[col_ean].replace(['nan', 'NaN', 'None', '<NA>'], '')

    # Limpeza Financeira Universal (Transfoma em Float)
    for col_fin in cols_financeiras:
        df[col_fin] = df[col_fin].astype(str).str.upper().str.replace('R$', '', regex=False).str.replace('$', '', regex=False).str.strip()
        df[col_fin] = df[col_fin].apply(lambda x: x.replace('.', '').replace(',', '.') if ',' in x and '.' in x else x.replace(',', '.') if ',' in x else x)
        df[col_fin] = pd.to_numeric(df[col_fin], errors='coerce')

    # Limpeza de IPI
    if col_ipi:
        df[col_ipi] = df[col_ipi].astype(str).str.replace('%', '', regex=False).str.replace(',', '.').str.strip()
        df[col_ipi] = pd.to_numeric(df[col_ipi], errors='coerce')
        if df[col_ipi].max() <= 1.0 and df[col_ipi].max() > 0:
            df[col_ipi] = df[col_ipi] * 100
            
    return df


def processar_validacoes(df_higienizado):
    """
    FASE 2: Motor de Regras de Negócio da Rede Âncora.
    Recebe os dados limpos, audita os erros e separa o Joio do Trigo.
    """
    df = df_higienizado.copy()
    erros_por_linha = {i: [] for i in df.index}
    
    colunas = df.columns.tolist()
    col_sku = next((c for c in colunas if "SKU" in c.upper() or "CÓD" in c.upper()), None)
    col_ncm = next((c for c in colunas if "NCM" in c.upper()), None)
    
    # Pode existir mais de um preço, vamos validar o Principal (Preço Base)
    col_preco_base = next((c for c in colunas if "PREÇO BASE" in c.upper() or "PRECO BASE" in c.upper()), None)

    for idx, row in df.iterrows():
        # Validação SKU
        if col_sku:
            val_sku = str(row[col_sku]).strip()
            if val_sku in ["", "nan", "None", "<NA>"]:
                erros_por_linha[idx].append("SKU Vazio")
                
        # Validação NCM
        if col_ncm:
            val_ncm = str(row[col_ncm])
            if val_ncm != "": 
                if not val_ncm.isdigit() or len(val_ncm) != 8:
                    erros_por_linha[idx].append(f"NCM Inválido ({val_ncm})")

        # Validação Preço Base
        if col_preco_base:
            val_preco = row[col_preco_base]
            if pd.isna(val_preco):
                erros_por_linha[idx].append("Preço base inválido ou nulo")
            elif val_preco <= 0:
                erros_por_linha[idx].append("Preço base zerado ou negativo")

    # Duplicidade de SKU
    if col_sku:
        duplicados = df[df.duplicated(subset=[col_sku], keep=False)]
        for idx in duplicados.index:
            val_sku = df.at[idx, col_sku]
            if str(val_sku).strip() not in ["", "nan", "None"]:
                erros_por_linha[idx].append("SKU Duplicado")

    # Compilação
    df['Motivos de Rejeição'] = [ " | ".join(erros_por_linha[i]) for i in df.index ]
    mask_tem_erro = df['Motivos de Rejeição'] != ""
    
    df_rejeitados = df[mask_tem_erro].copy()
    df_aprovados = df[~mask_tem_erro].drop(columns=['Motivos de Rejeição']).copy()
    
    return df_aprovados, df_rejeitados