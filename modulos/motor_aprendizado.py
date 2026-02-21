import json
import os
import unicodedata
import re
from difflib import SequenceMatcher
import pandas as pd

FICHEIRO_MEMORIA = "memoria_mapeamento.json"

# ==========================================
# PILAR 1: DICIONÁRIO DE SINÔNIMOS (LÉXICO)
# ==========================================
# A IA já nasce sabendo os jargões do mercado de autopeças.
DICIONARIO_SINONIMOS = {
    "SKU": ["COD", "CODIGO", "REF", "REFERENCIA", "PROD", "PRODUTO", "ITEM", "PARTNUMBER", "DS", "BOSH"],
    "Preço Base": ["PRECO", "VLR", "VALOR", "CUSTO", "PRC", "TABELA", "BRUTO", "UNITARIO", "VENDA"],
    "Preço Promocional": ["PROMO", "LIQUIDO", "LIQ", "FINAL", "DESCONTADO", "OFERTA", "CAMPANHA"],
    "IPI": ["IPI", "IMPOSTO", "ALIQ", "ALIQUOTA"],
    "Desconto": ["DESC", "DESCONTO", "LIVRE", "REBATE", "BONIF"],
    "NCM": ["NCM", "FISCAL", "CLASS", "CLASSIFICACAO", "TIPI"],
    "CST": ["CST", "ORIGEM", "TRIBUTACAO", "O", "C", "S", "T"],
    "Descrição": ["DESC", "DESCRICAO", "NOME", "MATERIAL", "APLICACAO", "TEXTO"],
    "Múltiplo": ["MULT", "MULTIPLO", "CX", "CAIXA", "EMB", "EMBALAGEM", "QTD", "MINIMO", "QNT", "PADRAO"],
    "EAN": ["EAN", "BARRAS", "GTIN", "CEAN", "CODBARRAS"],
    "Marca": ["MARCA", "FABRICANTE", "FORNECEDOR", "LINHA"]
}

def normalizar_termo(termo):
    if pd.isna(termo) or str(termo).strip() == "": return ""
    t = str(termo).upper().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')

def carregar_memoria():
    if not os.path.exists(FICHEIRO_MEMORIA): return {}
    with open(FICHEIRO_MEMORIA, 'r', encoding='utf-8') as f: return json.load(f)

def salvar_memoria(memoria):
    with open(FICHEIRO_MEMORIA, 'w', encoding='utf-8') as f: json.dump(memoria, f, indent=4, ensure_ascii=False)

def obter_chave(termo_a, termo_b):
    termos = sorted([normalizar_termo(termo_a), normalizar_termo(termo_b)])
    return f"{termos[0]}|{termos[1]}"

# ==========================================
# PILAR 2: DATA PROFILING (DNA DA COLUNA)
# ==========================================
def analisar_dna_coluna(serie_dados, conceito_erp):
    """
    Analisa uma amostra de 10 linhas da coluna para caçar padrões matemáticos (NCM, CST, EAN).
    Retorna um bônus de 0 a 40 pontos.
    """
    if serie_dados is None or serie_dados.dropna().empty: return 0
    
    # Pega uma amostra rápida convertida para string
    amostra = serie_dados.dropna().astype(str).head(10).tolist()
    bonus = 0
    
    # 1. Caçador de NCM (DNA: 8708.99.90 ou 87089990/IMP)
    if "NCM" in conceito_erp:
        acertos = sum(1 for v in amostra if re.match(r'^\d{4}\.?\d{2}\.?\d{2}', v.strip()))
        if acertos / len(amostra) >= 0.5: bonus += 40  # Se mais da metade bateu o padrão, é NCM!
        
    # 2. Caçador de CST / Origem (DNA: 0, 1, 2... ou textos como "Nac", "Imp")
    elif "CST" in conceito_erp or "Origem" in conceito_erp:
        acertos = 0
        for v in amostra:
            v_limpo = v.strip().upper()
            if re.match(r'^\d{1,3}$', v_limpo): acertos += 1 # Apenas dígitos (ex: 0, 040)
            elif v_limpo in ["NAC", "NACIONAL", "IMP", "IMPORTADO"]: acertos += 1
        if acertos / len(amostra) >= 0.5: bonus += 40

    # 3. Caçador de EAN (DNA: Apenas números, 13 ou 14 dígitos)
    elif "EAN" in conceito_erp:
        acertos = sum(1 for v in amostra if re.match(r'^\d{13,14}$', v.strip()))
        if acertos / len(amostra) >= 0.5: bonus += 40

    return bonus

# ==========================================
# O MOTOR CENTRAL (ENSEMBLE)
# ==========================================
def calcular_confianca(coluna_excel, conceito_erp, fornecedor="GERAL", serie_dados=None):
    """
    Calcula a confiança unindo: 1. Fuzzy Matching + Sinônimos | 2. DNA da Coluna | 3. Memória Histórica
    """
    col_norm = normalizar_termo(coluna_excel)
    conceito_norm = normalizar_termo(conceito_erp)
    
    # --- PILAR 1: LÉXICO (Fuzzy + Sinônimos) ---
    similaridade_base = SequenceMatcher(None, col_norm, conceito_norm).ratio() * 100
    
    # Procura nos sinônimos para dar um salto de confiança
    for chave_sinonimo, lista_termos in DICIONARIO_SINONIMOS.items():
        if normalizar_termo(chave_sinonimo) in conceito_norm:
            for termo in lista_termos:
                if termo in col_norm:
                    similaridade_base = max(similaridade_base, 75.0) # Bônus imediato por ser sinônimo de mercado
                    break
                    
    # --- PILAR 2: DNA DA COLUNA (Profiling) ---
    bonus_dna = analisar_dna_coluna(serie_dados, conceito_erp)
    
    # --- PILAR 3: MEMÓRIA DO USUÁRIO (O Chefe) ---
    memoria = carregar_memoria()
    chave = obter_chave(coluna_excel, conceito_erp)
    
    contagem_aprovacoes = 0
    if fornecedor in memoria and chave in memoria[fornecedor]:
        contagem_aprovacoes = memoria[fornecedor][chave]
        
    # Matemática agressiva: Se o analista confirmou 2 vezes, a máquina obedece cegamente (100%)
    bonus_memoria = contagem_aprovacoes * 50.0 
    
    # A nota final é a junção do Cabeçalho + DNA da Célula + O que o usuário ensinou
    nota_final = min(similaridade_base + bonus_dna + bonus_memoria, 100.0) 
    
    return {
        "confianca_total": round(nota_final, 1),
        "similaridade_texto": round(similaridade_base, 1),
        "bonus_dna": round(bonus_dna, 1),
        "bonus_memoria": round(bonus_memoria, 1),
        "vezes_confirmado": contagem_aprovacoes
    }

def registar_aprendizado(termo_a, termo_b, fornecedor="GERAL"):
    memoria = carregar_memoria()
    chave = obter_chave(termo_a, termo_b)
    if fornecedor not in memoria: memoria[fornecedor] = {}
    if chave not in memoria[fornecedor]: memoria[fornecedor][chave] = 1
    else: memoria[fornecedor][chave] += 1
    salvar_memoria(memoria)

def esquecer_aprendizado(termo_a, termo_b, fornecedor="GERAL"):
    memoria = carregar_memoria()
    chave = obter_chave(termo_a, termo_b)
    if fornecedor in memoria and chave in memoria[fornecedor]:
        memoria[fornecedor][chave] = 0
        salvar_memoria(memoria)