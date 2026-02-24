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
    "LINHA": "Linha do Produto (Leve/Pesada)",
    "MULTIPLO": "Múltiplo de Venda",
    "EAN": "EAN / Cód. Barras",
    "MARCA": "Marca / Fabricante"
}

# Lista extraída para o Streamlit desenhar os botões
NOMES_VISUAIS_ERP = list(DICIONARIO_ERP.values())

# Dicionário Reverso (Para o sistema descobrir o ID a partir do nome visual)
REVERSO_ERP = {v: k for k, v in DICIONARIO_ERP.items()}

# ==========================================
# REGRAS DE CARDINALIDADE (NOVO)
# ==========================================
# IDs que têm "Passe Livre" para aparecer em múltiplas colunas simultaneamente.
# Tudo o que NÃO estiver aqui será considerado ÚNICO (1:1).
CONCEITOS_MULTIPLOS = [
    "IGNORAR",
    "PRECO_SECUNDARIO",
    "POLITICA",
    "DESCONTO"
]

# ==========================================
# DICIONÁRIO DE SINÔNIMOS (O LÉXICO DA IA)
# ==========================================

DICIONARIO_SINONIMOS = {
    "SKU": ["COD", "CODIGO", "REF", "REFERENCIA", "PROD", "PRODUTO", "ITEM", "PARTNUMBER", "DS", "BOSH"],
    "PRECO_BASE": ["PRECO", "VLR", "VALOR", "CUSTO", "PRC", "TABELA", "BRUTO", "UNITARIO", "VENDA", "SP"],
    "PRECO_PROMO": ["PROMO", "LIQUIDO", "LIQ", "FINAL", "DESCONTADO", "OFERTA", "CAMPANHA"],
    "PRECO_SECUNDARIO": ["12", "7", "4", "ICMS", "ESTADO", "REGIAO", "SUL", "SUDESTE", "NORDESTE"],
    "IPI": ["IPI", "IMPOSTO", "ALIQ", "ALIQUOTA"],
    "DESCONTO": ["DESC", "DESCONTO"],
    "NCM": ["NCM", "FISCAL", "CLASS", "CLASSIFICACAO", "TIPI"],
    "CST": ["CST", "ORIGEM"],
    "DESCRICAO": ["DESC", "DESCRICAO", "NOME", "MATERIAL", "APLICACAO", "TEXTO"],
    "LINHA": ["LINHA", "SEGMENTO"],
    "MULTIPLO": ["MULT", "MULTIPLO", "CX", "CAIXA", "EMB", "EMBALAGEM", "QTD", "MINIMO", "QNT", "PADRAO", "FRACAO"],
    "EAN": ["EAN", "BARRAS", "GTIN", "CEAN", "CODBARRAS"],
    "MARCA": ["MARCA", "FABRICANTE", "FORNECEDOR"]
}