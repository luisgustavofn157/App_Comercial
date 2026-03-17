import re
import pandas as pd

# Mantive os seus dicionários (expandimos um pouco para cobrir mais o mercado BR)
MARCAS_CONHECIDAS = [
    "BOSCH", "NGK", "DS", "VALEO", "COFAP", "NAKATA", "MAGNETI MARELLI", "DELPHI", 
    "VW", "FIAT", "FORD", "GM", "CHEVROLET", "TOYOTA", "HONDA", "RENAULT", "PEUGEOT",
    "MONROE", "TRW", "FRAS-LE", "SABO", "LUK", "INA", "FAG", "DAYCO", "GATES", "TECFIL", "MANN",
    "3M", "3B RIO", "3R RUBBER", "2M PLASTIC", "BROSOL", "URBA", "BROSOL", "MTE-THOMSON"
]

SEGMENTOS_CONHECIDOS = [
    "LEVE", "PESAD", "AGRICOLA", "UTILITARIO", "MOTO", "SUV", "COMERCIAL", "PASSAGEIRO", "TRATOR", "OFF-ROAD"
]

TERMOS_BOOLEANOS = ["SIM", "NAO", "NÃO", "S", "N", "TRUE", "FALSE", "ATIVO", "INATIVO", "V", "F"]

