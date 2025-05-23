# -*- coding: utf-8 -*-
"""Refatorado: Otimizado para desempenho e fluidez, com upload de imagens."""

import streamlit as st
st.set_page_config(page_title="Entregas - Tempo de Permanência", layout="wide")

import pandas as pd
import os
import time
import uuid
import pytz
import bcrypt
import hashlib
import psycopg2 # Considerar remover se não usar mais conexão direta
import smtplib
import socket
import re # Importado para validação de email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from dateutil import parser
from psycopg2 import sql # Considerar remover se não usar mais conexão direta
from io import BytesIO
from dotenv import load_dotenv

from streamlit_autorefresh import st_autorefresh # Avaliar necessidade/intervalo
# import streamlit_authenticator as stauth # Não parece estar sendo usado
from streamlit_cookies_manager import EncryptedCookieManager

from supabase import create_client, Client as SupabaseClient, SupabaseStorageClient

# --- CARREGAR VARIÁVEIS DE AMBIENTE ---
load_dotenv()

# --- CONFIGURAÇÕES GERAIS ---
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "ticketclicklogtransportes@gmail.com")
EMAIL_SENHA = os.getenv("EMAIL_SENHA", "hlossktfkqlsxepo")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://vismjxhlsctehpvgmata.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZpc21qeGhsc2N0ZWhwdmdtYXRhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY1NzA4NTIsImV4cCI6MjA2MjE0Njg1Mn0.zTjSWenfuVJTIixq2RThSUpqcHGfZWP2xkFDU3USPb0")
COOKIE_PASSWORD = os.getenv("COOKIE_PASSWORD", "chave-muito-secreta-para-cookies")

# Configurar timeout para operações de socket
socket.setdefaulttimeout(20)  # Aumentado para 20 segundos

# --- DEFINIÇÃO DO FUSO HORÁRIO BRASILEIRO ---
FUSO_HORARIO_BRASIL = pytz.timezone("America/Sao_Paulo")

# --- SETUP DO COOKIE MANAGER ---
cookies = EncryptedCookieManager(
    prefix="tk_permanencia_",
    password=COOKIE_PASSWORD
)
if not cookies.ready():
    # Espera o cookie manager inicializar
    st.spinner("Inicializando...")
    time.sleep(1)
    st.rerun()

# --- CONEXÃO COM O SUPABASE ---
try:
    supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)
    storage: SupabaseStorageClient = supabase.storage
except Exception as e:
    st.error(f"Falha ao conectar com o Supabase: {e}")
    st.stop()

# --- FUNÇÕES DE UTILIDADE GERAL ---

def obter_data_hora_atual_brasil() -> datetime:
    """Retorna a data e hora atual no fuso horário do Brasil."""
    return datetime.now(FUSO_HORARIO_BRASIL)

def converter_para_fuso_brasil(data_hora: datetime) -> datetime:
    """Converte uma data/hora para o fuso horário do Brasil."""
    if data_hora.tzinfo is None:
        # Se não tiver fuso, assume UTC como padrão antes de converter
        data_hora = pytz.utc.localize(data_hora)
    return data_hora.astimezone(FUSO_HORARIO_BRASIL)

def calcular_diferenca_tempo(data_hora_inicial: datetime, data_hora_final: datetime = None) -> timedelta:
    """Calcula a diferença entre duas datas/horas, garantindo o mesmo fuso horário (Brasil)."""
    if data_hora_final is None:
        data_hora_final = obter_data_hora_atual_brasil()

    # Garante que ambas as datas estão no fuso horário do Brasil
    data_hora_inicial_br = converter_para_fuso_brasil(data_hora_inicial)
    data_hora_final_br = converter_para_fuso_brasil(data_hora_final)

    return data_hora_final_br - data_hora_inicial_br

