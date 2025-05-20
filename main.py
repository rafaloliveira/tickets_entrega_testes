# versão liberada para usuario


import streamlit as st
st.set_page_config(page_title="Entregas - Tempo de Permanência", layout="wide")

import pandas as pd
import os
import time
import uuid
import pytz
import bcrypt
from email.message import EmailMessage
import hashlib
import psycopg2
from datetime import datetime, timedelta, timezone
from dateutil import parser
from psycopg2 import sql
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
import os


from streamlit_autorefresh import st_autorefresh
import streamlit_authenticator as stauth
from streamlit_cookies_manager import EncryptedCookieManager

from supabase import create_client, Client as SupabaseClient

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
                    cookies["expiry_time"] = expiry_time.strftime("%d-%m-%Y %H:%M:%S")
                    cookies.save()
                    st.session_state.login = True  # Atualiza a sessão para indicar que o login foi bem-sucedido
                    st.rerun()  # Recarga a página após login

        st.stop()  # Impede que o código continue sendo executado após login falhar


# --- Chama login antes de qualquer coisa ---
login()


# --- SE CHEGOU AQUI, USUÁRIO ESTÁ AUTENTICADO ---
#--------------------------------------------------------------------------INICIO APP -------------------------------------------------------------

TZ_BR = pytz.timezone("America/Sao_Paulo")


#- -- INICIALIZAÇÃO DE SESSÃO ---
if "ocorrencias_abertas" not in st.session_state:
    st.session_state.ocorrencias_abertas = []

if "ocorrencias_finalizadas" not in st.session_state:
    st.session_state.ocorrencias_finalizadas = []

# --- ABA NOVA OCORRÊNCIA ---
aba1, aba2, aba3, aba5, aba4,  = st.tabs(["📝 Nova Ocorrência", "📌 Ocorrências em Aberto", "✅ Ocorrências Finalizadas", "📝 Tickets por Focal", "📊 Configurações"])

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

# Função de inserção no Supabase
def inserir_ocorrencia_supabase(dados):
    payload = {
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
        "data_abertura_manual": dados["data_abertura_manual"],  # string "YYYY-MM-DD"
        "hora_abertura_manual": dados["hora_abertura_manual"],   # string "HH:MM:SS"
        "permanencia": dados["permanencia"],
        "complementar": dados["complementar"]
    }

    try:
        print("Payload a ser enviado:")
        print(payload)
        response = supabase.table("ocorrencias").insert([payload]).execute()
        return response
    except Exception as e:
        st.error("Erro ao inserir ocorrência.")
        st.exception(e)
        return None



# --- CARREGAMENTO DE DADOS Tabelas com nomes de motorista e clientes ---

# Carrega a aba "clientes" do arquivo clientes.xlsx
df_clientes = pd.read_excel("data/clientes.xlsx", sheet_name="clientes")
df_clientes.columns = df_clientes.columns.str.strip()  # Remove espaços extras nas colunas
df_clientes = df_clientes[["Cliente", "Focal"]].dropna(subset=["Cliente"])

df_clientes = pd.read_excel("data/clientes.xlsx", sheet_name="clientes")
df_clientes.columns = df_clientes.columns.str.strip()
df_clientes = df_clientes[["Cliente", "Focal", "enviar_para_email", "email_copia"]].dropna(subset=["Cliente"])


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


#============================================
# FUNÇÃO ENVIA E-MAIL AO ADICIONAR OCORRENCIA
#============================================


load_dotenv()  # Carrega as variáveis do .env

EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_SENHA = os.getenv("EMAIL_SENHA")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))


def enviar_email_ocorrencia(cliente_nome: str, assunto: str, corpo_email: str):
    # Lê planilha com e-mails
    try:
        df_clientes = pd.read_excel('data/clientes.xlsx', sheet_name='clientes')
    except Exception as e:
        st.error(f"Erro ao carregar planilha de clientes: {e}")
        return

    cliente_linha = df_clientes[df_clientes['Cliente'] == cliente_nome]
    if cliente_linha.empty:
        st.warning(f"⚠️ Cliente '{cliente_nome}' não encontrado na lista de e-mails.")
        return

    enviar_para = cliente_linha['enviar_para_email'].values[0]
    copia_para = cliente_linha['email_copia'].values[0]

    # Criar mensagem
    msg = EmailMessage()
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = enviar_para
    if copia_para and isinstance(copia_para, str) and copia_para.strip() != "":
        msg['Cc'] = copia_para
    msg['Subject'] = assunto
    msg.set_content(corpo_email)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()  # iniciar TLS
            smtp.login(EMAIL_REMETENTE, EMAIL_SENHA)
            smtp.send_message(msg)
        st.success(f"E-mail enviado para {enviar_para}")
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")




