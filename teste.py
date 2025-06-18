# funcionando com envio de e-mail 17-06
# versão completa com todas as funcionalidades solicitadas
# versão liberada para usuário com correção de fuso horário e uso exclusivo de datas manuais
# envio de email atraves do gmail


import streamlit as st
st.set_page_config(page_title="Entregas - Tempo de Permanência", layout="wide")

import pandas as pd
import os
import re
import time
import uuid
import pytz
import bcrypt
import hashlib
import html
import smtplib
import socket
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from dateutil import parser
from psycopg2 import sql
from io import BytesIO
from dotenv import load_dotenv
from email.mime.image import MIMEImage


from streamlit_autorefresh import st_autorefresh
import streamlit_authenticator as stauth
from streamlit_cookies_manager import EncryptedCookieManager

from supabase import create_client, Client as SupabaseClient
load_dotenv()
# --- CONFIGURAÇÕES DE E-MAIL DA KINGHOST ---
# Estas configurações podem ser movidas para um arquivo .env se preferir
EMAIL_REMETENTE = "ticketclicklogtransportes@gmail.com"
EMAIL_SENHA = st.secrets["EMAIL_SENHA"]
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
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
url = "https://vismjxhlsctehpvgmata.supabase.co"  # ✅ sua URL real, já sem o ">" no meio
supabase_key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, supabase_key)


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
        st.markdown("<h1 style=\'text-align: center;\'>📝 Entregas - Tempo de Permanência </h1>", unsafe_allow_html=True)

    # Se o login já foi feito e o cookie não expirou, configura a sessão
    if login_cookie and username_cookie and not is_cookie_expired(expiry_time_cookie):
        # Buscar unidade do usuário logado
        try:
            usuario_data = supabase.table("usuarios").select("unidade").eq("nome_usuario", username_cookie).execute().data
            unidade_cookie = usuario_data[0]["unidade"] if usuario_data else "Não definida"
        except:
            unidade_cookie = "Não definida"

        # Preenche session_state
        st.session_state.login = True
        st.session_state.username = username_cookie
        st.session_state.is_admin = is_admin_cookie == "True"
        st.session_state.unidade = unidade_cookie

        st.markdown(f"👋 **Bem-vindo, {st.session_state.username}!**")

        # Botão de logout
        col1, col2, col3 = st.columns([6, 1, 1])
        with col3:
            if st.button("🔒 Sair", key="logout_button"):
                cookies["login"] = ""
                cookies["username"] = ""
                cookies["is_admin"] = ""
                cookies["expiry_time"] = ""
                cookies.save()
                st.session_state.login = False
                st.rerun()

    else:
        # Exibe formulário de login
        with col2:
            st.markdown("##### Login")
            username = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")

            if st.button("Entrar", key="login_button"):
                usuario = autenticar_usuario(username, senha)
                if usuario:
                    # Armazenar cookies
                    cookies["login"] = str(True)
                    cookies["username"] = usuario["nome_usuario"]
                    cookies["is_admin"] = str(usuario.get("is_admin", False))
                    expiry_time = datetime.now(timezone.utc) + timedelta(hours=24)
                    cookies["expiry_time"] = expiry_time.strftime("%Y-%m-%d %H:%M:%S")
                    cookies.save()

                    # Armazenar na sessão
                    st.session_state.login = True
                    st.session_state.username = usuario["nome_usuario"]
                    st.session_state.is_admin = usuario.get("is_admin", False)
                    st.session_state.unidade = usuario.get("unidade", "Não definida")

                    st.rerun()


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

# Inicialização da configuração de tempo de envio de e-mail
if "tempo_envio_email" not in st.session_state:
    st.session_state.tempo_envio_email = 30  # Valor padrão: 30 minutos

