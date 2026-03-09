# modulos/cerebro/mapeador.py
from configuracoes.config_erp import DICIONARIO_ERP, CONCEITOS_MULTIPLOS, REVERSO_ERP
import pandas as pd
import numpy as np

def verificar_complementaridade(df, col1, col2):
    """
    Verifica se duas colunas podem ser fundidas sem conflito real de informação.
    """
    # Criamos cópias temporárias normalizadas para comparação
    # Convertemos para string, removemos espaços e tratamos NaNs uniformemente
    s1 = df[col1].astype(str).str.strip().replace(['nan', 'None', ''], np.nan)
    s2 = df[col2].astype(str).str.strip().replace(['nan', 'None', ''], np.nan)

    # Máscara de linhas onde AMBAS têm valores preenchidos
    mask_conflito_potencial = s1.notna() & s2.notna()
    linhas_com_duplicidade = df[mask_conflito_potencial]

    if linhas_com_duplicidade.empty:
        return True # Complementaridade perfeita (onde uma tem, a outra não)

    # Se há sobreposição, os valores precisam ser exatamente iguais
    for idx in linhas_com_duplicidade.index:
        val1 = str(df.at[idx, col1]).strip()
        val2 = str(df.at[idx, col2]).strip()
        if val1 != val2:
            return False # Conflito real detectado
            
    return True # Valores sobrepostos são idênticos, unificação é segura

def processar_mapeamento_inteligente(resultados_ia, selecoes_usuario_atuais, df_amostra):
    # 1. Agrupamento por conceito (ignora múltiplos permitidos no config_erp)
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
            # Testa a complementaridade entre todas as colunas do grupo
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