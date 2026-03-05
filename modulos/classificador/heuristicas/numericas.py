import re
import pandas as pd

def calcular_digito_verificador_cnpj(cnpj_limpo):
    """
    Cálculo matemático real do Módulo 11 para CNPJ.
    """
    if len(cnpj_limpo) != 14 or cnpj_limpo == cnpj_limpo[0] * 14:
        return False
    try:
        # Validação do primeiro dígito
        soma = 0
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        for i in range(12):
            soma += int(cnpj_limpo[i]) * pesos1[i]
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto
        if int(cnpj_limpo[12]) != digito1:
            return False
        
        # Validação do segundo dígito
        soma = 0
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        for i in range(13):
            soma += int(cnpj_limpo[i]) * pesos2[i]
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto
        if int(cnpj_limpo[13]) != digito2:
            return False
            
        return True
    except:
        return False

def calcular_digito_verificador_ean(codigo_limpo):
    """
    Cálculo matemático real do Módulo 10 para códigos de barras.
    Se a matemática bater, a chance de ser um EAN falso é praticamente nula.
    """
    if len(codigo_limpo) not in [8, 12, 13, 14]:
        return False
    try:
        # Pega o último dígito (o verificador enviado pelo fornecedor)
        digito_fornecido = int(codigo_limpo[-1])
        
        # Pega o restante do código e inverte a ordem para o cálculo
        corpo_reverso = [int(x) for x in codigo_limpo[:-1]][::-1]
        
        # A regra do EAN: da direita para a esquerda, multiplica alternando por 3 e 1
        soma = sum(d * 3 if i % 2 == 0 else d * 1 for i, d in enumerate(corpo_reverso))
        
        # O dígito verificador é o quanto falta para o próximo múltiplo de 10
        digito_calculado = (10 - (soma % 10)) % 10
        
        return digito_fornecido == digito_calculado
    except:
        return False

