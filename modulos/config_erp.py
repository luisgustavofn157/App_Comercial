# ==========================================
# DICIONÁRIO OFICIAL DO SISTEMA
# ==========================================
# A chave (esquerda) é o ID imutável que o código usa para trabalhar.
# O valor (direita) é o nome visual/emoji que aparece para o usuário na tela.

DICIONARIO_ERP = {
    "IGNORAR": "Ignorar / Não Importa",
    "SKU": "SKU (Código Fornecedor)",
    "PRECO_BASE": "Preço Base",
    "PRECO_PROMO": "Preço Promocional",
    "PRECO_SECUNDARIO": "Preços Secundários (Região/Estado)",
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

# Lista extraída para o Streamlit desenhar os botões
NOMES_VISUAIS_ERP = list(DICIONARIO_ERP.values())

# Dicionário Reverso (Para o sistema descobrir o ID a partir do nome visual que o usuário clicou)
REVERSO_ERP = {v: k for k, v in DICIONARIO_ERP.items()}

# ==========================================
# DICIONÁRIO DE SINÔNIMOS (O LÉXICO DA IA)
# ==========================================
# Agora usamos os IDs Imutáveis! Se o nome visual mudar, a IA continua funcionando perfeitamente.
DICIONARIO_SINONIMOS = {
    "SKU": ["COD", "CODIGO", "REF", "REFERENCIA", "PROD", "PRODUTO", "ITEM", "PARTNUMBER", "DS", "BOSH"],
    "PRECO_BASE": ["PRECO", "VLR", "VALOR", "CUSTO", "PRC", "TABELA", "BRUTO", "UNITARIO", "VENDA"],
    "PRECO_PROMO": ["PROMO", "LIQUIDO", "LIQ", "FINAL", "DESCONTADO", "OFERTA", "CAMPANHA"],
    "PRECO_SECUNDARIO": ["12", "7", "4", "ICMS", "ESTADO", "REGIAO", "SUL", "SUDESTE", "NORDESTE"],
    "IPI": ["IPI", "IMPOSTO", "ALIQ", "ALIQUOTA"],
    "DESCONTO": ["DESC", "DESCONTO", "LIVRE", "REBATE", "BONIF"],
    "NCM": ["NCM", "FISCAL", "CLASS", "CLASSIFICACAO", "TIPI"],
    "CST": ["CST", "ORIGEM", "TRIBUTACAO", "O", "C", "S", "T"],
    "DESCRICAO": ["DESC", "DESCRICAO", "NOME", "MATERIAL", "APLICACAO", "TEXTO"],
    "MULTIPLO": ["MULT", "MULTIPLO", "CX", "CAIXA", "EMB", "EMBALAGEM", "QTD", "MINIMO", "QNT", "PADRAO"],
    "EAN": ["EAN", "BARRAS", "GTIN", "CEAN", "CODBARRAS"],
    "MARCA": ["MARCA", "FABRICANTE", "FORNECEDOR", "LINHA"]
}