def criar_datetime_manual(data_str: str, hora_str: str) -> datetime | None:
    """Cria um objeto datetime a partir de strings de data e hora, com fuso horário do Brasil."""
    try:
        # Tenta fazer o parse da data e hora
        data_hora_naive = datetime.strptime(f"{data_str} {hora_str}", "%Y-%m-%d %H:%M:%S")
        # Localiza para o fuso horário do Brasil
        return FUSO_HORARIO_BRASIL.localize(data_hora_naive)
    except ValueError as e:
        st.error(f"Formato inválido de data ou hora: {e}")
        return None
    except Exception as e:
        st.error(f"Erro ao criar datetime manual: {e}")
        return None

def validar_texto_maiusculo(texto: str) -> bool:
    """Verifica se o texto está em letras maiúsculas."""
    return texto == texto.upper()

def validar_email(email: str) -> bool:
    """Verifica se o e-mail tem um formato válido."""
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

def validar_emails_multiplos(emails: str) -> bool:
    """Verifica se múltiplos e-mails separados por ; têm formato válido."""
    if not emails:
        return True  # Campo vazio é válido

    lista_emails = emails.split(';')
    for email in lista_emails:
        email_strip = email.strip()
        if email_strip and not validar_email(email_strip):
            return False
    return True

# --- FUNÇÕES DE CACHE DE DADOS (SUPABASE) ---

# Cache para clientes (expira a cada 1 hora)
@st.cache_data(ttl=3600)
def carregar_clientes_supabase() -> pd.DataFrame:
    """Carrega dados de clientes do Supabase, otimizado com cache."""
    try:
        response = supabase.table("clientes").select("cliente, focal, enviar_para_email, email_copia, receber_emails").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            df = df.dropna(subset=["cliente"]) # Garante que cliente não seja nulo
            # Garante que colunas de email existam, mesmo que vazias
            for col in ["enviar_para_email", "email_copia"]:
                 if col not in df.columns:
                     df[col] = ""
            df.fillna({"enviar_para_email": "", "email_copia": ""}, inplace=True)
            return df
        else:
            return pd.DataFrame(columns=["cliente", "focal", "enviar_para_email", "email_copia", "receber_emails"])
    except Exception as e:
        st.error(f"Erro ao carregar clientes do Supabase: {e}")
        return pd.DataFrame(columns=["cliente", "focal", "enviar_para_email", "email_copia", "receber_emails"])

# Cache para cidades (expira a cada 6 horas)
@st.cache_data(ttl=21600)
def carregar_cidades_supabase() -> list:
    """Carrega a lista de cidades do Supabase, otimizado com cache."""
    try:
        response = supabase.table("cidades").select("cidade").execute()
        if response.data:
            cidades = [item["cidade"] for item in response.data if item.get("cidade")]
            return sorted(list(set(cidades))) # Remove duplicados e ordena
        else:
            return []
    except Exception as e:
        st.error(f"Erro ao carregar cidades do Supabase: {e}")
        return []

# Cache para motoristas (expira a cada 1 hora)
@st.cache_data(ttl=3600)
def carregar_motoristas_supabase() -> list:
    """Carrega a lista de motoristas do Supabase com paginação, otimizado com cache."""
    motoristas = []
    pagina = 0
    pagina_tamanho = 1000 # Limite do Supabase por requisição
    try:
        while True:
            resposta = supabase.table("motoristas") \
                .select("motorista") \
                .range(pagina * pagina_tamanho, (pagina + 1) * pagina_tamanho - 1) \
                .execute()

            dados = resposta.data
            if not dados:
                break # Sai do loop se não houver mais dados

            motoristas.extend([item["motorista"].strip() for item in dados if item.get("motorista")])
            pagina += 1

            # Segurança para evitar loop infinito (improvável, mas bom ter)
            if pagina > 100: # Limite de 100k motoristas
                 st.warning("Atingido limite de páginas ao carregar motoristas.")
                 break

        return sorted(list(set(motoristas))) # Remove duplicados e ordena

    except Exception as e:
        st.error(f"Erro ao carregar motoristas do Supabase: {e}")
        return []

