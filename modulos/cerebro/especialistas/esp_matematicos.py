import re
import pandas as pd

def avaliar_matematica(serie_dados, conceito_erp):
    nota_dna = 0.0
    veto_absoluto = False

    if serie_dados is None or serie_dados.dropna().empty:
        return nota_dna, veto_absoluto

    amostra = serie_dados.dropna().astype(str).head(20).tolist()
    total_amostra = len(amostra)
    
    if total_amostra == 0: 
        return nota_dna, veto_absoluto

    # ==========================================
    # 🛡️ O ESCUDO ANTI-DATAS
    # ==========================================
    datas_encontradas = 0
    for v in amostra:
        v_limpo = v.strip()
        if re.match(r'^\d{2}[-/]\d{2}[-/]\d{2,4}', v_limpo) or re.match(r'^\d{4}[-/]\d{2}[-/]\d{2}', v_limpo):
            datas_encontradas += 1
    if (datas_encontradas / total_amostra) > 0.3:
        return 0.0, True

    acertos = 0

    # ==========================================
    # 1. O CAÇADOR DE NCM
    # ==========================================
    if conceito_erp == "NCM":
        for v in amostra:
            v_limpo = v.strip()
            if re.match(r'^\d{4}\.?\d{2}\.?\d{2}', v_limpo):
                acertos += 1
        
        taxa_acerto = acertos / total_amostra
        if taxa_acerto >= 0.8: nota_dna = 40.0 
        elif taxa_acerto >= 0.4: nota_dna = 20.0 
        elif taxa_acerto == 0.0: veto_absoluto = True 

    # ==========================================
    # 2. O CAÇADOR DE EAN (BLINDADO CONTRA PANDAS)
    # ==========================================
    elif conceito_erp == "EAN":
        for v in amostra:
            v_limpo = v.strip()
            
            # Tenta salvar números que o Pandas transformou em float ou notação científica (ex: 7.89E+12)
            try:
                if 'E' in v_limpo.upper() or '.' in v_limpo:
                    v_limpo = str(int(float(v_limpo)))
            except:
                pass
                
            # Extrai apenas os números puros
            numeros_puros = re.sub(r'\D', '', v_limpo)
            
            # EANs/GTINs válidos no mercado têm 8, 12, 13 ou 14 dígitos exatos
            if len(numeros_puros) in [8, 12, 13, 14]:
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
            if re.match(r'^\d{1,3}$', v_limpo) or v_limpo in ["NAC", "NAC.", "NACIONAL", "IMP", "IMP.", "IMPORTADO"]:
                acertos += 1
                
        taxa_acerto = acertos / total_amostra
        if taxa_acerto >= 0.8: nota_dna = 40.0
        elif taxa_acerto >= 0.4: nota_dna = 20.0

    return nota_dna, veto_absoluto