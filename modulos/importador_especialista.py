import pandas as pd
import unicodedata
import numpy as np

# ==========================================
# DICIONÁRIOS DE CONCEITOS (SEMÂNTICA)
# ==========================================
CONCEITO_CODIGO = ["cod", "sku", "ean", "ref", "fabrica", "partnumber", "pn"]
CONCEITO_PRECO = ["preco", "valor", "custo", "tabela", "venda", "bruto", "liquido"]

def normalizar_texto(texto):
    if pd.isna(texto): return ""
    texto = str(texto).lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def deduplicar_colunas(colunas):
    """
    Garante que não existam colunas com nomes iguais ou vazios, 
    adicionando sufixos numéricos (ex: preco, preco_1, preco_2).
    """
    nomes_vistos = {}
    novas_colunas = []
    
    for i, col in enumerate(colunas):
        # 1. Trata colunas que ficaram totalmente sem nome
        if not col or str(col).strip() == "":
            col = f"col_vazia_{i}"
            
        # 2. Trata colunas com nomes repetidos
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
    
    # Procura termos comerciais gerais para achar o cabeçalho
    palavras_gerais = CONCEITO_CODIGO + CONCEITO_PRECO + ["descricao", "produto", "ipi", "ncm", "icms"]
    
    for texto in textos_normalizados:
        for palavra in palavras_gerais:
            if palavra in texto:
                termos_encontrados += 1
                break
                
    nota += (termos_encontrados * 10)
    return nota

# ==========================================
# FASE 2: PERFILAMENTO DE DADOS (COMPORTAMENTO)
# ==========================================
def analisar_comportamento_colunas(df):
    """
    Analisa os dados REAIS da tabela para confirmar se os conceitos de Código e Preço existem,
    seja pelo nome do cabeçalho ou pelo tipo de dado contido na coluna.
    """
    tem_conceito_codigo = False
    tem_conceito_preco = False
    
    colunas = [normalizar_texto(col) for col in df.columns]
    
    # 1. Validação Semântica (Pelo nome do cabeçalho)
    for col in colunas:
        if any(termo in col for termo in CONCEITO_CODIGO): tem_conceito_codigo = True
        if any(termo in col for termo in CONCEITO_PRECO): tem_conceito_preco = True
            
    # 2. Inferência de Tipo de Dado (Caso o cabeçalho seja bizarro, olhamos os dados)
    # Se ainda não achamos um preço pelo nome, vamos procurar colunas estritamente numéricas
    if not tem_conceito_preco:
        for col in df.columns:
            # Tenta converter a coluna para número (ignorando erros)
            numeros = pd.to_numeric(df[col], errors='coerce')
            # Se mais de 80% da coluna for número válido, ela se comporta como um preço/custo
            if numeros.notna().mean() > 0.8:
                tem_conceito_preco = True
                break

    # Se ainda não achamos um código pelo nome, procuramos colunas com alta exclusividade
    if not tem_conceito_codigo:
        for col in df.columns:
            # Uma coluna de códigos tem muitos valores únicos (alta cardinalidade)
            qtd_unicos = df[col].nunique()
            qtd_total = len(df[col].dropna())
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
    
    limite_busca = min(50, len(df))
    for i in range(limite_busca):
        nota = pontuar_linha_cabecalho(df.iloc[i].values)
        if nota > melhor_nota:
            melhor_nota = nota
            indice_melhor_linha = i

    if melhor_nota < 10: return None
        
    # Recorta a tabela a partir da linha vencedora
    df_recortado = df.iloc[indice_melhor_linha:].copy()
    
    # ---> A CORREÇÃO ESTÁ AQUI: Aplica a desduplicação antes de jogar pro DataFrame <---
    colunas_brutas = df_recortado.iloc[0].apply(normalizar_texto).tolist()
    df_recortado.columns = deduplicar_colunas(colunas_brutas) 
    
    # Remove a linha de cabeçalho dos dados e limpa vazios
    df_recortado = df_recortado[1:].dropna(axis=1, how='all').dropna(axis=0, how='all').reset_index(drop=True)
    
    # Só analisa o comportamento se a tabela tiver dados suficientes (evita erros)
    if len(df_recortado) > 1:
        tem_codigo, tem_preco = analisar_comportamento_colunas(df_recortado)
    else:
        tem_codigo, tem_preco = False, False

    # A CLASSIFICAÇÃO INTELIGENTE:
    if tem_codigo and tem_preco:
        sugestao = "✅ Consolidar (Lista Preço)"
        motivo = "O sistema identificou a presença de Códigos e Preços (Semântica/Tipo de Dado)."
    elif tem_codigo and not tem_preco:
        sugestao = "ℹ️ Tabela Técnica"
        motivo = "O sistema identificou Códigos, mas não encontrou padrão de Preços."
    else:
        sugestao = "❓ Pendente"
        motivo = "O sistema não conseguiu confirmar a presença da dupla Código+Preço."

    return {
        "id_unico": f"{nome_arquivo}_{nome_aba}",
        "arquivo": nome_arquivo,
        "aba": nome_aba,
        "confianca": melhor_nota,
        "sugestao_acao": sugestao, 
        "motivo_escolha": motivo,
        "dados": df_recortado
    }