import pandas as pd
import numpy as np

def aplicar_filtro_morte(df_bruto, col_sku_original):
    """
    Filtro de Morte (Executado ANTES de jogar as colunas fora).
    Remove lixo puro: Linhas duplicadas 100%, Cabeçalhos no meio da planilha, SKUs vazios.
    """
    df = df_bruto.copy()
    linhas_excluidas = []
    
    # 1. Linhas 100% Duplicadas
    duplicadas_mask = df.duplicated(keep='first')
    if duplicadas_mask.any():
        df_dup = df[duplicadas_mask].copy()
        df_dup['Motivo de Exclusão'] = "Linha 100% Duplicada"
        linhas_excluidas.append(df_dup)
        df = df[~duplicadas_mask]

    # 2 e 3. Exclusões Baseadas no SKU
    if col_sku_original and col_sku_original in df.columns:
        # Pega a coluna como texto puro
        sku_str = df[col_sku_original].astype(str).str.strip().str.lower()
        
        # Máscara: SKU Vazio
        vazio_mask = sku_str.isin(["", "nan", "none", "<na>"]) | df[col_sku_original].isna()
        if vazio_mask.any():
            df_vazio = df[vazio_mask].copy()
            df_vazio['Motivo de Exclusão'] = "SKU Vazio ou Nulo"
            linhas_excluidas.append(df_vazio)
            df = df[~vazio_mask]
            
        # Máscara: Cabeçalho Repetido (O valor do SKU é igual ao nome da coluna)
        cabecalho_mask = df[col_sku_original].astype(str).str.strip() == str(col_sku_original).strip()
        if cabecalho_mask.any():
            df_cab = df[cabecalho_mask].copy()
            df_cab['Motivo de Exclusão'] = "Linha de Cabeçalho Repetida"
            linhas_excluidas.append(df_cab)
            df = df[~cabecalho_mask]

    # Consolida o Lixo
    if linhas_excluidas:
        df_lixo = pd.concat(linhas_excluidas, ignore_index=True)
    else:
        df_lixo = pd.DataFrame(columns=list(df.columns) + ['Motivo de Exclusão'])

    return df, df_lixo

def higienizar_dados(df_mapeado):
    """FASE 1: Tratamento de Tipagem e Limpeza Visual para o Motor ERP."""
    df = df_mapeado.copy()
    colunas = df.columns.tolist()
    
    col_ncm = next((c for c in colunas if "NCM" in c.upper()), None)
    col_ean = next((c for c in colunas if "EAN" in c.upper() or "BARRAS" in c.upper()), None)
    col_ipi = next((c for c in colunas if "IPI" in c.upper()), None)
    
    cols_financeiras = [c for c in colunas if any(palavra in c.upper() for palavra in ["PREÇO", "PRECO", "CUSTO", "DESCONTO", "POLÍTICA"])]

    if col_ncm:
        df[col_ncm] = df[col_ncm].astype(str).str.replace(r'[\.\-\s]', '', regex=True)
        df[col_ncm] = df[col_ncm].replace(['nan', 'NaN', 'None', '<NA>'], '')
    if col_ean:
        df[col_ean] = df[col_ean].astype(str).str.replace(r'\D', '', regex=True)
        df[col_ean] = df[col_ean].replace(['nan', 'NaN', 'None', '<NA>'], '')

    for col_fin in cols_financeiras:
        df[col_fin] = df[col_fin].astype(str).str.upper().str.replace('R$', '', regex=False).str.replace('$', '', regex=False).str.strip()
        df[col_fin] = df[col_fin].apply(lambda x: x.replace('.', '').replace(',', '.') if ',' in x and '.' in x else x.replace(',', '.') if ',' in x else x)
        df[col_fin] = pd.to_numeric(df[col_fin], errors='coerce')

    if col_ipi:
        df[col_ipi] = df[col_ipi].astype(str).str.replace('%', '', regex=False).str.replace(',', '.').str.strip()
        df[col_ipi] = pd.to_numeric(df[col_ipi], errors='coerce')
        if df[col_ipi].max() <= 1.0 and df[col_ipi].max() > 0:
            df[col_ipi] = df[col_ipi] * 100
            
    return df

def processar_validacoes(df_higienizado):
    """FASE 2: Motor de Regras de Negócio - HARD STOP."""
    df = df_higienizado.copy()
    erros_por_linha = {i: [] for i in df.index}
    
    colunas = df.columns.tolist()
    col_sku = next((c for c in colunas if "SKU" in c.upper() or "CÓD" in c.upper()), None)
    col_ncm = next((c for c in colunas if "NCM" in c.upper()), None)
    col_preco_base = next((c for c in colunas if "PREÇO BASE" in c.upper() or "PRECO BASE" in c.upper()), None)
    col_preco_promo = next((c for c in colunas if "PREÇO PROMOCIONAL" in c.upper() or "PRECO PROMO" in c.upper()), None)

    for idx, row in df.iterrows():
        # NCM
        if col_ncm:
            val_ncm = str(row[col_ncm])
            if val_ncm != "": 
                if not val_ncm.isdigit() or len(val_ncm) != 8:
                    erros_por_linha[idx].append(f"NCM Inválido ({val_ncm})")

        # Preço Base
        if col_preco_base:
            val_preco = row[col_preco_base]
            if pd.isna(val_preco):
                erros_por_linha[idx].append("Preço base inválido ou nulo")
            elif val_preco <= 0:
                erros_por_linha[idx].append("Preço base zerado ou negativo")

        # Validação Cruzada: Promoção não pode ser maior que a Base
        if col_preco_base and col_preco_promo:
            val_base = row[col_preco_base]
            val_promo = row[col_preco_promo]
            if pd.notna(val_base) and pd.notna(val_promo):
                if val_promo >= val_base:
                    erros_por_linha[idx].append("Preço Promocional maior ou igual ao Preço Base")

    # Duplicidade de SKU (O Morte já tirou a 100% igual. O que sobrar aqui é SKU igual com preço diferente)
    if col_sku:
        duplicados = df[df.duplicated(subset=[col_sku], keep=False)]
        for idx in duplicados.index:
            erros_por_linha[idx].append("SKU Duplicado (Dados conflitantes na planilha)")

    df['Motivos de Rejeição'] = [ " | ".join(erros_por_linha[i]) for i in df.index ]
    mask_tem_erro = df['Motivos de Rejeição'] != ""
    
    df_rejeitados = df[mask_tem_erro].copy()
    df_aprovados = df[~mask_tem_erro].drop(columns=['Motivos de Rejeição']).copy()
    
    return df_aprovados, df_rejeitados