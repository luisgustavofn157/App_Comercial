import pandas as pd
import unicodedata
from configuracoes.config_erp import DICIONARIO_SINONIMOS

# ==========================================
# CONSTANTES COMPUTADAS NA INICIALIZAÇÃO (Otimização de Memória)
# ==========================================
def normalizar_texto(texto):
    """Remove acentos, espaços extra e passa para minúsculas."""
    if pd.isna(texto): return ""
    texto = str(texto).lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# Computa os sets UMA ÚNICA VEZ ao carregar o módulo (Performance Máxima)
SINO_PRECOS = {normalizar_texto(t) for t in DICIONARIO_SINONIMOS.get("PRECO_BASE", [])}
SINO_CODIGOS = {normalizar_texto(t) for t in DICIONARIO_SINONIMOS.get("SKU", [])}

# Cria um SET com todos os sinónimos já normalizados para busca instantânea O(1)
TODOS_SINONIMOS_SET = {
    normalizar_texto(item) 
    for sublist in DICIONARIO_SINONIMOS.values() 
    for item in sublist
}

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
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
    """Pontua a linha usando interseção de conjuntos matemáticos."""
    celulas_preenchidas = [val for val in linha_valores if pd.notna(val) and str(val).strip() != ""]
    if not celulas_preenchidas: return 0
    
    nota = len(celulas_preenchidas) * 1  # Pontuação base por densidade
    
    # Transforma a linha atual num Set de palavras normalizadas
    textos_linha_set = {normalizar_texto(val) for val in celulas_preenchidas}
    
    # Interseção instantânea com todos os sinónimos do sistema
    termos_encontrados = len(textos_linha_set.intersection(TODOS_SINONIMOS_SET))
    
    nota += (termos_encontrados * 10)
    return nota

# ==========================================
# FASE 2: PERFILAMENTO DE DADOS (COMPORTAMENTO)
# ==========================================
def analisar_comportamento_colunas(df):
    tem_conceito_codigo = False
    tem_conceito_preco = False
    colunas_normalizadas = [normalizar_texto(col) for col in df.columns]
    
    # 1. Checagem por Nome de Coluna
    for col in colunas_normalizadas:
        partes_coluna = set(col.split())
        if partes_coluna.intersection(SINO_CODIGOS): tem_conceito_codigo = True
        if partes_coluna.intersection(SINO_PRECOS): tem_conceito_preco = True
            
    # 2. Checagem por Conteúdo Heurístico (Seguro)
    if not tem_conceito_preco:
        for col in df.columns:
            # Garante que é numérico e tem formato de preço (evita EANs)
            if pd.api.types.is_float_dtype(df[col]) or pd.api.types.is_numeric_dtype(df[col]):
                if df[col].notna().mean() > 0.8:
                    tem_conceito_preco = True
                    break

    if not tem_conceito_codigo:
        for col in df.columns:
            qtd_total = len(df[col].dropna())
            if qtd_total > 0:
                # Se a coluna tem quase 100% de valores únicos, é um candidato a SKU
                if (df[col].nunique() / qtd_total) > 0.9:
                    tem_conceito_codigo = True
                    break
                
    return tem_conceito_codigo, tem_conceito_preco

# ==========================================
# MOTOR PRINCIPAL (A INTELIGÊNCIA)
# ==========================================
def encontrar_tabela_valida(df_bruto, nome_arquivo, nome_aba):
    """
    Recebe o DataFrame cru do leitor_arquivos.py, recorta o lixo do topo,
    avalia o comportamento e devolve o Dicionário Padrão da Landing Zone.
    """
    df = df_bruto.dropna(axis=1, how='all').dropna(axis=0, how='all').reset_index(drop=True)
    if df.empty: return None
        
    melhor_nota = 0
    indice_melhor_linha = 0
    
    # Procura o cabeçalho nas primeiras 50 linhas
    limite_busca = min(50, len(df))
    for i in range(limite_busca):
        nota = pontuar_linha_cabecalho(df.iloc[i].values)
        if nota > melhor_nota:
            melhor_nota = nota
            indice_melhor_linha = i

    # Se a nota for muito baixa, assume que é uma aba de lixo (ex: instruções, capas)
    if melhor_nota < 10: 
        return None
        
    df_recortado = df.iloc[indice_melhor_linha:].copy()
    
    # Promove a linha vencedora a cabeçalho e deduplica nomes repetidos
    primeira_linha = pd.Series(df_recortado.iloc[0]).ffill()
    colunas_brutas = primeira_linha.apply(normalizar_texto).tolist()
    df_recortado.columns = deduplicar_colunas(colunas_brutas) 
    
    # Remove a linha do cabeçalho que ficou nos dados e limpa linhas/colunas vazias
    df_recortado = df_recortado[1:].dropna(axis=1, how='all').dropna(axis=0, how='all').reset_index(drop=True)
    
    # Avalia se a tabela tem a estrutura mínima para ser uma lista de preços
    tem_codigo = False
    tem_preco = False
    if not df_recortado.empty:
        tem_codigo, tem_preco = analisar_comportamento_colunas(df_recortado)

    if tem_codigo and tem_preco:
        sugestao = "Consolidar"
        motivo = "Bom candidato a lista de preços (Contém Código + Preço)."
    else:
        sugestao = "Ignorar"
        motivo = "Não aparenta ser um intervalo de lista de preços válido."

    # Devolve o pacote estritamente formatado para o Passo 2 ler
    return {
        "id_unico": f"{nome_arquivo}_{nome_aba}".replace(".", "_"),
        "arquivo": nome_arquivo,
        "aba": nome_aba,
        "confianca": melhor_nota,
        "sugestao_acao": sugestao, 
        "motivo_escolha": motivo,
        "dados": df_recortado
    }