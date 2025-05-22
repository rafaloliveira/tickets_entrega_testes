import smtplib
from email.message import EmailMessage

EMAIL_REMETENTE = "ticketclicklogtransportes@gmail.com"
EMAIL_SENHA = "hlossktfkqlsxepo"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
DESTINATARIO = "controladoria@clicklogtransportes.com.br"

try:
    msg = EmailMessage()
    msg['Subject'] = "Teste SMTP com Gmail – Acentos ok!"
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = DESTINATARIO
    msg.set_content("Olá!\n\nEste é um teste de envio via Gmail com acentos como: é, ç, ã, ê, etc.\n\nAbraços.")

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
    server.set_debuglevel(1)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(EMAIL_REMETENTE, EMAIL_SENHA)
    server.send_message(msg)
    server.quit()
    print("✅ E-mail enviado com sucesso!")

except Exception as e:
    print("❌ Erro ao enviar o e-mail:")
    print(e)