# --- FORMULÁRIO PARA NOVA OCORRÊNCIA ---

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

            tz = pytz.timezone("America/Sao_Paulo")
            agora = datetime.now(tz)

            # Layout com valores padrão preenchidos com a hora atual em UTC−3
            col_data, col_hora = st.columns(2)
            with col_data:
                data_abertura_manual = st.date_input(
                    "Data de Abertura",
                    value=agora.date(),
                    format="DD/MM/YYYY"
                )
            with col_hora:
                hora_abertura_manual = st.time_input(
                    "Hora de Abertura",
                    value=agora.time().replace(microsecond=0)
                )


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
                numero_ticket = datetime.now().strftime("%Y%m%d%H%M%S%f")  # Ex: 20250513151230543210

                # Validando os valores antes de enviar para o Supabase
                fuso_sp = pytz.timezone("America/Sao_Paulo")
                agora_sp = datetime.now(fuso_sp)
                abertura_sem_fuso = agora_sp.replace(tzinfo=None)  # Remove o fuso horário para formato sem TZ
                

                # Montagem do dicionário de nova ocorrência
                nova_ocorrencia = {
                    "id": str(uuid.uuid4()),
                    "nota_fiscal": nf,
                    "cliente": cliente,
                    "focal": st.session_state["focal_responsavel"],
                    "destinatario": destinatario,
                    "cidade": cidade,
                    "motorista": motorista,
                    "tipo_de_ocorrencia": ", ".join(tipo),
                    "observacoes": obs,
                    "responsavel": responsavel,

                    # Agora com base na data/hora manual inserida
                    "data_hora_abertura": abertura_sem_fuso.strftime("%Y-%m-%d %H:%M:%S"),
                    "abertura_timestamp": abertura_sem_fuso.isoformat(),
                    "abertura_datetime_obj": abertura_sem_fuso,
                    "abertura_ticket": abertura_sem_fuso.strftime("%Y-%m-%d %H:%M:%S"),

                    "data_abertura_manual": data_abertura_manual.strftime("%Y-%m-%d"),
                    "hora_abertura_manual": hora_abertura_manual.strftime("%H:%M:%S"),
                    "complementar": "",
                    "permanencia": ""
                }

                # Inserção no banco de dados            
                response = inserir_ocorrencia_supabase(nova_ocorrencia)
                numero_ticket_db = response.data[0].get("numero_ticket", "N/D")

                
                if response.data:
                    # Adiciona localmente para exibição imediata
                    nova_ocorrencia_local = nova_ocorrencia.copy()
                    nova_ocorrencia_local["Data/Hora Finalização"] = ""
                    st.session_state.ocorrencias_abertas.append(nova_ocorrencia_local)

                    st.session_state["focal_responsavel"] = ""

                    sucesso = st.empty()
                    sucesso.success("✅ Ocorrência aberta com sucesso!")
                    time.sleep(2)
                    sucesso.empty()
            



# Função de classificação

tz_sp = pytz.timezone("America/Sao_Paulo")
TEMPO_LIMITE_EMAIL_MINUTOS = 30  # Altere aqui para 45, 60, etc., quando quiser
def parse_manual_datetime(data_str, hora_str, fmt="%d-%m-%Y %H:%M"):
    """Converte as strings de data e hora manuais para um datetime aware no fuso de SP."""
    try:
        dt = datetime.strptime(f"{data_str} {hora_str}", fmt)
        return tz_sp.localize(dt)
    except Exception as e:
        st.error(f"Erro ao converter data/hora manual: {e}")
        return None
    
def calcular_permanencia(dt_inicio, dt_fim):
    """Calcula a permanência no formato HH:MM dado dois datetime."""
    delta = dt_fim - dt_inicio
    total_segundos = int(delta.total_seconds())
    horas = total_segundos // 3600
    minutos = (total_segundos % 3600) // 60
    return f"{horas:02d}:{minutos:02d}"

# =========================
#    FUNÇÃO CLASSIFICAÇÃO
# =========================
def classificar_ocorrencia_por_tempo(data_abertura_manual, hora_abertura_manual):
    """Usa as datas manuais para determinar o status visual da ocorrência."""
    if not data_abertura_manual or not hora_abertura_manual:
        return "Data/hora inválida", "gray"
    dt_abertura = parse_manual_datetime(data_abertura_manual, hora_abertura_manual, fmt="%Y-%m-%d %H:%M:%S")
    if dt_abertura is None:
        return "Erro", "gray"
    agora = datetime.now(tz_sp)
    minutos_decorridos = (agora - dt_abertura).total_seconds() / 60

    if minutos_decorridos < 10:
        return "🟢 Normal", "#2ecc71"
    elif minutos_decorridos < 15:
        return "🟡 Alerta", "#f1c40f"
    elif minutos_decorridos < 30:
        return "🔴 Crítico", "#e74c3c"
    else:
        return "🚨 +60 min", "#c0392b"