def avaliar_matematica(serie_dados, conceito_erp):
    """
    Varre a coluna de dados e retorna uma nota de Semântica (0.0 a 100.0) 
    e um Veto Absoluto (True/False) caso tenha certeza que NÃO é esse conceito.
    """
    nota_dna = 0.0
    veto_absoluto = False

    if serie_dados is None or serie_dados.dropna().empty:
        return 0.0, True

    # Pega uma amostra representativa (aumentei para 30 para termos mais margem estatística)
    amostra = serie_dados.dropna().head(30)
    total_amostra = len(amostra)
    if total_amostra == 0: 
        return 0.0, True

    # ==========================================
    # 🛡️ O ESCUDO ANTI-DATAS (Nível Pandas)
    # ==========================================
    # 1. Checa se o próprio Pandas já tipou a coluna como data na importação
    if pd.api.types.is_datetime64_any_dtype(serie_dados):
        return 0.0, True
        
    # 2. Checa as strings (Formato BR e Americano)
    datas_encontradas = sum(
        1 for v in amostra.astype(str) 
        if re.match(r'^\d{2}[-/]\d{2}[-/]\d{2,4}', v.strip()) or re.match(r'^\d{4}[-/]\d{2}[-/]\d{2}', v.strip())
    )
    if (datas_encontradas / total_amostra) > 0.3:
        return 0.0, True

    acertos_simples = 0
    acertos_perfeitos = 0

    # ==========================================
    # 1. O CAÇADOR DE NCM (Regra Fiscal BR)
    # ==========================================
    if conceito_erp == "NCM":
        for v in amostra.astype(str):
            # Limpa tudo que não for número (tira pontos, traços e o maldito ".0" do pandas)
            v_limpo = re.sub(r'\D', '', v.split('.')[0])
            
            # NCM tem exatamente 8 dígitos e começa com capítulos válidos (01 a 97)
            if len(v_limpo) == 8:
                capitulo = int(v_limpo[:2])
                if 1 <= capitulo <= 97:
                    acertos_perfeitos += 1
        
        taxa = acertos_perfeitos / total_amostra
        if taxa >= 0.8: nota_dna = 95.0
        elif taxa >= 0.4: nota_dna = 50.0
        elif taxa == 0.0: veto_absoluto = True

    # ==========================================
    # 2. O CAÇADOR DE EAN (Módulo 10)
    # ==========================================
    elif conceito_erp == "EAN":
        for v in amostra.astype(str):
            v_limpo = v.strip().upper()
            
            # Salva da notação científica (ex: 7.89E+12)
            if 'E' in v_limpo or ('.' in v_limpo and v_limpo.endswith('0')):
                try:
                    v_limpo = str(int(float(v_limpo)))
                except:
                    pass
            
            numeros_puros = re.sub(r'\D', '', v_limpo)
            
            if len(numeros_puros) in [8, 12, 13, 14]:
                acertos_simples += 1 # O tamanho bate
                if calcular_digito_verificador_ean(numeros_puros):
                    acertos_perfeitos += 1 # A matemática bate!
                    
        taxa_perfeita = acertos_perfeitos / total_amostra
        taxa_simples = acertos_simples / total_amostra
        
        if taxa_perfeita >= 0.5: nota_dna = 100.0  # Se metade tem matemática válida, É UMA COLUNA DE EAN!
        elif taxa_simples >= 0.8: nota_dna = 60.0  # O tamanho bate, mas a matemática não (fornecedor gerou código falso internamente)
        elif taxa_simples == 0.0: veto_absoluto = True

    # ==========================================
    # 3. O CAÇADOR DE MÚLTIPLO DE VENDA
    # ==========================================
    elif conceito_erp == "MULTIPLO":
        for v in amostra.astype(str):
            try:
                # Múltiplo precisa ser convertível para número
                valor_float = float(v.replace(',', '.'))
                # Precisa ser inteiro e maior que zero
                if valor_float.is_integer() and valor_float > 0:
                    acertos_simples += 1
                    # Bônus: 90% das autopeças são vendidas em caixas de 1, 2, 4, 6, 12, 24...
                    if valor_float in [1, 2, 3, 4, 5, 6, 10, 12, 18, 20, 24, 30, 36, 50, 100]:
                        acertos_perfeitos += 1
            except:
                pass
                
        taxa_simples = acertos_simples / total_amostra
        taxa_perfeita = acertos_perfeitos / total_amostra
        
        if taxa_perfeita >= 0.8: nota_dna = 90.0
        elif taxa_simples >= 0.8: nota_dna = 60.0

    # ==========================================
    # 4. O CAÇADOR DE CST / ORIGEM
    # ==========================================
    elif conceito_erp == "CST":
        for v in amostra.astype(str):
            v_limpo = v.strip().upper()
            # Foco em códigos exatos de CST/CSOSN (2 a 3 dígitos) e palavras-chave
            if v_limpo in ["NAC", "NACIONAL", "IMP", "IMPORTADO"]:
                acertos_simples += 1
                
        taxa = acertos_simples / total_amostra
        # CST nunca ganha 100 sozinho na Semântica porque pode confundir com IPI. 
        # Deixamos no máximo em 75, forçando o Árbitro ou o Lexical a confirmar o título da coluna.
        if taxa >= 0.8: nota_dna = 75.0 
        elif taxa >= 0.4: nota_dna = 40.0

    # ==========================================
    # 5. O CAÇADOR DE IPI (%)
    # ==========================================
    elif conceito_erp == "IPI":
        valores = []
        for v in amostra.astype(str):
            s = v.strip().replace('%', '').replace(',', '.')
            try:
                valores.append(float(s))
            except:
                pass

        if not valores:
            veto_absoluto = True
        else:
            def casas_decimais(x: float) -> int:
                s = f"{x:.12f}".rstrip('0').rstrip('.')
                return len(s.split('.')[1]) if '.' in s else 0

            total = len(valores)
            max_abs = max(abs(x) for x in valores)
            qtd_unicos = len(set(valores))
            proporcao_unicos = qtd_unicos / total

            # Heurísticas de Veto (Cara de Preço)
            if max_abs > 60:
                veto_absoluto = True
            elif proporcao_unicos > 0.4 and total >= 10:
                veto_absoluto = True
            else:
                # Whitelist de alíquotas
                aliquotas_pct = {
                    0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.25, 3.5, 4.0, 4.5, 5.0,
                    6.0, 6.5, 7.0, 7.5, 8.0, 9.0, 10.0, 11.0, 11.7, 11.75, 12.0, 13.0, 14.0,
                    15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 22.0, 25.0, 30.0, 35.0, 40.0, 50.0
                }
                TOL = 0.02

                def bate_aliquota(valor: float) -> bool:
                    if valor < 0: return False
                    candidatos = [valor, valor * 100.0]
                    for cand in candidatos:
                        for a in aliquotas_pct:
                            if abs(cand - a) <= TOL: return True
                    return False

                acertos_whitelist = 0
                acertos_intervalo = 0
                sinais_preco = 0

                for x in valores:
                    if 0 <= x <= 50: acertos_intervalo += 1
                    if bate_aliquota(x): acertos_whitelist += 1
                    if x > 1.0 and casas_decimais(x) > 2: sinais_preco += 1

                taxa_whitelist = acertos_whitelist / total
                taxa_intervalo = acertos_intervalo / total
                taxa_sinais_preco = sinais_preco / total
                taxa_repeticao = 1.0 - (qtd_unicos / total)

                # Decisão Final
                if taxa_sinais_preco > 0.15:
                    veto_absoluto = True
                elif taxa_whitelist >= 0.6: # <-- Mudei de 0.7 para 0.6 aqui
                    nota_dna = 90.0 if taxa_repeticao > 0.4 else 75.0
                else:
                    veto_absoluto = True

    # ==========================================
    # 6. O CAÇADOR DE CNPJ (Módulo 11)
    # ==========================================
    elif conceito_erp == "CNPJ":
        for v in amostra.astype(str):
            # Limpa a pontuação. Ex: "44.023.471/0002-71" vira "44023471000271"
            v_limpo = re.sub(r'\D', '', v)
            
            # O Excel costuma comer os zeros à esquerda do CNPJ. 
            if 0 < len(v_limpo) <= 14:
                v_limpo = v_limpo.zfill(14)
                
            if len(v_limpo) == 14:
                acertos_simples += 1 # O tamanho bate
                if calcular_digito_verificador_cnpj(v_limpo):
                    acertos_perfeitos += 1 # A matemática bate!
                    
        taxa_perfeita = acertos_perfeitos / total_amostra
        taxa_simples = acertos_simples / total_amostra
        
        if taxa_perfeita >= 0.5: nota_dna = 100.0  # Se metade tem matemática válida, É CNPJ!
        elif taxa_simples >= 0.8: nota_dna = 60.0  # Tamanho bate, mas matemática não
        elif taxa_simples == 0.0: veto_absoluto = True

    return nota_dna, veto_absoluto