def avaliar_texto(serie_dados, conceito_erp):
    """
    PASSO 1: Análise Local.
    Avalia a estrutura e a semântica de colunas de texto (SKU, Descrição, Marca, Linha).
    """
    if serie_dados is None or serie_dados.dropna().empty:
        return 0.0, True

    amostra_bruta = serie_dados.dropna().astype(str).head(30)
    total_amostra = len(amostra_bruta)
    
    if total_amostra == 0: 
        return 0.0, True

    # ==========================================
    # 🛡️ ESCUDOS GLOBAIS (Rápidos)
    # ==========================================
    datas = links = booleanos = 0
    
    # Faz uma única varredura rápida na amostra para extrair os indicadores globais
    for v in amostra_bruta:
        v_upper = v.strip().upper()
        if re.match(r'^\d{2}[-/]\d{2}[-/]\d{2,4}', v_upper) or re.match(r'^\d{4}[-/]\d{2}[-/]\d{2}', v_upper):
            datas += 1
        if "HTTP" in v_upper or "WWW." in v_upper or ".COM" in v_upper or ".BR" in v_upper:
            links += 1
        if v_upper in TERMOS_BOOLEANOS:
            booleanos += 1

    # Se a coluna é majoritariamente data, link ou status, ela NUNCA será nenhum conceito textual
    if (datas / total_amostra) > 0.3 or (links / total_amostra) > 0.3 or (booleanos / total_amostra) > 0.5:
        return 0.0, True

    nota_dna = 0.0
    veto_absoluto = False
    acertos = 0

    # ==========================================
    # 1. O CAÇADOR DE SKU
    # ==========================================
    if conceito_erp == "SKU":
        for v in amostra_bruta:
            v_limpo = v.strip().upper()
            
            # Limpeza do artefato fantasma do Pandas (ex: 23710.0 vira 23710)
            if re.match(r'^\d+\.0$', v_limpo):
                v_limpo = v_limpo[:-2]
                
            tamanho = len(v_limpo)
            espacos = v_limpo.count(' ')
            
            # VETO 1: Se for muito longo ou tiver muitos espaços (ex: Descrição)
            if tamanho < 2 or tamanho > 25 or espacos > 1:
                continue
                
            # VETO 2: Se for puramente um número decimal longo (ex: Preço, Peso)
            if re.match(r'^\d+\.\d{2,}$', v_limpo):
                continue

            # Pontua base (Passou pelas travas, tem cara de SKU)
            acertos += 1
            
            # Bônus do SKU: Misto de letras e números, ou hífens/pontos bem colocados
            tem_letra_e_numero = bool(re.search(r'\d', v_limpo)) and bool(re.search(r'[A-Z]', v_limpo))
            tem_hifen = '-' in v_limpo
            
            # Só dá bônus de ponto se NÃO for apenas um número com vírgula (ex: 8543.90.90 ganha, 5.0 não)
            tem_ponto_complexo = '.' in v_limpo and not re.match(r'^\d+\.\d+$', v_limpo)
            
            if tem_hifen or tem_letra_e_numero or tem_ponto_complexo:
                acertos += 0.5 
                
        taxa = acertos / total_amostra
        if taxa >= 1.0: nota_dna = 85.0 
        elif taxa >= 0.8: nota_dna = 70.0 
        elif taxa >= 0.5: nota_dna = 40.0
        
        if sum(1 for v in amostra_bruta if len(v.strip()) > 35) / total_amostra > 0.8:
            veto_absoluto = True

    # ==========================================
    # 2. O CAÇADOR DE DESCRIÇÃO
    # ==========================================
    elif conceito_erp == "DESCRICAO":
        # Descrição: Longa, com espaços, e OBRIGATORIAMENTE tem letras.
        letras_count = 0
        for v in amostra_bruta:
            v_limpo = v.strip()
            if len(v_limpo) > 10 and v_limpo.count(' ') >= 1:
                acertos += 1
            if bool(re.search(r'[a-zA-Z]', v_limpo)):
                letras_count += 1
                
        taxa_acerto = acertos / total_amostra
        taxa_letras = letras_count / total_amostra
        
        if taxa_letras < 0.2: # Se quase não tem letras na coluna, não é descrição (é NCM, EAN, etc)
            return 0.0, True
            
        if taxa_acerto >= 0.8: nota_dna = 95.0 # Descrição é muito fácil de achar
        elif taxa_acerto >= 0.5: nota_dna = 60.0

    # ==========================================
    # 3. O CAÇADOR DE MARCA
    # ==========================================
    elif conceito_erp == "MARCA":
        # Marca: Palavras curtas (1 a 2). E o nosso Dicionário é a arma secreta.
        for v in amostra_bruta:
            v_limpo = v.strip().upper()
            
            # Se bateu com nosso dicionário, é "Jackpot" (Bingo!)
            if any(marca == v_limpo for marca in MARCAS_CONHECIDAS): # Verificação EXATA é mais segura
                acertos += 2 # Peso duplo para o dicionário
            elif any(marca in v_limpo for marca in MARCAS_CONHECIDAS):
                acertos += 1.5 # Contém a palavra, peso bônus
            # Se não bateu no dicionário, aplicamos regras genéricas de marca
            elif 2 <= len(v_limpo) <= 25 and bool(re.search(r'[A-Z]', v_limpo)) and v_limpo.count(' ') <= 2:
                # Garante que não é um Segmento (que também é curto)
                if not any(seg in v_limpo for seg in SEGMENTOS_CONHECIDOS):
                    acertos += 1
                
        taxa = acertos / total_amostra
        if taxa >= 1.5: nota_dna = 100.0 # Dicionário carregou a nota
        elif taxa >= 0.8: nota_dna = 80.0
        elif taxa >= 0.4: nota_dna = 40.0
        
        if sum(1 for v in amostra_bruta if len(v.strip()) > 30) / total_amostra > 0.8:
            veto_absoluto = True

    # ==========================================
    # 4. O CAÇADOR DE LINHA (SEGMENTO)
    # ==========================================
    elif conceito_erp == "LINHA":
        for v in amostra_bruta:
            v_limpo = v.strip().upper()
            
            # Bingo no Dicionário
            if any(seg in v_limpo for seg in SEGMENTOS_CONHECIDOS):
                acertos += 2
            # Regras genéricas (Curto e com letras)
            elif 3 <= len(v_limpo) <= 20 and bool(re.search(r'[A-Z]', v_limpo)) and v_limpo.count(' ') <= 2:
                acertos += 1
                
        taxa = acertos / total_amostra
        if taxa >= 1.5: nota_dna = 100.0
        elif taxa >= 0.8: nota_dna = 80.0
        elif taxa >= 0.4: nota_dna = 40.0
        
        if sum(1 for v in amostra_bruta if len(v.strip()) > 25) / total_amostra > 0.8:
            veto_absoluto = True

    return min(100.0, nota_dna), veto_absoluto