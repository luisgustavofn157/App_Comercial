import pandas as pd
from modulos.motor_aprendizado import calcular_confianca

def gerar_propostas_fusao(tabelas_aprovadas, fornecedor="geral"):
    """
    Pega a Tabela 1 como 'Base' e compara as colunas de todas as outras tabelas com ela.
    Devolve uma lista de sugestões de unificação baseadas no aprendizado da máquina.
    """
    if len(tabelas_aprovadas) <= 1:
        return [] # Não há o que fundir se houver apenas 1 tabela

    tabela_base = tabelas_aprovadas[0]
    colunas_base = list(tabela_base['dados'].columns)
    
    propostas = []
    
    # Varre a partir da segunda tabela em diante
    for tbl in tabelas_aprovadas[1:]:
        for col_estrangeira in tbl['dados'].columns:
            
            melhor_match = None
            maior_confianca = 0
            detalhes = None
            
            # Compara a coluna estrangeira com TODAS as colunas da base
            for col_base in colunas_base:
                resultado = calcular_confianca(col_estrangeira, col_base, fornecedor)
                
                if resultado['confianca_total'] > maior_confianca:
                    maior_confianca = resultado['confianca_total']
                    melhor_match = col_base
                    detalhes = resultado
            
            # Regra de Negócio: Se a confiança for maior que 60%, sugerimos unificar
            if maior_confianca >= 60.0:
                propostas.append({
                    "id_tabela": tbl['id_unico'],
                    "aba": tbl['aba'],
                    "coluna_origem": col_estrangeira,
                    "coluna_destino": melhor_match, # A coluna que achamos que é igual
                    "confianca": maior_confianca,
                    "detalhes": detalhes
                })
            else:
                # Se não parece com nada, sugerimos manter separada como coluna nova
                propostas.append({
                    "id_tabela": tbl['id_unico'],
                    "aba": tbl['aba'],
                    "coluna_origem": col_estrangeira,
                    "coluna_destino": "💡 Manter como Coluna Nova",
                    "confianca": maior_confianca,
                    "detalhes": detalhes
                })
                
    return propostas, colunas_base