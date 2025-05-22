# funcionando com envio de e-mail 21-05
# versão completa com todas as funcionalidades solicitadas
# versão liberada para usuário com correção de fuso horário e uso exclusivo de datas manuais


import streamlit as st
st.set_page_config(page_title="Entregas - Tempo de Permanência", layout="wide")

import pandas as pd
import os
import time
import uuid
import pytz
import bcrypt
import hashlib
import psycopg2
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from dateutil import parser
from psycopg2 import sql
from io import BytesIO
from dotenv import load_dotenv

from streamlit_autorefresh import st_autorefresh
import streamlit_authenticator as stauth
from streamlit_cookies_manager import EncryptedCookieManager

from supabase import create_client, Client as SupabaseClient

# --- CONFIGURAÇÕES DE E-MAIL DA KINGHOST ---
# Estas configurações podem ser movidas para um arquivo .env se preferir


EMAIL_REMETENTE = "ticket@clicklogtransportes.com.br"
EMAIL_SENHA = "Clicklogi9up@360"
SMTP_HOST = "smtp.kinghost.net"
SMTP_PORT = 587

print(os.getcwd())

# Configurar timeout para operações de socket
socket.setdefaulttimeout(10)  # 10 segundos de timeout

# --- DEFINIÇÃO DO FUSO HORÁRIO BRASILEIRO ---
# Usar este fuso horário em todas as operações de data/hora
FUSO_HORARIO_BRASIL = pytz.timezone("America/Sao_Paulo")

# --- SETUP DO COOKIE MANAGER ---
cookies = EncryptedCookieManager(
    prefix="meu_app_",  # Prefixo dos cookies
    password="chave-muito-secreta-para-cookies"  # Troque por uma senha forte
)
if not cookies.ready():
    st.stop()


# --- Função para verificar se o cookie expirou ---
def is_cookie_expired(expiry_time_str):
    try:
        expiry_time = datetime.strptime(expiry_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        # Caso o formato da data não seja o esperado, lança erro
        return False
    return datetime.now(timezone.utc) > expiry_time


# --- Função de autenticação ---
def autenticar_usuario(nome_usuario, senha):
    try:
        dados_usuario = supabase.table("usuarios").select("*").eq("nome_usuario", nome_usuario).execute()

        if dados_usuario.data:
            usuario = dados_usuario.data[0]
            if verificar_senha(senha, usuario["senha_hash"]):
                return usuario
        return None
    except Exception:
        return None

# --- CONEXÃO COM O SUPABASE ---
url = "https://vismjxhlsctehpvgmata.supabase.co"  # ✅ sua URL real, já sem o '>' no meio
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZpc21qeGhsc2N0ZWhwdmdtYXRhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY1NzA4NTIsImV4cCI6MjA2MjE0Njg1Mn0.zTjSWenfuVJTIixq2RThSUpqcHGfZWP2xkFDU3USPb0"  # ✅ sua chave real (evite expor em público!)
supabase = create_client = create_client(url, key)


# Função para hash de senha
def hash_senha(senha):
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

# Criar usuário via Supabase Auth e tabela `usuarios`
# Criar usuário direto na tabela 'usuarios' (sem Supabase Auth)

# Função para verificar se a senha fornecida corresponde ao hash
def verificar_senha(senha_fornecida, senha_hash):
    return bcrypt.checkpw(senha_fornecida.encode(), senha_hash.encode())
    
usuario_logado = "admin"  # Exemplo de nome de usuário do admin logado
dados_usuario = {
    "nome_usuario": "admin",
    "senha_hash": "$2b$12$OqjiW19Pjd9.eGnFfmJSrW.TqX/pq6RmPjbsHbuZ56MzeP3dNKuyq"  # Exemplo de senha já hashada (gerada com bcrypt)
}
    
# Função de autenticação simples com mensagens
def autenticar_usuario(nome_usuario, senha):
    try:
        dados = supabase.table("usuarios").select("*").eq("nome_usuario", nome_usuario).execute()

        if dados.data:
            usuario = dados.data[0]
            if verificar_senha(senha, usuario["senha_hash"]):
                st.success("✅ Logado com sucesso!")
                return usuario
        st.error("🛑 Usuário ou senha incorretos.")
        return None

    except Exception as e:
        st.error("Erro ao autenticar.")
        return None

# --- Interface de Login ---
def login():
    login_cookie = cookies.get("login")
    username_cookie = cookies.get("username")
    is_admin_cookie = cookies.get("is_admin")
    expiry_time_cookie = cookies.get("expiry_time")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>📝 Entregas - Tempo de Permanência </h1>", unsafe_allow_html=True)

    # Se o login já foi feito e o cookie não expirou, configura a sessão
    if login_cookie and username_cookie and not is_cookie_expired(expiry_time_cookie):
        st.session_state.login = True
        st.session_state.username = username_cookie
        st.session_state.is_admin = is_admin_cookie == "True"
        st.markdown(f"👋 **Bem-vindo, {st.session_state.username}!**")

        # Opção de logout
        col1, col2, col3 = st.columns([6, 1, 1])
        with col3:
            if st.button("🔒 Sair", key="logout_button"):
                # Limpa os cookies e faz logout
                cookies["login"] = ""
                cookies["username"] = ""
                cookies["is_admin"] = ""
                cookies["expiry_time"] = ""
                cookies.save()  # Salva a remoção dos cookies
                st.session_state.login = False  # Atualiza a sessão para refletir o logout
                st.rerun()  # Redireciona para a página inicial
    else:
        # Se o usuário não estiver logado, exibe o formulário de login
        with col2:
            st.markdown("##### Login")
            username = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")

            if st.button("Entrar", key="login_button"):
                usuario = autenticar_usuario(username, senha)
                if usuario:
                    # Armazena as informações de login nos cookies
                    cookies["login"] = str(True)
                    cookies["username"] = usuario["nome_usuario"]
                    cookies["is_admin"] = str(usuario.get("is_admin", False))
                    expiry_time = datetime.now(timezone.utc) + timedelta(hours=24)
                    cookies["expiry_time"] = expiry_time.strftime("%Y-%m-%d %H:%M:%S")
                    cookies.save()
                    st.session_state.login = True  # Atualiza a sessão para indicar que o login foi bem-sucedido
                    st.rerun()  # Recarga a página após login

        st.stop()  # Impede que o código continue sendo executado após login falhar


# --- Chama login antes de qualquer coisa ---
login()


# --- SE CHEGOU AQUI, USUÁRIO ESTÁ AUTENTICADO ---
#--------------------------------------------------------------------------INICIO APP -------------------------------------------------------------


#- -- INICIALIZAÇÃO DE SESSÃO ---
if "ocorrencias_abertas" not in st.session_state:
    st.session_state.ocorrencias_abertas = []

if "ocorrencias_finalizadas" not in st.session_state:
    st.session_state.ocorrencias_finalizadas = []

if "historico_emails" not in st.session_state:
    st.session_state.historico_emails = []

if "focal_selecionado" not in st.session_state:
    st.session_state.focal_selecionado = None

# --- ABA NOVA OCORRÊNCIA ---
# Definir abas - a aba de notificações só aparece para admin
if st.session_state.is_admin:
    aba1, aba2, aba3, aba5, aba4, aba6 = st.tabs(["📝 Nova Ocorrência", "📌 Ocorrências em Aberto", "✅ Ocorrências Finalizadas", "📝 Tickets por Focal", "📊 Configurações", "📧 Notificações por E-mail"])
else:
    aba1, aba2, aba3, aba5, aba4 = st.tabs(["📝 Nova Ocorrência", "📌 Ocorrências em Aberto", "✅ Ocorrências Finalizadas", "📝 Tickets por Focal", "📊 Configurações"])

# Definindo a conexão com o banco de dados (ajuste com as suas credenciais)
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname="nome_do_banco",
            user="usuario",
            password="senha",
            host="host_do_banco",
            port="porta"
        )
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

# --- FUNÇÕES DE DATA E HORA COM FUSO HORÁRIO ---

