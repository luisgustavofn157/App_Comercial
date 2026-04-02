import pandas as pd
import io
from openpyxl.styles import PatternFill, Font, Border, Side

# A cor escolhida em formato Hexadecimal (RGB: 31, 73, 125)
COR_PRIMARIA_HEX = "1F497D"

def aplicar_estilo_ancora(worksheet, df):
    """
    Varre a aba do Excel recém-criada e aplica a identidade visual corporativa:
    - Cabeçalho: Fundo Azul Escuro, Fonte Branca em Negrito.
    - Linhas de Dados: Bordas finas na mesma cor do cabeçalho.
    """
    estilo_fundo_cabecalho = PatternFill(start_color=COR_PRIMARIA_HEX, end_color=COR_PRIMARIA_HEX, fill_type="solid")
    estilo_fonte_cabecalho = Font(bold=True, color="FFFFFF") 
    
    linha_borda = Side(border_style="thin", color=COR_PRIMARIA_HEX)
    estilo_borda_celula = Border(left=linha_borda, right=linha_borda, top=linha_borda, bottom=linha_borda)
    
    max_row = df.shape[0] + 1 
    max_col = df.shape[1]
    
    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = worksheet.cell(row=r, column=c)
            cell.border = estilo_borda_celula
            
            if r == 1:
                cell.fill = estilo_fundo_cabecalho
                cell.font = estilo_fonte_cabecalho

def aplicar_estilo_basico(worksheet, df):
    """
    Aplica um formato cru/neutro para extrações de banco de dados:
    - Retira o negrito do cabeçalho.
    - Força a remoção de TODAS as bordas (sobrepondo o padrão do Pandas).
    """
    estilo_fonte_normal = Font(bold=False) # Força a remoção do negrito do Pandas
    sem_borda = Border() # Borda vazia (None) atua como uma borracha
    
    max_row = df.shape[0] + 1
    max_col = df.shape[1]
    
    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = worksheet.cell(row=r, column=c)
            
            # Aplica a borracha em TODAS as células para matar qualquer padrão
            cell.border = sem_borda
            
            # Tira o negrito apenas da primeira linha
            if r == 1:
                cell.font = estilo_fonte_normal

# ==========================================
# FUNÇÕES PÚBLICAS DE EXPORTAÇÃO
# ==========================================

def exportar_devolutiva_erros(df_dados):
    """Gera o arquivo de erros/críticas (Passo 4 da Análise) com o estilo da empresa."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        nome_aba = 'Devolutiva_Erros'
        df_dados.to_excel(writer, sheet_name=nome_aba, index=False)
        worksheet = writer.sheets[nome_aba]
        aplicar_estilo_ancora(worksheet, df_dados)
       
    return output.getvalue()

def exportar_consulta_sql(df_dados):
    """Gera a extração bruta do banco de dados em um layout neutro."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        nome_aba = 'Resultado_Consulta'
        df_dados.to_excel(writer, sheet_name=nome_aba, index=False)
        
        # Aplica o estilo "clean" (sem cores, sem negrito)
        worksheet = writer.sheets[nome_aba]
        aplicar_estilo_basico(worksheet, df_dados)
        
    return output.getvalue()

def gerar_excel_critica(df_ok, df_remocao, df_erros):
    """
    Gera o ficheiro de Crítica com as três caixas da Camada Silver e aplica o estilo corporativo.
    """
    output = io.BytesIO()
    
    # Engine trocado para openpyxl para permitir a formatação
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        
        # Aba 1: Validadas 100%
        df_1 = df_ok if not df_ok.empty else pd.DataFrame(columns=['Sem dados válidos'])
        aba_1 = 'Validadas 100%'
        df_1.to_excel(writer, sheet_name=aba_1, index=False)
        aplicar_estilo_ancora(writer.sheets[aba_1], df_1)
            
        # Aba 2: Remoção Automática
        df_2 = df_remocao if not df_remocao.empty else pd.DataFrame(columns=['Sem remoções'])
        aba_2 = 'Remoção Automática'
        df_2.to_excel(writer, sheet_name=aba_2, index=False)
        aplicar_estilo_ancora(writer.sheets[aba_2], df_2)
            
        # Aba 3: Com Erros
        df_3 = df_erros if not df_erros.empty else pd.DataFrame(columns=['Sem erros detectados'])
        aba_3 = 'Com Erros'
        df_3.to_excel(writer, sheet_name=aba_3, index=False)
        aplicar_estilo_ancora(writer.sheets[aba_3], df_3)
            
    return output.getvalue()