# Cache para focais (usa dados dos clientes cacheados)
@st.cache_data(ttl=3600)
def carregar_focais_supabase() -> list:
    """Carrega a lista de focais a partir dos dados de clientes cacheados."""
    df_clientes = carregar_clientes_supabase() # Usa a função cacheada
    if not df_clientes.empty and "focal" in df_clientes.columns:
        focais = df_clientes["focal"].dropna().unique().tolist()
        return sorted([f for f in focais if f]) # Remove vazios e ordena
    return []

# Cache para configurações (expira a cada 15 minutos)
@st.cache_data(ttl=900)
def carregar_configuracao_supabase(chave: str, padrao: any = None) -> any:
    """Carrega um valor de configuração específico do Supabase."""
    try:
        response = supabase.table("configuracoes").select("valor").eq("chave", chave).limit(1).execute()
        if response.data:
            return response.data[0]["valor"]
        else:
            return padrao
    except Exception as e:
        st.error(f"Erro ao carregar configuração '{chave}': {e}")
        return padrao

# --- FUNÇÕES DE AUTENTICAÇÃO ---

def hash_senha(senha: str) -> str:
    """Gera o hash de uma senha usando bcrypt."""
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_senha(senha_fornecida: str, senha_hash: str) -> bool:
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    if senha_hash and isinstance(senha_hash, str):
        try:
            return bcrypt.checkpw(senha_fornecida.encode('utf-8'), senha_hash.encode('utf-8'))
        except ValueError:
             # Hash inválido ou incompatível
             return False
    return False

def autenticar_usuario(nome_usuario: str, senha: str) -> dict | None:
    """Autentica o usuário contra a tabela 'usuarios' no Supabase."""
    if not nome_usuario or not senha:
        return None
    try:
        response = supabase.table("usuarios").select("*").eq("nome_usuario", nome_usuario).limit(1).execute()
        if response.data:
            usuario = response.data[0]
            if verificar_senha(senha, usuario.get("senha_hash")):
                return usuario
        return None
    except Exception as e:
        st.error(f"Erro durante a autenticação: {e}")
        return None

def is_cookie_expired(expiry_time_str: str) -> bool:
    """Verifica se o timestamp do cookie expirou."""
    if not expiry_time_str:
        return True
    try:
        # Assume que o tempo está em UTC
        expiry_time = datetime.strptime(expiry_time_str, "%Y-%m-%d %H:%M:%S.%f%z")
        return datetime.now(timezone.utc) > expiry_time
    except ValueError:
        # Tenta formato sem microsegundos e timezone (menos preciso, fallback)
        try:
            expiry_time_naive = datetime.strptime(expiry_time_str, "%Y-%m-%d %H:%M:%S")
            # Assume UTC se não houver timezone info
            expiry_time = pytz.utc.localize(expiry_time_naive)
            return datetime.now(timezone.utc) > expiry_time
        except ValueError:
            st.warning(f"Formato de data/hora de expiração do cookie inválido: {expiry_time_str}")
            return True # Considera expirado se não conseguir parsear

def realizar_login(usuario_data: dict):
    """Define os cookies e o estado da sessão após login bem-sucedido."""
    st.session_state.login = True
    st.session_state.username = usuario_data["nome_usuario"]
    st.session_state.is_admin = usuario_data.get("is_admin", False)

    expiry_time = datetime.now(timezone.utc) + timedelta(hours=24)
    cookies["login"] = "True"
    cookies["username"] = st.session_state.username
    cookies["is_admin"] = str(st.session_state.is_admin)
    cookies["expiry_time"] = expiry_time.isoformat() # Usar ISO format com timezone
    cookies.save()
    st.rerun() # Rerun para atualizar a interface após login

def realizar_logout():
    """Limpa os cookies e o estado da sessão para logout."""
    # Limpa o estado da sessão relacionado ao login
    keys_to_delete = ["login", "username", "is_admin"]
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]

    # Limpa os cookies
    cookies["login"] = ""
    cookies["username"] = ""
    cookies["is_admin"] = ""
    cookies["expiry_time"] = ""
    cookies.save()
    st.rerun() # Rerun para voltar à tela de login

