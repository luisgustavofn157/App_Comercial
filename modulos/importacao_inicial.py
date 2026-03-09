import pandas as pd
import unicodedata
import numpy as np
from configuracoes.config_erp import DICIONARIO_SINONIMOS, CONCEITOS_MULTIPLOS

# ==========================================
# AUXILIARES DE SEMÂNTICA DINÂMICA
# ==========================================

SINO_PRECOS = (
    DICIONARIO_SINONIMOS.get("PRECO_BASE", [])
)

SINO_CODIGOS = (
    DICIONARIO_SINONIMOS.get("SKU", [])
)

def normalizar_texto(texto):
    if pd.isna(texto): return ""
    texto = str(texto).lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

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

# ==========================================
# FASE 1: ENCONTRAR O CABEÇALHO (RECORTE)
# ==========================================
def pontuar_linha_cabecalho(linha_valores):
    nota = 0
    celulas_preenchidas = [val for val in linha_valores if not pd.isna(val) and str(val).strip() != ""]
    densidade = len(celulas_preenchidas)
    nota += (densidade * 1) 
    
    textos_normalizados = [normalizar_texto(val) for val in celulas_preenchidas]
    termos_encontrados = 0
    
    # Agora varre todos os sinônimos do seu arquivo de configuração
    todos_sinonimos = [item for sublist in DICIONARIO_SINONIMOS.values() for item in sublist]
    
    for texto in textos_normalizados:
        for palavra in todos_sinonimos:
            #if palavra.lower() in texto:
            if palavra.lower() == texto:
                termos_encontrados += 1
                break
                
    nota += (termos_encontrados * 10)
    return nota

# ==========================================
# FASE 2: PERFILAMENTO DE DADOS (COMPORTAMENTO)
# ==========================================
def analisar_comportamento_colunas(df):
    tem_conceito_codigo = False
    tem_conceito_preco = False
    colunas = [normalizar_texto(col) for col in df.columns]
    
    # 1. Checagem por Nome de Coluna (Baseado no seu Dicionário)
    for col in colunas:
        if any(termo.lower() in col for termo in SINO_CODIGOS): tem_conceito_codigo = True
        if any(termo.lower() in col for termo in SINO_PRECOS): tem_conceito_preco = True
            
    # 2. Checagem por Conteúdo (Caso o fornecedor use nomes genéricos como "Coluna 1")
    if not tem_conceito_preco:
        for col in df.columns:
            numeros = pd.to_numeric(df[col], errors='coerce')
            # Se a coluna for majoritariamente numérica, tratamos como potencial preço
            if numeros.notna().mean() > 0.8:
                tem_conceito_preco = True
                break

    if not tem_conceito_codigo:
        for col in df.columns:
            qtd_unicos = df[col].nunique()
            qtd_total = len(df[col].dropna())
            # Se os dados são quase todos exclusivos, tratamos como SKU/Código
            if qtd_total > 0 and (qtd_unicos / qtd_total) > 0.9:
                tem_conceito_codigo = True
                break
                
    return tem_conceito_codigo, tem_conceito_preco

# ==========================================
# MOTOR PRINCIPAL
# ==========================================

def encontrar_tabela_valida(df_bruto, nome_arquivo, nome_aba):
    df = df_bruto.dropna(axis=1, how='all').dropna(axis=0, how='all').reset_index(drop=True)
    if df.empty: return None
        
    melhor_nota = 0
    indice_melhor_linha = 0
    df_recortado = None 
    
    limite_busca = min(50, len(df))
    for i in range(limite_busca):
        nota = pontuar_linha_cabecalho(df.iloc[i].values)
        if nota > melhor_nota:
            melhor_nota = nota
            indice_melhor_linha = i

    if melhor_nota < 10: 
        return None
        
    df_recortado = df.iloc[indice_melhor_linha:].copy()
    
    # --- TRATAMENTO DE COLUNAS ---
    primeira_linha = pd.Series(df_recortado.iloc[0]).ffill()
    colunas_brutas = primeira_linha.apply(normalizar_texto).tolist()
    df_recortado.columns = deduplicar_colunas(colunas_brutas) 
    
    df_recortado = df_recortado[1:].dropna(axis=1, how='all').dropna(axis=0, how='all').reset_index(drop=True)
    
    # --- REPLICAÇÃO DE DADOS (FFILL) INTELIGENTE ---
    # Só replica colunas que NÃO são preços (usando seu SINO_PRECOS)
    colunas_seguras_para_replicar = [
        col for col in df_recortado.columns 
        if not any(termo.lower() in col for termo in SINO_PRECOS)
    ]
    df_recortado[colunas_seguras_para_replicar] = df_recortado[colunas_seguras_para_replicar].ffill()
    
    # --- ANÁLISE DE COMPORTAMENTO ---
    if df_recortado is not None and len(df_recortado) > 0:
        tem_codigo, tem_preco = analisar_comportamento_colunas(df_recortado)
    else:
        tem_codigo, tem_preco = False, False

    if tem_codigo and tem_preco:
        sugestao = "Consolidar"
        motivo = "Bom candidato a lista de preços (Contém Código + Preço)."
    else:
        sugestao = "Ignorar"
        motivo = "Não aparenta ser um intervalo de lista de preços."

    return {
        "id_unico": f"{nome_arquivo}_{nome_aba}".replace(".", "_"),
        "arquivo": nome_arquivo,
        "aba": nome_aba,
        "confianca": melhor_nota,
        "sugestao_acao": sugestao, 
        "motivo_escolha": motivo,
        "dados": df_recortado
    }