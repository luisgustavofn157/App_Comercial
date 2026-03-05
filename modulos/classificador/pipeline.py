import pandas as pd
from difflib import SequenceMatcher
from modulos.classificador.aprendizado import consultar_memoria, normalizar_termo
from modulos.classificador.heuristicas import numericas, textuais, financeiras

from config_erp import DICIONARIO_ERP, DICIONARIO_SINONIMOS, REVERSO_ERP 

def avaliar_coluna(coluna_excel, lista_conceitos_erp, fornecedor, df_amostra=None):
    melhor_match = DICIONARIO_ERP["IGNORAR"]
    maior_nota = 0.0
    pontuacao_bruta_vencedora = 0.0 
    detalhes_vencedor = None
    
    col_norm = normalizar_termo(coluna_excel)
    
    # Prepara a série de dados uma única vez para não pesar o loop
    serie_atual = None
    if df_amostra is not None and not df_amostra.empty:
        if coluna_excel in df_amostra.columns:
            serie_atual = df_amostra[coluna_excel]
    
    for conceito_visual in lista_conceitos_erp:
        if conceito_visual == DICIONARIO_ERP["IGNORAR"]: continue
        
        id_conceito = REVERSO_ERP.get(conceito_visual)
        if not id_conceito: continue
        
        # ==========================================
        # 1. PILAR LÉXICO (O Título da Coluna) - Peso: 35%
        # ==========================================
        conceito_norm = normalizar_termo(conceito_visual)
        nota_lexica = SequenceMatcher(None, col_norm, conceito_norm).ratio() * 100

        # 🛡️ NOVO: Escudo Anti-Acrônimos (Impede PIS de confundir com IPI)
        # Se as duas palavras são curtas (siglas) e não são idênticas, zera a similaridade.
        if len(col_norm) <= 4 and len(conceito_norm) <= 4 and col_norm != conceito_norm:
            nota_lexica = 0.0

        if id_conceito in DICIONARIO_SINONIMOS:
            for termo in DICIONARIO_SINONIMOS[id_conceito]:
                termo_norm = normalizar_termo(termo)

                if termo_norm == col_norm:
                    nota_lexica = 100.0
                elif termo_norm in col_norm:
                    # Se o termo está contido, mas a coluna é muito maior (ex: PRECO_BRUTO_IPI vs IPI)
                    # Reduzimos a nota léxica em vez de fixar em 80
                    proporcao = len(termo_norm) / len(col_norm)
                    nota_lexica = max(nota_lexica, 60.0 * proporcao)
        
        # ==========================================
        # 2. PILAR SEMÂNTICO (O DNA dos Dados) - Peso: 65%
        # ==========================================
        nota_dna = 0.0
        veto_absoluto = False
        
        if serie_atual is not None:
            # ROTEAMENTO CORRIGIDO PARA A NOVA ARQUITETURA
            if id_conceito in ["NCM", "EAN", "CST", "IPI", "MULTIPLO", "CNPJ"]:
                nota_dna, veto_absoluto = numericas.avaliar_matematica(serie_atual, id_conceito)
            elif id_conceito in ["SKU", "DESCRICAO", "MARCA", "LINHA"]:
                nota_dna, veto_absoluto = textuais.avaliar_texto(serie_atual, id_conceito)
            elif id_conceito in ["PRECO_BASE", "PRECO_PROMO", "PRECO_SECUNDARIO", "DESCONTO", "POLITICA"]:
                nota_dna, veto_absoluto = financeiras.avaliar_financeiro(serie_atual, id_conceito)

        # ==========================================
        # 3. PILAR MEMÓRIA (O Bônus do Histórico)
        # ==========================================
        nota_memoria = consultar_memoria(coluna_excel, conceito_visual, fornecedor)

        # ==========================================
        # CÁLCULO FINAL DA CONFIANÇA (A Matemática Ponderada)
        # ==========================================
        if veto_absoluto:
            confianca_final = 0.0
            pontuacao_bruta = 0.0
        else:
            # A IA Pura respeita os pesos (35% Título / 65% Dados)
            nota_ia_pura = (nota_lexica * 0.35) + (nota_dna * 0.65)
            
            # A memória entra como um modificador por cima da IA Pura
            pontuacao_bruta = nota_ia_pura + nota_memoria
            
            # O usuário só vê o número capado no máximo em 100%
            confianca_final = min(max(pontuacao_bruta, 0.0), 100.0)
            
        # O DESEMPATE INTELIGENTE (Mantido, pois é uma lógica excelente!)
        if confianca_final > maior_nota or (confianca_final == maior_nota and pontuacao_bruta > pontuacao_bruta_vencedora):
            maior_nota = confianca_final
            pontuacao_bruta_vencedora = pontuacao_bruta
            melhor_match = conceito_visual
            detalhes_vencedor = {
                "nota": round(confianca_final, 1),
                "lexica": round(nota_lexica, 1),
                "dna": round(nota_dna, 1),
                "memoria": round(nota_memoria, 1),
                "ia_pura": round(nota_ia_pura if not veto_absoluto else 0.0, 1)
            }
            
    if maior_nota < 60.0:
        melhor_match = DICIONARIO_ERP["IGNORAR"]
        
    return melhor_match, maior_nota, detalhes_vencedor