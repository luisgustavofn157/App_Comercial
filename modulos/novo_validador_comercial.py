import pandas as pd
from config_erp import DICIONARIO_ERP

def processar_validacoes(df_input, mapeamento_oficial):
    """
    Motor de Regras Comerciais - Conectado ao Dicionário do ERP.
    Usa as decisões da Etapa 3 para identificar colunas e, ao final, 
    devolve as tabelas na linguagem original do fornecedor.
    """
    df = df_input.copy()
    lista_rejeitados = []

    # ==========================================
    # 1. ENGENHARIA REVERSA DE NOMES (Fornecedor <-> ERP)
    # ==========================================
    # Reconstrói a lógica da Etapa 3 para saber exatamente o nome final no df_limpo
    colunas_uteis = {k: v for k, v in mapeamento_oficial.items() if v != DICIONARIO_ERP.get("IGNORAR", "Ignorar")}
    contagens = {}
    for destino in colunas_uteis.values():
        contagens[destino] = contagens.get(destino, 0) + 1
        
    renomeio_final = {}
    ocorrencias = {}
    for col_excel, destino in colunas_uteis.items():
        if contagens[destino] > 1:
            ocorrencias[destino] = ocorrencias.get(destino, 0) + 1
            renomeio_final[col_excel] = f"{destino} ({ocorrencias[destino]})"
        else:
            renomeio_final[col_excel] = destino

    # Dicionário mágico que vai devolver a linguagem do fornecedor no final
    inverso_renomeio = {v: k for k, v in renomeio_final.items()}

    # ==========================================
    # 2. MAPEAMENTO ESTRITO COM O DICIONARIO_ERP
    # ==========================================
    def pegar_conceito(chaves_possiveis, fallback_palavra=None):
        for k in chaves_possiveis:
            if k in DICIONARIO_ERP:
                return DICIONARIO_ERP[k]
        if fallback_palavra:
            for k, v in DICIONARIO_ERP.items():
                if fallback_palavra in str(k).upper():
                    return v
        return None

    col_sku = pegar_conceito(["SKU", "CODIGO"])
    col_preco = pegar_conceito(["PRECO_BRUTO", "PRECO", "PRECO_BASE"], "PRECO")
    col_ncm = pegar_conceito(["NCM"])
    col_cst = pegar_conceito(["CST"])

    def rejeitar_linhas(mask, motivo):
        nonlocal df
        if mask.any():
            df_rej = df[mask].copy()
            df_rej.insert(0, "Motivo Rejeição", motivo)
            lista_rejeitados.append(df_rej)
            df = df[~mask]

    # ==========================================
    # REGRAS DE NEGÓCIO DA REDE ÂNCORA
    # ==========================================
    
    # Regra 1 e 2: Fantasmas e Cabeçalhos
    if col_sku and col_sku in df.columns:
        df[col_sku] = df[col_sku].astype(str).str.strip()
        mask_fantasma = df[col_sku].str.upper().isin(['', 'NAN', 'NONE', 'NULL'])
        rejeitar_linhas(mask_fantasma, "Produto sem Código (Fantasma)")
        
        mask_cabecalho = df[col_sku].str.upper().isin(['CODIGO', 'CÓDIGO', 'COD. FORNECEDOR', 'CODIGO FORNECEDOR', 'SKU'])
        rejeitar_linhas(mask_cabecalho, "Linha repetida de cabeçalho")

    # Regra 3: Sanidade de Preço (Corrigido para formato BR e US)
    if col_preco and col_preco in df.columns:
        def limpar_preco(val):
            if pd.isna(val): return None
            if isinstance(val, (int, float)): return float(val)
            val_str = str(val).upper().replace('R$', '').strip()
            if not val_str or val_str in ['NAN', 'NONE', 'NULL']: return None
            if ',' in val_str:
                val_str = val_str.replace('.', '').replace(',', '.')
            try:
                return float(val_str)
            except:
                return None

        df[col_preco] = df[col_preco].apply(limpar_preco)
        mask_preco = df[col_preco].isna() | (df[col_preco] < 0)
        rejeitar_linhas(mask_preco, "Preço inválido ou negativo")

    # Regra 4: Faxineiro NCM
    if col_ncm and col_ncm in df.columns:
        df[col_ncm] = df[col_ncm].astype(str).str.replace(r'\D', '', regex=True)
        mask_ncm = (df[col_ncm] != '') & (df[col_ncm] != 'nan') & (df[col_ncm].str.len() != 8)
        rejeitar_linhas(mask_ncm, "NCM Inválido (Deve conter exatos 8 dígitos)")

    # Regra 5: CST
    if col_cst and col_cst in df.columns:
        mapa_cst = {
            '00': '0', '0': '0', '4': '0', '5': '0', 'NACIONAL': '0',
            '1': '2', '2': '2', '3': '2', '6': '2', '7': '2', '8': '2', '9': '2', 'IMPORTADO': '2', 'ESTRANGEIRO': '2'
        }
        df_cst_limpo = df[col_cst].astype(str).str.strip().str.upper()
        mask_cst = (~df_cst_limpo.isin(mapa_cst.keys())) & (df_cst_limpo != '') & (df_cst_limpo != 'NAN')
        rejeitar_linhas(mask_cst, "CST Desconhecido ou Inválido")
        df.loc[df_cst_limpo.isin(mapa_cst.keys()), col_cst] = df_cst_limpo.map(mapa_cst)

    # REGRA 6: A GUERRA DOS DUPLICADOS
    
    # 6.1 Isolar os metadados: Comparamos apenas as colunas reais do fornecedor
    colunas_reais = [c for c in df.columns if not str(c).startswith('__')]
    
    # 6.2 Cura e Quarentena: Acha duplicatas exatas nas colunas reais e joga no lixo (mantendo a 1ª)
    mask_100_duplicado = df.duplicated(subset=colunas_reais, keep='first')
    rejeitar_linhas(mask_100_duplicado, "Linha 100% duplicada (Mesmos dados, abas/arquivos diferentes)")

    # 6.3 O Purgatório: O que sobrou com o mesmo SKU tem dados comerciais diferentes (Conflito)
    if col_sku and col_sku in df.columns:
        mask_conflito = df.duplicated(subset=[col_sku], keep=False)
        df_conflitos = df[mask_conflito].copy()
        df_aprovados = df[~mask_conflito].copy()
    else:
        df_conflitos = pd.DataFrame()
        df_aprovados = df.copy()

    # Consolidação dos Rejeitados
    if lista_rejeitados:
        df_rejeitados = pd.concat(lista_rejeitados, ignore_index=True)
    else:
        df_rejeitados = pd.DataFrame(columns=df.columns.insert(0, "Motivo Rejeição"))

    # ==========================================
    # 3. RETORNO PARA A LINGUAGEM DO FORNECEDOR
    # ==========================================
    df_aprovados = df_aprovados.rename(columns=inverso_renomeio)
    
    if not df_rejeitados.empty:
        df_rejeitados = df_rejeitados.rename(columns=inverso_renomeio)
        
    if not df_conflitos.empty:
        df_conflitos = df_conflitos.rename(columns=inverso_renomeio)

    return df_aprovados, df_rejeitados, df_conflitos