import pandas as pd
import traceback
import io
from modulos.importacao_inicial import encontrar_tabela_valida

def processar_arquivos_upload(arquivos_upados):
    """
    Recebe os arquivos crus da interface, descobre a extensão,
    aplica o motor de leitura correto e envia para o Especialista validar.
    Retorna uma lista de tabelas encontradas e uma lista de erros (se houver).
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
                df = pd.read_csv(bytes_arquivo, sep=None, engine='python', header=None)
                resultado = encontrar_tabela_valida(df, nome_curto, "CSV")
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
            # Em vez de travar tudo, capturamos o erro e devolvemos organizadamente para a interface
            erros_encontrados.append({
                "arquivo": nome_curto,
                "traceback": traceback.format_exc()
            })
            
    return tabelas_extraidas, erros_encontrados