import json
import os
import unicodedata

ARQUIVO_MEMORIA = "banco_memoria.json"

def normalizar_termo(texto):
    """Remove acentos, espaços extras e deixa tudo maiúsculo."""
    if not isinstance(texto, str): return ""
    texto = unicodedata.normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('utf-8')
    return texto.strip().upper()

def carregar_memoria():
    if os.path.exists(ARQUIVO_MEMORIA):
        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_memoria(dados):
    with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4)

def consultar_memoria(coluna_excel, conceito_visual, fornecedor):
    """Retorna o bônus/penalidade do histórico."""
    memoria = carregar_memoria()
    fornecedor_norm = normalizar_termo(fornecedor)
    col_norm = normalizar_termo(coluna_excel)
    
    if fornecedor_norm in memoria:
        if col_norm in memoria[fornecedor_norm]:
            historico = memoria[fornecedor_norm][col_norm]
            if historico.get("conceito_aprovado") == conceito_visual:
                # Se no passado aprovaram isso, ganha bônus de +20 pontos
                return 20.0 
            elif historico.get("conceito_rejeitado") == conceito_visual:
                # Se no passado rejeitaram isso, toma penalidade de -30 pontos
                return -30.0
    return 0.0

def registrar_feedback(coluna_excel, conceito_escolhido, lista_conceitos, fornecedor):
    """
    Quando o usuário clica em 'Salvar Perfil', gravamos a decisão num JSON físico.
    """
    memoria = carregar_memoria()
    fornecedor_norm = normalizar_termo(fornecedor)
    col_norm = normalizar_termo(coluna_excel)
    
    if fornecedor_norm not in memoria:
        memoria[fornecedor_norm] = {}
        
    # Salva a decisão positiva (O que o usuário escolheu)
    memoria[fornecedor_norm][col_norm] = {
        "conceito_aprovado": conceito_escolhido,
        # Poderíamos guardar o rejeitado se a IA tivesse sugerido algo diferente do que o usuário escolheu,
        # mas para manter simples, cravamos a aprovação como a verdade absoluta.
    }
    
    salvar_memoria(memoria)