def obter_data_hora_atual_brasil():
    """Retorna a data e hora atual no fuso horário do Brasil."""
    return datetime.now(FUSO_HORARIO_BRASIL)

def converter_para_fuso_brasil(data_hora):
    """Converte uma data/hora para o fuso horário do Brasil."""
    if data_hora.tzinfo is None:
        # Se não tiver fuso, assume UTC
        data_hora = data_hora.replace(tzinfo=timezone.utc)
    return data_hora.astimezone(FUSO_HORARIO_BRASIL)

def calcular_diferenca_tempo(data_hora_inicial, data_hora_final=None):
    """Calcula a diferença entre duas datas/horas no mesmo fuso horário."""
    if data_hora_final is None:
        data_hora_final = obter_data_hora_atual_brasil()
    
    # Garantir que ambas as datas estão no mesmo fuso
    if data_hora_inicial.tzinfo is None:
        data_hora_inicial = FUSO_HORARIO_BRASIL.localize(data_hora_inicial)
    else:
        data_hora_inicial = data_hora_inicial.astimezone(FUSO_HORARIO_BRASIL)
    
    if data_hora_final.tzinfo is None:
        data_hora_final = FUSO_HORARIO_BRASIL.localize(data_hora_final)
    else:
        data_hora_final = data_hora_final.astimezone(FUSO_HORARIO_BRASIL)
    
    return data_hora_final - data_hora_inicial

def criar_datetime_manual(data_str, hora_str):
    """Cria um objeto datetime a partir de strings de data e hora, com fuso horário do Brasil."""
    try:
        data_hora_str = f"{data_str} {hora_str}"
        data_hora = datetime.strptime(data_hora_str, "%Y-%m-%d %H:%M:%S")
        return FUSO_HORARIO_BRASIL.localize(data_hora)
    except Exception as e:
        st.error(f"Erro ao criar datetime manual: {e}")
        return None

# Função de inserção no Supabase
def inserir_ocorrencia_supabase(dados):
    # Criar data_hora_abertura a partir dos campos manuais
    data_hora_manual = criar_datetime_manual(dados["data_abertura_manual"], dados["hora_abertura_manual"])
    
    if data_hora_manual:
        # Usar a data/hora manual para todos os campos de data/hora
        data_hora_str = data_hora_manual.strftime("%Y-%m-%d %H:%M:%S")
        timestamp_iso = data_hora_manual.isoformat()
        
        response = supabase.table("ocorrencias").insert([{
            "id": dados["id"],
            "nota_fiscal": dados["nota_fiscal"],
            "cliente": dados["cliente"],
            "focal": dados["focal"],
            "destinatario": dados["destinatario"],
            "cidade": dados["cidade"],
            "motorista": dados["motorista"],
            "tipo_de_ocorrencia": dados["tipo_de_ocorrencia"],
            "observacoes": dados["observacoes"],
            "responsavel": dados["responsavel"],
            "status": "Aberta",
            "data_hora_abertura": data_hora_str,  # Usar data/hora manual
            "abertura_timestamp": timestamp_iso,  # Usar data/hora manual
            "permanencia": dados["permanencia"],
            "complementar": dados["complementar"],
            "data_abertura_manual": dados["data_abertura_manual"],
            "hora_abertura_manual": dados["hora_abertura_manual"],
            "email_abertura_enviado": False,
            "email_finalizacao_enviado": False
        }]).execute()
        return response
    else:
        st.error("Erro ao criar data/hora manual para inserção no banco")
        return None


# --- CARREGAMENTO DE DADOS Tabelas com nomes de motorista e clientes ---
import pandas as pd

# Carrega a aba "clientes" do arquivo clientes.xlsx
df_clientes = pd.read_excel("data/clientes.xlsx", sheet_name="clientes")
df_clientes.columns = df_clientes.columns.str.strip()  # Remove espaços extras nas colunas
df_clientes = df_clientes[["Cliente", "Focal"]].dropna(subset=["Cliente"])

# Carrega a lista de cidades do arquivo cidade.xlsx
df_cidades = pd.read_excel("data/cidade.xlsx")
df_cidades.columns = df_cidades.columns.str.strip()
cidades = df_cidades["cidade"].dropna().unique().tolist()

# Cria dicionário Cliente -> Focal e lista de clientes
cliente_to_focal = dict(zip(df_clientes["Cliente"], df_clientes["Focal"]))
clientes = df_clientes["Cliente"].tolist()

# Carrega a aba "motoristas" do arquivo motoristas.xlsx
df_motoristas = pd.read_excel("data/motoristas.xlsx", sheet_name="motoristas")
df_motoristas.columns = df_motoristas.columns.str.strip()
motoristas = df_motoristas["Motorista"].dropna().tolist()

# --- FORMULÁRIO PARA NOVA OCORRÊNCIA ---




# Função de classificação
from datetime import datetime
import pytz

# =========================
#    FUNÇÃO CLASSIFICAÇÃO
# =========================
def classificar_ocorrencia_por_tempo(data_str, hora_str):
    try:
        # Criar datetime a partir das strings de data e hora
        data_hora = criar_datetime_manual(data_str, hora_str)
        if not data_hora:
            return "Erro", "gray"
        
        # Calcula a diferença de tempo com a hora atual do Brasil
        agora = obter_data_hora_atual_brasil()
        diferenca = calcular_diferenca_tempo(data_hora, agora)
        
        # Classifica com base no tempo decorrido (novos intervalos)
        if diferenca <= timedelta(minutes=15):
            return "Até 15min", "#2ecc71"  # Verde
        elif diferenca <= timedelta(minutes=30):
            return "15-30min", "#f39c12"  # Laranja
        elif diferenca <= timedelta(minutes=45):
            return "30-45min", "#e74c3c"  # Vermelho
        else:
            return "Mais de 45min", "#800000"  # Vermelho escuro
            
    except Exception as e:
        print(f"Erro ao classificar ocorrência: {e}")
        return "Erro", "gray"


# =========================
#    FUNÇÕES DE E-MAIL
# =========================

def carregar_dados_clientes_email():
    """Carrega os dados dos clientes da planilha, incluindo e-mails."""
    try:
        df = pd.read_excel('data/clientes.xlsx')
        # Criar um dicionário com Cliente como chave e e-mails como valores
        clientes_emails = {}
        for _, row in df.iterrows():
            cliente = row['Cliente']
            email_principal = row.get('enviar_para_email')
            email_copia = row.get('email_copia')
            
            # Só adiciona se tiver pelo menos um e-mail principal
            if pd.notna(email_principal):
                clientes_emails[cliente] = {
                    'principal': email_principal,
                    'copia': email_copia if pd.notna(email_copia) else None
                }
        
        return clientes_emails
    except Exception as e:
        st.error(f"Erro ao carregar dados dos clientes: {e}")
        return {}

def obter_ocorrencias_abertas_30min():
    """Obtém ocorrências abertas há mais de 30 minutos que ainda não receberam e-mail."""
    try:
        # Obter todas as ocorrências abertas que ainda não receberam e-mail
        response = supabase.table("ocorrencias").select("*").eq("status", "Aberta").eq("email_abertura_enviado", False).execute()
        ocorrencias = response.data
        
        # Filtrar ocorrências abertas há mais de 30 minutos
        ocorrencias_30min = []
        agora = obter_data_hora_atual_brasil()
        
        for ocorr in ocorrencias:
            # Verificar se tem data e hora manual
            if ocorr.get("data_abertura_manual") and ocorr.get("hora_abertura_manual"):
                try:
                    # Criar datetime a partir das strings de data e hora manual
                    data_hora_abertura = criar_datetime_manual(
                        ocorr["data_abertura_manual"], 
                        ocorr["hora_abertura_manual"]
                    )
                    
                    if data_hora_abertura:
                        # Verificar se passou mais de 30 minutos
                        diferenca = calcular_diferenca_tempo(data_hora_abertura, agora)
                        if diferenca > timedelta(minutes=30):
                            ocorrencias_30min.append(ocorr)
                except Exception as e:
                    st.error(f"Erro ao processar data/hora da ocorrência {ocorr.get('nota_fiscal', '-')}: {e}")
        
        return ocorrencias_30min
    except Exception as e:
        st.error(f"Erro ao obter ocorrências abertas: {e}")
        return []

