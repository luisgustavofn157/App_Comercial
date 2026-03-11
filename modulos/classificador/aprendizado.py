import unicodedata
from configuracoes.config_erp import REVERSO_ERP, DICIONARIO_ERP

# Importamos as funções do banco de dados em vez de lidar com JSON
from modulos.gerenciador_memoria import obter_pesos_coluna, salvar_pesos_coluna

def normalizar_termo(texto):
    """Remove acentos, espaços extras e deixa tudo maiúsculo."""
    if not isinstance(texto, str): return ""
    texto = unicodedata.normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('utf-8')
    return texto.strip().upper()

def consultar_memoria(coluna_excel, conceito_visual, fornecedor):
    """Lê a matriz de pesos do banco e devolve a nota acumulada (Bônus - Penalidade)."""
    fornecedor_norm = normalizar_termo(fornecedor)
    col_norm = normalizar_termo(coluna_excel)
    
    id_conceito = REVERSO_ERP.get(conceito_visual)
    if not id_conceito: return 0.0
    
    # O banco já devolve apenas os pesos exatos desta coluna, super rápido
    pesos = obter_pesos_coluna(fornecedor_norm, col_norm)
    
    # 1. Busca se tem reforço positivo
    bonus = pesos.get(id_conceito, 0.0)
    
    # 2. Busca se existe uma punição radioativa ("Ignorar")
    penalidade = pesos.get("PENALIZACAO_IGNORAR", 0.0)
    
    return bonus + penalidade

def registrar_feedback(coluna_excel, conceito_visual_escolhido, fornecedor):
    """
    Motor de Machine Learning:
    - Confirmação = +10 pontos (Teto +40)
    - Rejeição (Ignorar) = -20 pontos (Piso -60)
    """
    fornecedor_norm = normalizar_termo(fornecedor)
    col_norm = normalizar_termo(coluna_excel)

    # Busca o estado atual dos pesos no banco
    pesos = obter_pesos_coluna(fornecedor_norm, col_norm)

    # SE O USUÁRIO MANDOU IGNORAR:
    if conceito_visual_escolhido == DICIONARIO_ERP["IGNORAR"]:
        peso_atual_punicao = pesos.get("PENALIZACAO_IGNORAR", 0.0)
        pesos["PENALIZACAO_IGNORAR"] = max(peso_atual_punicao - 20.0, -60.0)
        
        # Zera qualquer bônus positivo que essa coluna pudesse ter
        for chave in list(pesos.keys()):
            if chave != "PENALIZACAO_IGNORAR":
                pesos[chave] = 0.0
                
    # SE O USUÁRIO APROVOU UM CONCEITO VÁLIDO:
    else:
        id_conceito = REVERSO_ERP.get(conceito_visual_escolhido)
        if id_conceito:
            peso_atual_bonus = pesos.get(id_conceito, 0.0)
            pesos[id_conceito] = min(peso_atual_bonus + 10.0, 40.0)
            
            # Limpa qualquer "Penalidade Ignorar" que tivesse aqui
            pesos["PENALIZACAO_IGNORAR"] = 0.0

    # Envia os pesos atualizados para o gerenciador salvar no banco
    salvar_pesos_coluna(fornecedor_norm, col_norm, pesos)