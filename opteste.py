# funcionando 100% sem envio de e-mail

# versão liberada para usuário 15-05 


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
from datetime import datetime, timedelta, timezone
from datetime import date, datetime, time
from dateutil import parser
from psycopg2 import sql
from io import BytesIO
from datetime import datetime, date, time
import pytz
import uuid
import time  # para time.sleep
from dateutil import parser  # para parse da data na finalização

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


    #- -- INICIALIZAÇÃO DE SESSÃO ---
if "ocorrencias_abertas" not in st.session_state:
    st.session_state.ocorrencias_abertas = []

if "ocorrencias_finalizadas" not in st.session_state:
    st.session_state.ocorrencias_finalizadas = []

# --- ABA NOVA OCORRÊNCIA ---
aba1, aba2, aba3, aba5, aba6, aba4 = st.tabs([
    "📝 Nova Ocorrência", 
    "📌 Ocorrências em Aberto", 
    "✅ Ocorrências Finalizadas", 
    "📝 Tickets por Focal",
    "📊 Estatísticas de Tickets Finalizados",  # vírgula aqui
    "🛠️ Configurações"
])

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
        "data_abertura_manual": dados["data_abertura_manual"],
        "hora_abertura_manual": dados["hora_abertura_manual"],
        "permanencia_manual": dados.get("permanencia_manual", ""),
        "complementar": dados["complementar"]
    }]).execute()
    return response


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
            data_abertura_manual = st.date_input("Data de Abertura (manual)", value=datetime.now().date())
            hora_abertura_manual = st.time_input("Hora de Abertura (manual)", value=datetime.now().time())

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
                    "data_abertura_manual": data_abertura_manual.strftime("%Y-%m-%d"),
                    "hora_abertura_manual": hora_abertura_manual.strftime("%H:%M:%S"),
                    "permanencia_manual": "",                   # será calculado na finalização
                    "permanencia": "",                         # Novo campo para cálculo na finalização
                     "complementar": ""
                     
                }

                # Inserção no banco de dados
                response = inserir_ocorrencia_supabase(nova_ocorrencia)
                
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
                else:
                    st.error(f"Erro ao salvar ocorrência no Supabase: {response.error}")


# Função de classificação
from datetime import datetime
import pytz

# =========================
#    FUNÇÃO CLASSIFICAÇÃO
# =========================
def classificar_ocorrencia_por_tempo(data_abertura_str):
    tz_sp = pytz.timezone("America/Sao_Paulo")

    try:
        # Garante que a string esteja no formato correto
        data_abertura_str = data_abertura_str.replace('T', ' ')
        data_abertura_naive = datetime.strptime(data_abertura_str, "%Y-%m-%d %H:%M:%S")

        # Aplica o fuso horário de São Paulo
        data_abertura = tz_sp.localize(data_abertura_naive)

    except Exception as e:
        print(f"Erro ao converter data: {e}")
        return "Erro", "gray"

    agora = datetime.now(tz_sp)  # aware
    tempo_decorrido = (agora - data_abertura).total_seconds() / 60  # minutos

    if tempo_decorrido < 15:
        return "🟢 Normal", "#2ecc71"
    elif tempo_decorrido < 30:
        return "🟡 Alerta", "#f1c40f"
    elif tempo_decorrido < 45:
        return "🔴 Crítico", "#e74c3c"
    elif tempo_decorrido < 60:
        return "🔴 Crítico", "#e74c3c"
    else:
        return "🚨 +60 min", "#c0392b"


# Função para carregar ocorrências abertas
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
from datetime import datetime