# --- FUNÇÕES DE ENVIO DE E-MAIL ---
def enviar_email(destinatario_email, assunto, corpo_html, imagem_path=None):
    msg = MIMEMultipart\'related\'
    msg[\'From\'] = EMAIL_REMETENTE
    msg[\'To\'] = destinatario_email
    msg[\'Subject\'] = assunto

    msg.attach(MIMEText(corpo_html, \'html\'))

    if imagem_path:
        try:
            with open(imagem_path, \'rb\') as img_file:
                img = MIMEImage(img_file.read())
                img.add_header(\'Content-ID\', \'<image1>\') # Referência no HTML
                msg.attach(img)
        except FileNotFoundError:
            st.warning(f"Imagem não encontrada: {imagem_path}")
        except Exception as e:
            st.error(f"Erro ao anexar imagem: {e}")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_REMETENTE, EMAIL_SENHA)
            server.sendmail(EMAIL_REMETENTE, destinatario_email, msg.as_string())
        return True
    except smtplib.SMTPAuthenticationError:
        st.error("Erro de autenticação SMTP. Verifique o e-mail e a senha.")
        return False
    except smtplib.SMTPConnectError as e:
        st.error(f"Erro de conexão SMTP: {e}. Verifique o host e a porta.")
        return False
    except smtplib.SMTPException as e:
        st.error(f"Erro SMTP: {e}")
        return False
    except socket.timeout:
        st.error("Timeout de conexão SMTP. Aumente o timeout ou verifique a rede.")
        return False
    except Exception as e:
        st.error(f"Erro inesperado ao enviar e-mail: {e}")
        return False

def enviar_email_abertura(ocorrencia):
    cliente_email_info = cliente_to_emails.get(ocorrencia["cliente"], {"principal": "", "copia": ""})
    destinatario_principal = cliente_email_info["principal"]
    destinatario_copia = cliente_email_info["copia"]

    if not destinatario_principal:
        st.warning(f"E-mail principal para o cliente {ocorrencia[\'cliente\']} não configurado. E-mail de abertura não enviado.")
        return

    assunto = f"[ABERTURA] Ocorrência NF: {ocorrencia[\'nota_fiscal\']} - Cliente: {ocorrencia[\'cliente\]}"
    
    # Formatar data e hora para o e-mail
    data_hora_abertura_formatada = "N/A"
    try:
        data_abertura = datetime.strptime(ocorrencia["data_abertura_manual"], "%Y-%m-%d").strftime("%d/%m/%Y")
        hora_abertura = ocorrencia["hora_abertura_manual"]
        data_hora_abertura_formatada = f"{data_abertura} às {hora_abertura}"
    except ValueError:
        pass # Já inicializado como N/A

    corpo_html = f"""
    <html>
    <body>
        <p>Prezados,</p>
        <p>Informamos a abertura de uma nova ocorrência:</p>
        <ul>
            <li><b>Nota Fiscal:</b> {ocorrencia[\'nota_fiscal\]}</li>
            <li><b>Cliente:</b> {ocorrencia[\'cliente\]}</li>
            <li><b>Focal:</b> {ocorrencia[\'focal\]}</li>
            <li><b>Destinatário:</b> {ocorrencia[\'destinatario\]}</li>
            <li><b>Cidade:</b> {ocorrencia[\'cidade\]}</li>
            <li><b>Motorista:</b> {ocorrencia[\'motorista\]}</li>
            <li><b>Tipo de Ocorrência:</b> {ocorrencia[\'tipo_de_ocorrencia\]}</li>
            <li><b>Observações:</b> {ocorrencia[\'observacoes\]}</li>
            <li><b>Responsável:</b> {ocorrencia[\'responsavel\]}</li>
            <li><b>Data/Hora Abertura:</b> {data_hora_abertura_formatada}</li>
            <li><b>Informação Complementar:</b> {ocorrencia[\'complementar\]}</li>
            <li><b>Unidade:</b> {ocorrencia[\'ticket_unidade\]}</li>
        </ul>
        <p>Acompanhe o status da ocorrência pelo sistema.</p>
        <p>Atenciosamente,</p>
        <p>Equipe de Operações</p>
        {f\'\<img src="{ocorrencia["imagem_url"]}" alt="Imagem da Ocorrência" style="max-width: 600px;">\' if ocorrencia.get(\'imagem_url\') else \'\'}
    </body>
    </html>
    """

    destinatarios = [destinatario_principal]
    if destinatario_copia:
        destinatarios.append(destinatario_copia)

    for dest in destinatarios:
        if enviar_email(dest, assunto, corpo_html):
            st.session_state.historico_emails.append({
                "Tipo": "Abertura",
                "Nota Fiscal": ocorrencia["nota_fiscal"],
                "Cliente": ocorrencia["cliente"],
                "Destinatário": dest,
                "Assunto": assunto,
                "Data/Hora Envio": obter_data_hora_atual_brasil().strftime("%Y-%m-%d %H:%M:%S")
            })
            st.success(f"E-mail de abertura enviado para {dest} (NF: {ocorrencia[\'nota_fiscal\]}).")
        else:
            st.error(f"Falha ao enviar e-mail de abertura para {dest} (NF: {ocorrencia[\'nota_fiscal\]}).")

def enviar_email_finalizacao(ocorrencia):
    cliente_email_info = cliente_to_emails.get(ocorrencia["cliente"], {"principal": "", "copia": ""})
    destinatario_principal = cliente_email_info["principal"]
    destinatario_copia = cliente_email_info["copia"]

    if not destinatario_principal:
        st.warning(f"E-mail principal para o cliente {ocorrencia[\'cliente\']} não configurado. E-mail de finalização não enviado.")
        return

    assunto = f"[FINALIZAÇÃO] Ocorrência NF: {ocorrencia[\'nota_fiscal\']} - Cliente: {ocorrencia[\'cliente\]}"

    # Formatar datas e permanência para o e-mail
    data_hora_abertura_formatada = "N/A"
    data_hora_finalizacao_formatada = "N/A"
    permanencia_formatada = f"{ocorrencia.get(\'permanencia\', \'0\')} minutos"

    try:
        data_abertura = datetime.strptime(ocorrencia["data_abertura_manual"], "%Y-%m-%d").strftime("%d/%m/%Y")
        hora_abertura = ocorrencia["hora_abertura_manual"]
        data_hora_abertura_formatada = f"{data_abertura} às {hora_abertura}"
    except ValueError:
        pass

    try:
        data_finalizacao_dt = datetime.strptime(ocorrencia["data_hora_finalizacao"], "%Y-%m-%d %H:%M:%S")
        data_hora_finalizacao_formatada = data_finalizacao_dt.strftime("%d/%m/%Y às %H:%M:%S")
    except (ValueError, TypeError):
        pass

    corpo_html = f"""
    <html>
    <body>
        <p>Prezados,</p>
        <p>Informamos a finalização da ocorrência:</p>
        <ul>
            <li><b>Nota Fiscal:</b> {ocorrencia[\'nota_fiscal\]}</li>
            <li><b>Cliente:</b> {ocorrencia[\'cliente\]}</li>
            <li><b>Focal:</b> {ocorrencia[\'focal\]}</li>
            <li><b>Destinatário:</b> {ocorrencia[\'destinatario\]}</li>
            <li><b>Cidade:</b> {ocorrencia[\'cidade\]}</li>
            <li><b>Motorista:</b> {ocorrencia[\'motorista\]}</li>
            <li><b>Tipo de Ocorrência:</b> {ocorrencia[\'tipo_de_ocorrencia\]}</li>
            <li><b>Observações:</b> {ocorrencia[\'observacoes\]}</li>
            <li><b>Responsável:</b> {ocorrencia[\'responsavel\]}</li>
            <li><b>Data/Hora Abertura:</b> {data_hora_abertura_formatada}</li>
            <li><b>Data/Hora Finalização:</b> {data_hora_finalizacao_formatada}</li>
            <li><b>Tempo de Permanência:</b> {permanencia_formatada}</li>
            <li><b>Informação Complementar:</b> {ocorrencia[\'complementar\]}</li>
            <li><b>Unidade:</b> {ocorrencia[\'ticket_unidade\]}</li>
        </ul>
        <p>Agradecemos a atenção.</p>
        <p>Atenciosamente,</p>
        <p>Equipe de Operações</p>
        {f\'\<img src="{ocorrencia["imagem_url"]}" alt="Imagem da Ocorrência" style="max-width: 600px;">\' if ocorrencia.get(\'imagem_url\') else \'\'}
    </body>
    </html>
    """

    destinatarios = [destinatario_principal]
    if destinatario_copia:
        destinatarios.append(destinatario_copia)

    for dest in destinatarios:
        if enviar_email(dest, assunto, corpo_html):
            st.session_state.historico_emails.append({
                "Tipo": "Finalização",
                "Nota Fiscal": ocorrencia["nota_fiscal"],
                "Cliente": ocorrencia["cliente"],
                "Destinatário": dest,
                "Assunto": assunto,
                "Data/Hora Envio": obter_data_hora_atual_brasil().strftime("%Y-%m-%d %H:%M:%S")
            })
            st.success(f"E-mail de finalização enviado para {dest} (NF: {ocorrencia[\'nota_fiscal\]}).")
        else:
            st.error(f"Falha ao enviar e-mail de finalização para {dest} (NF: {ocorrencia[\'nota_fiscal\]}).")

# --- ABA NOVA OCORRÊNCIA ---
# Definir abas - a aba de notificações só aparece para admin
if st.session_state.is_admin:
    aba1, aba2, aba3, aba5, aba4, aba6, aba7, aba8 = st.tabs(["📝 Nova Ocorrência", "📌 Ocorrências em Aberto", "✅ Ocorrências Finalizadas", "📝 Tickets por Focal", "📊 Configurações", "📧 Notificações por E-mail", "🔄 Cadastros",  "📊 Estatística"])
else:
    aba1, aba2, aba3, aba5, aba4, aba7, aba8 = st.tabs(["📝 Nova Ocorrência", "📌 Ocorrências em Aberto", "✅ Ocorrências Finalizadas", "📝 Tickets por Focal", "📊 Configurações", "🔄 Cadastros", "📊 Estatística"])

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
            "email_finalizacao_enviado": False,
            "imagem_url": dados["imagem_url"],
            "ticket_unidade": dados["ticket_unidade"]

        }]).execute()
        return response
    else:
        st.error("Erro ao criar data/hora manual para inserção no banco")
        return None


# --- CARREGAMENTO DE DADOS Tabelas com nomes de motorista e clientes ---
@st.cache_data(ttl=3600) # Cache por 1 hora (3600 segundos)
def carregar_clientes_supabase():
    with st.spinner("Carregando clientes..."):
        try:
            response = supabase.table("clientes").select("cliente, focal, enviar_para_email, email_copia").execute()
            if response.data:
                df_clientes = pd.DataFrame(response.data)
                df_clientes = df_clientes.dropna(subset=["cliente"])
                return df_clientes
            else:
                return pd.DataFrame(columns=["cliente", "focal", "enviar_para_email", "email_copia"])
        except Exception as e:
            st.error(f"Erro ao carregar clientes do banco: {e}")
            return pd.DataFrame(columns=["cliente", "focal", "enviar_para_email", "email_copia"])

# Carregar dados
df_clientes = carregar_clientes_supabase()

# Dicionários úteis
cliente_to_focal = dict(zip(df_clientes["cliente"], df_clientes["focal"]))
cliente_to_emails = {
    row["cliente"]: {
        "principal": row.get("enviar_para_email", ""),
        "copia": row.get("email_copia", "")
    }
    for _, row in df_clientes.iterrows()
}
clientes = df_clientes["cliente"].tolist()



# Buscar lista de cidades diretamente do Supabase
@st.cache_data(ttl=3600)
def carregar_cidades_supabase():
    with st.spinner("Carregando cidades..."):
        try:
            response = supabase.table("cidades").select("cidade").execute()
            #st.write("✅ Cidades no banco:", response.data)  # para debug
            if response.data:
                cidades = [item["cidade"] for item in response.data if item.get("cidade")]
                return sorted(set(cidades))  # Ordena e remove duplicados
            else:
                return []
        except Exception as e:
            st.error(f"Erro ao carregar cidades do banco: {e}")
            return []

cidades = carregar_cidades_supabase()


# Buscar lista de motoristas diretamente do Supabase
@st.cache_data(ttl=3600)
def carregar_motoristas_supabase():
    with st.spinner("Carregando motoristas..."):
        try:
            motoristas = []
            pagina = 0
            pagina_tamanho = 1000  # Supabase retorna no máximo 1000 por requisição

            while True:
                resposta = supabase.table("motoristas") \
                    .select("motorista") \
                    .range(pagina * pagina_tamanho, (pagina + 1) * pagina_tamanho - 1) \
                    .execute()

                dados = resposta.data
                if not dados:
                    break

                motoristas.extend([item["motorista"].strip() for item in dados if item.get("motorista")])
                pagina += 1

            return sorted(set(motoristas))

        except Exception as e:
            st.error(f"Erro ao carregar motoristas do banco: {e}")
            return []



motoristas = carregar_motoristas_supabase()

try:
    resposta = supabase.table("motoristas").select("*").execute()
    
except Exception as e:
    st.error(f"Erro ao consultar a tabela motoristas: {e}")

# Buscar lista de focais diretamente do Supabase
@st.cache_data(ttl=3600)
def carregar_focal_supabase():
    with st.spinner("Carregando focais..."):
        try:
            response = supabase.table("clientes").select("focal").execute()
            if response.data:
                focais = [item["focal"] for item in response.data if item.get("focal")]
                return sorted(set(focais))
            else:
                return []
        except Exception as e:
            st.error(f"Erro ao carregar focais do banco: {e}")
            return []

focais = carregar_focal_supabase()

# --- FUNÇÕES PARA A ABA CADASTROS ---

def validar_texto_maiusculo(texto):
    """Verifica se o texto está em letras maiúsculas."""
    return texto == texto.upper()

def validar_email(email):
    """Verifica se o e-mail tem um formato válido."""
    import re
    padrao = r\'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$\'
    return re.match(padrao, email) is not None

def validar_emails_multiplos(emails_str):
    """Valida uma string com múltiplos e-mails separados por vírgula."""
    if not emails_str:
        return True
    emails = [e.strip() for e in emails_str.split(\'\')]
    for email in emails:
        if not validar_email(email):
            return False
    return True


def adicionar_cliente_supabase(cliente, focal, enviar_para_email, email_copia):
    try:
        # Verificar se o cliente já existe
        response_check = supabase.table("clientes").select("cliente").eq("cliente", cliente).execute()
        if response_check.data:
            st.warning(f"O cliente \'{cliente}\' já existe.")
            return False

        response = supabase.table("clientes").insert({
            "cliente": cliente,
            "focal": focal,
            "enviar_para_email": enviar_para_email,
            "email_copia": email_copia
        }).execute()
        st.success(f"Cliente \'{cliente}\' adicionado com sucesso!")
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar cliente: {e}")
        return False

def adicionar_cidade_supabase(cidade):
    try:
        # Verificar se a cidade já existe
        response_check = supabase.table("cidades").select("cidade").eq("cidade", cidade).execute()
        if response_check.data:
            st.warning(f"A cidade \'{cidade}\' já existe.")
            return False

        response = supabase.table("cidades").insert({"cidade": cidade}).execute()
        st.success(f"Cidade \'{cidade}\' adicionada com sucesso!")
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar cidade: {e}")
        return False

def adicionar_motorista_supabase(motorista):
    try:
        # Verificar se o motorista já existe
        response_check = supabase.table("motoristas").select("motorista").eq("motorista", motorista).execute()
        if response_check.data:
            st.warning(f"O motorista \'{motorista}\' já existe.")
            return False

        response = supabase.table("motoristas").insert({"motorista": motorista}).execute()
        st.success(f"Motorista \'{motorista}\' adicionado com sucesso!")
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar motorista: {e}")
        return False

def adicionar_usuario_supabase(nome_usuario, senha, is_admin, unidade):
    try:
        # Verificar se o usuário já existe
        response_check = supabase.table("usuarios").select("nome_usuario").eq("nome_usuario", nome_usuario).execute()
        if response_check.data:
            st.warning(f"O usuário \'{nome_usuario}\' já existe.")
            return False

        senha_hash = hash_senha(senha)
        response = supabase.table("usuarios").insert({
            "nome_usuario": nome_usuario,
            "senha_hash": senha_hash,
            "is_admin": is_admin,
            "unidade": unidade
        }).execute()
        st.success(f"Usuário \'{nome_usuario}\' adicionado com sucesso!")
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar usuário: {e}")
        return False


def remover_cliente_supabase(cliente):
    try:
        response = supabase.table("clientes").delete().eq("cliente", cliente).execute()
        if response.data:
            st.success(f"Cliente \'{cliente}\' removido com sucesso!")
            return True
        else:
            st.warning(f"Cliente \'{cliente}\' não encontrado.")
            return False
    except Exception as e:
        st.error(f"Erro ao remover cliente: {e}")
        return False

def remover_cidade_supabase(cidade):
    try:
        response = supabase.table("cidades").delete().eq("cidade", cidade).execute()
        if response.data:
            st.success(f"Cidade \'{cidade}\' removida com sucesso!")
            return True
        else:
            st.warning(f"Cidade \'{cidade}\' não encontrada.")
            return False
    except Exception as e:
        st.error(f"Erro ao remover cidade: {e}")
        return False

def remover_motorista_supabase(motorista):
    try:
        response = supabase.table("motoristas").delete().eq("motorista", motorista).execute()
        if response.data:
            st.success(f"Motorista \'{motorista}\' removido com sucesso!")
            return True
        else:
            st.warning(f"Motorista \'{motorista}\' não encontrado.")
            return False
    except Exception as e:
        st.error(f"Erro ao remover motorista: {e}")
        return False

def remover_usuario_supabase(nome_usuario):
    try:
        response = supabase.table("usuarios").delete().eq("nome_usuario", nome_usuario).execute()
        if response.data:
            st.success(f"Usuário \'{nome_usuario}\' removido com sucesso!")
            return True
        else:
            st.warning(f"Usuário \'{nome_usuario}\' não encontrado.")
            return False
    except Exception as e:
        st.error(f"Erro ao remover usuário: {e}")
        return False


# --- ABA NOVA OCORRÊNCIA ---
with aba1:
    st.markdown("### Nova Ocorrência")

    with st.form("form_nova_ocorrencia", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nota_fiscal = st.text_input("Nota Fiscal", max_chars=50).strip().upper()
            cliente_selecionado = st.selectbox("Cliente", options=["Selecione"] + clientes)
            destinatario = st.text_input("Destinatário", max_chars=100).strip().upper()
            cidade_selecionada = st.selectbox("Cidade", options=["Selecione"] + cidades)
            motorista_selecionado = st.selectbox("Motorista", options=["Selecione"] + motoristas)
            tipo_de_ocorrencia = st.selectbox("Tipo de Ocorrência", options=["Selecione", "Aguardando Carregamento", "Aguardando Descarga", "Aguardando Liberação", "Aguardando Transbordo", "Outros"])
            
            # Campos de data e hora manuais
            data_abertura_manual = st.date_input("Data de Abertura", value="today", format="YYYY-MM-DD")
            hora_abertura_manual = st.time_input("Hora de Abertura", value="now", step=60)

        with col2:
            observacoes = st.text_area("Observações", height=150, max_chars=500).strip()
            responsavel = st.text_input("Responsável", value=st.session_state.username, disabled=True)
            permanencia = st.text_input("Tempo de Permanência (minutos)", value="0", disabled=True)
            complementar = st.text_input("Informação Complementar", max_chars=200).strip()
            
            # Upload de imagem
            imagem_upload = st.file_uploader("Anexar Imagem (Opcional)", type=["png", "jpg", "jpeg"])
            imagem_url = "" # Inicializa vazio

            submitted = st.form_submit_button("Registrar Ocorrência")

            if submitted:
                if not nota_fiscal or cliente_selecionado == "Selecione" or not destinatario or cidade_selecionada == "Selecione" or motorista_selecionado == "Selecione" or tipo_de_ocorrencia == "Selecione":
                    st.error("Por favor, preencha todos os campos obrigatórios.")
                else:
                    # Upload da imagem para o Supabase Storage
                    if imagem_upload:
                        try:
                            file_extension = os.path.splitext(imagem_upload.name)[1]
                            file_name = f"{uuid.uuid4()}{file_extension}"
                            
                            # Upload para o bucket \'imagens-ocorrencias\'
                            response_upload = supabase.storage.from_("imagens-ocorrencias").upload(file_name, imagem_upload.getvalue(), {"content-type": imagem_upload.type})
                            
                            if response_upload.get("error"):
                                st.error(f"Erro ao fazer upload da imagem: {response_upload[\'error\'][\'message\]}")
                            else:
                                # Obter URL pública da imagem
                                imagem_url = supabase.storage.from_("imagens-ocorrencias").get_public_url(file_name)
                                st.success("Imagem enviada com sucesso!")
                        except Exception as e:
                            st.error(f"Erro inesperado ao enviar imagem: {e}")

                    # Gerar ID único para a ocorrência
                    ocorrencia_id = str(uuid.uuid4())

                    # Obter o focal do cliente selecionado
                    focal_cliente = cliente_to_focal.get(cliente_selecionado, "Não definido")

                    # Obter a unidade do usuário logado
                    ticket_unidade = st.session_state.get("unidade", "Não definida")

                    nova_ocorrencia = {
                        "id": ocorrencia_id,
                        "nota_fiscal": nota_fiscal,
                        "cliente": cliente_selecionado,
                        "focal": focal_cliente,
                        "destinatario": destinatario,
                        "cidade": cidade_selecionada,
                        "motorista": motorista_selecionado,
                        "tipo_de_ocorrencia": tipo_de_ocorrencia,
                        "observacoes": observacoes,
                        "responsavel": responsavel,
                        "status": "Aberta",
                        "data_abertura_manual": data_abertura_manual.strftime("%Y-%m-%d"),
                        "hora_abertura_manual": hora_abertura_manual.strftime("%H:%M:%S"),
                        "permanencia": "0", # Inicializa com 0
                        "complementar": complementar,
                        "imagem_url": imagem_url,
                        "ticket_unidade": ticket_unidade
                    }

                    # Inserir no Supabase
                    response_insert = inserir_ocorrencia_supabase(nova_ocorrencia)

                    if response_insert and not response_insert.get("error"):
                        st.success("Ocorrência registrada com sucesso!")
                        # Adicionar à lista de ocorrências abertas na sessão
                        st.session_state.ocorrencias_abertas.append(nova_ocorrencia)
                        # Enviar e-mail de abertura
                        enviar_email_abertura(nova_ocorrencia)
                    else:
                        st.error(f"Erro ao registrar ocorrência: {response_insert.get(\'error\', {}).get(\'message\', \'Erro desconhecido\')}")


# --- ABA OCORRÊNCIAS EM ABERTO ---
with aba2:
    st.markdown("### Ocorrências em Aberto")

    # Filtro por unidade (apenas para admins)
    if st.session_state.is_admin:
        unidades_disponiveis = ["Todas"] + sorted(list(set([o.get("ticket_unidade", "Não definida") for o in st.session_state.ocorrencias_abertas])))
        filtro_unidade_aberto = st.selectbox("Filtrar por Unidade (Aberto)", unidades_disponiveis, key="filtro_unidade_aberto")
    else:
        filtro_unidade_aberto = st.session_state.unidade # Usuário normal vê apenas sua unidade

    # Carregar ocorrências abertas do Supabase (sempre que a aba é acessada ou a página é recarregada)
    # Apenas carrega se a lista de sessão estiver vazia ou se for admin e o filtro mudar
    if not st.session_state.ocorrencias_abertas or (st.session_state.is_admin and "filtro_unidade_aberto" in st.session_state and st.session_state.filtro_unidade_aberto != st.session_state.get("last_filtro_unidade_aberto")):
        with st.spinner("Carregando ocorrências em aberto..."):
            try:
                query = supabase.table("ocorrencias").select("*").eq("status", "Aberta")
                if not st.session_state.is_admin:
                    query = query.eq("ticket_unidade", st.session_state.unidade)
                elif filtro_unidade_aberto != "Todas":
                    query = query.eq("ticket_unidade", filtro_unidade_aberto)
                
                response = query.order("data_hora_abertura", desc=True).execute()
                if response.data:
                    st.session_state.ocorrencias_abertas = response.data
                else:
                    st.session_state.ocorrencias_abertas = []
            except Exception as e:
                st.error(f"Erro ao carregar ocorrências em aberto do banco: {e}")
                st.session_state.ocorrencias_abertas = []
        
        if st.session_state.is_admin:
            st.session_state.last_filtro_unidade_aberto = filtro_unidade_aberto

    if st.session_state.ocorrencias_abertas:
        df_ocorrencias_abertas = pd.DataFrame(st.session_state.ocorrencias_abertas)
        
        # Converter colunas de data/hora para datetime com fuso horário
        df_ocorrencias_abertas["data_hora_abertura_dt"] = df_ocorrencias_abertas.apply(
            lambda row: criar_datetime_manual(row["data_abertura_manual"], row["hora_abertura_manual"]),
            axis=1
        )
        
        # Calcular permanência
        df_ocorrencias_abertas["permanencia_atual"] = df_ocorrencias_abertas["data_hora_abertura_dt"].apply(
            lambda dt: calcular_diferenca_tempo(dt).total_seconds() / 60
        ).astype(int)

        # Atualizar a coluna \'permanencia\' no DataFrame
        df_ocorrencias_abertas["permanencia"] = df_ocorrencias_abertas["permanencia_atual"]

        # Exibir tabela
        st.dataframe(
            df_ocorrencias_abertas[["nota_fiscal", "cliente", "focal", "destinatario", "cidade", "motorista", "tipo_de_ocorrencia", "observacoes", "responsavel", "permanencia", "complementar", "ticket_unidade"]],
            use_container_width=True,
            hide_row_index=True
        )

        # Opção para finalizar ocorrência
        st.markdown("### Finalizar Ocorrência")
        nf_finalizar = st.text_input("Nota Fiscal da ocorrência a ser finalizada", key="nf_finalizar").strip().upper()
        
        if st.button("Finalizar Ocorrência", key="btn_finalizar_ocorrencia"):
            ocorrencia_para_finalizar = None
            for oc in st.session_state.ocorrencias_abertas:
                if oc["nota_fiscal"] == nf_finalizar:
                    ocorrencia_para_finalizar = oc
                    break

            if ocorrencia_para_finalizar:
                with st.spinner("Finalizando ocorrência..."):
                    try:
                        # Calcular tempo de permanência final
                        data_hora_abertura_dt = criar_datetime_manual(ocorrencia_para_finalizar["data_abertura_manual"], ocorrencia_para_finalizar["hora_abertura_manual"])
                        permanencia_final = int(calcular_diferenca_tempo(data_hora_abertura_dt).total_seconds() / 60)

                        # Atualizar no Supabase
                        response_update = supabase.table("ocorrencias").update({
                            "status": "Finalizada",
                            "data_hora_finalizacao": obter_data_hora_atual_brasil().strftime("%Y-%m-%d %H:%M:%S"),
                            "finalizacao_timestamp": obter_data_hora_atual_brasil().isoformat(),
                            "permanencia": str(permanencia_final) # Salvar como string
                        }).eq("id", ocorrencia_para_finalizar["id"]).execute()

                        if response_update and not response_update.get("error"):
                            st.success(f"Ocorrência {nf_finalizar} finalizada com sucesso! Tempo de permanência: {permanencia_final} minutos.")
                            # Remover da lista de abertas e adicionar à de finalizadas
                            st.session_state.ocorrencias_abertas = [oc for oc in st.session_state.ocorrencias_abertas if oc["nota_fiscal"] != nf_finalizar]
                            ocorrencia_para_finalizar["status"] = "Finalizada"
                            ocorrencia_para_finalizar["permanencia"] = str(permanencia_final)
                            st.session_state.ocorrencias_finalizadas.append(ocorrencia_para_finalizar)
                            # Enviar e-mail de finalização
                            enviar_email_finalizacao(ocorrencia_para_finalizar)
                            st.rerun()
                        else:
                            st.error(f"Erro ao finalizar ocorrência: {response_update.get(\'error\', {}).get(\'message\', \'Erro desconhecido\')}")
                    except Exception as e:
                        st.error(f"Erro inesperado ao finalizar ocorrência: {e}")
            else:
                st.warning(f"Ocorrência com Nota Fiscal {nf_finalizar} não encontrada ou já finalizada.")
    else:
        st.info("Nenhuma ocorrência em aberto.")


# --- ABA OCORRÊNCIAS FINALIZADAS ---
with aba3:
    st.markdown("### Ocorrências Finalizadas")

    # Filtro por unidade (apenas para admins)
    if st.session_state.is_admin:
        unidades_disponiveis_finalizadas = ["Todas"] + sorted(list(set([o.get("ticket_unidade", "Não definida") for o in st.session_state.ocorrencias_finalizadas])))
        filtro_unidade_finalizado = st.selectbox("Filtrar por Unidade (Finalizado)", unidades_disponiveis_finalizadas, key="filtro_unidade_finalizado")
    else:
        filtro_unidade_finalizado = st.session_state.unidade # Usuário normal vê apenas sua unidade

    # Carregar ocorrências finalizadas do Supabase
    if not st.session_state.ocorrencias_finalizadas or (st.session_state.is_admin and "filtro_unidade_finalizado" in st.session_state and st.session_state.filtro_unidade_finalizado != st.session_state.get("last_filtro_unidade_finalizado")):
        with st.spinner("Carregando ocorrências finalizadas..."):
            try:
                query = supabase.table("ocorrencias").select("*").eq("status", "Finalizada")
                if not st.session_state.is_admin:
                    query = query.eq("ticket_unidade", st.session_state.unidade)
                elif filtro_unidade_finalizado != "Todas":
                    query = query.eq("ticket_unidade", filtro_unidade_finalizado)

                response = query.order("data_hora_finalizacao", desc=True).execute()
                if response.data:
                    st.session_state.ocorrencias_finalizadas = response.data
                else:
                    st.session_state.ocorrencias_finalizadas = []
            except Exception as e:
                st.error(f"Erro ao carregar ocorrências finalizadas do banco: {e}")
                st.session_state.ocorrencias_finalizadas = []
        
        if st.session_state.is_admin:
            st.session_state.last_filtro_unidade_finalizado = filtro_unidade_finalizado

    if st.session_state.ocorrencias_finalizadas:
        df_ocorrencias_finalizadas = pd.DataFrame(st.session_state.ocorrencias_finalizadas)
        st.dataframe(
            df_ocorrencias_finalizadas[["nota_fiscal", "cliente", "focal", "destinatario", "cidade", "motorista", "tipo_de_ocorrencia", "observacoes", "responsavel", "permanencia", "complementar", "data_hora_abertura", "data_hora_finalizacao", "ticket_unidade"]],
            use_container_width=True,
            hide_row_index=True
        )
    else:
        st.info("Nenhuma ocorrência finalizada.")


# --- ABA TICKETS POR FOCAL ---
with aba5:
    st.markdown("### Tickets por Focal")

    # Carregar focais para o filtro
    focais_disponiveis = ["Todos"] + focais # focais já carregados e cacheados
    focal_selecionado_filtro = st.selectbox("Selecione o Focal", focais_disponiveis, key="focal_selecionado_filtro")

    # Carregar ocorrências do Supabase com base no filtro de focal
    # Recarrega apenas se o focal selecionado mudar
    if st.session_state.focal_selecionado != focal_selecionado_filtro:
        with st.spinner(f"Carregando tickets para {focal_selecionado_filtro}..."):
            try:
                query = supabase.table("ocorrencias").select("*")
                if focal_selecionado_filtro != "Todos":
                    query = query.eq("focal", focal_selecionado_filtro)
                
                # Filtrar por unidade se não for admin
                if not st.session_state.is_admin:
                    query = query.eq("ticket_unidade", st.session_state.unidade)

                response = query.order("data_hora_abertura", desc=True).execute()
                if response.data:
                    st.session_state.tickets_por_focal = response.data
                else:
                    st.session_state.tickets_por_focal = []
            except Exception as e:
                st.error(f"Erro ao carregar tickets por focal: {e}")
                st.session_state.tickets_por_focal = []
        st.session_state.focal_selecionado = focal_selecionado_filtro

    if st.session_state.get("tickets_por_focal"):
        df_tickets_por_focal = pd.DataFrame(st.session_state.tickets_por_focal)
        st.dataframe(
            df_tickets_por_focal[["nota_fiscal", "cliente", "focal", "destinatario", "cidade", "motorista", "tipo_de_ocorrencia", "observacoes", "responsavel", "status", "permanencia", "data_hora_abertura", "data_hora_finalizacao", "ticket_unidade"]],
            use_container_width=True,
            hide_row_index=True
        )
    else:
        st.info("Nenhum ticket encontrado para o focal selecionado.")


# --- ABA CONFIGURAÇÕES ---
with aba4:
    st.markdown("### Configurações")
    st.write("Aqui você pode ajustar as configurações do aplicativo.")

    # Configuração do tempo de envio de e-mail
    novo_tempo_envio = st.number_input(
        "Intervalo para envio de e-mails de notificação (minutos):",
        min_value=1,
        max_value=1440, # 24 horas
        value=st.session_state.tempo_envio_email,
        step=1
    )

    if st.button("Salvar Configurações"):
        st.session_state.tempo_envio_email = novo_tempo_envio
        st.success(f"Intervalo de envio de e-mails atualizado para {novo_tempo_envio} minutos.")


# --- ABA NOTIFICAÇÕES POR E-MAIL (APENAS ADMIN) ---
if st.session_state.is_admin:
    with aba6:
        st.markdown("### Notificações por E-mail")
        st.write("Histórico de e-mails enviados:")

        if st.session_state.historico_emails:
            df_historico_emails = pd.DataFrame(st.session_state.historico_emails)
            st.dataframe(df_historico_emails, use_container_width=True)
        else:
            st.info("Nenhum e-mail enviado ainda.")


# --- ABA CADASTROS ---
with aba7:
    st.markdown("### Gerenciar Cadastros")

    tab_clientes, tab_cidades, tab_motoristas, tab_usuarios = st.tabs(["Clientes", "Cidades", "Motoristas", "Usuários"])

    with tab_clientes:
        st.markdown("#### Clientes")
        with st.form("form_cliente", clear_on_submit=True):
            novo_cliente = st.text_input("Nome do Cliente", max_chars=100).strip().upper()
            novo_focal = st.text_input("Focal", max_chars=100).strip().upper()
            novo_email_principal = st.text_input("E-mail Principal (para notificações)", max_chars=200).strip().lower()
            novo_email_copia = st.text_input("E-mail Cópia (separar por vírgula)", max_chars=200).strip().lower()
            
            submitted_cliente = st.form_submit_button("Adicionar Cliente")
            if submitted_cliente:
                if not novo_cliente or not novo_focal or not novo_email_principal:
                    st.error("Nome do Cliente, Focal e E-mail Principal são obrigatórios.")
                elif not validar_email(novo_email_principal):
                    st.error("Por favor, insira um e-mail principal válido.")
                elif novo_email_copia and not validar_emails_multiplos(novo_email_copia):
                    st.error("Por favor, insira e-mails de cópia válidos, separados por vírgula.")
                else:
                    if adicionar_cliente_supabase(novo_cliente, novo_focal, novo_email_principal, novo_email_copia):
                        st.rerun() # Recarrega para atualizar a lista de clientes

        st.markdown("##### Clientes Cadastrados")
        df_clientes_cadastrados = carregar_clientes_supabase() # Recarrega para exibir o mais recente
        if not df_clientes_cadastrados.empty:
            st.dataframe(df_clientes_cadastrados, use_container_width=True, hide_row_index=True)
            cliente_remover = st.selectbox("Selecione o Cliente para Remover", options=["Selecione"] + df_clientes_cadastrados["cliente"].tolist(), key="remover_cliente_sb")
            if st.button("Remover Cliente", key="btn_remover_cliente"):
                if cliente_remover != "Selecione":
                    if remover_cliente_supabase(cliente_remover):
                        st.rerun()
                else:
                    st.warning("Por favor, selecione um cliente para remover.")
        else:
            st.info("Nenhum cliente cadastrado.")

    with tab_cidades:
        st.markdown("#### Cidades")
        with st.form("form_cidade", clear_on_submit=True):
            nova_cidade = st.text_input("Nome da Cidade", max_chars=100).strip().upper()
            submitted_cidade = st.form_submit_button("Adicionar Cidade")
            if submitted_cidade:
                if not nova_cidade:
                    st.error("O nome da cidade é obrigatório.")
                else:
                    if adicionar_cidade_supabase(nova_cidade):
                        st.rerun() # Recarrega para atualizar a lista de cidades

        st.markdown("##### Cidades Cadastradas")
        cidades_cadastradas = carregar_cidades_supabase() # Recarrega para exibir o mais recente
        if cidades_cadastradas:
            df_cidades_cadastradas = pd.DataFrame({"Cidade": cidades_cadastradas})
            st.dataframe(df_cidades_cadastradas, use_container_width=True, hide_row_index=True)
            cidade_remover = st.selectbox("Selecione a Cidade para Remover", options=["Selecione"] + cidades_cadastradas, key="remover_cidade_sb")
            if st.button("Remover Cidade", key="btn_remover_cidade"):
                if cidade_remover != "Selecione":
                    if remover_cidade_supabase(cidade_remover):
                        st.rerun()
                else:
                    st.warning("Por favor, selecione uma cidade para remover.")
        else:
            st.info("Nenhuma cidade cadastrada.")

    with tab_motoristas:
        st.markdown("#### Motoristas")
        with st.form("form_motorista", clear_on_submit=True):
            novo_motorista = st.text_input("Nome do Motorista", max_chars=100).strip().upper()
            submitted_motorista = st.form_submit_button("Adicionar Motorista")
            if submitted_motorista:
                if not novo_motorista:
                    st.error("O nome do motorista é obrigatório.")
                else:
                    if adicionar_motorista_supabase(novo_motorista):
                        st.rerun() # Recarrega para atualizar a lista de motoristas

        st.markdown("##### Motoristas Cadastrados")
        motoristas_cadastrados = carregar_motoristas_supabase() # Recarrega para exibir o mais recente
        if motoristas_cadastrados:
            df_motoristas_cadastrados = pd.DataFrame({"Motorista": motoristas_cadastrados})
            st.dataframe(df_motoristas_cadastrados, use_container_width=True, hide_row_index=True)
            motorista_remover = st.selectbox("Selecione o Motorista para Remover", options=["Selecione"] + motoristas_cadastrados, key="remover_motorista_sb")
            if st.button("Remover Motorista", key="btn_remover_motorista"):
                if motorista_remover != "Selecione":
                    if remover_motorista_supabase(motorista_remover):
                        st.rerun()
                else:
                    st.warning("Por favor, selecione um motorista para remover.")
        else:
            st.info("Nenhum motorista cadastrado.")

    with tab_usuarios:
        st.markdown("#### Usuários")
        with st.form("form_usuario", clear_on_submit=True):
            novo_nome_usuario = st.text_input("Nome de Usuário", max_chars=50).strip().lower()
            nova_senha = st.text_input("Senha", type="password", max_chars=50).strip()
            novo_is_admin = st.checkbox("É Administrador?")
            nova_unidade = st.text_input("Unidade (Ex: SP, RJ, MG)", max_chars=10).strip().upper()
            submitted_usuario = st.form_submit_button("Adicionar Usuário")
            if submitted_usuario:
                if not novo_nome_usuario or not nova_senha or not nova_unidade:
                    st.error("Nome de Usuário, Senha e Unidade são obrigatórios.")
                else:
                    if adicionar_usuario_supabase(novo_nome_usuario, nova_senha, novo_is_admin, nova_unidade):
                        st.rerun() # Recarrega para atualizar a lista de usuários

        st.markdown("##### Usuários Cadastrados")
        # Carregar usuários do Supabase (não cacheado, pois pode mudar com frequência)
        try:
            response_usuarios = supabase.table("usuarios").select("nome_usuario, is_admin, unidade").execute()
            if response_usuarios.data:
                df_usuarios_cadastrados = pd.DataFrame(response_usuarios.data)
                st.dataframe(df_usuarios_cadastrados, use_container_width=True, hide_row_index=True)
                usuario_remover = st.selectbox("Selecione o Usuário para Remover", options=["Selecione"] + df_usuarios_cadastrados["nome_usuario"].tolist(), key="remover_usuario_sb")
                if st.button("Remover Usuário", key="btn_remover_usuario"):
                    if usuario_remover != "Selecione":
                        if remover_usuario_supabase(usuario_remover):
                            st.rerun()
                    else:
                        st.warning("Por favor, selecione um usuário para remover.")
            else:
                st.info("Nenhum usuário cadastrado.")
        except Exception as e:
            st.error(f"Erro ao carregar usuários: {e}")


# --- ABA ESTATÍSTICA ---
with aba8:
    st.markdown("### Estatísticas de Ocorrências")

    # Carregar todas as ocorrências para estatísticas (pode ser cacheado se os dados não mudarem muito frequentemente)
    @st.cache_data(ttl=600) # Cache por 10 minutos
    def carregar_todas_ocorrencias_supabase():
        with st.spinner("Carregando todas as ocorrências para estatísticas..."):
            try:
                query = supabase.table("ocorrencias").select("*")
                if not st.session_state.is_admin:
                    query = query.eq("ticket_unidade", st.session_state.unidade)
                response = query.execute()
                if response.data:
                    return pd.DataFrame(response.data)
                else:
                    return pd.DataFrame()
            except Exception as e:
                st.error(f"Erro ao carregar todas as ocorrências: {e}")
                return pd.DataFrame()

    df_todas_ocorrencias = carregar_todas_ocorrencias_supabase()

    if not df_todas_ocorrencias.empty:
        st.markdown("#### Visão Geral")
        total_ocorrencias = len(df_todas_ocorrencias)
        ocorrencias_abertas_count = df_todas_ocorrencias[df_todas_ocorrencias["status"] == "Aberta"].shape[0]
        ocorrencias_finalizadas_count = df_todas_ocorrencias[df_todas_ocorrencias["status"] == "Finalizada"].shape[0]

        col_total, col_abertas, col_finalizadas = st.columns(3)
        with col_total:
            st.metric(label="Total de Ocorrências", value=total_ocorrencias)
        with col_abertas:
            st.metric(label="Ocorrências em Aberto", value=ocorrencias_abertas_count)
        with col_finalizadas:
            st.metric(label="Ocorrências Finalizadas", value=ocorrencias_finalizadas_count)

        st.markdown("#### Permanência Média por Tipo de Ocorrência (Finalizadas)")
        df_finalizadas = df_todas_ocorrencias[df_todas_ocorrencias["status"] == "Finalizada"].copy()
        if not df_finalizadas.empty:
            df_finalizadas["permanencia"] = pd.to_numeric(df_finalizadas["permanencia"], errors=\'coerce\')
            permanencia_media_por_tipo = df_finalizadas.groupby("tipo_de_ocorrencia")["permanencia"].mean().reset_index()
            permanencia_media_por_tipo["permanencia"] = permanencia_media_por_tipo["permanencia"].astype(int)
            st.dataframe(permanencia_media_por_tipo.rename(columns={"permanencia": "Permanência Média (minutos)"}), use_container_width=True, hide_row_index=True)
        else:
            st.info("Nenhuma ocorrência finalizada para calcular a permanência média.")

        st.markdown("#### Ocorrências por Cliente")
        ocorrencias_por_cliente = df_todas_ocorrencias["cliente"].value_counts().reset_index()
        ocorrencias_por_cliente.columns = ["Cliente", "Número de Ocorrências"]
        st.dataframe(ocorrencias_por_cliente, use_container_width=True, hide_row_index=True)

        st.markdown("#### Ocorrências por Focal")
        ocorrencias_por_focal = df_todas_ocorrencias["focal"].value_counts().reset_index()
        ocorrencias_por_focal.columns = ["Focal", "Número de Ocorrências"]
        st.dataframe(ocorrencias_por_focal, use_container_width=True, hide_row_index=True)

        st.markdown("#### Ocorrências por Motorista")
        ocorrencias_por_motorista = df_todas_ocorrencias["motorista"].value_counts().reset_index()
        ocorrencias_por_motorista.columns = ["Motorista", "Número de Ocorrências"]
        st.dataframe(ocorrencias_por_motorista, use_container_width=True, hide_row_index=True)

    else:
        st.info("Nenhum dado de ocorrência disponível para estatísticas.")

# Auto-refresh para atualizar ocorrências em aberto a cada X minutos
st_autorefresh(interval=st.session_state.tempo_envio_email * 60 * 1000, key="data_refresh")
