import re
import pandas as pd
import numpy as np

def extrair_valor_numerico(valor):
    """Função inteligente para limpar strings de moeda em BR ou US format."""
    if pd.isna(valor): return np.nan
    v = str(valor).strip()
    
    eh_negativo = v.startswith('-') or v.endswith('-') or ('(' in v and ')' in v) 
    
    # Mantém apenas números, ponto e vírgula
    v_clean = re.sub(r'[^\d.,]', '', v)
    if not v_clean: return np.nan
    
    # Descobre quem é o separador decimal olhando para a ÚLTIMA ocorrência
    last_comma = v_clean.rfind(',')
    last_dot = v_clean.rfind('.')
    
    if last_comma > last_dot:
        # Formato BR: 1.000,50 ou 1000,50
        v_clean = v_clean.replace('.', '').replace(',', '.')
    elif last_dot > last_comma:
        # Formato US: 1,000.50 ou 1000.50
        v_clean = v_clean.replace(',', '')
        
    try: 
        numero = float(v_clean)
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

    amostra_bruta = serie_dados.dropna().astype(str).head(50)
    serie_numerica = amostra_bruta.apply(extrair_valor_numerico).dropna()
    total_amostra = len(serie_numerica)
    
    if total_amostra == 0: 
        return 0.0, True

    # ==========================================
    # 🛡️ ESCUDO ANTI-NEGATIVOS E ANTI-ZEROS
    # ==========================================
    qtd_negativos = (serie_numerica < 0).sum()
    if (qtd_negativos / total_amostra) > 0.1:
        return 0.0, True
        
    # Métricas estatísticas poderosas
    media_atual = serie_numerica.mean()
    maximo = serie_numerica.max()
    qtd_unicos = serie_numerica.nunique()
    proporcao_unicos = qtd_unicos / total_amostra

    tem_cifrao = amostra_bruta.str.contains(r'R\$|\$', regex=True, flags=re.IGNORECASE).any()
    tem_porcentagem = amostra_bruta.str.contains('%').any()

    # ==========================================
    # 1. OS PREÇOS (Base, Promo, Secundário)
    # ==========================================
    if conceito_erp in ["PRECO_BASE", "PRECO_PROMO", "PRECO_SECUNDARIO"]:
        if media_atual <= 0:
            return 0.0, True

        # Veto Cruzado: Se tem %, NUNCA será preço. É imposto ou desconto.
        if tem_porcentagem:
            return 0.0, True

        # NOVA REGRA DE CASAS DECIMAIS: Usa Regex para não ser enganado pelos milhares
        # Procura um ponto ou vírgula seguido de exatamente 2 ou 4 números no final da string
        acertos_casas_decimais = amostra_bruta.str.contains(r'[.,]\d{2,4}\b', regex=True).sum()
        taxa_decimais = acertos_casas_decimais / total_amostra

        # Bônus de Existência: Se chegou até aqui vivo e é positivo, tem alguma chance de ser preço
        nota_dna += 15.0

        if tem_cifrao: 
            nota_dna += 50.0 
        
        if taxa_decimais >= 0.8: 
            nota_dna += 30.0 
        elif taxa_decimais >= 0.4:
            nota_dna += 15.0 
            
        # O Pulo do Gato (Variância): Preços têm muitos valores diferentes. Descontos se repetem muito.
        if proporcao_unicos >= 0.5:
            nota_dna += 20.0

    # ==========================================
    # 2. OS DESCONTOS E POLÍTICAS (%)
    # ==========================================
    elif conceito_erp in ["DESCONTO", "POLITICA"]:
        if media_atual < 0:
            return 0.0, True
            
        # Veto Cruzado: Se tem R$, é preço.
        if tem_cifrao:
            return 0.0, True
            
        # Desconto na Rede Âncora em 99% das vezes é taxa percentual entre 0 e 100
        if 0 <= maximo <= 100:
            
            if tem_porcentagem:
                nota_dna += 60.0 # Certeza quase absoluta!
            else:
                nota_dna += 15.0 # Bônus de Existência (números pequenos)
            
            # O Pulo do Gato Inverso (Variância): Descontos se repetem muito! (ex: tudo 5%, tudo 10%)
            # Se tiver muita repetição, ganha bônus de Desconto
            if proporcao_unicos < 0.3:
                nota_dna += 20.0
        else:
            veto_absoluto = True

    return min(100.0, nota_dna), veto_absoluto