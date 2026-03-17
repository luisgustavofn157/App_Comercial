import pandas as pd
import numpy as np
from configuracoes.config_erp import DICIONARIO_ERP, CONCEITOS_MULTIPLOS, REVERSO_ERP

# ==========================================
# 1. FUNÇÕES DE APOIO A CONFLITOS (Da sua autoria)
# ==========================================
def verificar_complementaridade(df, col1, col2):
    """
    Verifica se duas colunas podem ser fundidas sem conflito real de informação.
    """
    s1 = df[col1].astype(str).str.strip().replace(['nan', 'None', ''], np.nan)
    s2 = df[col2].astype(str).str.strip().replace(['nan', 'None', ''], np.nan)

    mask_conflito_potencial = s1.notna() & s2.notna()
    linhas_com_duplicidade = df[mask_conflito_potencial]

    if linhas_com_duplicidade.empty:
        return True 

    for idx in linhas_com_duplicidade.index:
        val1 = str(df.at[idx, col1]).strip()
        val2 = str(df.at[idx, col2]).strip()
        if val1 != val2:
            return False 
            
    return True 

def processar_mapeamento_inteligente(resultados_ia, selecoes_usuario_atuais, df_amostra):
    """
    Motor de agrupamento de conceitos para sugerir unificações.
    """
    contagem_estritos = {}
    for col, escolha in selecoes_usuario_atuais.items():
        if escolha == DICIONARIO_ERP["IGNORAR"]: continue
        id_conc = REVERSO_ERP.get(escolha)
        if id_conc not in CONCEITOS_MULTIPLOS:
            contagem_estritos[escolha] = contagem_estritos.get(escolha, []) + [col]

    colunas_com_erro = []
    sugestoes_unificacao = []
    tem_conflito_bloqueante = False
    
    for conceito, colunas in contagem_estritos.items():
        if len(colunas) > 1:
            pode_unificar = True
            for i in range(len(colunas)):
                for j in range(i + 1, len(colunas)):
                    if not verificar_complementaridade(df_amostra, colunas[i], colunas[j]):
                        pode_unificar = False
                        break
            
            if pode_unificar:
                sugestoes_unificacao.append({"conceito": conceito, "colunas": colunas})
            else:
                colunas_com_erro.extend(colunas)
                tem_conflito_bloqueante = True

    return resultados_ia, tem_conflito_bloqueante, colunas_com_erro, sugestoes_unificacao

# ==========================================
# 2. FUNÇÕES DE FORJA DA CAMADA SILVER (Novas)
# ==========================================
def mesclar_colunas_seguras(df_bronze, col_mestra, col_secundaria):
    """
    Toma duas colunas que não colidem e preenche os vazios da mestra com a secundária.
    Devolve um novo DataFrame sem a coluna secundária (pois já foi absorvida).
    """
    df_temp = df_bronze.copy()
    
    # Preenche os vazios da mestra com os dados da secundária
    df_temp[col_mestra] = df_temp[col_mestra].fillna(df_temp[col_secundaria])
    
    # Apaga a coluna secundária pois já foi engolida
    df_temp = df_temp.drop(columns=[col_secundaria])
    
    return df_temp

def forjar_camada_silver(df_bronze, dicionario_mapeamento):
    """
    Recebe a camada Bronze e o dicionário com a decisão final do utilizador.
    Descarta colunas ignoradas, renomeia as restantes para o NOME TÉCNICO DO ERP
    e guarda a chave de tradução em memória.
    """
    import streamlit as st # Importado aqui para guardar no session_state
    df_silver = df_bronze.copy()
    
    # 1. Separar o joio do trigo
    colunas_para_manter = {k: v for k, v in dicionario_mapeamento.items() if v != DICIONARIO_ERP["IGNORAR"]}
    colunas_para_descartar = [k for k, v in dicionario_mapeamento.items() if v == DICIONARIO_ERP["IGNORAR"]]
    
    # 2. Descartar as colunas lixo
    colunas_existentes_descarte = [c for c in colunas_para_descartar if c in df_silver.columns]
    df_silver = df_silver.drop(columns=colunas_existentes_descarte)
    
    # 3. Converter Nome Visual -> Nome Técnico e tratar duplicados
    contagens = {}
    for destino_visual in colunas_para_manter.values():
        destino_tecnico = REVERSO_ERP.get(destino_visual, destino_visual)
        contagens[destino_tecnico] = contagens.get(destino_tecnico, 0) + 1
        
    renomeio_final = {} # Dicionário: Coluna Original Excel -> NOME TÉCNICO
    ocorrencias = {}
    
    for col_excel, destino_visual in colunas_para_manter.items():
        destino_tecnico = REVERSO_ERP.get(destino_visual, destino_visual)
        
        if contagens[destino_tecnico] > 1:
            ocorrencias[destino_tecnico] = ocorrencias.get(destino_tecnico, 0) + 1
            renomeio_final[col_excel] = f"{destino_tecnico}_{ocorrencias[destino_tecnico]}"
        else:
            renomeio_final[col_excel] = destino_tecnico
            
    # 4. Guarda os dicionários em memória para o Passo 4 usar na máscara
    st.session_state.mapa_original_para_tecnico = renomeio_final
    st.session_state.mapa_tecnico_para_original = {v: k for k, v in renomeio_final.items()}
            
    # 5. Aplicar os nomes TÉCNICOS definitivos
    df_silver = df_silver.rename(columns=renomeio_final)
    
    return df_silver