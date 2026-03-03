import pandas as pd
from difflib import SequenceMatcher
from modulos.cerebro.memoria import consultar_memoria, normalizar_termo
from modulos.cerebro.especialistas import esp_matematicos, esp_textuais, esp_financeiros

from config_erp import DICIONARIO_ERP, DICIONARIO_SINONIMOS, REVERSO_ERP 

def avaliar_coluna(coluna_excel, lista_conceitos_erp, fornecedor, df_amostra=None):
    melhor_match = DICIONARIO_ERP["IGNORAR"]
    maior_nota = 0.0
    pontuacao_bruta_vencedora = 0.0 # <-- A NOSSA NOVA VARIÁVEL SECRETA!
    detalhes_vencedor = None
    
    col_norm = normalizar_termo(coluna_excel)
    
    for conceito_visual in lista_conceitos_erp:
        if conceito_visual == DICIONARIO_ERP["IGNORAR"]: continue
        
        id_conceito = REVERSO_ERP.get(conceito_visual)
        if not id_conceito: continue
        
        conceito_norm = normalizar_termo(conceito_visual)
        
        # 1. PILAR LÉXICO
        nota_lexica = SequenceMatcher(None, col_norm, conceito_norm).ratio() * 100
        
        if id_conceito in DICIONARIO_SINONIMOS:
            for termo in DICIONARIO_SINONIMOS[id_conceito]:
                if termo in col_norm:
                    nota_lexica = max(nota_lexica, 75.0) 
                    break
                    
        # 2. PILAR MEMÓRIA
        nota_memoria = consultar_memoria(coluna_excel, conceito_visual, fornecedor)
        
        # 3. PILAR ESPECIALISTAS
        nota_dna = 0.0
        veto_absoluto = False
        
        if df_amostra is not None and not df_amostra.empty:
            serie_atual = df_amostra[coluna_excel]
            
            if id_conceito in ["NCM", "EAN", "CST"]:
                nota_dna, veto_absoluto = esp_matematicos.avaliar_matematica(serie_atual, id_conceito)
            elif id_conceito in ["SKU", "DESCRICAO", "MARCA", "LINHA"]:
                nota_dna, veto_absoluto = esp_textuais.avaliar_texto(serie_atual, id_conceito)
            elif id_conceito in ["PRECO_BASE", "PRECO_PROMO", "PRECO_SECUNDARIO", "IPI", "DESCONTO", "MULTIPLO"]:
                nota_dna, veto_absoluto = esp_financeiros.avaliar_financeiro(df_amostra, coluna_excel, id_conceito)

        # ==========================================
        # CÁLCULO FINAL DA CONFIANÇA
        # ==========================================
        if veto_absoluto:
            confianca_final = 0.0
            pontuacao_bruta = 0.0
        else:
            # Salvamos a pontuação pura sem limite
            pontuacao_bruta = nota_lexica + nota_dna + nota_memoria
            # O usuário só vê o número capado no máximo em 100%
            confianca_final = min(pontuacao_bruta, 100.0)
            
        # O DESEMPATE INTELIGENTE:
        # Se bater a nota maior OU se houver um empate no 100%, a maior pontuação bruta ("sobra") vence!
        if confianca_final > maior_nota or (confianca_final == maior_nota and pontuacao_bruta > pontuacao_bruta_vencedora):
            maior_nota = confianca_final
            pontuacao_bruta_vencedora = pontuacao_bruta
            melhor_match = conceito_visual
            detalhes_vencedor = {
                "nota": round(confianca_final, 1),
                "lexica": round(nota_lexica, 1),
                "dna": round(nota_dna, 1),
                "memoria": round(nota_memoria, 1)
            }
            
    if maior_nota < 60.0:
        melhor_match = DICIONARIO_ERP["IGNORAR"]
        
    return melhor_match, maior_nota, detalhes_vencedor