# --- Função para carregar ocorrências abertas ---
def carregar_ocorrencias_abertas():
    try:
        response = supabase.table("ocorrencias").select("*").eq("status", "Aberta").order("data_hora_abertura", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao carregar ocorrências abertas: {e}")
        return []

# =========================
#    FUNÇÃO SALVAR FINALIZADA
# =========================
def salvar_ocorrencia_finalizada(ocorr, complemento):
    try:
        # Obtem data/hora de finalização a partir do campo "Data/Hora Finalização" (se houver) ou já convertido nos inputs
        if isinstance(ocorr.get("Data/Hora Finalização"), str):
            try:
                data_hora_finalizacao = datetime.strptime(ocorr["Data/Hora Finalização"], "%d-%m-%Y %H:%M:%S")
            except ValueError:
                st.error("Erro: Formato de 'Data/Hora Finalização' inválido! Use DD-MM-AAAA HH:MM:SS")
                return
        else:
            data_hora_finalizacao = ocorr["Data/Hora Finalização"]
    
        # Recupera o timestamp de abertura (originalmente salvo no banco em ISO sem TZ)
        data_hora_abertura = parser.parse(ocorr["abertura_timestamp"]).replace(tzinfo=None)
    
        # Impede finalização se a finalização ocorrer antes da abertura
        if data_hora_finalizacao < data_hora_abertura:
            st.error("❌ Data/hora de finalização não pode ser menor que a de abertura.")
            return
    
        # Converte e formata as datas manuais para exibição consistente (formato DD-MM-AAAA para data e HH:MM para hora)
        data_finalizacao_manual = data_hora_finalizacao.strftime("%d-%m-%Y")
        hora_finalizacao_manual = data_hora_finalizacao.strftime("%H:%M")
        data_abertura_manual = data_hora_abertura.strftime("%d-%m-%Y")
        hora_abertura_manual = data_hora_abertura.strftime("%H:%M")
    
        # Calcula o tempo de permanência
        permanencia_manual = calcular_permanencia(data_hora_abertura, data_hora_finalizacao)
    
        # Atualiza no Supabase os campos manuais e o status
        response = supabase.table("ocorrencias").update({
            "status": "Finalizada",
            "complementar": complemento,
            "finalizado_por": st.session_state.username,
            "data_finalizacao_manual": data_finalizacao_manual,
            "hora_finalizacao_manual": hora_finalizacao_manual,
            "permanencia_manual": permanencia_manual
        }).eq("id", ocorr["id"]).execute()
    
        st.write("Resposta Supabase:", response)
        st.session_state["mensagem_sucesso_finalizacao"] = True
    except Exception as e:
        st.error(f"Erro ao salvar no banco de dados: {e}")
        st.session_state["mensagem_sucesso_finalizacao"] = False
    
    if st.session_state.get("mensagem_sucesso_finalizacao"):
        sucesso_msg = st.empty()
        sucesso_msg.success("✅ Ocorrência finalizada com sucesso!")
        time.sleep(2)
        sucesso_msg.empty()
        # Limpa o estado do campo 'complemento' para esse ticket
        st.session_state.pop(f"complemento_final_{ocorr['id']}", None)
        st.rerun()


# =========================
#     ABA 2 - EM ABERTO
# =========================
with aba2:
    st.header("Ocorrências em Aberto")
    
    ocorrencias_abertas = carregar_ocorrencias_abertas()
    
    if not ocorrencias_abertas:
        st.info("ℹ️ Nenhuma ocorrência aberta no momento.")
    else:
        num_colunas = 4
        cols = st.columns(num_colunas)
        st_autorefresh(interval=40000, key="ocorrencias_abertas_refresh")
        
        # Combina o envio de e-mails automáticos (quando passados 30min) e a renderização dos cartões
        for idx, ocorr in enumerate(ocorrencias_abertas):
            # Verifica se os campos manuais existem
            if ocorr.get("data_abertura_manual") and ocorr.get("hora_abertura_manual"):
                # Converte os campos manuais para datetime (usando o formato ISO que foi salvo no banco, por exemplo "YYYY-MM-DD")
                try:
                    # Supondo que os dados manuais foram salvos no insert como: data_abertura_manual: "YYYY-MM-DD" e hora_abertura_manual: "HH:MM:SS"
                    dt_abertura = datetime.strptime(f"{ocorr['data_abertura_manual']} {ocorr['hora_abertura_manual']}", "%Y-%m-%d %H:%M:%S")
                    dt_abertura = tz_sp.localize(dt_abertura)
                except Exception as e:
                    st.error(f"Erro ao converter data/hora de abertura: {e}")
                    continue
                
                # Verifica se o tempo decorrido (desde o dt_abertura) é maior ou igual a 30 minutos para envio de e-mail
                delta = datetime.now(tz_sp) - dt_abertura
                if delta.total_seconds() >= TEMPO_LIMITE_EMAIL_MINUTOS * 60 and not ocorr.get("email_abertura_enviado"):
                    try:
                        numero_ticket = ocorr.get("numero_ticket", "N/D")
                        cliente = ocorr.get("cliente", "Cliente não informado")
                        nf = ocorr.get("nota_fiscal", "N/D")
                        cidade = ocorr.get("cidade", "N/D")
                        motorista = ocorr.get("motorista", "N/D")
                        tipo = ocorr.get("tipo_de_ocorrencia", "N/D")
                        responsavel = ocorr.get("responsavel", "N/D")
                        data_abertura_fmt = dt_abertura.strftime("%d-%m-%Y")
                        hora_abertura_fmt = dt_abertura.strftime("%H:%M:%S")
                        
                        assunto_abertura = f"[Abertura de Ocorrência] Ticket {numero_ticket} para {cliente}"
                        corpo_abertura = f"""
                        Prezados,
                        
                        Informamos que o veículo responsável pela entrega, conforme identificado abaixo, está no ponto de descarga há mais de 30 minutos.
                        ⚠️ Atenção: após esse período, será aplicada a TDE conforme previsto em contrato.
                        
                        ➡️ Número do Ticket: {numero_ticket}
                        📄 Nota Fiscal: {nf}
                        📍 Cidade: {cidade}
                        🚚 Motorista: {motorista}
                        📌 Tipo: {tipo}
                        🕒 Abertura: {data_abertura_fmt} às {hora_abertura_fmt}
                        👤 Responsável: {responsavel}
                        """
                        enviar_email_ocorrencia(cliente_nome=cliente, assunto=assunto_abertura, corpo_email=corpo_abertura)
                        supabase.table("ocorrencias").update({"email_abertura_enviado": True}).eq("id", ocorr["id"]).execute()
                        st.toast(f"E-mail de abertura enviado para {cliente} (ticket {numero_ticket})", icon="📧")
                    except Exception as e:
                        st.warning(f"Falha ao enviar e-mail de abertura para {ocorr.get('cliente', '-')}: {e}")
                
                # Agora renderiza o cartão e área de finalização
                col = cols[idx % num_colunas]
                with col:
                    safe_idx = f"{idx}_{ocorr.get('nota_fiscal', '')}"
                    # Para exibição, usa os campos manuais conforme armazenados
                    data_abertura_manual_disp = ocorr.get("data_abertura_manual", "Não informada")
                    hora_abertura_manual_disp = ocorr.get("hora_abertura_manual", "Não informada")
                    # Usa a função de classificação baseada nas datas manuais (observando o formato que está no banco; se for "YYYY-MM-DD" para data, adapte o parse)
                    try:
                        # Se no banco os dados manuais estão em formato "YYYY-MM-DD", converte para o formato ISO para nossa função:
                        dt_classifica = datetime.strptime(f"{ocorr['data_abertura_manual']} {ocorr['hora_abertura_manual']}", "%Y-%m-%d %H:%M:%S")
                        dt_classifica = tz_sp.localize(dt_classifica)
                        data_abertura_iso = dt_classifica.strftime("%Y-%m-%d %H:%M:%S")
                        status, cor = classificar_ocorrencia_por_tempo(ocorr["data_abertura_manual"], ocorr["hora_abertura_manual"])
                    except Exception as e:
                        st.error(f"Erro ao processar data/hora da ocorrência {ocorr.get('nota_fiscal', '-')}: {e}")
                        status, cor = "Erro", "gray"
                    
                    with st.container():
                        st.markdown(
                            f"""
                            <div style="background-color:{cor};padding:10px;border-radius:10px;color:white;
                                 box-shadow: 0 4px 10px rgba(0,0,0,0.3);margin-bottom:5px;min-height:250px;font-size:15px;">
                                <strong>Ticket #:</strong> {ocorr.get('numero_ticket', 'N/A')}<br>
                                <strong>Status:</strong> <span style="background-color:#2c3e50;padding:4px 8px;border-radius:1px;color:white;">{status}</span><br>
                                <strong>NF:</strong> {ocorr.get('nota_fiscal', '-')}<br>
                                <strong>Cliente:</strong> {ocorr.get('cliente', '-')}<br>
                                <strong>Destinatário:</strong> {ocorr.get('destinatario', '-')}<br>
                                <strong>Focal:</strong> {ocorr.get('focal', '-')}<br>
                                <strong>Cidade:</strong> {ocorr.get('cidade', '-')}<br>
                                <strong>Motorista:</strong> {ocorr.get('motorista', '-')}<br>
                                <strong>Tipo:</strong> {ocorr.get('tipo_de_ocorrencia', '-')}<br>
                                <strong>Aberto por:</strong> {ocorr.get('responsavel', '-')}<br>
                                <strong>Data Abertura:</strong> {data_abertura_manual_disp}<br>
                                <strong>Hora Abertura:</strong> {hora_abertura_manual_disp}<br>
                                <strong>Observações:</strong> {ocorr.get('observacoes', 'Sem observações.')}<br>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    
                    with st.expander("Finalizar Ocorrência"):
                        data_atual = datetime.now(tz_sp).strftime("%d-%m-%Y")
                        hora_atual = datetime.now(tz_sp).strftime("%H:%M")
                        data_finalizacao_manual = st.text_input("Data Finalização (DD-MM-AAAA)", value=data_atual, key=f"data_final_{safe_idx}")
                        hora_finalizacao_manual = st.text_input("Hora Finalização (HH:MM)", value=hora_atual, key=f"hora_final_{safe_idx}")
    
                        comp_key = f"complemento_final_{safe_idx}"
                        if comp_key not in st.session_state:
                            st.session_state[comp_key] = ""
                        complemento = st.text_area("Complementar (obrigatório)", key=comp_key, value=st.session_state[comp_key])
    
                        if st.button("Finalizar", key=f"finalizar_{safe_idx}", disabled=not complemento.strip()):
                            # Usa os helpers para parse
                            dt_finalizacao = parse_manual_datetime(data_finalizacao_manual, hora_finalizacao_manual, fmt="%d-%m-%Y %H:%M")
                            dt_abertura_final = parse_manual_datetime(ocorr["data_abertura_manual"], ocorr["hora_abertura_manual"], fmt="%Y-%m-%d %H:%M:%S")
    
                            if dt_finalizacao is None or dt_abertura_final is None:
                                st.error("Erro na conversão de data/hora.")
                                continue
    
                            if dt_finalizacao < dt_abertura_final:
                                st.error("❌ Data/hora de finalização não pode ser menor que a de abertura.")
                                continue
    
                            permanencia_manual = calcular_permanencia(dt_abertura_final, dt_finalizacao)
    
                            # Atualiza no Supabase
                            supabase.table("ocorrencias").update({
                                "status": "Finalizada",
                                "complementar": complemento,
                                "data_hora_finalizacao": dt_finalizacao.strftime("%Y-%m-%d %H:%M:%S"),
                                "finalizado_por": st.session_state.username,
                                "data_finalizacao_manual": data_finalizacao_manual,
                                "hora_finalizacao_manual": hora_finalizacao_manual,
                                "permanencia_manual": permanencia_manual
                            }).eq("id", ocorr["id"]).execute()
    
                            try:
                                assunto_finalizacao = f"[Finalização de Ocorrência] Ticket {ocorr.get('numero_ticket')} - {ocorr.get('cliente')}"
                                corpo_finalizacao = f"""
                            Prezados,
    
                            Informamos que a seguinte ocorrência foi finalizada com sucesso:
    
                            ➡️ Número do Ticket: {ocorr.get('numero_ticket')}
                            📄 Nota Fiscal: {ocorr.get('nota_fiscal')}
                            📍 Cidade: {ocorr.get('cidade')}
                            🚚 Motorista: {ocorr.get('motorista')}
                            📌 Tipo: {ocorr.get('tipo_de_ocorrencia')}
                            🕒 Abertura: {dt_abertura_final.strftime('%d-%m-%Y')} às {dt_abertura_final.strftime('%H:%M:%S')}
                            🕒 Finalização: {dt_finalizacao.strftime('%d-%m-%Y')} às {dt_finalizacao.strftime('%H:%M:%S')}
                            ⌛ Tempo de Permanência: {permanencia_manual}
    
                            📝 Complementar:
                            {complemento if complemento else 'Sem detalhes adicionais.'}
    
                            Atenciosamente,
                            Equipe de Monitoramento
                                """
                                enviar_email_ocorrencia(
                                    cliente_nome=ocorr.get("cliente"),
                                    assunto=assunto_finalizacao,
                                    corpo_email=corpo_finalizacao
                                )
                                st.toast(f"📧 E-mail de finalização enviado para {ocorr.get('cliente')}.")
                            except Exception as e:
                                st.warning(f"❌ Falha ao enviar e-mail de finalização para {ocorr.get('cliente')}: {e}")
    
                            st.success("✅ Ocorrência finalizada com sucesso.")
                            # Limpa o campo 'complemento' deste ticket
                            st.session_state.pop(comp_key, None)
                            st.rerun()


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
#  FUNÇÃO PARSE
# =========================

def parse_datetime_safe(date_str, fmt=None):
    try:
        if fmt:
            return datetime.strptime(date_str, fmt)
        else:
            return parser.isoparse(date_str).replace(tzinfo=None)
    except Exception:
        return None
    
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
        col1, col2 = st.columns([1, 2])
        with col1:
            filtro_nf = st.text_input("🔎 Pesquisar por NF:", "", max_chars=10)

        with col2:
            try:
                # Cria o dataframe e prepara o arquivo Excel para download
                df = pd.DataFrame(ocorrencias_finalizadas)
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Finalizadas')
                output.seek(0)  # volta para o começo do arquivo

                # Botão direto de download
                st.download_button(
                    label="📤 Exportar Excel",
                    data=output,
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
                    # --- Datas sistema ---
                    data_abertura_raw = ocorr.get("abertura_ticket") or ocorr.get("abertura_timestamp")
                    data_finalizacao_raw = ocorr.get("data_hora_finalizacao")

                    data_abertura_dt = parser.isoparse(data_abertura_raw).replace(tzinfo=None) if data_abertura_raw else None
                    data_finalizacao_dt = parser.isoparse(data_finalizacao_raw).replace(tzinfo=None) if data_finalizacao_raw else None

                    data_abertura_formatada = data_abertura_dt.strftime("%d-%m-%Y %H:%M:%S") if data_abertura_dt else "-"
                    data_finalizacao_formatada = data_finalizacao_dt.strftime("%d-%m-%Y %H:%M:%S") if data_finalizacao_dt else "-"

                    tempo_permanencia_formatado = "-"
                    if data_abertura_dt and data_finalizacao_dt:
                        tempo_total = data_finalizacao_dt - data_abertura_dt
                        tempo_permanencia_formatado = str(tempo_total).split('.')[0]

                    # --- Datas manuais ---
                    data_abertura_manual = "-"
                    hora_abertura_manual = "-"
                    if ocorr.get("data_abertura_manual") and ocorr.get("hora_abertura_manual"):
                        try:
                            abertura_dt = datetime.strptime(
                                f"{ocorr['data_abertura_manual']} {ocorr['hora_abertura_manual']}",
                                "%Y-%m-%d %H:%M:%S"
                            )
                            data_abertura_manual = abertura_dt.strftime("%d-%m-%Y")
                            hora_abertura_manual = abertura_dt.strftime("%H:%M:%S")
                        except:
                            pass

                    data_finalizacao_manual = "-"
                    hora_finalizacao_manual = "-"
                    if ocorr.get("data_finalizacao_manual") and ocorr.get("hora_finalizacao_manual"):
                        try:
                            finalizacao_dt = datetime.strptime(
                                f"{ocorr['data_finalizacao_manual']} {ocorr['hora_finalizacao_manual']}",
                                "%Y-%m-%d %H:%M:%S"
                            )
                            data_finalizacao_manual = finalizacao_dt.strftime("%d-%m-%Y")
                            hora_finalizacao_manual = finalizacao_dt.strftime("%H:%M:%S")
                        except:
                            pass

                    status = ocorr.get("Status", "Finalizada")
                    cor = ocorr.get("Cor", "#34495e")

                except Exception as e:
                    st.error(f"Erro ao processar ocorrência (NF {ocorr.get('nota_fiscal', '-')}) — {e}")
                    data_abertura_formatada = data_finalizacao_formatada = tempo_permanencia_formatado = "-"
                    data_abertura_manual = hora_abertura_manual = "-"
                    data_finalizacao_manual = hora_finalizacao_manual = "-"
                    status = "Erro"
                    cor = "#7f8c8d"

                with colunas[idx]:
                    st.markdown(
                        f"""
                        <div style='background-color:{cor};padding:15px;border-radius:10px;color:white;
                            box-shadow: 0 4px 10px rgba(0,0,0,0.3);margin:8px;min-height:250px;font-size:15px;
                            border: 2px solid #ccc; box-sizing: border-box; width: 100%;'>
                            <strong>Ticket #:</strong> {ocorr.get('numero_ticket') or 'N/A'}<br>
                            <strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;border-radius:3px;color:white;'>{status}</span><br>
                            <strong>NF:</strong> {ocorr.get('nota_fiscal', '-')}<br>
                            <strong>Cliente:</strong> {ocorr.get('cliente', '-')}<br>
                            <strong>Destinatário:</strong> {ocorr.get('destinatario', '-')}<br>
                            <strong>Cidade:</strong> {ocorr.get('cidade', '-')}<br>
                            <strong>Motorista:</strong> {ocorr.get('motorista', '-')}<br>
                            <strong>Tipo:</strong> {ocorr.get('tipo_de_ocorrencia', '-')}<br>
                            <strong>Aberto por:</strong> {ocorr.get('responsavel', '-')}<br>
                            <strong>Data Abertura:</strong> {data_abertura_manual}<br>
                            <strong>Hora Abertura:</strong> {hora_abertura_manual}<br>
                            <strong>Data Finalização:</strong> {data_finalizacao_manual}<br>
                            <strong>Hora Finalização:</strong> {hora_finalizacao_manual}<br>
                            <strong>Finalizado por:</strong> {ocorr.get('finalizado_por', '-')}<br>
                            <strong>Tempo de Permanência:</strong> {ocorr.get('permanencia_manual', '-')}<br>
                            <strong>Observações:</strong> {ocorr.get('observacoes', 'Sem observações.')}<br>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


# ======================
#     ABA 4 - USUÁRIOS
# ======================

# Função para alterar a senha
def alterar_senha(user_id, nova_senha):
    try:
        senha_hashed = hash_senha(nova_senha)  # Gera o hash da nova senha
        response = supabase.table("usuarios").update({"senha_hash": senha_hashed}).eq("user_id", user_id).execute()

        if response.data:
            st.success("Senha alterada com sucesso!")
        else:
            st.error("Erro ao alterar a senha. A resposta da API não contém dados.")
    except Exception as e:
        st.error(f"Erro ao atualizar a senha: {e}")

with aba4:
    #st.header("🔐 Gestão de Usuários")

    usuario_logado = st.session_state.username
    dados_usuario = supabase.table("usuarios").select("*").eq("nome_usuario", usuario_logado).execute().data[0]
    admin = dados_usuario["is_admin"]

    # ===============================
    #  AÇÕES ADMINISTRATIVAS (ADMIN)
    # ===============================
    if admin:
        st.subheader("🛠️ Administração de Usuários")

        aba_admin = st.radio("Escolha uma ação", ["Criar Usuário", "Alterar Senha de Usuário", "Deletar Usuário"], horizontal=True)

        # --- CRIAR USUÁRIO ---
        if aba_admin == "Criar Usuário":
            st.subheader("➕ Criar novo usuário")

            novo_usuario = st.text_input("Nome de usuário")
            nova_senha = st.text_input("Senha", type="password")
            confirmar_senha = st.text_input("Confirmar senha", type="password")
            is_admin = st.checkbox("Conceder privilégios de administrador")

            if st.button("Criar"):
                if not novo_usuario or not nova_senha or not confirmar_senha:
                    st.warning("Preencha todos os campos.")
                elif nova_senha != confirmar_senha:
                    st.error("As senhas não coincidem.")
                else:
                    # Verificar se já existe
                    usuario_existente = supabase.table("usuarios").select("nome_usuario").eq("nome_usuario", novo_usuario).execute().data
                    if usuario_existente:
                        st.error(f"O usuário '{novo_usuario}' já existe.")
                    else:
                        try:
                            senha_hashed = hash_senha(nova_senha)
                            # Insira o novo usuário sem especificar o user_id, assumindo que ele é gerado automaticamente
                            supabase.table("usuarios").insert({
                                "nome_usuario": novo_usuario,
                                "senha_hash": senha_hashed,
                                "is_admin": is_admin
                            }).execute()
                            st.success("✅ Usuário criado com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao criar usuário: {e}")

        # --- ALTERAR SENHA DE OUTRO USUÁRIO ---
        elif aba_admin == "Alterar Senha de Usuário":
            st.subheader("🔄 Alterar Senha de Outro Usuário")

            usuarios = supabase.table("usuarios").select("nome_usuario, user_id").execute().data
            nomes_usuarios = [u["nome_usuario"] for u in usuarios]

            usuario_alvo = st.selectbox("Escolha o usuário", nomes_usuarios)
            nova_senha = st.text_input("Nova senha", type="password")
            confirmar_senha = st.text_input("Confirmar nova senha", type="password")

            if st.button("Alterar Senha"):
                if nova_senha != confirmar_senha:
                    st.error("As senhas não coincidem.")
                elif not nova_senha:
                    st.error("A nova senha não pode estar vazia.")
                else:
                    user_id = next((u["user_id"] for u in usuarios if u["nome_usuario"] == usuario_alvo), None)
                    if user_id:
                        alterar_senha(user_id, nova_senha)

        # --- DELETAR USUÁRIO ---
        elif aba_admin == "Deletar Usuário":
            st.subheader("🗑️ Deletar Usuário")

            usuarios = supabase.table("usuarios").select("nome_usuario, user_id").execute().data
            nomes_usuarios = [u["nome_usuario"] for u in usuarios if u["nome_usuario"] != usuario_logado]

            usuario_alvo = st.selectbox("Selecione o usuário a ser deletado", nomes_usuarios)

            if st.button("Confirmar Deleção"):
                try:
                    user_id = next((u["user_id"] for u in usuarios if u["nome_usuario"] == usuario_alvo), None)
                    if user_id:
                        supabase.table("usuarios").delete().eq("user_id", user_id).execute()
                        st.success(f"Usuário '{usuario_alvo}' deletado com sucesso.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro ao deletar: {e}")

    # ===============================
    #  ALTERAR SENHA DO PRÓPRIO USUÁRIO
    # ===============================
    if not admin:  # Para usuários não administradores, mostra apenas a opção de "Alterar Minha Senha"
        st.subheader("🔒 Alterar Minha Senha")

        senha_atual = st.text_input("Senha Atual", type="password", key="senha_atual")
        nova_senha1 = st.text_input("Nova Senha", type="password", key="nova1")
        nova_senha2 = st.text_input("Confirmar Nova Senha", type="password", key="nova2")

        if st.button("Atualizar Minha Senha"):
            if not senha_atual or not nova_senha1 or not nova_senha2:
                st.error("Todos os campos são obrigatórios.")
            elif nova_senha1 != nova_senha2:
                st.error("As novas senhas não coincidem.")
            elif not verificar_senha(senha_atual, dados_usuario["senha_hash"]):
                st.error("Senha atual incorreta.")
            else:
                alterar_senha(dados_usuario["user_id"], nova_senha1)


# Função para alterar a senha
def alterar_senha(user_id, nova_senha):
    try:
        senha_hashed = hash_senha(nova_senha)  # Gera o hash da nova senha
        response = supabase.table("usuarios").update({"senha_hash": senha_hashed}).eq("user_id", user_id).execute()

        if response.data:
            st.success("Senha alterada com sucesso!")
        else:
            st.error("Erro ao alterar a senha. A resposta da API não contém dados.")
    except Exception as e:
        st.error(f"Erro ao atualizar a senha: {e}")


# ==============================================
# FUNÇÃO PARA ENVIAR EMAIL AO FINALIZAR NA ABA5
# ==============================================

# Função para enviar email de finalização
def enviar_email_finalizacao(ocorrencia):
    try:
        # Exemplo básico de e-mail - personalize conforme seu servidor SMTP
        remetente = "seuemail@dominio.com"
        senha = "sua_senha"
        destinatarios = ["destinatario1@dominio.com", "destinatario2@dominio.com"]

        assunto = f"Finalização do Ticket #{ocorrencia.get('numero_ticket', 'N/A')}"
        corpo = f"""
        O ticket #{ocorrencia.get('numero_ticket', 'N/A')} foi finalizado.

        Cliente: {ocorrencia.get('cliente', '-')}
        Tipo: {ocorrencia.get('tipo_de_ocorrencia', '-')}
        Complementar: {ocorrencia.get('complementar', '')}
        Finalizado por: {st.session_state.username}
        Data e hora de finalização: {ocorrencia.get('data_hora_finalizacao')}

        Obrigado.
        """

        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = ", ".join(destinatarios)
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'plain'))

        with smtplib.SMTP('smtp.dominio.com', 587) as servidor:
            servidor.starttls()
            servidor.login(remetente, senha)
            servidor.sendmail(remetente, destinatarios, msg.as_string())

    except Exception as e:
        st.warning(f"⚠️ Falha ao enviar e-mail de finalização: {e}")

