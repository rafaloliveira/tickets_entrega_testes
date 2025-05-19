from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()  # carrega as variáveis do .env

def teste_env_e_envio():
    remetente = os.getenv("EMAIL_REMETENTE")
    senha = os.getenv("EMAIL_SENHA")
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")

    print("=== Variáveis carregadas ===")
    print(f"EMAIL_REMETENTE: {remetente}")
    print(f"EMAIL_SENHA: {'*' * len(senha) if senha else None}")
    print(f"SMTP_HOST: {smtp_host}")
    print(f"SMTP_PORT: {smtp_port}")

    if not all([remetente, senha, smtp_host, smtp_port]):
        print("❌ Variáveis do .env faltando ou inválidas!")
        return

    smtp_port = int(smtp_port)

    # Monta um e-mail de teste para você enviar para você mesmo
    destinatario = remetente
    assunto = "Teste de envio via SMTP com .env"
    corpo_email = "Este é um e-mail de teste para validar o envio e as variáveis do arquivo .env."

    msg = MIMEMultipart()
    msg["From"] = remetente
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg.attach(MIMEText(corpo_email, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as servidor:
            servidor.starttls()
            servidor.login(remetente, senha)
            servidor.sendmail(remetente, [destinatario], msg.as_string())
        print("✅ E-mail de teste enviado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")

if __name__ == "__main__":
    teste_env_e_envio()