def marcar_email_como_enviado(ocorrencia_id, tipo="abertura"):
    """Marca a ocorrência como tendo recebido e-mail."""
    try:
        campo = "email_abertura_enviado" if tipo == "abertura" else "email_finalizacao_enviado"
        response = supabase.table("ocorrencias").update({
            campo: True
        }).eq("id", ocorrencia_id).execute()
        
        return response.data is not None
    except Exception as e:
        st.error(f"Erro ao atualizar status de e-mail enviado: {e}")
        return False

def enviar_email(destinatario, copia, assunto, corpo):
    """Envia e-mail usando as configurações da KingHost."""
    try:
        # Criar mensagem
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = destinatario
        
        # Adicionar cópias se existirem
        if copia:
            # Separar múltiplos e-mails em CC (separados por ponto e vírgula)
            emails_cc = [email.strip() for email in copia.split(';') if email.strip()]
            if emails_cc:
                msg['Cc'] = ', '.join(emails_cc)
        
        msg['Subject'] = assunto
        
        # Adicionar corpo do e-mail
        msg.attach(MIMEText(corpo, 'html'))
        
        # Conectar ao servidor SMTP com timeout
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        
        # Determinar todos os destinatários (principal + cópias)
        todos_destinatarios = [destinatario]
        if copia:
            todos_destinatarios.extend([email.strip() for email in copia.split(';') if email.strip()])
        
        # Enviar e-mail
        server.sendmail(EMAIL_REMETENTE, todos_destinatarios, msg.as_string())
        server.quit()
        
        return True, "E-mail enviado com sucesso"
    except socket.timeout:
        return False, "Timeout ao conectar ao servidor SMTP. Possível bloqueio de firewall."
    except smtplib.SMTPAuthenticationError:
        return False, "Falha na autenticação. Verifique usuário e senha."
    except Exception as e:
        return False, f"Erro ao enviar e-mail: {e}"

def verificar_e_enviar_email_abertura(ocorrencia):
    """Verifica se a ocorrência precisa de e-mail e envia se necessário."""
    try:
        # Verificar se já passou 30 minutos desde a abertura
        agora = obter_data_hora_atual_brasil()
        
        if ocorrencia.get("data_abertura_manual") and ocorrencia.get("hora_abertura_manual"):
            # Criar datetime a partir das strings de data e hora manual
            data_hora_abertura = criar_datetime_manual(
                ocorrencia["data_abertura_manual"], 
                ocorrencia["hora_abertura_manual"]
            )
            
            if not data_hora_abertura:
                return False, "Erro ao criar datetime a partir de data/hora manual"
            
            # Verificar se passou mais de 30 minutos
            diferenca = calcular_diferenca_tempo(data_hora_abertura, agora)
            if diferenca > timedelta(minutes=30):
                # Carregar dados do cliente
                clientes_emails = carregar_dados_clientes_email()
                cliente = ocorrencia.get('cliente')
                
                if cliente in clientes_emails:
                    email_info = clientes_emails[cliente]
                    email_principal = email_info['principal']
                    email_copia = email_info['copia']
                    
                    # Formatar data/hora para exibição
                    data_hora_str = f"{ocorrencia['data_abertura_manual']} {ocorrencia['hora_abertura_manual']}"
                    
                    # Criar corpo do e-mail
                    corpo_html = f"""
                    <html>
                    <head>
                        <style>
                            body {{ font-family: Arial, sans-serif; }}
                            table {{ border-collapse: collapse; width: 100%; }}
                            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                            th {{ background-color: #f2f2f2; }}
                            .header {{ background-color: #4CAF50; color: white; padding: 10px; }}
                        </style>
                    </head>
                    <body>
                        <div class="header">
                            <h2>Notificação de Ocorrência Aberta</h2>
                        </div>
                        <p>Prezado cliente <strong>{cliente}</strong>,</p>
                        <p>Informamos que a seguinte ocorrência está aberta há mais de 30 minutos:</p>
                        <table>
                            <tr>
                                <th>Ticket</th>
                                <th>Nota Fiscal</th>
                                <th>Destinatário</th>
                                <th>Cidade</th>
                                <th>Motorista</th>
                                <th>Tipo</th>
                                <th>Data/Hora Abertura</th>
                            </tr>
                            <tr>
                                <td>{ocorrencia.get('numero_ticket', '-')}</td>
                                <td>{ocorrencia.get('nota_fiscal', '-')}</td>
                                <td>{ocorrencia.get('destinatario', '-')}</td>
                                <td>{ocorrencia.get('cidade', '-')}</td>
                                <td>{ocorrencia.get('motorista', '-')}</td>
                                <td>{ocorrencia.get('tipo_de_ocorrencia', '-')}</td>
                                <td>{data_hora_str}</td>
                            </tr>
                        </table>
                        <p>Por favor, entre em contato conosco para mais informações.</p>
                        <p>Atenciosamente,<br>Equipe de Suporte</p>
                    </body>
                    </html>
                    """
                    
                    # Enviar e-mail
                    assunto = f"Notificação: Ocorrência Aberta - {cliente} - NF {ocorrencia.get('nota_fiscal', '-')}"
                    sucesso, mensagem = enviar_email(email_principal, email_copia, assunto, corpo_html)
                    
                    if sucesso:
                        # Marcar como enviado no banco
                        marcar_email_como_enviado(ocorrencia["id"], "abertura")
                        
                        # Registrar no histórico
                        st.session_state.historico_emails.append({
                            "data": obter_data_hora_atual_brasil().strftime("%d-%m-%Y %H:%M:%S"),
                            "tipo": "Abertura",
                            "cliente": cliente,
                            "email": email_principal,
                            "ticket": ocorrencia.get('numero_ticket', '-'),
                            "nota_fiscal": ocorrencia.get('nota_fiscal', '-'),
                            "status": "Enviado"
                        })
                        
                        return True, "E-mail enviado com sucesso"
                    else:
                        return False, mensagem
                else:
                    return False, "Cliente não possui e-mail cadastrado"
            else:
                return False, f"Ocorrência aberta há menos de 30 minutos (diferença: {diferenca})"
        else:
            return False, "Dados de data/hora de abertura ausentes"
    except Exception as e:
        return False, f"Erro ao verificar e enviar e-mail: {e}"

