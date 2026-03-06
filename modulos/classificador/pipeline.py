import pandas as pd
from difflib import SequenceMatcher
from modulos.classificador.aprendizado import consultar_memoria, normalizar_termo
from modulos.classificador.heuristicas import numericas, textuais, financeiras

# Adicionamos CONCEITOS_MULTIPLOS na importação para o Árbitro saber quem pode repetir
from config_erp import DICIONARIO_ERP, DICIONARIO_SINONIMOS, REVERSO_ERP, CONCEITOS_MULTIPLOS

def avaliar_coluna_fase1(coluna_excel, lista_conceitos_erp, fornecedor, df_amostra=None, usar_memoria=True):
    """
    FASE 1 (Visão de Túnel): Analisa uma coluna isolada e gera um 'Boletim' com todas 
    as possibilidades que atingiram nota >= 60%.
    """
    boletim = []
    col_norm = normalizar_termo(coluna_excel)
    
    serie_atual = None
    if df_amostra is not None and not df_amostra.empty:
        if coluna_excel in df_amostra.columns:
            serie_atual = df_amostra[coluna_excel]
            
    for conceito_visual in lista_conceitos_erp:
        if conceito_visual == DICIONARIO_ERP["IGNORAR"]: continue
        
        id_conceito = REVERSO_ERP.get(conceito_visual)
        if not id_conceito: continue
        
        # ==========================================
        # 1. PILAR LÉXICO (Peso: 35%)
        # ==========================================
        conceito_norm = normalizar_termo(conceito_visual)
        nota_lexica = SequenceMatcher(None, col_norm, conceito_norm).ratio() * 100

        if len(col_norm) <= 4 and len(conceito_norm) <= 4 and col_norm != conceito_norm:
            nota_lexica = 0.0

        if id_conceito in DICIONARIO_SINONIMOS:
            for termo in DICIONARIO_SINONIMOS[id_conceito]:
                termo_norm = normalizar_termo(termo)
                if termo_norm == col_norm:
                    nota_lexica = 100.0
                    break # <-- CORREÇÃO: Freio de processamento adicionado!
                elif termo_norm in col_norm:
                    proporcao = len(termo_norm) / len(col_norm)
                    nota_lexica = max(nota_lexica, 60.0 * proporcao)
        
        # ==========================================
        # 2. PILAR SEMÂNTICO (Peso: 65%)
        # ==========================================
        nota_dna = 0.0
        veto_absoluto = False
        
        if serie_atual is not None:
            if id_conceito in ["NCM", "EAN", "CST", "IPI", "MULTIPLO", "CNPJ"]:
                nota_dna, veto_absoluto = numericas.avaliar_matematica(serie_atual, id_conceito)
            elif id_conceito in ["SKU", "DESCRICAO", "MARCA", "LINHA"]:
                nota_dna, veto_absoluto = textuais.avaliar_texto(serie_atual, id_conceito)
            elif id_conceito in ["PRECO_BASE", "PRECO_PROMO", "PRECO_SECUNDARIO", "DESCONTO", "POLITICA"]:
                nota_dna, veto_absoluto = financeiras.avaliar_financeiro(serie_atual, id_conceito)

        # ==========================================
        # 3. PILAR MEMÓRIA (O Modificador)
        # ==========================================
        nota_memoria = 0.0
        if usar_memoria:
            nota_memoria = consultar_memoria(coluna_excel, conceito_visual, fornecedor)

        # ==========================================
        # FECHAMENTO DA NOTA
        # ==========================================
        if veto_absoluto:
            continue # Se tomou veto, nem entra no boletim
            
        nota_ia_pura = (nota_lexica * 0.35) + (nota_dna * 0.65)
        pontuacao_bruta = nota_ia_pura + nota_memoria
        confianca_final = min(max(pontuacao_bruta, 0.0), 100.0)
        
        # Só guarda se a nota final for aprovável (>= 60)
        if confianca_final >= 60.0:
            boletim.append({
                "conceito_visual": conceito_visual,
                "id_conceito": id_conceito,
                "nota": confianca_final,
                "bruta": pontuacao_bruta,
                "detalhes": {
                    "nota": round(confianca_final, 1),
                    "lexica": round(nota_lexica, 1),
                    "dna": round(nota_dna, 1),
                    "memoria": round(nota_memoria, 1),
                    "ia_pura": round(nota_ia_pura, 1)
                }
            })

    # Ordena o boletim da maior nota para a menor
    boletim = sorted(boletim, key=lambda x: (x["nota"], x["bruta"]), reverse=True)
    return boletim