# ===============================
#  ABA 5 - TICKETS POR FOCAL
# ===============================   

with aba5:
    st.header("Tickets por Focal")

    # Carrega todas as ocorrências abertas
    ocorrencias_abertas = carregar_ocorrencias_abertas()

    if not ocorrencias_abertas:
        st.info("ℹ️ Nenhuma ocorrência aberta no momento.")
    else:
        # Agrupar por focal
        focais = {}
        for ocorr in ocorrencias_abertas:
            focal = ocorr.get("focal", "Sem Focal")
            focais.setdefault(focal, []).append(ocorr)

        st.subheader("Selecione uma Focal para visualizar os tickets:")

        colunas = st.columns(4)
        for idx, (focal, tickets) in enumerate(focais.items()):
            with colunas[idx % 4]:
                btn_key = f"btn_focal_{idx}"
                if st.button(f"{focal} ({len(tickets)} tickets)", key=btn_key):
                    if st.session_state.get("focal_selecionada") == focal:
                        st.session_state.focal_selecionada = None  # desmarcar
                    else:
                        st.session_state.focal_selecionada = focal

        focal_atual = st.session_state.get("focal_selecionada")
        if focal_atual and focal_atual in focais:
            st.markdown(f"### 🎯 Tickets da focal: **{focal_atual}**")
            tickets_focal = focais[focal_atual]

            num_colunas = 3
            for i in range(0, len(tickets_focal), num_colunas):
                linha = st.columns(num_colunas)
                for j, ocorr in enumerate(tickets_focal[i:i+num_colunas]):
                    with linha[j]:
                        ticket_id = ocorr["id"]

                        # Processa data de abertura manual
                        data_formatada = "Data não informada"
                        status = "Data manual ausente"
                        cor = "gray"
                        try:
                            if ocorr.get("data_abertura_manual") and ocorr.get("hora_abertura_manual"):
                                data_manual_str = f"{ocorr['data_abertura_manual']} {ocorr['hora_abertura_manual']}"
                                dt_manual = datetime.strptime(data_manual_str, "%Y-%m-%d %H:%M:%S")
                                data_formatada = dt_manual.strftime("%d-%m-%Y %H:%M:%S")
                                data_abertura_iso = dt_manual.strftime("%Y-%m-%d %H:%M:%S")
                                status, cor = classificar_ocorrencia_por_tempo(data_abertura_iso)
                        except Exception:
                            pass

                        # Exibe informações do ticket
                        st.markdown(
                            f"""
                            <div style='background-color:{cor};padding:10px;border-radius:10px;color:white;
                            box-shadow: 0 4px 10px rgba(0,0,0,0.3);margin-bottom:10px;font-size:15px;'>
                            <strong>Ticket #:</strong> {ocorr.get('numero_ticket', 'N/A')}<br>
                            <strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;
                            border-radius:1px;color:white;'>{status}</span><br>
                            <strong>NF:</strong> {ocorr.get('nota_fiscal', '-')}<br>
                            <strong>Cliente:</strong> {ocorr.get('cliente', '-')}<br>
                            <strong>Destinatário:</strong> {ocorr.get('destinatario', '-')}<br>
                            <strong>Cidade:</strong> {ocorr.get('cidade', '-')}<br>
                            <strong>Motorista:</strong> {ocorr.get('motorista', '-')}<br>
                            <strong>Tipo:</strong> {ocorr.get('tipo_de_ocorrencia', '-')}<br>
                            <strong>Abertura Manual:</strong> {data_formatada}<br>
                            <strong>Observações:</strong> {ocorr.get('observacoes', 'Sem observações.')}<br>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        with st.expander("🔒 Finalizar Ocorrência"):
                            contato_motorista_key = f"contato_motorista_{ticket_id}"
                            contato_industria_key = f"contato_industria_{ticket_id}"

                            valor_motorista = bool(ocorr.get("contato_motorista", False))
                            valor_industria = bool(ocorr.get("contato_industria", False))

                            col1, col2 = st.columns(2)
                            with col1:
                                novo_motorista = st.checkbox("✔️ Contato com motorista",
                                                            key=contato_motorista_key,
                                                            value=valor_motorista)
                            with col2:
                                novo_industria = st.checkbox("✔️ Contato com indústria",
                                                            key=contato_industria_key,
                                                            value=valor_industria)

                            if novo_motorista != valor_motorista:
                                supabase.table("ocorrencias").update({
                                    "contato_motorista": novo_motorista
                                }).eq("id", ticket_id).execute()

                            if novo_industria != valor_industria:
                                supabase.table("ocorrencias").update({
                                    "contato_industria": novo_industria
                                }).eq("id", ticket_id).execute()

                            comp_key = f"complementar_final_{ticket_id}"
                            if comp_key not in st.session_state:
                                st.session_state[comp_key] = ""
                            complemento = st.text_area("Complementar (obrigatório)", key=comp_key)


                            data_final_key = f"data_final_{ticket_id}"
                            hora_final_key = f"hora_final_{ticket_id}"

                            if data_final_key not in st.session_state:
                                st.session_state[data_final_key] = data_atual
                            if hora_final_key not in st.session_state:
                                st.session_state[hora_final_key] = hora_atual

                            data_finalizacao_manual = st.text_input("Data Finalização (DD-MM-AAAA)", key=data_final_key)
                            hora_finalizacao_manual = st.text_input("Hora Finalização (HH:MM)", key=hora_final_key)

                            finalizar_btn_key = f"finalizar_{ticket_id}"
                            if st.button("Finalizar", key=finalizar_btn_key):
                                if not complemento.strip():
                                    st.error("❌ O campo 'Complementar' é obrigatório para finalizar a ocorrência.")
                                else:
                                    try:
                                        data_hora_finalizacao = datetime.strptime(
                                            f"{data_finalizacao_manual} {hora_finalizacao_manual}", "%d-%m-%Y %H:%M"
                                        ).replace(tzinfo=tz_sp)

                                        data_hora_abertura = datetime.strptime(
                                            f"{ocorr['data_abertura_manual']} {ocorr['hora_abertura_manual']}",
                                            "%Y-%m-%d %H:%M:%S"
                                        )

                                        if data_hora_finalizacao < data_hora_abertura:
                                            st.error("❌ Data/hora de finalização não pode ser menor que a data/hora de abertura.")
                                        else:
                                            delta = data_hora_finalizacao - data_hora_abertura
                                            total_segundos = int(delta.total_seconds())
                                            horas_totais = total_segundos // 3600
                                            minutos = (total_segundos % 3600) // 60
                                            permanencia_manual = f"{horas_totais:02d}:{minutos:02d}"

                                            hora_finalizacao_banco = f"{hora_finalizacao_manual}:00"

                                            supabase.table("ocorrencias").update({
                                            "status": "Finalizada",
                                            "complementar": complemento,
                                            "data_hora_finalizacao": data_hora_finalizacao.strftime("%Y-%m-%d %H:%M:%S"),
                                            "finalizado_por": st.session_state.username,
                                            "permanencia": permanencia_manual
                                        }).eq("id", ocorr["id"]).execute()

                                            # Envio de e-mail de finalização
                                            try:
                                                assunto_finalizacao = f"[Finalização de Ocorrência] Ticket {ocorr.get('numero_ticket')} - {ocorr.get('cliente')}"
                                                corpo_finalizacao = f"""
                                                    Prezados,

                                                    Informamos que a seguinte ocorrência foi finalizada com sucesso:

                                                    ➡️ Número do Ticket: {ocorr.get('numero_ticket')}
                                                    📄 Nota Fiscal: {ocorr.get('nota_fiscal')}
                                                    📍 Cidade: {ocorr.get('cidade')}
                                                    🚚 Motorista: {ocorr.get('motorista')}
                                                    📌 Tipo: {ocorr.get('tipo_de_ocorrencia')}
                                                    🕒 Abertura: {data_hora_abertura.strftime('%d-%m-%Y')} às {data_hora_abertura.strftime('%H:%M:%S')}
                                                    🕒 Finalização: {data_hora_finalizacao.strftime('%d-%m-%Y')} às {data_hora_finalizacao.strftime('%H:%M:%S')}
                                                    ⌛ Tempo de Permanência: {permanencia_manual}
                                                    

                                                    📝 Complementar:
                                                    {complemento or 'Sem detalhes adicionais.'}

                                                    Atenciosamente,
                                                    Equipe de Monitoramento
                                                """

                                                enviar_email_ocorrencia(
                                                    cliente_nome=ocorr.get("cliente"),
                                                    assunto=assunto_finalizacao,
                                                    corpo_email=corpo_finalizacao
                                                )
                                                st.toast(f"📧 E-mail de finalização enviado para {ocorr.get('cliente')}.")
                                            except Exception as e:
                                                st.warning(f"❌ Falha ao enviar e-mail de finalização para {ocorr.get('cliente')}: {e}")

                                            st.success("✅ Ocorrência finalizada com sucesso.")
                                            st.rerun()

                                    except Exception as e:
                                        st.error(f"❌ Erro ao finalizar ocorrência: {e}")