import re
import pandas as pd
import numpy as np

def extrair_valor_numerico(valor):
    """Função ultrarrápida para limpar strings de moeda e transformar em float para calcular média."""
    if pd.isna(valor): return np.nan
    v = str(valor).strip()
    if ',' in v and '.' in v:
        v = v.replace('.', '').replace(',', '.')
    elif ',' in v:
        v = v.replace(',', '.')
    v = re.sub(r'[^\d.]', '', v)
    try: return float(v)
    except: return np.nan

def avaliar_financeiro(df_amostra, nome_coluna, id_conceito):
    """
    O Especialista Financeiro analisa a tabela inteira para comparar grandezas.
    Ele sabe que o Preço Base é sempre o MAIOR valor.
    """
    nota_dna = 0.0
    veto_absoluto = False
    
    if nome_coluna not in df_amostra.columns:
        return nota_dna, veto_absoluto
        
    serie = df_amostra[nome_coluna]
    if serie.dropna().empty: 
        return nota_dna, veto_absoluto

    # Tenta converter a coluna atual para números puros
    serie_numerica = serie.apply(extrair_valor_numerico).dropna()
    
    # Se não sobrou nenhum número, não é dinheiro nem porcentagem. Veto!
    if serie_numerica.empty:
        if id_conceito in ["PRECO_BASE", "PRECO_PROMO", "PRECO_SECUNDARIO", "IPI", "DESCONTO"]:
            return 0.0, True
        return nota_dna, veto_absoluto

    media_atual = serie_numerica.mean()
    
    # ==========================================
    # 1. ANÁLISE DE PORCENTAGEM (IPI e DESCONTO)
    # ==========================================
    if id_conceito in ["IPI", "DESCONTO"]:
        # IPI e Desconto costumam ser alíquotas entre 0 e 100
        if 0 <= media_atual <= 100:
            nota_dna = 20.0
            # Se a coluna original tinha o símbolo "%", a chance é altíssima!
            if serie.astype(str).str.contains('%').any():
                nota_dna = 40.0
        else:
            # Se a média da coluna for 1500, com certeza não é IPI. Veto!
            veto_absoluto = True
            
        return nota_dna, veto_absoluto

    # ==========================================
    # 2. ANÁLISE DE PREÇOS (Base vs Promo vs Secundário)
    # ==========================================
    if id_conceito in ["PRECO_BASE", "PRECO_PROMO", "PRECO_SECUNDARIO"]:
        
        # O especialista varre a amostra inteira para achar todas as colunas de "dinheiro"
        medias_dinheiro = {}
        for col in df_amostra.columns:
            s_num = df_amostra[col].apply(extrair_valor_numerico).dropna()
            if not s_num.empty:
                m = s_num.mean()
                # Considera dinheiro se a média for razoável (ignora colunas de zeros)
                if m > 0:
                    medias_dinheiro[col] = m
        
        # Se a coluna atual não conseguiu calcular média, aborta
        if nome_coluna not in medias_dinheiro:
            return 0.0, True
            
        maior_media = max(medias_dinheiro.values())
        
        # A Regra de Ouro do Analista Comercial:
        if id_conceito == "PRECO_BASE":
            if media_atual >= maior_media:
                nota_dna = 40.0 # É o maior preço (ou o único). É o nosso Base!
            else:
                veto_absoluto = True # Tem uma coluna maior que essa. Logo, essa NÃO PODE ser o Base.
                
        elif id_conceito in ["PRECO_PROMO", "PRECO_SECUNDARIO"]:
            if len(medias_dinheiro) > 1 and media_atual < maior_media:
                nota_dna = 30.0 # É dinheiro, mas é menor que o Base. O Orquestrador desempata pelo título!
            else:
                veto_absoluto = True # Se é a única coluna, ou a maior coluna, não é promocional/secundário.

    return nota_dna, veto_absoluto