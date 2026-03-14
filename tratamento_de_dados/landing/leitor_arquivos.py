import pandas as pd
import traceback
import io
from tratamento_de_dados.landing.identificador_tabelas import encontrar_tabela_valida

def processar_arquivos_upload(arquivos_upados):
    """
    Motor exclusivo de I/O. Descobre a extensão, aplica a engine correta de leitura
    e repassa o DataFrame cru para a heurística de identificação.
    """
    tabelas_extraidas = []
    erros_encontrados = []
    
    for arquivo in arquivos_upados:
        nome_original = arquivo.name
        ext = nome_original.split('.')[-1].lower()
        nome_curto = nome_original if len(nome_original) < 40 else nome_original[:35] + "... ." + ext
        
        try:
            bytes_arquivo = io.BytesIO(arquivo.getvalue())
            
            if ext == 'csv':
                df_cru = pd.read_csv(bytes_arquivo, sep=None, engine='python', header=None)
                resultado = encontrar_tabela_valida(df_cru, nome_curto, "CSV")
                if resultado: tabelas_extraidas.append(resultado)
            else:
                motor = 'openpyxl'
                if ext == 'xls': motor = 'calamine' 
                elif ext == 'xlsb': motor = 'pyxlsb'
                
                dict_abas = pd.read_excel(bytes_arquivo, sheet_name=None, header=None, engine=motor)
                
                for aba, df_aba in dict_abas.items():
                    resultado = encontrar_tabela_valida(df_aba, nome_curto, aba)
                    if resultado: tabelas_extraidas.append(resultado)
                    
        except Exception as e:
            erros_encontrados.append({
                "arquivo": nome_curto,
                "traceback": traceback.format_exc()
            })
            
    return tabelas_extraidas, erros_encontrados