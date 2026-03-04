import pandas as pd

def exportar_csv_br(df_original):
    """
    Gera um CSV à prova de falhas para o Excel do Brasil.
    Força a conversão de todos os números decimais para strings com vírgula
    antes da exportação, matando qualquer erro de leitura do Excel.
    """
    df = df_original.copy()
    
    # Pega todas as colunas que o Python reconheceu como números decimais
    colunas_float = df.select_dtypes(include=['float64', 'float32']).columns
    
    for col in colunas_float:
        # 1. Arredonda para 4 casas (Padrão ERP) para evitar dízimas de 15 dígitos
        df[col] = df[col].round(4)
        
        # 2. Transforma o número 20.6276 na string literal "20,6276". 
        # O Excel BR engole isso perfeitamente como número e não distorce nada.
        df[col] = df[col].apply(lambda x: f"{x:.4f}".replace('.', ',') if pd.notna(x) else "")
        
    # Gera o CSV. Como já cravamos as vírgulas na força bruta, o Excel não vai falhar.
    csv_string = df.to_csv(index=False, sep=';')
    
    return csv_string.encode('utf-8-sig')