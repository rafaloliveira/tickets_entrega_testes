import smtplib

SMTP_HOST = "smtp.kinghost.net"
SMTP_PORT = 587
EMAIL = "ticket@clicklogtransportes.com.br"
SENHA = "Clicklogi9up@360"

try:
    print(f"Conectando ao servidor SMTP {SMTP_HOST}:{SMTP_PORT}...")
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
    server.starttls()
    print("Conexão segura estabelecida (STARTTLS).")
    server.login(EMAIL, SENHA)
    print("Login realizado com sucesso.")
    server.quit()
    print("✅ Teste de conexão SMTP concluído com sucesso.")
except Exception as e:
    print("❌ Erro na conexão SMTP:")
    print(e)
