import pandas as pd
import numpy as np
import re

# ==========================================
# ESTEIRA 1: LIMPEZA ESTRUTURAL
# ==========================================
def aplicar_limpeza_estrutural(df):
    """
    Remove duplicidades exatas e linhas sem dados vitais.
    Tudo o que for barrado aqui vai para a 'Remoção Automática'.
    """
    df_trabalho = df.copy()
    col_sku = "SKU"
    col_preco = "PRECO_BASE"
    
    # Se nem as colunas vitais existirem, barra tudo
    if col_sku not in df_trabalho.columns or col_preco not in df_trabalho.columns:
        df_trabalho["MOTIVO_REJEICAO"] = "Remoção Automática: Faltam colunas vitais (SKU ou Preço Base)"
        return pd.DataFrame(), df_trabalho

    # 1. Identificar Duplicadas Exatas (Ignorando colunas de linhagem como ABA_ORIGEM)
    colunas_de_dados = [c for c in df_trabalho.columns if not str(c).startswith("__")]
    mask_duplicadas = df_trabalho.duplicated(subset=colunas_de_dados, keep='first')
    
    df_lixo_duplicadas = df_trabalho[mask_duplicadas].copy()
    if not df_lixo_duplicadas.empty:
        df_lixo_duplicadas["MOTIVO_REJEICAO"] = "Remoção Automática: Linha 100% idêntica a outra já processada"
        
    df_trabalho = df_trabalho[~mask_duplicadas].copy()

    # 2. Higienização rápida de vazios para a guilhotina
    df_trabalho[col_sku] = df_trabalho[col_sku].replace([None, 'nan', 'None', '', ' '], np.nan)
    df_trabalho[col_preco] = df_trabalho[col_preco].replace([None, 'nan', 'None', '', ' '], np.nan)

    # 3. A Guilhotina (Máscara de Validação)
    mask_valida = df_trabalho[col_sku].notna() & df_trabalho[col_preco].notna()
    
    df_vivos = df_trabalho[mask_valida].copy()
    df_lixo_guilhotina = df_trabalho[~mask_valida].copy()
    
    if not df_lixo_guilhotina.empty:
        df_lixo_guilhotina["MOTIVO_REJEICAO"] = "Remoção Automática: Falta SKU ou Preço Base"
        
    # 4. Consolida todo o lixo eliminatório
    dfs_lixo = []
    if not df_lixo_duplicadas.empty: dfs_lixo.append(df_lixo_duplicadas)
    if not df_lixo_guilhotina.empty: dfs_lixo.append(df_lixo_guilhotina)
    df_remocao_automatica = pd.concat(dfs_lixo, ignore_index=True) if dfs_lixo else pd.DataFrame()
    
    # 5. Ordenação Alfabética
    if not df_vivos.empty:
        df_vivos[col_sku] = df_vivos[col_sku].astype(str).str.strip()
        df_vivos = df_vivos.sort_values(by=col_sku).reset_index(drop=True)

    return df_vivos, df_remocao_automatica


# ==========================================
# ESTEIRA 2: PADRONIZAÇÃO E CONVERSÃO
# ==========================================
def converter_br_para_float(valor):
    """Motor robusto para transformar formatos pt-BR em Float nativo."""
    if pd.isna(valor) or str(valor).strip() in ["", "-", "NaN", "None"]:
        return np.nan
        
    if isinstance(valor, (int, float)):
        return float(valor)
        
    texto_limpo = re.sub(r'[^\d,\.-]', '', str(valor).strip())
    
    if not texto_limpo: 
        return np.nan
    
    qtd_pontos = texto_limpo.count('.')
    qtd_virgulas = texto_limpo.count(',')
    
    if qtd_virgulas == 1 and qtd_pontos > 0:
        texto_limpo = texto_limpo.replace('.', '').replace(',', '.')
    elif qtd_virgulas == 1 and qtd_pontos == 0:
        texto_limpo = texto_limpo.replace(',', '.')
    elif qtd_pontos == 1 and qtd_virgulas > 0:
        texto_limpo = texto_limpo.replace(',', '')
    elif qtd_pontos > 1 and qtd_virgulas == 0:
        texto_limpo = texto_limpo.replace('.', '')
        
    try:
        return float(texto_limpo)
    except ValueError:
        return np.nan

def formatar_ncm(valor):
    """Extrai números, mantém zeros à esquerda e limita a 8 dígitos."""
    if pd.isna(valor): return valor
    numeros = re.sub(r'\D', '', str(valor))
    if not numeros: return "ERRO"
    return numeros[:8]

def formatar_multiplo(valor):
    """Extrai apenas a parte numérica de textos como 'caixa com 12'."""
    if pd.isna(valor) or str(valor).strip() == "": return np.nan
    texto = str(valor).strip()
    match = re.search(r'\d+', texto)
    if match:
        return float(match.group())
    return "ERRO"

def formatar_percentual(valor):
    """Lida com IPI/ICMS lidando com frações (0.0975) ou formatos literais (9,75%)."""
    if pd.isna(valor) or str(valor).strip() in ["", "-", "NaN", "None"]: return np.nan
    texto_original = str(valor).strip()
    tem_simbolo = '%' in texto_original
    
    numero = converter_br_para_float(valor)
    
    if pd.isna(numero): return np.nan
    if numero == 0: return 0.0
    
    # Se o valor for uma fração decimal e não tiver símbolo explícito, normalizamos para 100
    if 0 < abs(numero) <= 1.5 and not tem_simbolo:
        return numero * 100.0
        
    return float(numero)

