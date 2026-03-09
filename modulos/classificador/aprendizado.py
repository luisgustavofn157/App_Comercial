import json
import os
import unicodedata
from configuracoes.config_erp import REVERSO_ERP, DICIONARIO_ERP

PASTA_MEMORIA = "memoria"
ARQUIVO_MEMORIA = os.path.join(PASTA_MEMORIA, "memoria_coluna_por_perfil.json")

def obter_perfis_salvos():
    """Lê o banco de memória e retorna a lista de fornecedores já mapeados."""
    memoria = carregar_memoria()
    return sorted(list(memoria.keys()))

def normalizar_termo(texto):
    """Remove acentos, espaços extras e deixa tudo maiúsculo."""
    if not isinstance(texto, str): return ""
    texto = unicodedata.normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('utf-8')
    return texto.strip().upper()

def carregar_memoria():
    # 2. Corrigimos o verificador. Sai 'memoria.exists' e entra 'os.path.exists'
    if os.path.exists(ARQUIVO_MEMORIA):
        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_memoria(dados):
    # 3. Trava de segurança: Se a pasta "memoria" não existir, o Python cria ela antes de salvar
    if not os.path.exists(PASTA_MEMORIA):
        os.makedirs(PASTA_MEMORIA)
        
    with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def consultar_memoria(coluna_excel, conceito_visual, fornecedor):
    """Lê a matriz de pesos e devolve a nota acumulada (Bônus - Penalidade)."""
    memoria = carregar_memoria()
    fornecedor_norm = normalizar_termo(fornecedor)
    col_norm = normalizar_termo(coluna_excel)
    
    id_conceito = REVERSO_ERP.get(conceito_visual)
    if not id_conceito: return 0.0
    
    if fornecedor_norm in memoria and col_norm in memoria[fornecedor_norm]:
        # 1. Busca se tem reforço positivo para este conceito exato
        bonus = memoria[fornecedor_norm][col_norm].get(id_conceito, 0.0)
        
        # 2. Busca se existe uma punição radioativa ("Ignorar") para esta coluna
        # Se o usuário mandou ignorar no passado, subtraímos pontos de QUALQUER conceito que a IA tente sugerir.
        penalidade = memoria[fornecedor_norm][col_norm].get("PENALIZACAO_IGNORAR", 0.0)
        
        return bonus + penalidade
            
    return 0.0

def registrar_feedback(coluna_excel, conceito_visual_escolhido, fornecedor):
    """
    Motor de Machine Learning:
    - Confirmação = +10 pontos (Teto +40)
    - Rejeição (Ignorar) = -20 pontos (Piso -60)
    """
    memoria = carregar_memoria()
    fornecedor_norm = normalizar_termo(fornecedor)
    col_norm = normalizar_termo(coluna_excel)

    if fornecedor_norm not in memoria: memoria[fornecedor_norm] = {}
    if col_norm not in memoria[fornecedor_norm]: memoria[fornecedor_norm][col_norm] = {}
        
    # SE O USUÁRIO MANDOU IGNORAR:
    if conceito_visual_escolhido == DICIONARIO_ERP["IGNORAR"]:
        peso_atual_punicao = memoria[fornecedor_norm][col_norm].get("PENALIZACAO_IGNORAR", 0.0)
        # Aplica -20 pontos por rodada, mas não deixa passar de -60 de punição
        memoria[fornecedor_norm][col_norm]["PENALIZACAO_IGNORAR"] = max(peso_atual_punicao - 20.0, -60.0)
        
        # Zera qualquer bônus positivo que essa coluna pudesse ter
        chaves_para_limpar = [k for k in memoria[fornecedor_norm][col_norm].keys() if k != "PENALIZACAO_IGNORAR"]
        for k in chaves_para_limpar:
            memoria[fornecedor_norm][col_norm][k] = 0.0
            
    # SE O USUÁRIO APROVOU UM CONCEITO VÁLIDO:
    else:
        id_conceito = REVERSO_ERP.get(conceito_visual_escolhido)
        if id_conceito:
            peso_atual_bonus = memoria[fornecedor_norm][col_norm].get(id_conceito, 0.0)
            # Aplica +10 pontos por rodada, teto de +40
            memoria[fornecedor_norm][col_norm][id_conceito] = min(peso_atual_bonus + 10.0, 40.0)
            
            # Se ele aprovou, a gente limpa qualquer "Penalidade Ignorar" que tivesse aqui
            memoria[fornecedor_norm][col_norm]["PENALIZACAO_IGNORAR"] = 0.0

    salvar_memoria(memoria)