import oracledb

def conexao():
    usuario = "DWITSM"
    senha = "a2QL#h59#Qw8#f9Y"
    dsn = "db-bi-dw-prd.manaus.am.gov.br/bidwpr"

    try:
        connection = oracledb.connect(user=usuario, password=senha, dsn=dsn)

        print("✅ Conexão realizada com sucesso!")
        print("Versão do Banco:", connection.version)
    except Exception as e:
        print("❌ Ops, erro na conexão:")
        print(e)
    return connection