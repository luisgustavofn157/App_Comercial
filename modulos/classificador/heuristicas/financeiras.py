import re
import pandas as pd
import numpy as np

def extrair_valor_numerico(valor):
    """Função ultrarrápida para limpar strings de moeda e transformar em float."""
    if pd.isna(valor): return np.nan
    v = str(valor).strip()
    
    eh_negativo = v.startswith('-') or v.endswith('-') or ('(' in v and ')' in v) 
    
    if ',' in v and '.' in v:
        v = v.replace('.', '').replace(',', '.')
    elif ',' in v:
        v = v.replace(',', '.')
        
    v = re.sub(r'[^\d.]', '', v)
    
    try: 
        numero = float(v)
        return -numero if eh_negativo else numero
    except: 
        return np.nan

def avaliar_financeiro(serie_dados, conceito_erp):
    """
    PASSO 1: Análise Local (Visão de Túnel).
    Avalia a "Cara de Dinheiro" ou "Cara de Desconto" de uma coluna isolada.
    """
    nota_dna = 0.0
    veto_absoluto = False

    if serie_dados is None or serie_dados.dropna().empty:
        return 0.0, True

    amostra_bruta = serie_dados.dropna().astype(str).head(30)
    serie_numerica = amostra_bruta.apply(extrair_valor_numerico).dropna()
    total_amostra = len(serie_numerica)
    
    if total_amostra == 0: 
        return 0.0, True

    # ==========================================
    # 🛡️ ESCUDO ANTI-NEGATIVOS
    # ==========================================
    qtd_negativos = (serie_numerica < 0).sum()
    if qtd_negativos > 0:
        taxa_negativos = qtd_negativos / total_amostra
        if taxa_negativos > 0.1: # Tolerância caiu para 10%. Preço comercial não é negativo.
            return 0.0, True
        else:
            return 0.0, False # Zera a nota, mas não veta (pode ser um erro de digitação isolado)

    # Métricas da coluna
    media_atual = serie_numerica.mean()
    tem_cifrao = amostra_bruta.str.contains(r'R\$|\$', regex=True, flags=re.IGNORECASE).any()
    tem_porcentagem = amostra_bruta.str.contains('%').any()

    # ==========================================
    # 1. OS PREÇOS (Base, Promo, Secundário)
    # ==========================================
    if conceito_erp in ["PRECO_BASE", "PRECO_PROMO", "PRECO_SECUNDARIO"]:
        # Regra de Ouro: Preço tem que ser maior que zero
        if media_atual <= 0:
            return 0.0, True

        acertos_casas_decimais = 0
        for v_str in amostra_bruta:
            # Conta quantas casas decimais tem após a vírgula/ponto
            if ',' in v_str or '.' in v_str:
                partes = v_str.replace(',', '.').split('.')
                if len(partes) == 2 and len(partes[1].strip()) in [2, 4]:
                    acertos_casas_decimais += 1

        taxa_decimais = acertos_casas_decimais / total_amostra

        # Pontuação Base (Cara de dinheiro)
        if tem_cifrao: 
            nota_dna += 50.0 # Se tem R$, é dinheiro (Preço) com certeza!
        
        if taxa_decimais >= 0.8: 
            nota_dna += 30.0 # Bônus: Formatação contábil perfeita (ex: 15,00)
        elif taxa_decimais >= 0.4:
            nota_dna += 15.0 

        # Se for um número solto (ex: "15"), ganha uma nota média. 
        # O Árbitro e o Lexical (Título da Coluna) vão ter que confirmar depois.
        
        # Sem cifrao, sem formatação contábil = não tenho evidência suficiente
        # Deixa nota_dna = 0.0 e deixa o Árbitro decidir com mais contexto

        # O Especialista NÃO tenta adivinhar quem é o Base ou Promo aqui. 
        # Ele dá a MESMA nota para os três conceitos, garantindo que eles cheguem vivos no Árbitro.

    # ==========================================
    # 2. OS DESCONTOS E POLÍTICAS (%)
    # ==========================================
    elif conceito_erp in ["DESCONTO", "POLITICA"]:
        if media_atual < 0:
            return 0.0, True
            
        # Desconto em 99% das vezes é uma taxa entre 0% e 100%
        if 0 <= media_atual <= 100:
            nota_dna += 30.0
            if tem_porcentagem:
                nota_dna += 50.0 # Certeza quase absoluta
        else:
            # Se a média for 1500, não é desconto, é preço.
            veto_absoluto = True

    # Limita a nota ao teto máximo de Semântica (100)
    return min(100.0, nota_dna), veto_absoluto