def salvar_ocorrencia_finalizada(ocorr, status, data_final_manual=None, hora_final_manual=None):
    try:
        # Parse data de abertura (como já feito)
        if isinstance(ocorr.get("Data/Hora Abertura"), str):
            data_hora_abertura = parser.parse(ocorr["Data/Hora Abertura"])
        else:
            data_hora_abertura = ocorr["Data/Hora Abertura"]

        # Se vier data/hora manual da finalização, construir o datetime
        if data_final_manual and hora_final_manual:
            data_hora_finalizacao = datetime.strptime(f"{data_final_manual} {hora_final_manual}", "%Y-%m-%d %H:%M:%S")
        else:
            # fallback para agora
            data_hora_finalizacao = datetime.now()

        # Calcular permanência
        permanencia_timedelta = data_hora_finalizacao - data_hora_abertura
        total_segundos = int(permanencia_timedelta.total_seconds())
        dias = total_segundos // 86400
        horas = (total_segundos % 86400) // 3600
        minutos = (total_segundos % 3600) // 60
        tempo_permanencia_formatado = f"{dias}d {horas}h {minutos}min"

        # Atualizar banco com data/hora manual e permanência
        response = supabase.table("ocorrencias").update({
            "data_hora_finalizacao": data_hora_finalizacao.strftime("%Y-%m-%d %H:%M:%S"),
            "finalizado_por": ocorr["Finalizado por"],
            "complementar": ocorr["Complementar"],
            "permanencia": tempo_permanencia_formatado,
            "status": "Finalizada"
        }).eq("id", ocorr["ID"]).execute()

        st.write("Resposta Supabase:", response)

        st.session_state["mensagem_sucesso_finalizacao"] = True

    except Exception as e:
        st.error(f"Erro ao salvar no banco de dados: {e}")
        st.session_state["mensagem_sucesso_finalizacao"] = False

    # Exibe mensagem de sucesso
    if st.session_state.get("mensagem_sucesso_finalizacao"):
        sucesso_msg = st.empty()
        sucesso_msg.success("✅ Ocorrência finalizada com sucesso!")
        time.sleep(2)
        sucesso_msg.empty()
        del st.session_state["mensagem_sucesso_finalizacao"]