def interface_login():
    """Renderiza a interface de login ou exibe o status de logado."""
    # Tenta carregar dados do cookie
    login_cookie = cookies.get("login")
    username_cookie = cookies.get("username")
    is_admin_cookie = cookies.get("is_admin")
    expiry_time_cookie = cookies.get("expiry_time")

    # Verifica se já está logado via session_state ou cookie válido
    if st.session_state.get("login", False):
        # Já logado na sessão atual
        pass
    elif login_cookie == "True" and username_cookie and not is_cookie_expired(expiry_time_cookie):
        # Não está logado na sessão, mas tem cookie válido
        st.session_state.login = True
        st.session_state.username = username_cookie
        st.session_state.is_admin = is_admin_cookie == "True"
    else:
        # Não está logado nem tem cookie válido
        st.session_state.login = False

    # --- Renderiza a interface --- 
    col1_title, col2_title, col3_title = st.columns([1, 2, 1])
    with col2_title:
        st.markdown("<h1 style='text-align: center;'>📝 Entregas - Tempo de Permanência</h1>", unsafe_allow_html=True)
        st.markdown("--- ")

    if st.session_state.get("login"): # Verifica se está logado
        # Exibe mensagem de boas-vindas e botão de logout
        col1_logout, col2_logout = st.columns([0.85, 0.15])
        with col1_logout:
             st.markdown(f"👋 Bem-vindo(a), **{st.session_state.username}**!")
        with col2_logout:
            if st.button("🔒 Sair", key="logout_button_main", use_container_width=True):
                realizar_logout()
        st.markdown("--- ")
        return True # Indica que o usuário está logado

    else:
        # Exibe formulário de login
        with st.form("login_form"): 
            st.markdown("##### Login")
            username = st.text_input("Usuário", key="login_username")
            senha = st.text_input("Senha", type="password", key="login_password")
            submitted = st.form_submit_button("Entrar")

            if submitted:
                usuario_data = autenticar_usuario(username, senha)
                if usuario_data:
                    realizar_login(usuario_data)
                else:
                    st.error("🛑 Usuário ou senha incorretos.")
        return False # Indica que o usuário não está logado

# --- LÓGICA PRINCIPAL DA APLICAÇÃO ---

