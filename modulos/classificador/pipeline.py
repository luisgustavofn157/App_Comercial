import pandas as pd
from modulos.classificador.aprendizado import consultar_memoria, normalizar_termo
from modulos.classificador.heuristicas import numericas, textuais, financeiras, lexical

# Adicionamos CONCEITOS_MULTIPLOS na importação para o Árbitro saber quem pode repetir
from config_erp import DICIONARIO_ERP, REVERSO_ERP, CONCEITOS_MULTIPLOS

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
            # O SEGREDO: Limpa os NaNs e pega os 50 primeiros dados REAIS.
            # Assim colunas do Intervalo 3 não são avaliadas como vazias!
            serie_atual = df_amostra[coluna_excel].dropna().head(50)
            
    for conceito_visual in lista_conceitos_erp:
        if conceito_visual == DICIONARIO_ERP["IGNORAR"]: continue
        
        id_conceito = REVERSO_ERP.get(conceito_visual)
        if not id_conceito: continue
        
        # ==========================================
        # 1. PILAR LÉXICO (Peso: 35%)
        # ==========================================
        conceito_norm = normalizar_termo(conceito_visual)
        nota_lexica = lexical.avaliar_titulo(col_norm, conceito_norm, id_conceito)
        
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
            
        nota_ia_pura = (nota_lexica * 0.40) + (nota_dna * 0.60)
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
    vencedores_atuais = {} 
    for col, boletim in mapa_boletins.items():
        if boletim:
            vencedores_atuais[col] = boletim[0]["id_conceito"]

    contagem_conceitos = {}
    for conceito in vencedores_atuais.values():
        contagem_conceitos[conceito] = contagem_conceitos.get(conceito, 0) + 1

    conflitos = [conc for conc, qtd in contagem_conceitos.items() if qtd > 1 and conc not in CONCEITOS_MULTIPLOS]

    if not conflitos:
        return mapa_boletins

    # O TRIBUNAL DE DESEMPATE
    for conceito_em_disputa in conflitos:
        colunas_brigando = [col for col, conc in vencedores_atuais.items() if conc == conceito_em_disputa]
        
        # ========================================================
        # 🛡️ NOVO: O ESCUDO DE COMPLEMENTARIDADE (Tolerância a Ruído)
        # ========================================================
        df_subset = df_amostra[colunas_brigando]
        df_str = df_subset.fillna("").astype(str).apply(lambda col: col.str.strip().str.lower())
        
        lixo_planilha = ["nan", "none", "<na>", "null", "0", "0.0", "-", "_", "."]
        mask_df = (df_str != "") & (~df_str.isin(lixo_planilha))
        
        # A MÁGICA: Em vez de .any() que quebra com 1 erro, usamos % de colisão
        linhas_colisao = (mask_df.sum(axis=1) > 1).sum()
        total_linhas = len(df_amostra)
        taxa_colisao = linhas_colisao / total_linhas if total_linhas > 0 else 0
        
        # Se a colisão for menor que 2%, consideramos que é lixo de Excel e damos o Salvo-Conduto!
        tem_sobreposicao = taxa_colisao > 0.02
        
        if not tem_sobreposicao:
            continue
            
        # ========================================================
        # Se chegou aqui, as colunas colidem e vão causar perda de dados.
        # O Árbitro volta a ser implacável e aplica as regras de execução.
        # ========================================================
        
        # REGRA 1: A GUERRA DOS PREÇOS (Base vs Promo)
        if conceito_em_disputa == "PRECO_BASE":
            medias = {}
            for col in colunas_brigando:
                try:
                    s_num = df_amostra[col].astype(str).str.replace(r'[^\d,-]', '', regex=True).str.replace(',', '.').astype(float)
                    medias[col] = s_num.mean()
                except:
                    medias[col] = 0.0
            coluna_vencedora = max(medias, key=medias.get)
            
        # REGRA 2: O HIGHLANDER (Regra Geral de Desempate)
        else:
            notas_brutas = {}
            for col in colunas_brigando:
                notas_brutas[col] = mapa_boletins[col][0]["bruta"]
            coluna_vencedora = max(notas_brutas, key=notas_brutas.get)

        # --------------------------------------------------------
        # A SENTENÇA (Rebaixamento dos Perdedores)
        # --------------------------------------------------------
        for col in colunas_brigando:
            if col != coluna_vencedora:
                mapa_boletins[col].pop(0)

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
        mapa_boletins[col] = avaliar_coluna_fase1(col, lista_conceitos_erp, fornecedor, df_amostra, usar_memoria=usar_memoria)
        
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