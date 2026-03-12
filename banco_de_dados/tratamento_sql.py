import pandas as pd

# Remove quebras de linhas internas e protege contra binários
def higienizar_para_exportacao(df: pd.DataFrame) -> pd.DataFrame:
    df_limpo = df.copy()
    
    for col in df_limpo.columns:
        df_limpo[col] = df_limpo[col].apply(lambda x: "<Dados Binários>" if isinstance(x, bytes) else x)
        
    df_limpo = df_limpo.fillna("")
    df_limpo = df_limpo.astype(str)
    df_limpo = df_limpo.replace(r'\n|\r|\t', ' ', regex=True)
    df_limpo = df_limpo.replace(r'[\x00-\x1F\x7F]', '', regex=True)
    
    return df_limpo