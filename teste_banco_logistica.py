import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sshtunnel import SSHTunnelForwarder

load_dotenv()

# Variáveis do Banco de Dados
DB_USER = os.getenv("WMS_DB_USER")
DB_PASS = os.getenv("WMS_DB_PASS")
DB_HOST = os.getenv("WMS_DB_HOST")
DB_NAME = os.getenv("WMS_DB_NAME")
DB_PORT = 25060

# Variáveis do Túnel SSH
SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PASS = os.getenv("SSH_PASS")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")

print("Iniciando a criação do Túnel SSH...")

try:
    # Lógica para usar Senha ou Chave dependendo do que foi preenchido no .env
    ssh_kwargs = {}
    if SSH_KEY_PATH:
        ssh_kwargs['ssh_pkey'] = SSH_KEY_PATH
    else:
        ssh_kwargs['ssh_password'] = SSH_PASS

    # 1. ESTÁGIO DO TÚNEL
    with SSHTunnelForwarder(
        (SSH_HOST, 22),
        ssh_username=SSH_USER,
        remote_bind_address=(DB_HOST, DB_PORT),
        **ssh_kwargs
    ) as tunnel:
        
        porta_local = tunnel.local_bind_port
        print(f"✅ Túnel SSH aberto com sucesso! Porta local gerada: {porta_local}")
        
        # 2. ESTÁGIO DO BANCO DE DADOS (Note que o IP mudou para 127.0.0.1)
        # O SQLAlchemy agora conecta na porta que o túnel abriu na sua própria máquina
        conexao_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@127.0.0.1:{porta_local}/{DB_NAME}"
        
        print("Conectando ao banco de dados pelo túnel...")
        engine = create_engine(conexao_url)
        
        with engine.connect() as conexao:
            resultado = conexao.execute(text("SELECT 1 AS teste"))
            for linha in resultado:
                print(f"✅ SUCESSO ABSOLUTO! O banco PostgreSQL respondeu: {linha.teste}")

except Exception as e:
    print(f"❌ Erro na operação:")
    print(e)