def main():
    """Função principal que executa a aplicação após o login."""

    # --- Inicialização do Estado da Sessão (se necessário) ---
    if "ocorrencias_abertas" not in st.session_state:
        st.session_state.ocorrencias_abertas = [] # Considerar carregar do DB aqui?
    if "ocorrencias_finalizadas" not in st.session_state:
        st.session_state.ocorrencias_finalizadas = [] # Considerar carregar do DB aqui?
    # if "historico_emails" not in st.session_state:
    #     st.session_state.historico_emails = [] # Remover se não usado
    if "focal_selecionado" not in st.session_state:
        st.session_state.focal_selecionado = None
    if "tempo_envio_email" not in st.session_state:
        # Carrega do banco ou usa padrão
        tempo_db = carregar_configuracao_supabase("tempo_envio_email", 30)
        try:
            st.session_state.tempo_envio_email = int(tempo_db)
        except (ValueError, TypeError):
            st.session_state.tempo_envio_email = 30 # Fallback para padrão

    # --- Carregar Dados Cacheados --- 
    df_clientes = carregar_clientes_supabase()
    clientes_lista = sorted(df_clientes["cliente"].unique().tolist()) if not df_clientes.empty else []
    cidades_lista = carregar_cidades_supabase()
    motoristas_lista = carregar_motoristas_supabase()
    focais_lista = carregar_focais_supabase()

    # Dicionários úteis (criados a partir do DataFrame cacheado)
    cliente_to_focal = dict(zip(df_clientes["cliente"], df_clientes["focal"])) if not df_clientes.empty else {}
    cliente_to_emails = {
        row["cliente"]: {
            "principal": row.get("enviar_para_email", ""),
            "copia": row.get("email_copia", "")
        }
        for _, row in df_clientes.iterrows()
    } if not df_clientes.empty else {}

    # --- Definição das Abas ---
    tabs_titulos = [
        "📝 Nova Ocorrência", 
        "📌 Ocorrências em Aberto", 
        "✅ Ocorrências Finalizadas", 
        "📝 Tickets por Focal", 
        "📊 Configurações", 
        "🔄 Cadastros", 
        "📊 Estatística"
    ]
    if st.session_state.get("is_admin", False):
        tabs_titulos.insert(5, "📧 Notificações por E-mail") # Adiciona aba de Notificações para admin

    tabs = st.tabs(tabs_titulos)

    # Mapeamento de títulos para índices para facilitar
    tab_map = {title: i for i, title in enumerate(tabs_titulos)}

    # --- ABA: Nova Ocorrência ---
    with tabs[tab_map["📝 Nova Ocorrência"]]:
        renderizar_aba_nova_ocorrencia(clientes_lista, cidades_lista, motoristas_lista, cliente_to_focal)

    # --- ABA: Ocorrências em Aberto ---
    with tabs[tab_map["📌 Ocorrências em Aberto"]]:
        renderizar_aba_ocorrencias_abertas()

    # --- ABA: Ocorrências Finalizadas ---
    with tabs[tab_map["✅ Ocorrências Finalizadas"]]:
        renderizar_aba_ocorrencias_finalizadas()

    # --- ABA: Tickets por Focal ---
    with tabs[tab_map["📝 Tickets por Focal"]]:
        renderizar_aba_tickets_por_focal(focais_lista)

    # --- ABA: Configurações ---
    with tabs[tab_map["📊 Configurações"]]:
        renderizar_aba_configuracoes()

    # --- ABA: Notificações por E-mail (Admin) ---
    if st.session_state.get("is_admin", False):
        with tabs[tab_map["📧 Notificações por E-mail"]]:
            renderizar_aba_notificacoes_email()

    # --- ABA: Cadastros ---
    with tabs[tab_map["🔄 Cadastros"]]:
        renderizar_aba_cadastros(clientes_lista, cidades_lista, motoristas_lista)

    # --- ABA: Estatística ---
    with tabs[tab_map["📊 Estatística"]]:
        renderizar_aba_estatistica()

# --- FUNÇÕES DE RENDERIZAÇÃO DAS ABAS (a serem implementadas/refatoradas) ---

