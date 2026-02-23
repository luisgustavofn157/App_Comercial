import re
import pandas as pd

def avaliar_matematica(serie_dados, conceito_erp):
    """
    O Especialista Matemático analisa amostras de dados puros usando Regex.
    Ele devolve dois valores:
    1. nota_dna: Um bónus de 0 a 40 pontos se o dado bater com a regra matemática.
    2. veto_absoluto: True se a coluna for completamente incompatível com o conceito.
    """
    nota_dna = 0.0
    veto_absoluto = False

    # Se a coluna estiver vazia, o matemático não tem o que analisar
    if serie_dados is None or serie_dados.dropna().empty:
        return nota_dna, veto_absoluto

    # Pegamos uma amostra rápida de 20 linhas para o sistema ser ultrarrápido (Performance)
    amostra = serie_dados.dropna().astype(str).head(20).tolist()
    total_amostra = len(amostra)
    
    if total_amostra == 0: 
        return nota_dna, veto_absoluto

    acertos = 0

    # ==========================================
    # 1. O CAÇADOR DE NCM
    # ==========================================
    if conceito_erp == "NCM":
        for v in amostra:
            v_limpo = v.strip()
            # Regex matadora: 4 dígitos, opcional ponto, 2 dígitos, opcional ponto, 2 dígitos.
            # Ignora o que vier depois (ex: 8708.99.90 ou 87089990/IMP)
            if re.match(r'^\d{4}\.?\d{2}\.?\d{2}', v_limpo):
                acertos += 1
        
        taxa_acerto = acertos / total_amostra
        if taxa_acerto >= 0.8: 
            nota_dna = 40.0 # Quase tudo é NCM, bónus máximo!
        elif taxa_acerto >= 0.4: 
            nota_dna = 20.0 # Tem alguns NCMs, mas está sujo. Bónus médio.
        elif taxa_acerto == 0.0:
            veto_absoluto = True # Não tem UM ÚNICO NCM na amostra. Veto imediato!

    # ==========================================
    # 2. O CAÇADOR DE EAN (CÓDIGO DE BARRAS)
    # ==========================================
    elif conceito_erp == "EAN":
        for v in amostra:
            v_limpo = v.strip()
            # Limpeza rápida: Se o Pandas leu o EAN como float, ele coloca um ".0" no final (ex: 78910.0)
            if v_limpo.endswith('.0'): 
                v_limpo = v_limpo[:-2]
                
            # Regex: Exatamente entre 12 e 14 dígitos puros
            if re.match(r'^\d{12,14}$', v_limpo):
                acertos += 1
                
        taxa_acerto = acertos / total_amostra
        if taxa_acerto >= 0.8: nota_dna = 40.0
        elif taxa_acerto >= 0.4: nota_dna = 20.0
        elif taxa_acerto == 0.0: veto_absoluto = True

    # ==========================================
    # 3. O CAÇADOR DE CST / ORIGEM
    # ==========================================
    elif conceito_erp == "CST":
        for v in amostra:
            v_limpo = v.strip().upper()
            # O CST é flexível: pode ser 1 a 3 dígitos (0, 040) ou os textos que você mapeou
            if re.match(r'^\d{1,3}$', v_limpo) or v_limpo in ["NAC", "NAC.", "NACIONAL", "IMP", "IMP.", "IMPORTADO"]:
                acertos += 1
                
        taxa_acerto = acertos / total_amostra
        if taxa_acerto >= 0.8: nota_dna = 40.0
        elif taxa_acerto >= 0.4: nota_dna = 20.0
        # Não aplicamos o veto absoluto no CST porque ele pode vir escrito de formas muito bizarras. 
        # Deixamos o Orquestrador decidir apenas pelo título se a matemática falhar.

    return nota_dna, veto_absoluto