# =========================
#     ABA 2 - EM ABERTO
# =========================
with aba2:
    st.header("Ocorrências em Aberto")

    ocorrencias_abertas = carregar_ocorrencias_abertas()

    if not ocorrencias_abertas:
        st.info("ℹ️ Nenhuma ocorrência aberta no momento.")
    else:
        num_colunas = 4  # Garante que sempre teremos 4 colunas
        colunas = st.columns(num_colunas)
        st_autorefresh(interval=40000, key="ocorrencias_abertas_refresh")

        for idx, ocorr in enumerate(ocorrencias_abertas):
            # Pegando a data diretamente do campo 'data_hora_abertura' retornado do Supabase
            data_abertura_data = ocorr.get("data_abertura_manual")
            data_abertura_hora = ocorr.get("hora_abertura_manual")
            if data_abertura_data and data_abertura_hora:
                data_abertura_str = f"{data_abertura_data} {data_abertura_hora}"
            else:
                st.error("Data ou hora de abertura ausente.")
                data_abertura_str = None

            try:
                if not data_abertura_str:
                    raise ValueError("Data de abertura ausente.")
                
                # Converte string mm-dd-yyyy HH:MM:SS para datetime
                data_abertura_str = data_abertura_str.replace('T', ' ')
                data_abertura = parser.parse(data_abertura_str)
                
                # Converte para string no formato brasileiro dd-mm-yyyy HH:MM:SS
                data_abertura_formatada = data_abertura.strftime("%d-%m-%Y %H:%M:%S")

            except Exception as e:
                st.error(f"Erro ao processar a data de abertura: {e}")
                data_abertura_formatada = "Data inválida"

            # Classificando o status e a cor com base no tempo de abertura
            status, cor = classificar_ocorrencia_por_tempo(data_abertura_str)

            try:
                data_abertura_str = data_abertura_str.replace('T', ' ')
                data_abertura = parser.parse(data_abertura_str)
                data_formatada = data_abertura.strftime('%d-%m-%Y %H:%M:%S')
            except Exception as e:
                st.error(f"Erro ao processar ocorrência (NF: {ocorr.get('nota_fiscal', '-')}) — {e}")
                continue

            # Preparar keys para session_state, com padrão _manual
            safe_idx = f"{idx}_{ocorr.get('nota_fiscal', '')}"

            data_abertura_manual_key = f"data_abertura_manual_{safe_idx}"
            hora_abertura_manual_key = f"hora_abertura_manual_{safe_idx}"
            data_finalizacao_manual_key = f"data_finalizacao_manual_{safe_idx}"
            hora_finalizacao_manual_key = f"hora_finalizacao_manual_{safe_idx}"
            complemento_key = f"complemento_final_{safe_idx}"

            # Inicializar session_state para data/hora abertura, se não existir
            if data_abertura_manual_key not in st.session_state:
                st.session_state[data_abertura_manual_key] = data_abertura.date()
            if hora_abertura_manual_key not in st.session_state:
                st.session_state[hora_abertura_manual_key] = data_abertura.time()

            # Inicializar session_state para finalização e complemento
            if data_finalizacao_manual_key not in st.session_state:
                st.session_state[data_finalizacao_manual_key] = date.today()
            if hora_finalizacao_manual_key not in st.session_state:
                st.session_state[hora_finalizacao_manual_key] = datetime.now().time()
            if complemento_key not in st.session_state:
                st.session_state[complemento_key] = ""

            with colunas[idx % num_colunas]:
                with st.container():
                    st.markdown(
                        f"""
                        <div style='background-color:{cor};padding:10px;border-radius:10px;color:white;
                                    box-shadow: 0 4px 10px rgba(0,0,0,0.3);margin-bottom:5px;min-height:250px;
                                    font-size:15px;'>
                            <strong>Ticket #:</strong> {ocorr.get('numero_ticket') if ocorr.get('numero_ticket') else 'N/A'}<br>
                            <strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;
                                            border-radius:1px;color:white;'>{status}</span><br>
                            <strong>NF:</strong> {ocorr.get('nota_fiscal', '-')}<br>
                            <strong>Cliente:</strong> {ocorr.get('cliente', '-')}<br>
                            <strong>Destinatário:</strong> {ocorr.get('destinatario', '-')}<br>
                            <strong>Focal:</strong> {ocorr.get('focal', '-')}<br>
                            <strong>Cidade:</strong> {ocorr.get('cidade', '-')}<br>
                            <strong>Motorista:</strong> {ocorr.get('motorista', '-')}<br>
                            <strong>Tipo:</strong> {ocorr.get('tipo_de_ocorrencia', '-')}<br>
                            <strong>Aberto por:</strong> {ocorr.get('responsavel', '-')}<br>
                            <strong>Data/Hora Abertura:</strong> {data_formatada}<br>
                            <strong>Observações:</strong> {ocorr.get('observacoes', 'Sem observações.')}<br>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Expander para finalizar
                    with st.expander("Finalizar Ocorrência"):
                        complemento = st.text_area(
                            "Complementar",
                            key=complemento_key,
                            value=st.session_state[complemento_key]
                        )

                        data_finalizacao_manual = st.date_input(
                            "Data da Finalização",
                            value=st.session_state[data_finalizacao_manual_key],
                            key=data_finalizacao_manual_key
                        )

                        hora_finalizacao_manual = st.time_input(
                            "Hora da Finalização",
                            value=st.session_state[hora_finalizacao_manual_key],
                            key=hora_finalizacao_manual_key
                        )

                        finalizar_disabled = not complemento.strip()

                        if st.button("Finalizar", key=f"finalizar_{safe_idx}", disabled=finalizar_disabled):
                            if finalizar_disabled:
                                st.error("❌ O campo 'Complementar' é obrigatório para finalizar a ocorrência.")
                            else:
                                # Construir datetime de finalização combinando data e hora manuais
                                dt_finalizacao = datetime.combine(data_finalizacao_manual, hora_finalizacao_manual)
                                dt_finalizacao = dt_finalizacao.replace(tzinfo=None)

                                # Atualiza a ocorrência com as informações de finalização
                                ocorr["Complementar"] = complemento
                                ocorr["Data/Hora Finalização"] = dt_finalizacao.strftime("%d/%m/%Y %H:%M:%S")
                                ocorr["Status"] = status
                                ocorr["Cor"] = cor
                                ocorr["Finalizada"] = True
                                ocorr["Finalizado por"] = st.session_state.username

                                # Calcular tempo de permanência usando timestamp de abertura e manual finalização
                                permanencia_manual = "N/A"
                                try:
                                    if "abertura_timestamp" in ocorr and ocorr["abertura_timestamp"]:
                                        abertura_ts = parser.parse(ocorr["abertura_timestamp"]).replace(tzinfo=None)
                                        delta = dt_finalizacao - abertura_ts
                                        horas = str(delta.seconds // 3600).zfill(2)
                                        minutos = str((delta.seconds // 60) % 60).zfill(2)
                                        segundos = str(delta.seconds % 60).zfill(2)
                                        permanencia_manual = f"{horas}:{minutos}:{segundos}"
                                except Exception as e:
                                    st.error(f"Erro ao calcular permanência: {e}")

                                # Atualiza no banco de dados
                                response = supabase.table("ocorrencias").update({
                                    "data_hora_finalizacao": dt_finalizacao.strftime("%Y-%m-%d %H:%M:%S"),
                                    "finalizado_por": ocorr["Finalizado por"],
                                    "complementar": ocorr["Complementar"],
                                    "status": "Finalizada",
                                    "permanencia": permanencia_manual,
                                }).eq("id", ocorr["id"]).execute()

                                if response and response.data:
                                    st.session_state.ocorrencias_finalizadas.append(ocorr)
                                    st.success("✅ Ocorrência finalizada com sucesso!")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("Erro ao salvar a finalização no banco de dados.")



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
        # Layout: filtro à esquerda e botão à extrema direita
        col_filtro, col_vazio, col_botao = st.columns([2, 6, 1])  # Ajuste as proporções conforme necessário

        with col_filtro:
            filtro_nf = st.text_input("🔎 Pesquisar por NF:", "", max_chars=10)

        with col_botao:
            try:
                df = pd.DataFrame(ocorrencias_finalizadas)
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Finalizadas')
                st.download_button(
                    label="⬇️ Exportar",
                    data=output.getvalue(),
                    file_name="ocorrencias_finalizadas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except Exception as e:
                st.error(f"Erro ao exportar para Excel: {e}")



        # --- Filtrar ocorrências finalizadas pela NF (caso o usuário digite algo) ---
        if filtro_nf:
            ocorrencias_filtradas = [
                ocorr for ocorr in ocorrencias_finalizadas
                if filtro_nf.lower() in str(ocorr.get("nota_fiscal", "")).lower()
            ]
        else:
            ocorrencias_filtradas = ocorrencias_finalizadas

        # Exibir cards em colunas
        num_colunas = 4
        colunas = st.columns(num_colunas)

for idx, ocorr in enumerate(ocorrencias_filtradas):
    try:
        # Pegando diretamente os campos manuais
        data_abertura_manual = ocorr.get("data_abertura_manual", "-")
        hora_abertura_manual = ocorr.get("hora_abertura_manual", "-")
        data_finalizacao_manual = ocorr.get("data_finalizacao_manual", "-")
        hora_finalizacao_manual = ocorr.get("hora_finalizacao_manual", "-")
        permanencia_manual = ocorr.get("permanencia_manual", "Não disponível")

        status = ocorr.get("status", "Finalizada")
        cor = ocorr.get("cor", "#34495e")

    except Exception as e:
        st.error(f"Erro ao processar ocorrência (NF {ocorr.get('nota_fiscal', '-')}) — {e}")
        data_abertura_manual = hora_abertura_manual = data_finalizacao_manual = hora_finalizacao_manual = permanencia_manual = "-"
        status = "Erro"
        cor = "#7f8c8d"

    with colunas[idx % num_colunas]:
        with st.container():
            st.markdown(
                f"""
                <div style='background-color:{cor};padding:10px;border-radius:10px;color:white;
                box-shadow: 0 4px 10px rgba(0,0,0,0.3);margin-bottom:5px;min-height:250px;font-size:15px;'>
                    <strong>Ticket #:</strong> {ocorr.get('numero_ticket', 'N/A')}<br>
                    <strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;border-radius:1px;color:white;'>{status}</span><br>
                    <strong>NF:</strong> {ocorr.get('nota_fiscal', '-')}<br>
                    <strong>Cliente:</strong> {ocorr.get('cliente', '-')}<br>
                    <strong>Destinatário:</strong> {ocorr.get('destinatario', '-')}<br>
                    <strong>Cidade:</strong> {ocorr.get('cidade', '-')}<br>
                    <strong>Motorista:</strong> {ocorr.get('motorista', '-')}<br>
                    <strong>Tipo:</strong> {ocorr.get('tipo_de_ocorrencia', '-')}<br>
                    <strong>Aberto por:</strong> {ocorr.get('responsavel', '-')}<br>
                    <strong>Data Abertura Manual:</strong> {data_abertura_manual} {hora_abertura_manual}<br>
                    <strong>Data Finalização Manual:</strong> {data_finalizacao_manual} {hora_finalizacao_manual}<br>
                    <strong>Finalizado por:</strong> {ocorr.get('finalizado_por', '-')}<br>
                    <strong>Tempo de Permanência Manual:</strong> {permanencia_manual}<br>
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

# =========================
#     ABA 5 - POR FOCAL
# =========================
with aba5:
    st.header("Ocorrências por Focal")

    ocorrencias_abertas = carregar_ocorrencias_abertas()

    if not ocorrencias_abertas:
        st.info("ℹ️ Nenhuma ocorrência aberta no momento.")
    else:
        # Agrupar por focal
        focais_dict = {}
        for ocorr in ocorrencias_abertas:
            focal = ocorr.get("focal", "Não informado")
            if focal not in focais_dict:
                focais_dict[focal] = []
            focais_dict[focal].append(ocorr)

        # Inicializar variável de estado
        if "focal_selecionado" not in st.session_state:
            st.session_state["focal_selecionado"] = None

        focal_ativo = st.session_state["focal_selecionado"]

        # Caso nenhum focal esteja selecionado, mostrar botões
        if focal_ativo is None:
            st.subheader("Selecione um Focal:")
            for focal, lista in focais_dict.items():
                if st.button(f"{focal} ({len(lista)})", key=f"btn_focal_{focal}"):
                    st.session_state["focal_selecionado"] = focal
                    st.rerun()

        else:
            # Botão de voltar
            if st.button("🔙 Voltar para lista de Focais"):
                st.session_state["focal_selecionado"] = None
                st.rerun()

            st.subheader(f"Tickets em aberto para: {focal_ativo}")
            ocorrencias_focal = focais_dict.get(focal_ativo, [])

            num_colunas = 4
            colunas = st.columns(num_colunas)

            for idx, ocorr in enumerate(ocorrencias_focal):
                status = "Data manual ausente"
                cor = "gray"
                abertura_manual_formatada = "Não informada"
                data_abertura_manual = ocorr.get("data_abertura_manual")
                hora_abertura_manual = ocorr.get("hora_abertura_manual")

                if data_abertura_manual and hora_abertura_manual:
                    try:
                        data_manual_str = f"{data_abertura_manual} {hora_abertura_manual}"
                        dt_manual = datetime.strptime(data_manual_str, "%Y-%m-%d %H:%M:%S")
                        abertura_manual_formatada = dt_manual.strftime("%d-%m-%Y %H:%M:%S")

                        status, cor = classificar_ocorrencia_por_tempo(data_abertura_manual, hora_abertura_manual)

                    except Exception as e:
                        st.error(f"Erro ao processar data/hora manual da ocorrência {ocorr.get('nota_fiscal', '-')}: {e}")
                        status = "Erro"
                        cor = "gray"

                with colunas[idx % num_colunas]:
                    base_key = f"oc_{ocorr['id']}"

                    with st.container():
                        st.markdown(
                            f"""
                            <div style='background-color:{cor};padding:10px;border-radius:10px;color:white;
                            box-shadow: 0 4px 10px rgba(0,0,0,0.3);margin-bottom:5px;min-height:250px;font-size:15px;'>
                            <strong>Ticket #:</strong> {ocorr.get('numero_ticket', 'N/A')}<br>
                            <strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;
                            border-radius:1px;color:white;'>{status}</span><br>
                            <strong>NF:</strong> {ocorr.get('nota_fiscal', '-')}<br>
                            <strong>Cliente:</strong> {ocorr.get('cliente', '-')}<br>
                            <strong>Destinatário:</strong> {ocorr.get('destinatario', '-')}<br>
                            <strong>Focal:</strong> {ocorr.get('focal', '-')}<br>
                            <strong>Cidade:</strong> {ocorr.get('cidade', '-')}<br>
                            <strong>Motorista:</strong> {ocorr.get('motorista', '-')}<br>
                            <strong>Tipo:</strong> {ocorr.get('tipo_de_ocorrencia', '-')}<br>
                            <strong>Aberto por:</strong> {ocorr.get('responsavel', '-')}<br>
                            <strong>Data Abertura:</strong> {data_abertura_manual or 'Não informada'}<br>
                            <strong>Hora Abertura:</strong> {hora_abertura_manual or 'Não informada'}<br> 
                            <strong>Observações:</strong> {ocorr.get('observacoes', 'Sem observações.')}<br>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    with st.expander("Finalizar Ocorrência"):
                        data_atual = datetime.now().strftime("%d-%m-%Y")
                        hora_atual = datetime.now().strftime("%H:%M")
                        data_finalizacao_manual = st.text_input("Data Finalização (DD-MM-AAAA)", value=data_atual, key=f"data_final_{base_key}")
                        hora_finalizacao_manual = st.text_input("Hora Finalização (HH:MM)", value=hora_atual, key=f"hora_final_{base_key}")

                        complemento_key = f"complemento_final_{base_key}"
                        if complemento_key not in st.session_state:
                            st.session_state[complemento_key] = ""

                        complemento = st.text_area("Complementar", key=complemento_key, value=st.session_state[complemento_key])
                        finalizar_disabled = not complemento.strip()

                        if st.button("Finalizar", key=f"finalizar_{base_key}", disabled=finalizar_disabled):
                            if finalizar_disabled:
                                st.error("❌ O campo 'Complementar' é obrigatório para finalizar a ocorrência.")
                            else:
                                try:
                                    data_hora_finalizacao = datetime.strptime(
                                        f"{data_finalizacao_manual} {hora_finalizacao_manual}", "%d-%m-%Y %H:%M"
                                    )
                                except ValueError:
                                    st.error("❌ Formato inválido. Use DD-MM-AAAA para a data e HH:MM para a hora.")
                                    st.stop()

                                if not data_abertura_manual or not hora_abertura_manual:
                                    st.error("❌ Data/hora de abertura manual ausente. Não é possível calcular a permanência.")
                                    st.stop()

                                try:
                                    data_hora_abertura = datetime.strptime(
                                        f"{data_abertura_manual} {hora_abertura_manual}", "%Y-%m-%d %H:%M:%S"
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

                                        response = supabase.table("ocorrencias").update({
                                            "data_hora_finalizacao": data_hora_finalizacao.strftime("%Y-%m-%d %H:%M"),
                                            "finalizado_por": st.session_state.username,
                                            "complementar": complemento,
                                            "status": "Finalizada",
                                            "permanencia_manual": permanencia_manual,
                                            "data_finalizacao_manual": data_hora_finalizacao.strftime("%Y-%m-%d"),
                                            "hora_finalizacao_manual": hora_finalizacao_banco,
                                        }).eq("id", ocorr["id"]).execute()

                                        if response and response.data:
                                            st.session_state.ocorrencias_finalizadas.append(ocorr)
                                            st.success("✅ Ocorrência finalizada com sucesso!")
                                            time.sleep(2)
                                            st.rerun()
                                        else:
                                            st.error("Erro ao salvar a finalização no banco de dados.")
                                except Exception as e:
                                    st.error(f"Erro ao calcular ou salvar permanência manual: {e}")




# =========================
#     ABA 6 - ESTATÍSTICAS
# =========================
with aba6:
    st.header("📊 Estatísticas de Ocorrências Finalizadas")

    # Carrega as ocorrências finalizadas
    ocorrencias_finalizadas = carregar_ocorrencias_finalizadas()

    if not ocorrencias_finalizadas:
        st.info("ℹ️ Nenhuma ocorrência finalizada para gerar estatísticas.")
        st.stop()

    df_finalizadas = pd.DataFrame(ocorrencias_finalizadas)

    # --- Limpeza e conversões ---
    df_finalizadas["data_hora_abertura"] = pd.to_datetime(
        df_finalizadas.get("abertura_ticket") or df_finalizadas.get("abertura_timestamp"), errors="coerce"
    )
    df_finalizadas["data_hora_finalizacao"] = pd.to_datetime(df_finalizadas["data_hora_finalizacao"], errors="coerce")
    df_finalizadas = df_finalizadas.dropna(subset=["data_hora_abertura", "data_hora_finalizacao"])

    # Calcula tempo de permanência
   # Remove timezone (caso exista)
    df_finalizadas["data_hora_abertura"] = df_finalizadas["data_hora_abertura"].dt.tz_localize(None)
    df_finalizadas["data_hora_finalizacao"] = df_finalizadas["data_hora_finalizacao"].dt.tz_localize(None)

    # Calcula permanência
    df_finalizadas["permanencia_horas"] = (
        df_finalizadas["data_hora_finalizacao"] - df_finalizadas["data_hora_abertura"]
    ).dt.total_seconds() / 3600

    # --- Estatísticas Gerais ---
    st.subheader("⏱️ Tempo Médio de Permanência")
    tempo_medio = df_finalizadas["permanencia_horas"].mean()
    st.metric("Tempo Médio de Permanência (h)", f"{tempo_medio:.2f} h")

    # --- Gráfico por Tipo de Ocorrência ---
    st.subheader("📌 Ocorrências por Tipo")
    tipo_counts = df_finalizadas["tipo_de_ocorrencia"].value_counts()
    st.bar_chart(tipo_counts)

    # --- Gráfico por Cliente ---
    st.subheader("🏢 Ocorrências por Cliente")
    cliente_counts = df_finalizadas["cliente"].value_counts()
    st.bar_chart(cliente_counts)

    # --- Gráfico de Tempo Médio por Focal ---
    st.subheader("👤 Tempo Médio por Focal")
    tempo_por_focal = df_finalizadas.groupby("focal")["permanencia_horas"].mean().sort_values(ascending=False)
    st.bar_chart(tempo_por_focal)


