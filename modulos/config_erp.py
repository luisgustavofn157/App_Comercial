# ==========================================
# DICIONÁRIO OFICIAL DO SISTEMA
# ==========================================
# A chave (esquerda) é o ID imutável que o código usa para trabalhar.
# O valor (direita) é o nome visual/emoji que aparece para o usuário na tela.

DICIONARIO_ERP = {
    "IGNORAR": "🗑️ Ignorar / Não Importa",
    "SKU": "🔑 SKU (Código Fornecedor)",
    "PRECO_BASE": "💰 Preço Base",
    "PRECO_PROMO": "🏷️ Preço Promocional",
    "POLITICA": "Política Comercial",
    "DESCONTO": "Desconto Adicional",
    "IPI": "IPI (%)",
    "NCM": "NCM",
    "CST": "Código CST / Origem",
    "DESCRICAO": "Descrição do Produto",
    "MULTIPLO": "Múltiplo de Venda",
    "EAN": "EAN / Cód. Barras",
    "MARCA": "Marca / Fabricante"
}

# Lista extraída automaticamente apenas com os nomes visuais para o Streamlit desenhar os botões
NOMES_VISUAIS_ERP = list(DICIONARIO_ERP.values())