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

    # Pega uma amostra representativa (os 50 dados reais já filtrados pelo pipeline)
    amostra = serie_dados.dropna()
    total_amostra = len(amostra)
    if total_amostra == 0: 
        return 0.0, True

    # ==========================================
    # 🛡️ O ESCUDO ANTI-DATAS (Nível Pandas)
    # ==========================================
    if pd.api.types.is_datetime64_any_dtype(serie_dados):
        return 0.0, True
        
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
            v_str = v.strip()
            
            # 1. Tira o fantasma do float (ex: "85439090.0" vira "85439090") sem quebrar NCMs com pontos reais
            if re.match(r'^\d{8}\.0$', v_str):
                v_str = v_str[:-2]
                
            # 2. Agora sim, remove tudo que não for número (ex: "8543.90.90" vira "85439090")
            v_limpo = re.sub(r'\D', '', v_str)
            
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
            
            if 'E' in v_limpo or ('.' in v_limpo and v_limpo.endswith('0')):
                try:
                    v_limpo = str(int(float(v_limpo)))
                except:
                    pass
            
            numeros_puros = re.sub(r'\D', '', v_limpo)
            
            if len(numeros_puros) in [8, 12, 13, 14]:
                acertos_simples += 1 
                if calcular_digito_verificador_ean(numeros_puros):
                    acertos_perfeitos += 1 
                    
        taxa_perfeita = acertos_perfeitos / total_amostra
        taxa_simples = acertos_simples / total_amostra
        
        if taxa_perfeita >= 0.5: nota_dna = 100.0  
        elif taxa_simples >= 0.8: nota_dna = 60.0  
        elif taxa_simples == 0.0: veto_absoluto = True

    # ==========================================
    # 3. O CAÇADOR DE MÚLTIPLO DE VENDA
    # ==========================================
    elif conceito_erp == "MULTIPLO":
        for v in amostra.astype(str):
            # Procura o primeiro bloco numérico da string (Salva dados como "1 UN", "10cx")
            match = re.search(r'(\d+[.,]?\d*)', v)
            if match:
                try:
                    v_num = match.group(1).replace(',', '.')
                    valor_float = float(v_num)
                    
                    if valor_float.is_integer() and valor_float > 0:
                        acertos_simples += 1
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
            
            # Regra 1: Textual (Nacional/Importado)
            if v_limpo in ["NAC", "NACIONAL", "IMP", "IMPORTADO"]:
                acertos_simples += 1
            else:
                # Regra 2: Numérica (Códigos Fiscais oficiais de 1, 2 ou 3 dígitos)
                v_num = re.sub(r'\D', '', v_limpo)
                if 1 <= len(v_num) <= 3 and len(v_num) == len(v_limpo):
                    acertos_simples += 1
                
        taxa = acertos_simples / total_amostra
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

            if max_abs > 60:
                veto_absoluto = True
            elif proporcao_unicos > 0.4 and total >= 10:
                veto_absoluto = True
            else:
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
                taxa_sinais_preco = sinais_preco / total
                taxa_repeticao = 1.0 - proporcao_unicos

                if taxa_sinais_preco > 0.15:
                    veto_absoluto = True
                elif taxa_whitelist >= 0.6: 
                    nota_dna = 90.0 if taxa_repeticao > 0.4 else 75.0
                else:
                    veto_absoluto = True

    # ==========================================
    # 6. O CAÇADOR DE CNPJ (Módulo 11)
    # ==========================================
    elif conceito_erp == "CNPJ":
        for v in amostra.astype(str):
            v_limpo = re.sub(r'\D', '', v)
            
            if 0 < len(v_limpo) <= 14:
                v_limpo = v_limpo.zfill(14)
                
            if len(v_limpo) == 14:
                acertos_simples += 1 
                if calcular_digito_verificador_cnpj(v_limpo):
                    acertos_perfeitos += 1 
                    
        taxa_perfeita = acertos_perfeitos / total_amostra
        taxa_simples = acertos_simples / total_amostra
        
        if taxa_perfeita >= 0.5: nota_dna = 100.0  
        elif taxa_simples >= 0.8: nota_dna = 60.0  
        elif taxa_simples == 0.0: veto_absoluto = True

    return nota_dna, veto_absoluto