def enviar_email_finalizacao(ocorrencia):
    """Envia e-mail de finalização para o cliente."""
    try:
        # Carregar dados do cliente
        clientes_emails = carregar_dados_clientes_email()
        cliente = ocorrencia.get('cliente')
        
        if cliente in clientes_emails:
            email_info = clientes_emails[cliente]
            email_principal = email_info['principal']
            email_copia = email_info['copia']
            
            # Obter dados de abertura e finalização
            data_abertura = f"{ocorrencia.get('data_abertura_manual', '-')} {ocorrencia.get('hora_abertura_manual', '-')}"
            data_finalizacao = f"{ocorrencia.get('data_finalizacao_manual', '-')} {ocorrencia.get('hora_finalizacao_manual', '-')}"
            
            # Criar corpo do e-mail
            corpo_html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .header {{ background-color: #4CAF50; color: white; padding: 10px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>Notificação de Ocorrência Finalizada</h2>
                </div>
                <p>Prezado cliente <strong>{cliente}</strong>,</p>
                <p>Informamos que a seguinte ocorrência foi finalizada:</p>
                <table>
                    <tr>
                        <th>Ticket</th>
                        <th>Nota Fiscal</th>
                        <th>Destinatário</th>
                        <th>Cidade</th>
                        <th>Motorista</th>
                        <th>Tipo</th>
                        <th>Data/Hora Abertura</th>
                        <th>Data/Hora Finalização</th>
                        <th>Permanência</th>
                    </tr>
                    <tr>
                        <td>{ocorrencia.get('numero_ticket', '-')}</td>
                        <td>{ocorrencia.get('nota_fiscal', '-')}</td>
                        <td>{ocorrencia.get('destinatario', '-')}</td>
                        <td>{ocorrencia.get('cidade', '-')}</td>
                        <td>{ocorrencia.get('motorista', '-')}</td>
                        <td>{ocorrencia.get('tipo_de_ocorrencia', '-')}</td>
                        <td>{data_abertura}</td>
                        <td>{data_finalizacao}</td>
                        <td>{ocorrencia.get('permanencia_manual', '-')}</td>
                    </tr>
                </table>
                <p><strong>Complemento:</strong> {ocorrencia.get('complementar', 'Sem complemento.')}</p>
                <p>Atenciosamente,<br>Equipe de Suporte</p>
            </body>
            </html>
            """
            
            # Enviar e-mail
            assunto = f"Notificação: Ocorrência Finalizada - {cliente} - NF {ocorrencia.get('nota_fiscal', '-')}"
            sucesso, mensagem = enviar_email(email_principal, email_copia, assunto, corpo_html)
            
            if sucesso:
                # Marcar como enviado no banco
                marcar_email_como_enviado(ocorrencia["id"], "finalizacao")
                
                # Registrar no histórico
                st.session_state.historico_emails.append({
                    "data": obter_data_hora_atual_brasil().strftime("%d-%m-%Y %H:%M:%S"),
                    "tipo": "Finalização",
                    "cliente": cliente,
                    "email": email_principal,
                    "ticket": ocorrencia.get('numero_ticket', '-'),
                    "nota_fiscal": ocorrencia.get('nota_fiscal', '-'),
                    "status": "Enviado"
                })
                
                return True, "E-mail de finalização enviado com sucesso"
            else:
                return False, mensagem
        else:
            return False, "Cliente não possui e-mail cadastrado"
    except Exception as e:
        return False, f"Erro ao enviar e-mail de finalização: {e}"

def notificar_ocorrencias_abertas():
    """Notifica clientes sobre ocorrências abertas há mais de 30 minutos e atualiza o status no banco."""
    resultados = []
    
    # Obter ocorrências abertas há mais de 30 minutos que ainda não receberam e-mail
    ocorrencias = obter_ocorrencias_abertas_30min()
    
    if not ocorrencias:
        return [{"status": "info", "mensagem": "Não há ocorrências abertas há mais de 30 minutos que precisem de notificação."}]
    
    # Enviar e-mail para cada ocorrência individualmente
    for ocorr in ocorrencias:
        sucesso, mensagem = verificar_e_enviar_email_abertura(ocorr)
        
        resultados.append({
            "cliente": ocorr.get('cliente'),
            "ticket": ocorr.get('numero_ticket', '-'),
            "nota_fiscal": ocorr.get('nota_fiscal', '-'),
            "status": "sucesso" if sucesso else "erro",
            "mensagem": mensagem
        })
    
    return resultados

def testar_conexao_smtp():
        """Testa a conexão com o servidor SMTP, com fallback e debug."""
        if not EMAIL_REMETENTE or not EMAIL_SENHA or not SMTP_HOST or not SMTP_PORT:
            return False, "❌ Variáveis de ambiente não carregadas corretamente. Verifique o arquivo .env."

        try:
            # Primeira tentativa: porta 587 com STARTTLS
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            server.set_debuglevel(1)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_REMETENTE, EMAIL_SENHA)
            server.quit()
            return True, "✅ Conexão SMTP (TLS na porta 587) bem-sucedida!"
        except Exception as e1:
            print("❗ Falha na porta 587. Tentando fallback para SSL 465...")
            try:
                # Segunda tentativa: porta 465 com SSL
                server = smtplib.SMTP_SSL(SMTP_HOST, 465, timeout=10)
                server.set_debuglevel(1)
                server.login(EMAIL_REMETENTE, EMAIL_SENHA)
                server.quit()
                return True, "✅ Conexão SMTP (SSL na porta 465) bem-sucedida!"
            except Exception as e2:
                return False, f"❌ Falha nas duas tentativas de conexão SMTP.\nErro TLS (587): {e1}\nErro SSL (465): {e2}"

# Função para carregar ocorrências abertas
def carregar_ocorrencias_abertas():
    try:
        response = supabase.table("ocorrencias").select("*").eq("status", "Aberta").order("data_hora_abertura", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao carregar ocorrências abertas: {e}")
        return []

# Função para carregar ocorrências por focal
def carregar_ocorrencias_por_focal(focal=None):
    try:
        if focal:
            response = supabase.table("ocorrencias").select("*").eq("status", "Aberta").eq("focal", focal).order("data_hora_abertura", desc=True).execute()
        else:
            response = supabase.table("ocorrencias").select("*").eq("status", "Aberta").order("data_hora_abertura", desc=True).execute()
        
        return response.data
    except Exception as e:
        st.error(f"Erro ao carregar ocorrências por focal: {e}")
        return []

# Função para obter lista de focais com contagem de tickets
def obter_focais_com_contagem():
    try:
        ocorrencias = carregar_ocorrencias_abertas()
        
        # Agrupar por focal e contar
        focais_contagem = {}
        for ocorr in ocorrencias:
            focal = ocorr.get('focal')
            if focal:
                if focal not in focais_contagem:
                    focais_contagem[focal] = 0
                focais_contagem[focal] += 1
        
        # Ordenar por contagem (decrescente)
        focais_ordenados = sorted(focais_contagem.items(), key=lambda x: x[1], reverse=True)
        
        return focais_ordenados
    except Exception as e:
        st.error(f"Erro ao obter focais com contagem: {e}")
        return []

# Função para finalizar ocorrência
def finalizar_ocorrencia(ocorr, complemento, data_finalizacao_manual, hora_finalizacao_manual):
    try:
        data_abertura_manual = ocorr.get("data_abertura_manual")
        hora_abertura_manual = ocorr.get("hora_abertura_manual")
        
        if not data_abertura_manual or not hora_abertura_manual:
            return False, "Data/hora de abertura manual ausente. Não é possível calcular a permanência."
        
        try:
            # Converter string para datetime com fuso horário do Brasil
            try:
                data_hora_finalizacao = datetime.strptime(
                    f"{data_finalizacao_manual} {hora_finalizacao_manual}", "%d-%m-%Y %H:%M"
                )
                data_hora_finalizacao = FUSO_HORARIO_BRASIL.localize(data_hora_finalizacao)
            except ValueError:
                return False, "Formato inválido para data/hora de finalização. Use DD-MM-AAAA para a data e HH:MM para a hora."
            
            # Converter data/hora de abertura para datetime com fuso horário do Brasil
            data_hora_abertura = criar_datetime_manual(data_abertura_manual, hora_abertura_manual)
            if not data_hora_abertura:
                return False, "Erro ao criar datetime a partir de data/hora de abertura manual."
            
            if data_hora_finalizacao < data_hora_abertura:
                return False, "Data/hora de finalização não pode ser menor que a data/hora de abertura."
            
            # Calcular diferença de tempo no mesmo fuso horário
            delta = calcular_diferenca_tempo(data_hora_abertura, data_hora_finalizacao)
            total_segundos = int(delta.total_seconds())
            horas_totais = total_segundos // 3600
            minutos = (total_segundos % 3600) // 60
            permanencia_manual = f"{horas_totais:02d}:{minutos:02d}"
            
            # Formatar para o banco
            data_finalizacao_banco = data_hora_finalizacao.strftime("%Y-%m-%d")
            hora_finalizacao_banco = f"{hora_finalizacao_manual}:00"
            
            # Atualizar no banco
            response = supabase.table("ocorrencias").update({
                "data_hora_finalizacao": data_hora_finalizacao.strftime("%Y-%m-%d %H:%M"),
                "finalizado_por": st.session_state.username,
                "complementar": complemento,
                "status": "Finalizada",
                "permanencia_manual": permanencia_manual,
                "data_finalizacao_manual": data_finalizacao_banco,
                "hora_finalizacao_manual": hora_finalizacao_banco,
                "email_finalizacao_enviado": False  # Inicializa como não enviado
            }).eq("id", ocorr["id"]).execute()
            
            if response and response.data:
                # Enviar e-mail de finalização
                ocorr_atualizada = response.data[0]
                enviar_email_finalizacao(ocorr_atualizada)
                
                return True, "Ocorrência finalizada com sucesso!"
            else:
                return False, "Erro ao salvar a finalização no banco de dados."
        except Exception as e:
            return False, f"Erro ao calcular ou salvar permanência manual: {e}"
    except Exception as e:
        return False, f"Erro ao finalizar ocorrência: {e}"

# =========================
#     ABA 1 - NOVA OCORRENCIA
# =========================
with aba1:
    st.header("Nova Ocorrência")

    # Definindo sessão focal_responsavel
    if "focal_responsavel" not in st.session_state:
        st.session_state["focal_responsavel"] = ""

    # Formulário para nova ocorrência
    with st.form("form_nova_ocorrencia", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            nf = st.text_input("Nota Fiscal", key="nf")
            nf_invalida = nf != "" and not nf.isdigit()
            if nf_invalida:
                st.error("Por favor, insira apenas números na Nota Fiscal.")

            destinatario = st.text_input("Destinatário", key="destinatario")

            cliente_opcao = st.selectbox("Cliente", options=clientes + ["Outro ()"], index=None, key="cliente_opcao")
            cliente = st.text_input("Digite o nome do cliente", key="cliente_manual") if cliente_opcao == "Outro ()" else cliente_opcao

            if cliente_opcao and cliente_opcao in cliente_to_focal:
                st.session_state["focal_responsavel"] = cliente_to_focal[cliente_opcao]
            elif cliente_opcao:
                st.session_state["focal_responsavel"] = ""

            cidade_opcao = st.selectbox("Cidade", options=cidades + ["Outro (digitar manualmente)"], index=None, key="cidade_opcao")
            cidade = st.text_input("Digite o nome da cidade", key="cidade_manual") if cidade_opcao == "Outro (digitar manualmente)" else cidade_opcao


        with col2:
            motorista_opcao = st.selectbox("Motorista", options=motoristas + ["Outro (digitar manualmente)"], index=None, key="motorista_opcao")
            motorista = st.text_input("Digite o nome do motorista", key="motorista_manual") if motorista_opcao == "Outro (digitar manualmente)" else motorista_opcao
            tipo = st.multiselect("Tipo de Ocorrência", options=["Chegada no Local", "Pedido Bloqueado", "Demora", "Divergência"], key="tipo_ocorrencia")
            obs = st.text_area("Observações", key="observacoes")
            responsavel = st.session_state.username
            st.text_input("Quem está abrindo o ticket", value=responsavel, disabled=True)

            #### data e hora de abertura inserido manual #####
            st.markdown("")

            col_data, col_hora = st.columns(2)
            with col_data:
                data_abertura_manual = st.date_input("Data de Abertura", format="DD/MM/YYYY")
            with col_hora:
                hora_abertura_manual = st.time_input("Hora de Abertura")


        enviar = st.form_submit_button("Adicionar Ocorrência")


        # Validações
        if enviar:
            campos_obrigatorios = {
                "Nota Fiscal": nf,
                "Cliente": cliente,
                "Focal Responsável": st.session_state["focal_responsavel"],
                "Destinatário": destinatario,
                "Cidade": cidade,
                "Motorista": motorista,
                "Tipo de Ocorrência": tipo,
                "Responsável": responsavel
            }

            faltando = [campo for campo, valor in campos_obrigatorios.items() if not valor]

            if nf_invalida:
                st.error("Ocorrência não adicionada: Nota Fiscal deve conter apenas números.")
            elif faltando:
                st.error(f"❌ Preencha todos os campos obrigatórios: {', '.join(faltando)}")
            elif not cliente:  # Verificação adicional para o campo "Cliente"
                st.error("❌ O campo 'Cliente' é obrigatório.")
        
            else:
                # Gera número de ticket único baseado em data/hora
                numero_ticket = obter_data_hora_atual_brasil().strftime("%Y%m%d%H%M%S%f")  # Ex: 20250513151230543210

                # Formatar data e hora manual para string no formato esperado pelo banco
                data_abertura_manual_str = data_abertura_manual.strftime("%Y-%m-%d")
                hora_abertura_manual_str = hora_abertura_manual.strftime("%H:%M:%S")

                # Montagem do dicionário de nova ocorrência
                nova_ocorrencia = {
                    "id": str(uuid.uuid4()),
                    "numero_ticket": numero_ticket, #numero ticket
                    "nota_fiscal": nf,
                    "cliente": cliente,
                    "focal": st.session_state["focal_responsavel"],
                    "destinatario": destinatario,
                    "cidade": cidade,
                    "motorista": motorista,
                    "tipo_de_ocorrencia": ", ".join(tipo),
                    "observacoes": obs,
                    "responsavel": responsavel,
                    "data_abertura_manual": data_abertura_manual_str, # data abertura inserido manual
                    "hora_abertura_manual": hora_abertura_manual_str, # hora abertura inserido manual
                    "complementar": "",
                    "permanencia": "",
                }

                # Inserção no banco de dados
                response = inserir_ocorrencia_supabase(nova_ocorrencia)
                
                if response and response.data:
                    # Adiciona localmente para exibição imediata
                    nova_ocorrencia_local = nova_ocorrencia.copy()
                    nova_ocorrencia_local["Data/Hora Finalização"] = ""
                    st.session_state.ocorrencias_abertas.append(nova_ocorrencia_local)

                    st.session_state["focal_responsavel"] = ""

                    sucesso = st.empty()
                    sucesso.success("✅ Ocorrência aberta com sucesso!")
                    time.sleep(2)
                    sucesso.empty()
                    
                    # Verificar se precisa enviar e-mail (mais de 30 minutos)
                    verificar_e_enviar_email_abertura(nova_ocorrencia)
                    print("Verificando e-mails...")
                else:
                    st.error(f"Erro ao salvar ocorrência no Supabase: {response.error if response else 'Erro desconhecido'}")

# =========================
#     ABA 2 - EM ABERTO
# =========================
with aba2:
    st.header("Ocorrências em Aberto")

    ocorrencias_abertas = carregar_ocorrencias_abertas()
    
    # Verificar e enviar e-mails para ocorrências abertas há mais de 30 minutos
    for ocorr in ocorrencias_abertas:
        if not ocorr.get("email_abertura_enviado", False):
            verificar_e_enviar_email_abertura(ocorr)

    if not ocorrencias_abertas:
        st.info("ℹ️ Nenhuma ocorrência aberta no momento.")
    else:
        num_colunas = 4
        colunas = st.columns(num_colunas)
        st_autorefresh(interval=40000, key="ocorrencias_abertas_refresh")

        for idx, ocorr in enumerate(ocorrencias_abertas):
            status = "Data manual ausente"
            cor = "gray"
            abertura_manual_formatada = "Não informada"
            data_abertura_manual = ocorr.get("data_abertura_manual")
            hora_abertura_manual = ocorr.get("hora_abertura_manual")

            if data_abertura_manual and hora_abertura_manual:
                try:
                    # Criar datetime a partir das strings de data e hora manual
                    dt_manual = criar_datetime_manual(data_abertura_manual, hora_abertura_manual)
                    if dt_manual:
                        abertura_manual_formatada = dt_manual.strftime("%d-%m-%Y %H:%M:%S")

                        # Classificação por tempo com base nas datas manuais
                        status, cor = classificar_ocorrencia_por_tempo(data_abertura_manual, hora_abertura_manual)
                    else:
                        status = "Erro"
                        cor = "gray"

                except Exception as e:
                    st.error(f"Erro ao processar data/hora manual da ocorrência {ocorr.get('nota_fiscal', '-')}: {e}")
                    status = "Erro"
                    cor = "gray"

            with colunas[idx % num_colunas]:
                safe_idx = f"{idx}_{ocorr.get('nota_fiscal', '')}"

                with st.container():
                    # Adicionar indicador de e-mail enviado
                    email_enviado = ocorr.get('email_abertura_enviado', False)
                    email_status = "📧 E-mail enviado" if email_enviado else ""
                    
                    st.markdown(
                        f"""
                        <div style='background-color:{cor};padding:10px;border-radius:10px;color:white;
                        box-shadow: 0 4px 10px rgba(0,0,0,0.3);margin-bottom:5px;min-height:250px;font-size:15px;'>
                        <strong>Ticket #:</strong> {ocorr.get('numero_ticket', 'N/A')}<br>
                        <strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;
                        border-radius:1px;color:white;'>{status}</span> {email_status}<br>
                        <strong>NF:</strong> {ocorr.get('nota_fiscal', '-')}<br>
                        <strong>Cliente:</strong> {ocorr.get('cliente', '-')}<br>
                        <strong>Destinatário:</strong> {ocorr.get('destinatario', '-')}<br>
                        <strong>Focal:</strong> {ocorr.get('focal', '-')}<br>
                        <strong>Cidade:</strong> {ocorr.get('cidade', '-')}<br>
                        <strong>Motorista:</strong> {ocorr.get('motorista', '-')}<br>
                        <strong>Tipo:</strong> {ocorr.get('tipo_de_ocorrencia', '-')}<br>
                        <strong>Aberto por:</strong> {ocorr.get('responsavel', '-')}<br>
                        <strong>Data Abertura:</strong> {abertura_manual_formatada.split(" ")[0] if abertura_manual_formatada != "Não informada" else 'Não informada'}<br>
                        <strong>Hora Abertura:</strong> {hora_abertura_manual or 'Não informada'}<br> 
                        <strong>Observações:</strong> {ocorr.get('observacoes', 'Sem observações.')}<br>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with st.expander("Finalizar Ocorrência"):
                    data_atual = obter_data_hora_atual_brasil().strftime("%d-%m-%Y")
                    hora_atual = obter_data_hora_atual_brasil().strftime("%H:%M")
                    data_finalizacao_manual = st.text_input("Data Finalização (DD-MM-AAAA)", value=data_atual, key=f"data_final_{safe_idx}")
                    hora_finalizacao_manual = st.text_input("Hora Finalização (HH:MM)", value=hora_atual, key=f"hora_final_{safe_idx}")

                    complemento_key = f"complemento_final_{safe_idx}"
                    if complemento_key not in st.session_state:
                        st.session_state[complemento_key] = ""

                    complemento = st.text_area("Complementar", key=complemento_key, value=st.session_state[complemento_key])
                    finalizar_disabled = not complemento.strip()

                    if st.button("Finalizar", key=f"finalizar_{safe_idx}", disabled=finalizar_disabled):
                        if finalizar_disabled:
                            st.error("❌ O campo 'Complementar' é obrigatório para finalizar a ocorrência.")
                        else:
                            sucesso, mensagem = finalizar_ocorrencia(
                                ocorr, 
                                complemento, 
                                data_finalizacao_manual, 
                                hora_finalizacao_manual
                            )
                            
                            if sucesso:
                                st.success(mensagem)
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(mensagem)

# =============================== 
#    FUNÇÃO CARREGAR FINALIZADAS 
# ===============================        
def carregar_ocorrencias_finalizadas():
    try:
        response = supabase.table("ocorrencias").select("*").eq("status", "Finalizada").order("data_hora_finalizacao", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao carregar ocorrências finalizadas: {e}")
        return []


# =========================
#     ABA 3 - FINALIZADAS
# =========================
with aba3:
    st.header("Ocorrências Finalizadas")

    try:
        ocorrencias_finalizadas = carregar_ocorrencias_finalizadas()
    except Exception as e:
        st.error(f"Erro ao carregar ocorrências finalizadas: {e}")
        st.stop()

    if not ocorrencias_finalizadas:
        st.info("ℹ️ Nenhuma ocorrência finalizada.")
    else:
        # --- Filtros e exportação ---
        col1, col2 = st.columns([1, 2])
        with col1:
            filtro_nf = st.text_input("🔎 Pesquisar por NF:", "", max_chars=10)
        with col2:
            if st.button("📤 Exportar Excel"):
                try:
                    df = pd.DataFrame(ocorrencias_finalizadas)
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Finalizadas')
                    st.download_button(
                        label="⬇️ Baixar Relatório Excel",
                        data=output.getvalue(),
                        file_name="ocorrencias_finalizadas.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except Exception as e:
                    st.error(f"Erro ao exportar para Excel: {e}")

        # --- Filtrar ---
        if filtro_nf:
            ocorrencias_filtradas = [
                ocorr for ocorr in ocorrencias_finalizadas
                if filtro_nf.lower() in str(ocorr.get("nota_fiscal", "")).lower()
            ]
        else:
            ocorrencias_filtradas = ocorrencias_finalizadas

        num_colunas = 4
        for i in range(0, len(ocorrencias_filtradas), num_colunas):
            linha = ocorrencias_filtradas[i:i+num_colunas]
            colunas = st.columns(num_colunas)

            for idx, ocorr in enumerate(linha):
                try:
                    # --- Datas manuais ---
                    data_abertura_manual = "-"
                    hora_abertura_manual = "-"
                    if ocorr.get("data_abertura_manual") and ocorr.get("hora_abertura_manual"):
                        try:
                            # Criar datetime a partir das strings de data e hora manual
                            abertura_dt = criar_datetime_manual(
                                ocorr["data_abertura_manual"], 
                                ocorr["hora_abertura_manual"]
                            )
                            if abertura_dt:
                                data_abertura_manual = abertura_dt.strftime("%d-%m-%Y")
                                hora_abertura_manual = abertura_dt.strftime("%H:%M:%S")
                        except:
                            pass

                    data_finalizacao_manual = "-"
                    hora_finalizacao_manual = "-"
                    if ocorr.get("data_finalizacao_manual") and ocorr.get("hora_finalizacao_manual"):
                        try:
                            # Criar datetime a partir das strings de data e hora manual
                            finalizacao_dt = criar_datetime_manual(
                                ocorr["data_finalizacao_manual"], 
                                ocorr["hora_finalizacao_manual"]
                            )
                            if finalizacao_dt:
                                data_finalizacao_manual = finalizacao_dt.strftime("%d-%m-%Y")
                                hora_finalizacao_manual = finalizacao_dt.strftime("%H:%M:%S")
                        except:
                            pass

                    status = ocorr.get("Status", "Finalizada")
                    cor = ocorr.get("Cor", "#34495e")

                except Exception as e:
                    st.error(f"Erro ao processar ocorrência (NF {ocorr.get('nota_fiscal', '-')}) — {e}")
                    data_abertura_manual = hora_abertura_manual = "-"
                    data_finalizacao_manual = hora_finalizacao_manual = "-"
                    status = "Erro"
                    cor = "gray"

                with colunas[idx]:
                    # Adicionar indicador de e-mail enviado
                    email_abertura = "📧 E-mail abertura enviado" if ocorr.get('email_abertura_enviado', False) else ""
                    email_finalizacao = "📧 E-mail finalização enviado" if ocorr.get('email_finalizacao_enviado', False) else ""
                    
                    st.markdown(
                        f"""
                        <div style='background-color:{cor};padding:10px;border-radius:10px;color:white;
                        box-shadow: 0 4px 10px rgba(0,0,0,0.3);margin-bottom:5px;min-height:250px;font-size:15px;'>
                        <strong>Ticket #:</strong> {ocorr.get('numero_ticket', 'N/A')}<br>
                        <strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;
                        border-radius:1px;color:white;'>{status}</span><br>
                        {email_abertura}<br>{email_finalizacao}<br>
                        <strong>NF:</strong> {ocorr.get('nota_fiscal', '-')}<br>
                        <strong>Cliente:</strong> {ocorr.get('cliente', '-')}<br>
                        <strong>Destinatário:</strong> {ocorr.get('destinatario', '-')}<br>
                        <strong>Focal:</strong> {ocorr.get('focal', '-')}<br>
                        <strong>Cidade:</strong> {ocorr.get('cidade', '-')}<br>
                        <strong>Motorista:</strong> {ocorr.get('motorista', '-')}<br>
                        <strong>Tipo:</strong> {ocorr.get('tipo_de_ocorrencia', '-')}<br>
                        <strong>Aberto por:</strong> {ocorr.get('responsavel', '-')}<br>
                        <strong>Finalizado por:</strong> {ocorr.get('finalizado_por', '-')}<br>
                        <strong>Data Abertura:</strong> {data_abertura_manual}<br>
                        <strong>Hora Abertura:</strong> {hora_abertura_manual}<br>
                        <strong>Data Finalização:</strong> {data_finalizacao_manual}<br>
                        <strong>Hora Finalização:</strong> {hora_finalizacao_manual}<br>
                        <strong>Permanência:</strong> {ocorr.get('permanencia_manual', '-')}<br>
                        <strong>Complementar:</strong> {ocorr.get('complementar', 'Sem complemento.')}<br>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

# =========================
#     ABA 5 - TICKETS POR FOCAL
# =========================
with aba5:
    st.header("Tickets por Focal")
    
    # Obter lista de focais com contagem
    focais_contagem = obter_focais_com_contagem()
    
    if not focais_contagem:
        st.info("ℹ️ Nenhuma ocorrência aberta no momento.")
    else:
        # Exibir lista de focais com contagem
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("Focais")
            
            # Botão para limpar seleção
            if st.button("Limpar seleção"):
                st.session_state.focal_selecionado = None
                st.rerun()
            
            # Exibir lista de focais com contagem
            for focal, contagem in focais_contagem:
                if st.button(f"{focal} ({contagem})", key=f"focal_{focal}"):
                    st.session_state.focal_selecionado = focal
                    st.rerun()
        
        with col2:
            # Exibir ocorrências do focal selecionado
            if st.session_state.focal_selecionado:
                st.subheader(f"Ocorrências de {st.session_state.focal_selecionado}")
                
                # Carregar ocorrências do focal selecionado
                ocorrencias_focal = carregar_ocorrencias_por_focal(st.session_state.focal_selecionado)
                
                if not ocorrencias_focal:
                    st.info(f"ℹ️ Nenhuma ocorrência aberta para {st.session_state.focal_selecionado}.")
                else:
                    # Exibir ocorrências em cards
                    for idx, ocorr in enumerate(ocorrencias_focal):
                        status = "Data manual ausente"
                        cor = "gray"
                        abertura_manual_formatada = "Não informada"
                        data_abertura_manual = ocorr.get("data_abertura_manual")
                        hora_abertura_manual = ocorr.get("hora_abertura_manual")

                        if data_abertura_manual and hora_abertura_manual:
                            try:
                                # Criar datetime a partir das strings de data e hora manual
                                dt_manual = criar_datetime_manual(data_abertura_manual, hora_abertura_manual)
                                if dt_manual:
                                    abertura_manual_formatada = dt_manual.strftime("%d-%m-%Y %H:%M:%S")

                                    # Classificação por tempo com base nas datas manuais
                                    status, cor = classificar_ocorrencia_por_tempo(data_abertura_manual, hora_abertura_manual)
                                else:
                                    status = "Erro"
                                    cor = "gray"

                            except Exception as e:
                                st.error(f"Erro ao processar data/hora manual da ocorrência {ocorr.get('nota_fiscal', '-')}: {e}")
                                status = "Erro"
                                cor = "gray"

                        safe_idx = f"focal_{idx}_{ocorr.get('nota_fiscal', '')}"

                        with st.container():
                            # Adicionar indicador de e-mail enviado
                            email_enviado = ocorr.get('email_abertura_enviado', False)
                            email_status = "📧 E-mail enviado" if email_enviado else ""
                            
                            st.markdown(
                                f"""
                                <div style='background-color:{cor};padding:10px;border-radius:10px;color:white;
                                box-shadow: 0 4px 10px rgba(0,0,0,0.3);margin-bottom:5px;font-size:15px;'>
                                <strong>Ticket #:</strong> {ocorr.get('numero_ticket', 'N/A')}<br>
                                <strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;
                                border-radius:1px;color:white;'>{status}</span> {email_status}<br>
                                <strong>NF:</strong> {ocorr.get('nota_fiscal', '-')}<br>
                                <strong>Cliente:</strong> {ocorr.get('cliente', '-')}<br>
                                <strong>Destinatário:</strong> {ocorr.get('destinatario', '-')}<br>
                                <strong>Cidade:</strong> {ocorr.get('cidade', '-')}<br>
                                <strong>Motorista:</strong> {ocorr.get('motorista', '-')}<br>
                                <strong>Tipo:</strong> {ocorr.get('tipo_de_ocorrencia', '-')}<br>
                                <strong>Aberto por:</strong> {ocorr.get('responsavel', '-')}<br>
                                <strong>Data Abertura:</strong> {abertura_manual_formatada.split(" ")[0] if abertura_manual_formatada != "Não informada" else 'Não informada'}<br>
                                <strong>Hora Abertura:</strong> {hora_abertura_manual or 'Não informada'}<br> 
                                <strong>Observações:</strong> {ocorr.get('observacoes', 'Sem observações.')}<br>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        with st.expander("Finalizar Ocorrência"):
                            data_atual = obter_data_hora_atual_brasil().strftime("%d-%m-%Y")
                            hora_atual = obter_data_hora_atual_brasil().strftime("%H:%M")
                            data_finalizacao_manual = st.text_input("Data Finalização (DD-MM-AAAA)", value=data_atual, key=f"data_final_{safe_idx}")
                            hora_finalizacao_manual = st.text_input("Hora Finalização (HH:MM)", value=hora_atual, key=f"hora_final_{safe_idx}")

                            complemento_key = f"complemento_final_{safe_idx}"
                            if complemento_key not in st.session_state:
                                st.session_state[complemento_key] = ""

                            complemento = st.text_area("Complementar", key=complemento_key, value=st.session_state[complemento_key])
                            finalizar_disabled = not complemento.strip()

                            if st.button("Finalizar", key=f"finalizar_{safe_idx}", disabled=finalizar_disabled):
                                if finalizar_disabled:
                                    st.error("❌ O campo 'Complementar' é obrigatório para finalizar a ocorrência.")
                                else:
                                    sucesso, mensagem = finalizar_ocorrencia(
                                        ocorr, 
                                        complemento, 
                                        data_finalizacao_manual, 
                                        hora_finalizacao_manual
                                    )
                                    
                                    if sucesso:
                                        st.success(mensagem)
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error(mensagem)
            else:
                st.info("👈 Selecione um focal para ver suas ocorrências.")

# =========================
#     ABA 4 - CONFIGURAÇÕES
# =========================
with aba4:
    st.header("Configurações")
    
    # Seção de troca de senha
    st.subheader("Alterar Senha")
    
    with st.form("form_alterar_senha"):
        senha_atual = st.text_input("Senha Atual", type="password")
        nova_senha = st.text_input("Nova Senha", type="password")
        confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
        
        alterar_senha = st.form_submit_button("Alterar Senha")
        
        if alterar_senha:
            if not senha_atual or not nova_senha or not confirmar_senha:
                st.error("❌ Todos os campos são obrigatórios.")
            elif nova_senha != confirmar_senha:
                st.error("❌ As senhas não coincidem.")
            else:
                try:
                    # Verificar senha atual
                    usuario = st.session_state.username
                    response = supabase.table("usuarios").select("*").eq("nome_usuario", usuario).execute()
                    
                    if response.data:
                        usuario_data = response.data[0]
                        if verificar_senha(senha_atual, usuario_data["senha_hash"]):
                            # Atualizar senha
                            nova_senha_hash = hash_senha(nova_senha)
                            update_response = supabase.table("usuarios").update({
                                "senha_hash": nova_senha_hash
                            }).eq("nome_usuario", usuario).execute()
                            
                            if update_response.data:
                                st.success("✅ Senha alterada com sucesso!")
                            else:
                                st.error("❌ Erro ao atualizar senha.")
                        else:
                            st.error("❌ Senha atual incorreta.")
                    else:
                        st.error("❌ Usuário não encontrado.")
                except Exception as e:
                    st.error(f"❌ Erro ao alterar senha: {e}")
    
    # Seção de administração de usuários (apenas para admin)
    if st.session_state.is_admin:
        st.subheader("Administração de Usuários")
        
        # Tabs para diferentes operações
        admin_tab1, admin_tab2, admin_tab3 = st.tabs(["Listar Usuários", "Adicionar Usuário", "Editar/Excluir Usuário"])
        
        with admin_tab1:
            try:
                response = supabase.table("usuarios").select("*").execute()
                if response.data:
                    usuarios = response.data
                    
                    # Criar DataFrame para exibição
                    df_usuarios = pd.DataFrame([
                        {
                            "Nome de Usuário": u["nome_usuario"],
                            "Admin": "Sim" if u.get("is_admin", False) else "Não",
                            "Último Login": u.get("ultimo_login", "-")
                        }
                        for u in usuarios
                    ])
                    
                    st.dataframe(df_usuarios)
                else:
                    st.info("Nenhum usuário encontrado.")
            except Exception as e:
                st.error(f"Erro ao listar usuários: {e}")
        
        with admin_tab2:
            with st.form("form_adicionar_usuario"):
                novo_usuario = st.text_input("Nome de Usuário")
                nova_senha_usuario = st.text_input("Senha", type="password")
                confirmar_senha_usuario = st.text_input("Confirmar Senha", type="password")
                is_admin = st.checkbox("Usuário Administrador")
                
                adicionar_usuario = st.form_submit_button("Adicionar Usuário")
                
                if adicionar_usuario:
                    if not novo_usuario or not nova_senha_usuario or not confirmar_senha_usuario:
                        st.error("❌ Todos os campos são obrigatórios.")
                    elif nova_senha_usuario != confirmar_senha_usuario:
                        st.error("❌ As senhas não coincidem.")
                    else:
                        try:
                            # Verificar se usuário já existe
                            check_response = supabase.table("usuarios").select("*").eq("nome_usuario", novo_usuario).execute()
                            
                            if check_response.data:
                                st.error("❌ Nome de usuário já existe.")
                            else:
                                # Criar novo usuário
                                senha_hash = hash_senha(nova_senha_usuario)
                                insert_response = supabase.table("usuarios").insert({
                                    "nome_usuario": novo_usuario,
                                    "senha_hash": senha_hash,
                                    "is_admin": is_admin,
                                    "criado_em": obter_data_hora_atual_brasil().isoformat()
                                }).execute()
                                
                                if insert_response.data:
                                    st.success("✅ Usuário adicionado com sucesso!")
                                else:
                                    st.error("❌ Erro ao adicionar usuário.")
                        except Exception as e:
                            st.error(f"❌ Erro ao adicionar usuário: {e}")
        
        with admin_tab3:
            try:
                response = supabase.table("usuarios").select("*").execute()
                if response.data:
                    usuarios = response.data
                    nomes_usuarios = [u["nome_usuario"] for u in usuarios]
                    
                    usuario_selecionado = st.selectbox("Selecione um usuário", nomes_usuarios)
                    
                    if usuario_selecionado:
                        usuario_data = next((u for u in usuarios if u["nome_usuario"] == usuario_selecionado), None)
                        
                        if usuario_data:
                            with st.form("form_editar_usuario"):
                                nova_senha_admin = st.text_input("Nova Senha (deixe em branco para não alterar)", type="password")
                                is_admin_edit = st.checkbox("Usuário Administrador", value=usuario_data.get("is_admin", False))
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    editar_usuario = st.form_submit_button("Atualizar Usuário")
                                with col2:
                                    excluir_usuario = st.form_submit_button("Excluir Usuário", type="primary", help="Esta ação não pode ser desfeita")
                                
                                if editar_usuario:
                                    try:
                                        update_data = {"is_admin": is_admin_edit}
                                        
                                        if nova_senha_admin:
                                            update_data["senha_hash"] = hash_senha(nova_senha_admin)
                                        
                                        update_response = supabase.table("usuarios").update(update_data).eq("nome_usuario", usuario_selecionado).execute()
                                        
                                        if update_response.data:
                                            st.success("✅ Usuário atualizado com sucesso!")
                                        else:
                                            st.error("❌ Erro ao atualizar usuário.")
                                    except Exception as e:
                                        st.error(f"❌ Erro ao atualizar usuário: {e}")
                                
                                if excluir_usuario:
                                    if usuario_selecionado == st.session_state.username:
                                        st.error("❌ Você não pode excluir seu próprio usuário.")
                                    else:
                                        try:
                                            delete_response = supabase.table("usuarios").delete().eq("nome_usuario", usuario_selecionado).execute()
                                            
                                            if delete_response.data:
                                                st.success("✅ Usuário excluído com sucesso!")
                                                time.sleep(2)
                                                st.rerun()
                                            else:
                                                st.error("❌ Erro ao excluir usuário.")
                                        except Exception as e:
                                            st.error(f"❌ Erro ao excluir usuário: {e}")
                else:
                    st.info("Nenhum usuário encontrado.")
            except Exception as e:
                st.error(f"Erro ao carregar usuários: {e}")

# =========================
#     ABA 6 - NOTIFICAÇÕES POR E-MAIL (APENAS ADMIN)
# =========================
if st.session_state.is_admin and 'aba6' in locals():
    with aba6:
        st.header("Notificações por E-mail")
        
        st.markdown("""
        ### Sistema de Notificação Automática
        
        Este sistema envia e-mails automáticos para clientes que possuem ocorrências abertas há mais de 30 minutos.
        
        Os e-mails são enviados utilizando:
        - **Remetente:** ticket@clicklogtransportes.com.br
        - **Servidor SMTP:** smtp.kinghost.net
        
        Os destinatários são obtidos da planilha de clientes:
        - **E-mail principal:** Coluna C (enviar_para_email)
        - **E-mails em cópia (CC):** Coluna D (email_copia), separados por ponto e vírgula
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Testar Conexão SMTP")
            if st.button("Testar Conexão"):
                with st.spinner("Testando conexão com servidor SMTP..."):
                    sucesso, mensagem = testar_conexao_smtp()
                    if sucesso:
                        st.success(mensagem)
                    else:
                        st.error(mensagem)
        
        with col2:
            st.subheader("Enviar Notificações Manualmente")
            if st.button("Enviar Notificações Agora"):
                with st.spinner("Verificando ocorrências e enviando e-mails..."):
                    resultados = notificar_ocorrencias_abertas()
                    
                    # Exibir resultados
                    for resultado in resultados:
                        if resultado.get("status") == "info":
                            st.info(resultado.get("mensagem"))
                        elif resultado.get("status") == "sucesso":
                            st.success(f"✅ E-mail enviado para {resultado.get('cliente')} - Ticket {resultado.get('ticket')} - NF {resultado.get('nota_fiscal')}")
                        else:
                            st.error(f"❌ Erro ao enviar para {resultado.get('cliente')}: {resultado.get('mensagem')}")
        
        # Exibir histórico de e-mails enviados
        st.subheader("Histórico de E-mails Enviados")
        
        if st.session_state.historico_emails:
            df_historico = pd.DataFrame(st.session_state.historico_emails)
            st.dataframe(df_historico)
        else:
            st.info("Nenhum e-mail enviado ainda.")

# Verificar e enviar e-mails para ocorrências abertas há mais de 30 minutos
ocorrencias_abertas = carregar_ocorrencias_abertas()
for ocorr in ocorrencias_abertas:
    if not ocorr.get("email_abertura_enviado", False):
        verificar_e_enviar_email_abertura(ocorr)