def renderizar_aba_nova_ocorrencia(clientes: list, cidades: list, motoristas: list, cliente_focal_map: dict):
    st.header("Registar Nova Ocorrência")

    # Usar st.form para agrupar inputs e submeter de uma vez
    with st.form("form_nova_ocorrencia", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            nf = st.text_input("Nota Fiscal*", key="nf_input", help="Digite apenas números.")
            destinatario = st.text_input("Destinatário*", key="dest_input")

            # Seleção de Cliente com opção "Outro"
            cliente_selecionado = st.selectbox("Cliente*", options=[""] + clientes + ["Outro (digitar)"], index=0, key="cliente_select")
            cliente_manual = st.text_input("Nome do Cliente (se Outro)*", key="cliente_manual_input", disabled=(cliente_selecionado != "Outro (digitar)"))
            cliente_final = cliente_manual if cliente_selecionado == "Outro (digitar)" else cliente_selecionado

            # Atualiza Focal automaticamente
            focal_responsavel = cliente_focal_map.get(cliente_final, "")
            st.text_input("Focal Responsável", value=focal_responsavel, key="focal_display", disabled=True)

            # Seleção de Cidade com opção "Outro"
            cidade_selecionada = st.selectbox("Cidade*", options=[""] + cidades + ["Outro (digitar)"], index=0, key="cidade_select")
            cidade_manual = st.text_input("Nome da Cidade (se Outro)*", key="cidade_manual_input", disabled=(cidade_selecionada != "Outro (digitar)"))
            cidade_final = cidade_manual if cidade_selecionada == "Outro (digitar)" else cidade_selecionada

        with col2:
            # Seleção de Motorista com opção "Outro"
            motorista_selecionado = st.selectbox("Motorista*", options=[""] + motoristas + ["Outro (digitar)"], index=0, key="motorista_select")
            motorista_manual = st.text_input("Nome do Motorista (se Outro)*", key="motorista_manual_input", disabled=(motorista_selecionado != "Outro (digitar)"))
            motorista_final = motorista_manual if motorista_selecionado == "Outro (digitar)" else motorista_selecionado

            tipo_ocorrencia = st.multiselect("Tipo de Ocorrência*", options=["Chegada no Local", "Pedido Bloqueado", "Aguardando Descarga", "Divergência"], key="tipo_multi")
            observacoes = st.text_area("Observações", key="obs_text")

            # Inputs manuais de Data e Hora
            st.markdown("**Data e Hora da Ocorrência***")
            col_data, col_hora = st.columns(2)
            with col_data:
                data_abertura_manual = st.date_input("Data", value=datetime.now(FUSO_HORARIO_BRASIL).date(), key="data_manual", format="DD/MM/YYYY")
            with col_hora:
                hora_abertura_manual = st.time_input("Hora", value=datetime.now(FUSO_HORARIO_BRASIL).time(), key="hora_manual", step=60)

            # Responsável (usuário logado)
            responsavel = st.session_state.get("username", "Desconhecido")
            st.text_input("Registado por", value=responsavel, disabled=True)
            
            # --- Upload de Imagens ---
            st.markdown("**Anexar Imagens (Opcional)**")
            img1 = st.file_uploader("Imagem 1", type=["png", "jpg", "jpeg"], key="img_upload_1")
            img2 = st.file_uploader("Imagem 2", type=["png", "jpg", "jpeg"], key="img_upload_2")
            imagens_para_upload = [img for img in [img1, img2] if img is not None]

        # Botão de submissão do formulário
        submitted = st.form_submit_button("Adicionar Ocorrência")

        if submitted:
            # Validações
            erros = []
            if not nf or not nf.isdigit():
                erros.append("Nota Fiscal (deve conter apenas números)")
            if not destinatario:
                erros.append("Destinatário")
            if not cliente_final:
                erros.append("Cliente")
            # Focal é derivado, não precisa validar diretamente
            if not cidade_final:
                erros.append("Cidade")
            if not motorista_final:
                erros.append("Motorista")
            if not tipo_ocorrencia:
                erros.append("Tipo de Ocorrência")
            if data_abertura_manual is None or hora_abertura_manual is None:
                 erros.append("Data/Hora da Ocorrência")

            if erros:
                st.error(f"❌ Por favor, preencha os campos obrigatórios corretamente: {', '.join(erros)}")
            else:
                # Processar submissão
                try:
                    # Formatar data e hora manual para strings YYYY-MM-DD e HH:MM:SS
                    data_manual_str = data_abertura_manual.strftime("%Y-%m-%d")
                    hora_manual_str = hora_abertura_manual.strftime("%H:%M:%S")

                    # Criar datetime combinado para timestamp
                    datetime_manual = criar_datetime_manual(data_manual_str, hora_manual_str)
                    if datetime_manual is None:
                         st.error("Erro ao formatar data/hora manual.")
                         return # Aborta se data/hora inválida

                    timestamp_iso = datetime_manual.isoformat()

                    # Gerar ID único
                    ocorrencia_id = str(uuid.uuid4())
                    
                    # --- Upload das Imagens para Supabase Storage ---
                    urls_imagens = []
                    if imagens_para_upload:
                        st.info("A fazer upload das imagens...")
                        for idx, img_file in enumerate(imagens_para_upload):
                            try:
                                # Nome do ficheiro no storage: ocorrencias/{ocorrencia_id}/{timestamp}_{idx}.ext
                                timestamp_upload = datetime.now().strftime("%Y%m%d%H%M%S")
                                file_ext = os.path.splitext(img_file.name)[1]
                                file_path = f"ocorrencias/{ocorrencia_id}/{timestamp_upload}_{idx}{file_ext}"
                                
                                # Faz o upload
                                storage.from_("imagens-ocorrencias").upload(file=img_file.getvalue(), path=file_path, file_options={"content-type": img_file.type})
                                
                                # Obtém a URL pública (ou assinada, dependendo da config do bucket)
                                # Nota: Verifique se o bucket "imagens-ocorrencias" existe e tem permissões adequadas
                                res_url = storage.from_("imagens-ocorrencias").get_public_url(file_path)
                                urls_imagens.append(res_url)
                                st.write(f"Imagem {idx+1} enviada: {res_url}") # Feedback
                            except Exception as upload_error:
                                st.error(f"Erro ao fazer upload da imagem {idx+1}: {upload_error}")
                                # Decide se continua ou aborta
                                # return 

                    # Montar dados da ocorrência
                    nova_ocorrencia_dados = {
                        "id": ocorrencia_id,
                        "nota_fiscal": nf,
                        "cliente": cliente_final,
                        "focal": focal_responsavel,
                        "destinatario": destinatario,
                        "cidade": cidade_final,
                        "motorista": motorista_final,
                        "tipo_de_ocorrencia": ", ".join(tipo_ocorrencia),
                        "observacoes": observacoes,
                        "responsavel": responsavel,
                        "status": "Aberta",
                        "data_hora_abertura": f"{data_manual_str} {hora_manual_str}", # String simples para exibição talvez?
                        "abertura_timestamp": timestamp_iso, # Timestamp com fuso para cálculos
                        "permanencia": "", # Calculado ao finalizar
                        "complementar": "", # Preenchido ao finalizar
                        "data_abertura_manual": data_manual_str,
                        "hora_abertura_manual": hora_manual_str,
                        "email_abertura_enviado": False,
                        "email_finalizacao_enviado": False,
                        "url_imagem1": urls_imagens[0] if len(urls_imagens) > 0 else None,
                        "url_imagem2": urls_imagens[1] if len(urls_imagens) > 1 else None,
                    }

                    # Inserir no Supabase
                    response = supabase.table("ocorrencias").insert(nova_ocorrencia_dados).execute()

                    if response.data:
                        st.success("✅ Ocorrência registada com sucesso!")
                        # Limpar estado local ou forçar recarregamento dos dados na próxima aba
                        # st.session_state.ocorrencias_abertas.append(nova_ocorrencia_dados) # Evitar adicionar localmente, recarregar do DB
                        st.cache_data.clear() # Limpa o cache de dados gerais, pode ser específico se necessário
                        # Poderia usar st.experimental_rerun() aqui, mas o clear_on_submit=True já ajuda
                    else:
                        st.error(f"Erro ao salvar ocorrência no Supabase: {response.error}")

                except Exception as e:
                    st.error(f"Ocorreu um erro inesperado ao adicionar a ocorrência: {e}")

def renderizar_aba_ocorrencias_abertas():
    st.header("Ocorrências em Aberto")
    # Adicionar lógica para buscar e exibir ocorrências abertas do Supabase
    # Usar st.dataframe ou criar layout customizado
    # Adicionar botões para finalizar ocorrência
    st.write("Conteúdo da Aba Ocorrências em Aberto")
    # Exemplo de busca (precisa adaptar colunas e filtros)
    try:
        response = supabase.table("ocorrencias").select("*, clientes(focal)").eq("status", "Aberta").order("abertura_timestamp", desc=True).execute()
        if response.data:
            df_abertas = pd.DataFrame(response.data)
            # Processar/formatar o dataframe para exibição
            st.dataframe(df_abertas, use_container_width=True)
        else:
            st.info("Nenhuma ocorrência em aberto encontrada.")
    except Exception as e:
        st.error(f"Erro ao carregar ocorrências abertas: {e}")

def renderizar_aba_ocorrencias_finalizadas():
    st.header("Ocorrências Finalizadas")
    # Adicionar lógica para buscar e exibir ocorrências finalizadas
    st.write("Conteúdo da Aba Ocorrências Finalizadas")
    try:
        response = supabase.table("ocorrencias").select("*, clientes(focal)").eq("status", "Finalizada").order("data_hora_finalizacao", desc=True).limit(100).execute() # Limitar resultados iniciais
        if response.data:
            df_finalizadas = pd.DataFrame(response.data)
            # Processar/formatar o dataframe
            st.dataframe(df_finalizadas, use_container_width=True)
        else:
            st.info("Nenhuma ocorrência finalizada encontrada.")
    except Exception as e:
        st.error(f"Erro ao carregar ocorrências finalizadas: {e}")

def renderizar_aba_tickets_por_focal(focais: list):
    st.header("Tickets por Focal")
    focal_selecionado = st.selectbox("Selecione o Focal", options=["Todos"] + focais)
    st.write(f"Exibindo tickets para: {focal_selecionado}")
    # Adicionar lógica para filtrar e exibir tickets por focal

def renderizar_aba_configuracoes():
    st.header("Configurações")
    st.write("Ajustes gerais da aplicação.")
    
    tempo_atual = st.session_state.get("tempo_envio_email", 30)
    novo_tempo = st.number_input(
        "Tempo (minutos) para notificação de e-mail (ocorrência aberta)", 
        min_value=5, 
        max_value=120, 
        value=tempo_atual, 
        step=5
    )
    
    if st.button("Salvar Tempo de Envio"):
        if novo_tempo != tempo_atual:
            try:
                # Atualiza no banco de dados
                response = supabase.table("configuracoes").upsert({
                    "chave": "tempo_envio_email",
                    "valor": str(novo_tempo)
                }, on_conflict="chave").execute() # Usa upsert
                
                if response.data:
                    st.session_state.tempo_envio_email = novo_tempo
                    st.cache_data.clear() # Limpa cache para carregar novo valor
                    st.success(f"Tempo de envio atualizado para {novo_tempo} minutos!")
                    time.sleep(1.5) # Pequena pausa para o usuário ver a mensagem
                    st.rerun() # Recarrega para refletir em toda a app
                else:
                     st.error(f"Erro ao salvar configuração no banco: {response.error}")
            except Exception as e:
                st.error(f"Erro ao atualizar tempo de envio: {e}")
        else:
            st.info("O tempo selecionado já é o atual.")

def renderizar_aba_notificacoes_email():
    st.header("Notificações por E-mail (Admin)")
    st.write("Gerenciamento e histórico de e-mails enviados.")
    # Adicionar lógica para exibir histórico, reenviar e-mails, etc.

def renderizar_aba_cadastros(clientes_lista, cidades_lista, motoristas_lista):
    st.header("Cadastros")
    
    tab_cli, tab_cid, tab_mot = st.tabs(["Clientes", "Cidades", "Motoristas"])
    
    with tab_cli:
        st.subheader("Gerenciar Clientes")
        # Adicionar formulário para adicionar/editar clientes
        st.write("Clientes existentes:", clientes_lista)
        
    with tab_cid:
        st.subheader("Gerenciar Cidades")
        # Adicionar formulário para adicionar/editar cidades
        st.write("Cidades existentes:", cidades_lista)

    with tab_mot:
        st.subheader("Gerenciar Motoristas")
        # Adicionar formulário para adicionar/editar motoristas
        st.write("Motoristas existentes:", len(motoristas_lista))
        # st.dataframe(pd.DataFrame(motoristas_lista, columns=["Motorista"])) # Descomentar se quiser listar

def renderizar_aba_estatistica():
    st.header("Estatísticas")
    st.write("Gráficos e dados sobre as ocorrências.")
    # Adicionar lógica para gerar gráficos (ex: ocorrências por dia/cliente/tipo)

# --- PONTO DE ENTRADA DA APLICAÇÃO ---
if __name__ == "__main__":
    # 1. Verifica se o usuário está logado
    if interface_login():
        # 2. Se logado, executa a aplicação principal
        main()
    # Se não estiver logado, interface_login() cuida de exibir o formulário
    # e interrompe a execução se o login falhar.

