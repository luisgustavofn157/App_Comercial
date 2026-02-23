import pandas as pd
from difflib import SequenceMatcher
from modulos.cerebro.memoria import consultar_memoria, normalizar_termo
from modulos.cerebro.especialistas import esp_matematicos, esp_textuais, esp_financeiros

# Importamos TUDO da fonte central de verdade
from modulos.config_erp import DICIONARIO_ERP, DICIONARIO_SINONIMOS, REVERSO_ERP 

def avaliar_coluna(coluna_excel, lista_conceitos_erp, fornecedor, df_amostra=None):
    melhor_match = DICIONARIO_ERP["IGNORAR"]
    maior_nota = 0
    detalhes_vencedor = None
    
    col_norm = normalizar_termo(coluna_excel)
    
    for conceito_visual in lista_conceitos_erp:
        if conceito_visual == DICIONARIO_ERP["IGNORAR"]: continue
        
        # Descobre o ID real imutável (Ex: "💰 Preço Base" -> "PRECO_BASE")
        id_conceito = REVERSO_ERP.get(conceito_visual)
        if not id_conceito: continue
        
        conceito_norm = normalizar_termo(conceito_visual)
        
        # ==========================================
        # 1. PILAR LÉXICO (Similaridade + Sinônimos)
        # ==========================================
        nota_lexica = SequenceMatcher(None, col_norm, conceito_norm).ratio() * 100
        
        # Procura nos sinônimos blindados usando o ID
        if id_conceito in DICIONARIO_SINONIMOS:
            for termo in DICIONARIO_SINONIMOS[id_conceito]:
                if termo in col_norm:
                    nota_lexica = max(nota_lexica, 75.0) 
                    break
                    
        # ==========================================
        # 2. PILAR MEMÓRIA E TRANSFER LEARNING
        # ==========================================
        # Passamos o conceito visual para cruzar com a interface do usuário
        nota_memoria = consultar_memoria(coluna_excel, conceito_visual, fornecedor)
        
        # ==========================================
        # 3. PILAR ESPECIALISTAS (DNA da Célula) & VETO
        # ==========================================
        nota_dna = 0.0
        veto_absoluto = False
        
        # Só aciona os detetives se tivermos dados para eles analisarem
        if df_amostra is not None and not df_amostra.empty:
            serie_atual = df_amostra[coluna_excel]
            
            # Delega para o Matemático
            if id_conceito in ["NCM", "EAN", "CST"]:
                nota_dna, veto_absoluto = esp_matematicos.avaliar_matematica(serie_atual, id_conceito)
            
            # Delega para o Linguista
            elif id_conceito in ["SKU", "DESCRICAO", "MARCA"]:
                nota_dna, veto_absoluto = esp_textuais.avaliar_texto(serie_atual, id_conceito)
                
            # Delega para o Financeiro (passando o DF inteiro para ele comparar as colunas)
            elif id_conceito in ["PRECO_BASE", "PRECO_PROMO", "PRECO_SECUNDARIO", "IPI", "DESCONTO", "MULTIPLO"]:
                nota_dna, veto_absoluto = esp_financeiros.avaliar_financeiro(df_amostra, coluna_excel, id_conceito)

        # ==========================================
        # CÁLCULO FINAL DA CONFIANÇA
        # ==========================================
        if veto_absoluto:
            confianca_final = 0.0 # O Especialista provou que o dado não condiz com o título
        else:
            confianca_final = min(nota_lexica + nota_dna + nota_memoria, 100.0)
            
        if confianca_final > maior_nota:
            maior_nota = confianca_final
            melhor_match = conceito_visual
            detalhes_vencedor = {
                "nota": round(confianca_final, 1),
                "lexica": round(nota_lexica, 1),
                "dna": round(nota_dna, 1),
                "memoria": round(nota_memoria, 1)
            }
            
    # O CORTA LUZ (Threshold de 40%) blindado
    if maior_nota < 40.0:
        melhor_match = DICIONARIO_ERP["IGNORAR"]
        
    return melhor_match, maior_nota, detalhes_vencedor