def aplicar_padronizacao(df):
    """Aplica as funções de formatação dinamicamente pelas palavras-chave da coluna."""
    df_formatado = df.copy()
    
    if "NCM" in df_formatado.columns:
        df_formatado["NCM"] = df_formatado["NCM"].apply(formatar_ncm)
        
    if "MULTIPLO" in df_formatado.columns:
        df_formatado["MULTIPLO"] = df_formatado["MULTIPLO"].apply(formatar_multiplo)
        
    colunas_moeda = [c for c in df_formatado.columns if any(termo in str(c) for termo in ["PRECO", "CUSTO"])]
    for col in colunas_moeda:
        df_formatado[col] = df_formatado[col].apply(converter_br_para_float)
        
    colunas_percentuais = [c for c in df_formatado.columns if any(termo in str(c) for termo in ["IPI", "ICMS", "ST", "MARGEM", "DESCONTO"])]
    for col in colunas_percentuais:
        df_formatado[col] = df_formatado[col].apply(formatar_percentual)
        
    for col in df_formatado.columns:
        if df_formatado[col].dtype == 'object':
            df_formatado[col] = df_formatado[col].apply(lambda x: str(x).strip() if pd.notna(x) else x)
            
    return df_formatado


# ==========================================
# ESTEIRA 3: VALIDAÇÃO LÓGICA DE NEGÓCIO
# ==========================================
def aplicar_validacao_logica(df):
    """Inspeciona as colunas formatadas e carimba erros em quem falhou."""
    df_validado = df.copy()
    df_validado["ALERTAS_SISTEMA"] = ""
    
    # 1. Validação do NCM
    if "NCM" in df_validado.columns:
        mask_ncm_erro = df_validado["NCM"] == "ERRO"
        mask_ncm_curto = df_validado["NCM"].notna() & (df_validado["NCM"] != "ERRO") & (df_validado["NCM"].astype(str).str.len() != 8)
        
        df_validado.loc[mask_ncm_erro, "ALERTAS_SISTEMA"] += "[NCM Inválido (Sem números)] "
        df_validado.loc[mask_ncm_curto, "ALERTAS_SISTEMA"] += "[NCM Inválido (Diferente de 8 dígitos)] "
        df_validado.loc[mask_ncm_erro, "NCM"] = np.nan
        
    # 2. Validação do Múltiplo
    if "MULTIPLO" in df_validado.columns:
        mask_mult_erro = df_validado["MULTIPLO"] == "ERRO"
        df_validado.loc[mask_mult_erro, "ALERTAS_SISTEMA"] += "[Múltiplo Inválido (Não contém números)] "
        df_validado.loc[mask_mult_erro, "MULTIPLO"] = np.nan

    return df_validado


# ==========================================
# MÓDULO ERP (Simulação Segura)
# ==========================================
def aplicar_validacao_erp(df):
    """
    Realiza a conferência com a base do ERP (Benner).
    Acionado apenas após a base estar 100% limpa (Passo 4).
    """
    df_cruzado = df.copy()
    # TODO: Implementar a chamada ao banco de dados Benner real aqui.
    # Por agora, devolve os dados limpos intactos.
    return df_cruzado


# ==========================================
# ORQUESTRADOR CENTRAL (A Separação em 3 Caixas)
# ==========================================
def executar_motor_silver(df_bronze_mapeado):
    """
    Recebe a camada Bronze Mapeada e separa em:
    1. Gold (100% perfeitos)
    2. Remocao Automatica (Lixo estrutural)
    3. Com Erros (Quarentena/Conflitos)
    """
    # 1. Guilhotina Estrutural
    df_vivos, df_remocao_auto = aplicar_limpeza_estrutural(df_bronze_mapeado)
    if df_vivos.empty:
        return pd.DataFrame(), df_remocao_auto, pd.DataFrame()
        
    # 2. Transforma e Valida
    df_silver = aplicar_padronizacao(df_vivos)
    df_silver = aplicar_validacao_logica(df_silver)
    
    # 3. Adiciona os Conflitos (SKU repetido na base viva) na Quarentena de Erros
    col_sku = "SKU"
    if col_sku in df_silver.columns:
        mask_conflitos = df_silver.duplicated(subset=[col_sku], keep=False)
        df_silver.loc[mask_conflitos, "ALERTAS_SISTEMA"] += "[Conflito: SKU Duplicado com informações divergentes] "
        
    # 4. A SEPARAÇÃO FINAL
    mask_tem_erro = df_silver["ALERTAS_SISTEMA"] != ""
    
    df_com_erros = df_silver[mask_tem_erro].copy()
    df_gold = df_silver[~mask_tem_erro].copy()
    
    # Remove a coluna de alertas dos perfeitos
    if "ALERTAS_SISTEMA" in df_gold.columns:
        df_gold = df_gold.drop(columns=["ALERTAS_SISTEMA"])
    
    return df_gold, df_remocao_auto, df_com_erros