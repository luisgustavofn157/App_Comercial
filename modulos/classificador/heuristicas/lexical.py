from difflib import SequenceMatcher
from modulos.classificador.aprendizado import normalizar_termo
from configuracoes.config_erp import DICIONARIO_SINONIMOS

def avaliar_titulo(col_norm, conceito_norm, id_conceito):
    """
    Avalia a similaridade entre o nome da coluna no Excel e o conceito do ERP.
    Lida com siglas, erros de digitação e aplica pesquisa em dicionário de sinônimos.
    """
    # 1. Similaridade Base (O "Jaro-Winkler" nativo do Python)
    nota_lexica = SequenceMatcher(None, col_norm, conceito_norm).ratio() * 100

    # 2. 🛡️ Escudo Anti-Acrônimos (Impede PIS de confundir com IPI)
    if len(col_norm) <= 4 and len(conceito_norm) <= 4 and col_norm != conceito_norm:
        nota_lexica = 0.0

    # 3. 📖 Busca no Dicionário de Sinônimos
    if id_conceito in DICIONARIO_SINONIMOS:
        for termo in DICIONARIO_SINONIMOS[id_conceito]:
            termo_norm = normalizar_termo(termo)
            
            # Match exato
            if termo_norm == col_norm:
                nota_lexica = 100.0
                break # Freio de processamento
                
            # Match parcial (Substring) com penalidade de proporção
            elif termo_norm in col_norm:
                proporcao = len(termo_norm) / len(col_norm)
                # Garante que a nota não caia se a similaridade base já for maior
                nota_lexica = max(nota_lexica, 60.0 * proporcao)

    return nota_lexica