import json
import os
import unicodedata

FICHEIRO_MEMORIA = "memoria_mapeamento.json"

def normalizar_termo(termo):
    if not termo or str(termo).strip() == "": return ""
    t = str(termo).upper().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')

def obter_chave(termo_a, termo_b):
    termos = sorted([normalizar_termo(termo_a), normalizar_termo(termo_b)])
    return f"{termos[0]}|{termos[1]}"

def carregar_memoria():
    if not os.path.exists(FICHEIRO_MEMORIA):
        # Estrutura inicial: Uma área para perfis específicos e uma área Global
        return {"fornecedores": {}, "global": {}}
    with open(FICHEIRO_MEMORIA, 'r', encoding='utf-8') as f:
        return json.load(f)

def salvar_memoria(memoria):
    with open(FICHEIRO_MEMORIA, 'w', encoding='utf-8') as f:
        json.dump(memoria, f, indent=4, ensure_ascii=False)

def consultar_memoria(coluna_excel, conceito_erp, fornecedor):
    """
    Retorna o bônus histórico somando a experiência do Fornecedor + Experiência Global.
    """
    memoria = carregar_memoria()
    chave = obter_chave(coluna_excel, conceito_erp)
    
    bonus_local = 0
    bonus_global = 0
    
    # 1. Consulta o Perfil Específico
    if fornecedor in memoria.get("fornecedores", {}) and chave in memoria["fornecedores"][fornecedor]:
        stats = memoria["fornecedores"][fornecedor][chave]
        # Cada acerto vale +15%, cada erro (punição) tira -10%
        bonus_local = (stats.get("acertos", 0) * 15.0) - (stats.get("erros", 0) * 10.0)
        
    # 2. Consulta o Cérebro Global (Transfer Learning)
    if chave in memoria.get("global", {}):
        stats_globais = memoria["global"][chave]
        # O global dá um "empurrãozinho" de +5% por cada vez que qualquer fornecedor usou isso
        bonus_global = stats_globais.get("acertos", 0) * 5.0
        
    # O bônus nunca pode ser negativo na soma final (no pior dos casos, é 0)
    bonus_final = max(bonus_local + bonus_global, 0.0)
    
    return min(bonus_final, 100.0)

def registrar_feedback(coluna_excel, conceito_escolhido, lista_conceitos_erp, fornecedor):
    """
    A Mágica do Aprendizado: Premia a escolha certa e PUNE todas as outras opções que a IA sugeriu.
    """
    memoria = carregar_memoria()
    if fornecedor not in memoria["fornecedores"]:
        memoria["fornecedores"][fornecedor] = {}
        
    for conceito in lista_conceitos_erp:
        if conceito == "🗑️ Ignorar / Não Importa": continue
        
        chave = obter_chave(coluna_excel, conceito)
        
        # Garante que as estruturas existem
        if chave not in memoria["fornecedores"][fornecedor]:
            memoria["fornecedores"][fornecedor][chave] = {"acertos": 0, "erros": 0}
        if chave not in memoria["global"]:
            memoria["global"][chave] = {"acertos": 0, "erros": 0}
            
        if conceito == conceito_escolhido:
            # PREMIAÇÃO (O usuário escolheu este)
            memoria["fornecedores"][fornecedor][chave]["acertos"] += 1
            memoria["global"][chave]["acertos"] += 1
        else:
            # PUNIÇÃO (O usuário rejeitou este conceito para esta coluna)
            memoria["fornecedores"][fornecedor][chave]["erros"] += 1
            # Não punimos o global para não estragar a regra de outros fornecedores
            
    salvar_memoria(memoria)