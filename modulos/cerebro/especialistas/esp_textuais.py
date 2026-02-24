import re
import pandas as pd

MARCAS_CONHECIDAS = [
    "BOSCH", "NGK", "DS", "VALEO", "COFAP", "NAKATA", "MAGNETI MARELLI", "DELPHI", 
    "VW", "FIAT", "FORD", "GM", "CHEVROLET", "TOYOTA", "HONDA", "RENAULT", "PEUGEOT",
    "MONROE", "TRW", "FRAS-LE", "SABO", "LUK", "INA", "FAG", "DAYCO", "GATES", "TECFIL", "MANN",
    "3M", "3B RIO", "3R RUBBER", "2M PLASTIC"
]

SEGMENTOS_CONHECIDOS = [
    "LEVE", "PESAD", "AGRICOLA", "UTILITARIO", "MOTO", "SUV", "COMERCIAL", "PASSAGEIRO", "TRATOR", "OFF-ROAD"
]

# NOVO: Dicionário de flags de sistema
TERMOS_BOOLEANOS = ["SIM", "NAO", "NÃO", "S", "N", "TRUE", "FALSE", "ATIVO", "INATIVO", "V", "F"]

def avaliar_texto(serie_dados, conceito_erp):
    nota_dna = 0.0
    veto_absoluto = False

    if serie_dados is None or serie_dados.dropna().empty:
        return nota_dna, veto_absoluto

    amostra = serie_dados.dropna().astype(str).head(20).tolist()
    total_amostra = len(amostra)
    
    if total_amostra == 0: 
        return nota_dna, veto_absoluto

    # ==========================================
    # 🛡️ ESCUDO 1: ANTI-DATAS E ANTI-LINKS
    # ==========================================
    datas_encontradas = 0
    links_encontrados = 0
    booleanos_encontrados = 0
    
    for v in amostra:
        v_limpo = v.strip().upper()
        if re.match(r'^\d{2}[-/]\d{2}[-/]\d{2,4}', v_limpo) or re.match(r'^\d{4}[-/]\d{2}[-/]\d{2}', v_limpo):
            datas_encontradas += 1
        if "HTTP" in v_limpo or "WWW." in v_limpo or ".COM" in v_limpo or ".BR" in v_limpo:
            links_encontrados += 1
        if v_limpo in TERMOS_BOOLEANOS:
            booleanos_encontrados += 1
            
    if (datas_encontradas / total_amostra) > 0.3 or (links_encontrados / total_amostra) > 0.3:
        return 0.0, True
        
    # 🛡️ ESCUDO 3: ANTI-BOOLEANO (Protege a IA de achar que "SIM/NÃO" é uma Marca ou Segmento)
    eh_coluna_status = (booleanos_encontrados / total_amostra) > 0.5

    acertos = 0

    if conceito_erp == "SKU":
        for v in amostra:
            v_limpo = v.strip().upper()
            if 2 <= len(v_limpo) <= 25 and v_limpo.count(' ') <= 1:
                acertos += 1
                
        taxa_acerto = acertos / total_amostra
        if taxa_acerto >= 0.8: nota_dna = 30.0 
        elif taxa_acerto >= 0.5: nota_dna = 15.0
        
        if all(len(v.strip()) > 35 or v.strip().count(' ') >= 3 for v in amostra) or eh_coluna_status:
            veto_absoluto = True

    elif conceito_erp == "DESCRICAO":
        for v in amostra:
            v_limpo = v.strip()
            if len(v_limpo) > 10 and v_limpo.count(' ') >= 1 and bool(re.search(r'[a-zA-Z]', v_limpo)):
                acertos += 1
                
        taxa_acerto = acertos / total_amostra
        if taxa_acerto >= 0.8: nota_dna = 40.0
        elif taxa_acerto >= 0.5: nota_dna = 20.0
        
        if all(not bool(re.search(r'[a-zA-Z]', v)) for v in amostra) or eh_coluna_status:
            veto_absoluto = True

    elif conceito_erp == "MARCA":
        for v in amostra:
            v_limpo = v.strip().upper()
            tem_letra = bool(re.search(r'[A-Z]', v_limpo))
            parece_segmento = any(seg in v_limpo for seg in SEGMENTOS_CONHECIDOS)
            
            if any(marca in v_limpo for marca in MARCAS_CONHECIDAS):
                acertos += 2
            elif 2 <= len(v_limpo) <= 30 and tem_letra and v_limpo.count(' ') <= 2 and not parece_segmento:
                acertos += 1
                
        pontuacao_relativa = acertos / total_amostra
        if pontuacao_relativa >= 1.0: nota_dna = 40.0
        elif pontuacao_relativa >= 0.5: nota_dna = 20.0
        
        if all(len(v.strip()) > 30 for v in amostra) or all(not bool(re.search(r'[A-Z]', v.strip().upper())) for v in amostra) or all(v.strip().count(' ') >= 3 for v in amostra) or eh_coluna_status:
            veto_absoluto = True

    elif conceito_erp == "LINHA":
        for v in amostra:
            v_limpo = v.strip().upper()
            if bool(re.search(r'[A-Z]', v_limpo)) and any(seg in v_limpo for seg in SEGMENTOS_CONHECIDOS):
                if len(v_limpo) <= 16 and v_limpo.count(' ') <= 2:
                    acertos += 1 
                else:
                    acertos += 0.2 
                        
        taxa_acerto = acertos / total_amostra
        if taxa_acerto >= 0.7: nota_dna = 40.0
        elif taxa_acerto >= 0.4: nota_dna = 20.0
        
        if all(len(v.strip()) > 25 for v in amostra) or eh_coluna_status:
            veto_absoluto = True

    return nota_dna, veto_absoluto