def fase2_arbitro_global(mapa_boletins, df_amostra):
    """
    FASE 2 (Visão de Águia): Resolve conflitos onde múltiplas colunas disputam 
    um conceito único (1:1) do ERP.
    """
    # Descobre quem está ganhando em cada coluna no momento
    vencedores_atuais = {} # { "Nome_Coluna_Excel": "ID_CONCEITO" }
    for col, boletim in mapa_boletins.items():
        if boletim:
            vencedores_atuais[col] = boletim[0]["id_conceito"]

    # Identifica os Conflitos (Conceitos Únicos sendo apontados por mais de uma coluna)
    # Ignoramos CONCEITOS_MULTIPLOS porque eles podem repetir sem problema.
    contagem_conceitos = {}
    for conceito in vencedores_atuais.values():
        contagem_conceitos[conceito] = contagem_conceitos.get(conceito, 0) + 1

    conflitos = [conc for conc, qtd in contagem_conceitos.items() if qtd > 1 and conc not in CONCEITOS_MULTIPLOS]

    # Se não tem conflito, o Árbitro não faz nada (encerra a sessão)
    if not conflitos:
        return mapa_boletins

    # O TRIBUNAL DE DESEMPATE
    for conceito_em_disputa in conflitos:
        # Pega o nome das colunas do Excel que estão brigando por esse conceito
        colunas_brigando = [col for col, conc in vencedores_atuais.items() if conc == conceito_em_disputa]
        
        # ========================================================
        # REGRA 1: A GUERRA DOS PREÇOS (Base vs Promo)
        # ========================================================
        if conceito_em_disputa == "PRECO_BASE":
            medias = {}
            for col in colunas_brigando:
                try:
                    # Tenta converter a coluna para número e tirar a média
                    # Limpeza rápida similar a do Especialista Financeiro
                    s_num = df_amostra[col].astype(str).str.replace(r'[^\d,-]', '', regex=True).str.replace(',', '.').astype(float)
                    medias[col] = s_num.mean()
                except:
                    medias[col] = 0.0
                    
            # O Vencedor é a coluna que tem a Maior Média (O Preço Base é sempre o maior)
            coluna_vencedora = max(medias, key=medias.get)
            
        # ========================================================
        # REGRA 2: O HIGHLANDER (Regra Geral de Desempate)
        # ========================================================
        else:
            # Para NCM, EAN, SKU, etc. Ganha quem tiver a maior "Nota Bruta" na Fase 1.
            # Se a máquina teve 120 de nota bruta em um e 105 no outro, o 120 vence.
            notas_brutas = {}
            for col in colunas_brigando:
                # Pega a nota bruta do primeiro lugar do boletim
                notas_brutas[col] = mapa_boletins[col][0]["bruta"]
                
            coluna_vencedora = max(notas_brutas, key=notas_brutas.get)

        # --------------------------------------------------------
        # A SENTENÇA (Rebaixamento dos Perdedores)
        # --------------------------------------------------------
        for col in colunas_brigando:
            if col != coluna_vencedora:
                # Remove o 1º lugar do boletim do perdedor (o conceito que ele perdeu)
                mapa_boletins[col].pop(0)
                # Como tiramos o 1º lugar, a coluna assume a sua 2ª opção automaticamente.
                # Se o boletim ficar vazio, ela vira IGNORAR lá na frente.

    return mapa_boletins

def classificar_dataset_completo(df_amostra, lista_conceitos_erp, fornecedor, usar_memoria=True, usar_arbitro=True):
    """
    O NOVO ORQUESTRADOR CENTRAL. 
    Chame esta função no main.py em vez de chamar 'avaliar_coluna' dentro de um loop.
    """
    colunas_excel = [c for c in df_amostra.columns if not str(c).startswith("__")]
    
    # RODA A FASE 1 (Gera todos os boletins de forma isolada)
    mapa_boletins = {}
    for col in colunas_excel:
        mapa_boletins[col] = avaliar_coluna_fase1(col, lista_conceitos_erp, fornecedor, df_amostra)
        
    # RODA A FASE 2 (O Tribunal - se a Feature Flag estiver ligada)
    if usar_arbitro:
        # Ele reprocessa o mapa_boletins alterando a ordem se houver conflitos
        mapa_boletins = fase2_arbitro_global(mapa_boletins, df_amostra)
        
    # MONTA A RESPOSTA FINAL (Apenas o 1º lugar de cada coluna para a Interface)
    resultado_final = {}
    for col, boletim in mapa_boletins.items():
        if boletim: # Se sobrou algo no boletim após o Tribunal
            vencedor = boletim[0]
            resultado_final[col] = (vencedor["conceito_visual"], vencedor["nota"], vencedor["detalhes"])
        else:
            # Se o boletim veio vazio ou foi esvaziado pelo Árbitro
            resultado_final[col] = (DICIONARIO_ERP["IGNORAR"], None, None)
            
    return resultado_final