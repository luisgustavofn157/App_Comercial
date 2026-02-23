import re
import pandas as pd

# Dicionário de sobrevivência do mercado de autopeças para reconhecer marcas rapidamente
MARCAS_CONHECIDAS = [
    "BOSCH", "NGK", "DS", "VALEO", "COFAP", "NAKATA", "MAGNETI MARELLI", "DELPHI", 
    "VW", "FIAT", "FORD", "GM", "CHEVROLET", "TOYOTA", "HONDA", "RENAULT", "PEUGEOT",
    "MONROE", "TRW", "FRAS-LE", "SABO", "LUK", "INA", "FAG", "DAYCO", "GATES", "TECFIL", "MANN"
]

def avaliar_texto(serie_dados, conceito_erp):
    """
    O Especialista Textual analisa o comprimento das strings, a presença de espaços (palavras)
    e procura por entidades nomeadas (marcas famosas).
    Devolve: nota_dna (0 a 40) e veto_absoluto (True/False).
    """
    nota_dna = 0.0
    veto_absoluto = False

    if serie_dados is None or serie_dados.dropna().empty:
        return nota_dna, veto_absoluto

    # Pega uma amostra de 20 linhas para análise rápida
    amostra = serie_dados.dropna().astype(str).head(20).tolist()
    total_amostra = len(amostra)
    
    if total_amostra == 0: 
        return nota_dna, veto_absoluto

    acertos = 0

    # ==========================================
    # 1. O CAÇADOR DE SKU (CÓDIGO DO FORNECEDOR)
    # ==========================================
    if conceito_erp == "SKU":
        for v in amostra:
            v_limpo = v.strip().upper()
            
            # Um SKU clássico tem entre 2 e 25 caracteres, e GERALMENTE não tem espaços (ou tem no máximo 1).
            # É composto por letras, números, hifens, pontos ou barras.
            tamanho_valido = 2 <= len(v_limpo) <= 25
            sem_muitos_espacos = v_limpo.count(' ') <= 1
            
            if tamanho_valido and sem_muitos_espacos:
                acertos += 1
                
        taxa_acerto = acertos / total_amostra
        if taxa_acerto >= 0.8: nota_dna = 30.0 # Bônus alto, mas não 40, pois SKU é muito genérico
        elif taxa_acerto >= 0.5: nota_dna = 15.0
        
        # VETO: Se a coluna inteira tem textos gigantes (mais de 40 caracteres), definitivamente não é SKU.
        if all(len(v.strip()) > 40 for v in amostra):
            veto_absoluto = True

    # ==========================================
    # 2. O CAÇADOR DE DESCRIÇÃO DO PRODUTO
    # ==========================================
    elif conceito_erp == "DESCRICAO":
        for v in amostra:
            v_limpo = v.strip()
            
            # Uma descrição tem que ser "falada". Tem que ter mais de 10 letras e pelo menos um espaço (várias palavras).
            # Ex: "PASTILHA DE FREIO DIANTEIRA"
            if len(v_limpo) > 10 and ' ' in v_limpo and not v_limpo.replace('.', '').replace(',', '').isdigit():
                acertos += 1
                
        taxa_acerto = acertos / total_amostra
        if taxa_acerto >= 0.8: nota_dna = 40.0
        elif taxa_acerto >= 0.5: nota_dna = 20.0
        
        # VETO: Se 100% da coluna for composta apenas por números puros (ex: 12345), não é descrição!
        if all(v.replace('.', '').replace(',', '').isdigit() for v in amostra):
            veto_absoluto = True

    # ==========================================
    # 3. O CAÇADOR DE MARCA / FABRICANTE
    # ==========================================
    elif conceito_erp == "MARCA":
        for v in amostra:
            v_limpo = v.strip().upper()
            
            # Estratégia A: Bateu com o nosso Dicionário de Marcas Conhecidas?
            if any(marca in v_limpo for marca in MARCAS_CONHECIDAS):
                acertos += 2 # Peso duplo se for uma marca famosa
            # Estratégia B: É uma palavra curta isolada? (Ex: "XPTO")
            elif 2 <= len(v_limpo) <= 15 and ' ' not in v_limpo and not v_limpo.isdigit():
                acertos += 1
                
        # Como o acerto de marca famosa vale por 2, a matemática do limite muda um pouco
        pontuacao_relativa = acertos / total_amostra
        if pontuacao_relativa >= 1.0: nota_dna = 40.0
        elif pontuacao_relativa >= 0.5: nota_dna = 20.0
        
        # VETO: Se as strings forem gigantes (descrições) ou puramente números decimais, não é marca.
        if all(len(v.strip()) > 30 or v.replace('.', '').isdigit() for v in amostra):
            veto_absoluto = True

    return nota_dna, veto_absoluto