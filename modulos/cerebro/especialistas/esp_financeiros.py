import re
import pandas as pd
import numpy as np

def extrair_valor_numerico(valor):
    """Função ultrarrápida para limpar strings de moeda e transformar em float."""
    if pd.isna(valor): return np.nan
    v = str(valor).strip()
    
    # 1. Preserva a informação se é um número negativo ANTES da limpeza
    # Cobre casos como "-15.00", "15.00-", ou padrão contábil "(15.00)"
    eh_negativo = v.startswith('-') or v.endswith('-') or ('(' in v and ')' in v) 
    
    if ',' in v and '.' in v:
        v = v.replace('.', '').replace(',', '.')
    elif ',' in v:
        v = v.replace(',', '.')
        
    # 2. Limpa tudo que não for dígito ou ponto
    v = re.sub(r'[^\d.]', '', v)
    
    try: 
        numero = float(v)
        # 3. Devolve o sinal de negativo se for o caso!
        return -numero if eh_negativo else numero
    except: 
        return np.nan

def avaliar_financeiro(df_amostra, nome_coluna, id_conceito):
    """
    O Especialista Financeiro analisa a tabela inteira para comparar grandezas.
    """
    nota_dna = 0.0
    veto_absoluto = False
    
    if nome_coluna not in df_amostra.columns:
        return nota_dna, veto_absoluto
        
    serie = df_amostra[nome_coluna]
    if serie.dropna().empty: 
        return nota_dna, veto_absoluto

    serie_numerica = serie.apply(extrair_valor_numerico).dropna()
    
    if serie_numerica.empty:
        if id_conceito in ["PRECO_BASE", "PRECO_PROMO", "PRECO_SECUNDARIO", "IPI", "DESCONTO", "MULTIPLO"]:
            return 0.0, True
        return nota_dna, veto_absoluto

    # ==========================================
    # 🛡️ ESCUDO ANTI-NEGATIVOS
    # ==========================================
    total_numeros = len(serie_numerica)
    qtd_negativos = (serie_numerica < 0).sum()
    penalidade = 0.0
    
    if qtd_negativos > 0:
        taxa_negativos = qtd_negativos / total_numeros
        
        # Se mais de 20% for negativo, é Veto Absoluto. Preço/Desconto não trabalha no vermelho.
        if taxa_negativos > 0.2:
            return 0.0, True
        else:
            # Se for minoria, aplicamos uma punição brutal (-30 pontos) na nota final do DNA
            penalidade = 30.0

    media_atual = serie_numerica.mean()
    
    # ==========================================
    # 1. ANÁLISE DE PORCENTAGEM (IPI e DESCONTO)
    # ==========================================
    if id_conceito in ["IPI", "DESCONTO"]:
        # IPI e Desconto costumam ser alíquotas entre 0 e 100
        if 0 <= media_atual <= 100:
            nota_dna = 20.0
            if serie.astype(str).str.contains('%').any():
                nota_dna = 40.0
        else:
            veto_absoluto = True
            
        return max(0.0, nota_dna - penalidade), veto_absoluto

    # ==========================================
    # 2. ANÁLISE DE PREÇOS (Base vs Promo vs Secundário)
    # ==========================================
    if id_conceito in ["PRECO_BASE", "PRECO_PROMO", "PRECO_SECUNDARIO"]:
        
        # O especialista varre a amostra para achar todas as colunas de "dinheiro"
        medias_dinheiro = {}
        for col in df_amostra.columns:
            s_num = df_amostra[col].apply(extrair_valor_numerico).dropna()
            if not s_num.empty:
                m = s_num.mean()
                # Considera para comparar preços apenas colunas que não sejam negativas na média geral
                if m > 0:
                    medias_dinheiro[col] = m
        
        if nome_coluna not in medias_dinheiro:
            return 0.0, True
            
        maior_media = max(medias_dinheiro.values())
        
        if id_conceito == "PRECO_BASE":
            if media_atual >= maior_media:
                nota_dna = 40.0 
            else:
                veto_absoluto = True 
                
        elif id_conceito in ["PRECO_PROMO", "PRECO_SECUNDARIO"]:
            if len(medias_dinheiro) > 1 and media_atual < maior_media:
                nota_dna = 30.0 
            else:
                veto_absoluto = True 
                
    # ==========================================
    # 3. ANÁLISE DE MÚLTIPLOS (Bônus)
    # ==========================================
    elif id_conceito == "MULTIPLO":
        # Múltiplos são inteiros pequenos. Se a média for razoável (0 a 5000) ganha pontos.
        if 0 < media_atual < 5000:
            nota_dna = 20.0

    # Aplica a penalidade matemática e garante que a nota do DNA nunca fique menor que zero
    nota_final_dna = max(0.0, nota_dna - penalidade)

    return nota_final_dna, veto_absoluto