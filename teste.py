# versão liberada para usuario


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
from dateutil import parser
from psycopg2 import sql
from io import BytesIO

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
        "data_hora_abertura": dados["data_hora_abertura"],
        "abertura_timestamp": dados["abertura_timestamp"],
        "permanencia": dados["permanencia"],
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
                    "data_hora_abertura": abertura_sem_fuso.strftime("%Y-%m-%d %H:%M:%S"),   # Para exibição (com TZ)
                    "abertura_timestamp": abertura_sem_fuso.isoformat(),            # ISO sem fuso (para cálculos)
                    "abertura_datetime_obj": abertura_sem_fuso,                     # Objeto datetime sem TZ (para cálculos)
                    "abertura_ticket": abertura_sem_fuso.strftime("%Y-%m-%d %H:%M:%S"),      # Novo campo para cálculo na finalização
                     "complementar": "",
                     "permanencia": ""
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
def salvar_ocorrencia_finalizada(ocorr, status):
    try:
        # Garantir que as chaves existam e as datas sejam strings válidas
        if isinstance(ocorr.get("Data/Hora Finalização"), str):
            try:
                data_hora_finalizacao = parser.parse(ocorr["Data/Hora Finalização"])
            except ValueError:
                st.error("Erro: Formato de 'Data/Hora Finalização' inválido!")
                return
        else:
            data_hora_finalizacao = ocorr["Data/Hora Finalização"]

        if isinstance(ocorr.get("Data/Hora Abertura"), str):
            try:
                data_hora_abertura = parser.parse(ocorr["Data/Hora Abertura"])
            except ValueError:
                st.error("Erro: Formato de 'Data/Hora Abertura' inválido!")
                return
        else:
            data_hora_abertura = ocorr["Data/Hora Abertura"]

           

            # Certifique-se que essas datas existem e são datetime válidos
            data_hora_abertura = parser.parse(ocorr["abertura_timestamp"]).replace(tzinfo=None)
            agora_sp = datetime.now()

            # Calcular permanência
            permanencia_timedelta = agora_sp - data_hora_abertura
            total_segundos = int(permanencia_timedelta.total_seconds())
            dias = total_segundos // 86400
            horas = (total_segundos % 86400) // 3600
            minutos = (total_segundos % 3600) // 60
            tempo_permanencia_formatado = f"{dias}d {horas}h {minutos}min"

            # Atualiza no banco de dados
            response = supabase.table("ocorrencias").update({
                "data_hora_finalizacao": agora_sp.strftime("%Y-%m-%d %H:%M:%S"),
                "finalizado_por": ocorr["Finalizado por"],
                "complementar": ocorr["Complementar"],
                "permanencia": tempo_permanencia_formatado,
                "status": "Finalizada"
            }).eq("id", ocorr["ID"]).execute()

            # Debug opcional
            st.write("Resposta Supabase:", response)




        
        st.session_state["mensagem_sucesso_finalizacao"] = True

    except Exception as e:
        st.error(f"Erro ao salvar no banco de dados: {e}")
        st.session_state["mensagem_sucesso_finalizacao"] = False

    # Exibe mensagem de sucesso se houver
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
        st_autorefresh(interval=30000, key="ocorrencias_abertas_refresh")

        for idx, ocorr in enumerate(ocorrencias_abertas):
            # Pegando a data diretamente do campo 'data_hora_abertura' retornado do Supabase
            data_abertura_str = ocorr.get("data_hora_abertura")

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
                print(f"Data processada corretamente: {data_formatada}")
            except Exception as e:
                st.error(f"Erro ao processar ocorrência (NF: {ocorr.get('nota_fiscal', '-')}) — {e}")
                continue

            # Agora, independentemente de erro, defina status e cor
            status = status
            cor = cor  # A cor é determinada pela classificação por tempo

            with colunas[idx % num_colunas]:
                safe_idx = f"{idx}_{ocorr.get('nota_fiscal', '')}"

                with st.container():
                    st.markdown(
                        f"""
                        <div style='background-color:{cor};padding:10px;border-radius:10px;color:white;box-shadow: 0 4px 10px rgba(0,0,0,0.3);margin-bottom:5px;min-height:250px;font-size:15px;'>
                            <strong>Ticket #:</strong> {ocorr.get('numero_ticket') if ocorr.get('numero_ticket') else 'N/A'}<br>
                            <strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;border-radius:1px;color:white;'>{status}</span><br>
                            <strong>NF:</strong> {ocorr.get('nota_fiscal', '-')}<br>
                            <strong>Cliente:</strong> {ocorr.get('cliente', '-')}<br>
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

                    # Usando o expander para "Finalizar Ocorrência"
                    with st.expander("Finalizar Ocorrência"):
                        # Complemento para a finalização
                        complemento_key = f"complemento_final_{safe_idx}"

                        # Inicializando o campo de complemento se não existir no session_state
                        if complemento_key not in st.session_state:
                            st.session_state[complemento_key] = ""

                        complemento = st.text_area(
                            "Complementar", 
                            key=complemento_key, 
                            value=st.session_state[complemento_key]
                        )

                        # Habilita ou desabilita o botão de finalização com base no preenchimento do complemento
                        finalizar_disabled = not complemento.strip()

                        # Quando o botão "Finalizar" for clicado, executa a finalização
                        if st.button("Finalizar", key=f"finalizar_{safe_idx}", disabled=finalizar_disabled):
                            if finalizar_disabled:
                                st.error("❌ O campo 'Complementar' é obrigatório para finalizar a ocorrência.")
                            else:
                                # Atualiza a ocorrência com as informações de finalização
                                ocorr["Complementar"] = complemento
                                agora_sp = datetime.now(pytz.timezone("America/Sao_Paulo")).replace(tzinfo=None)
                                ocorr["Data/Hora Finalização"] = agora_sp.strftime("%d/%m/%Y %H:%M:%S")
                                ocorr["Status"] = status
                                ocorr["Cor"] = cor
                                ocorr["Finalizada"] = True
                                ocorr["Finalizado por"] = st.session_state.username

                                # Calcular tempo de permanência
                                permanencia = "N/A"
                                try:
                                    if "abertura_timestamp" in ocorr and ocorr["abertura_timestamp"]:
                                        abertura_ts = parser.parse(ocorr["abertura_timestamp"]).replace(tzinfo=None)
                                        delta = agora_sp - abertura_ts
                                        horas = str(delta.seconds // 3600).zfill(2)
                                        minutos = str((delta.seconds // 60) % 60).zfill(2)
                                        segundos = str(delta.seconds % 60).zfill(2)
                                        permanencia = f"{horas}:{minutos}:{segundos}"

                                except Exception as e:
                                    st.error(f"Erro ao calcular permanência: {e}")

                                # Atualiza no banco de dados
                                response = supabase.table("ocorrencias").update({
                                    "data_hora_finalizacao": agora_sp.strftime("%Y-%m-%d %H:%M:%S"),
                                    "finalizado_por": ocorr["Finalizado por"],
                                    "complementar": ocorr["Complementar"],
                                    "status": "Finalizada",
                                    "permanencia": permanencia,
                                }).eq("id", ocorr["id"]).execute()

                                # Se a atualização for bem-sucedida, notifica o usuário
                                if response and response.data:
                                    st.session_state.ocorrencias_finalizadas.append(ocorr)
                                    st.success("✅ Ocorrência finalizada com sucesso!")
                                    time.sleep(2)
                                    st.rerun()  # Atualiza a tela para refletir a mudança
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
        # --- Linha com campo de pesquisa e botão de exportação ---
        col1, col2 = st.columns([1, 2])  # Definindo as colunas com o botão de exportação mais largo

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
                data_finalizacao_raw = ocorr.get("data_hora_finalizacao")
                data_abertura_raw = ocorr.get("abertura_ticket") or ocorr.get("abertura_timestamp")

                data_abertura_dt = parser.isoparse(data_abertura_raw).replace(tzinfo=None) if data_abertura_raw else None
                data_finalizacao_dt = parser.isoparse(data_finalizacao_raw).replace(tzinfo=None) if data_finalizacao_raw else None

                data_abertura_formatada = data_abertura_dt.strftime("%d-%m-%Y %H:%M:%S") if data_abertura_dt else "-"
                data_finalizacao_formatada = data_finalizacao_dt.strftime("%d-%m-%Y %H:%M:%S") if data_finalizacao_dt else "-"

                if data_abertura_dt and data_finalizacao_dt:
                    tempo_total = data_finalizacao_dt - data_abertura_dt
                    tempo_permanencia_formatado = str(tempo_total).split('.')[0]
                else:
                    tempo_permanencia_formatado = "Não disponível"

                status = ocorr.get("Status", "Finalizada")
                cor = ocorr.get("Cor", "#34495e")

            except Exception as e:
                st.error(f"Erro ao processar ocorrência (NF {ocorr.get('nota_fiscal', '-')}) — {e}")
                data_abertura_formatada = data_finalizacao_formatada = tempo_permanencia_formatado = "-"
                status = "Erro"
                cor = "#7f8c8d"

            with colunas[idx % num_colunas]:
                with st.container():
                    st.markdown(
                        f"""
                        <div style='background-color:{cor};padding:10px;border-radius:10px;color:white;
                        box-shadow: 0 4px 10px rgba(0,0,0,0.3);margin-bottom:5px;min-height:250px;font-size:15px;'>
                            <strong>Ticket #:</strong> {ocorr.get('numero_ticket') or 'N/A'}<br>
                            <strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;border-radius:1px;color:white;'>{status}</span><br>
                            <strong>NF:</strong> {ocorr.get('nota_fiscal', '-')}<br>
                            <strong>Cliente:</strong> {ocorr.get('cliente', '-')}<br>
                            <strong>Cidade:</strong> {ocorr.get('cidade', '-')}<br>
                            <strong>Motorista:</strong> {ocorr.get('motorista', '-')}<br>
                            <strong>Tipo:</strong> {ocorr.get('tipo_de_ocorrencia', '-')}<br>
                            <strong>Aberto por:</strong> {ocorr.get('responsavel', '-')}<br>
                            <strong>Data/Hora Abertura:</strong> {data_abertura_formatada}<br>
                            <strong>Data/Hora Finalização:</strong> {data_finalizacao_formatada}<br>
                            <strong>Finalizado por:</strong> {ocorr.get('finalizado_por', '-')}<br>
                            <strong>Tempo de Permanência:</strong> {tempo_permanencia_formatado}<br>
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
#     ABA 5 - TICKETS POR FOCAL
# =========================
with aba5:
    st.header("Tickets por Focal")

    # Carrega todas as ocorrências abertas
    todas_ocorrencias = carregar_ocorrencias_abertas()

    if not todas_ocorrencias:
        st.info("ℹ️ Nenhuma ocorrência aberta no momento.")
    else:
        # Agrupar por focal
        focais = {}
        for ocorr in todas_ocorrencias:
            focal = ocorr.get("focal", "Não informado")
            focais.setdefault(focal, []).append(ocorr)

        st.subheader("Selecione uma Focal para visualizar os tickets:")

        colunas = st.columns(4)
        for idx, (focal, tickets) in enumerate(focais.items()):
            with colunas[idx % 4]:
                btn_key = f"btn_focal_{idx}"
                if st.button(f"{focal} ({len(tickets)} tickets)", key=btn_key):
                    if st.session_state.get("focal_selecionada") == focal:
                        # Clicou de novo na mesma focal → esconder
                        st.session_state.focal_selecionada = None
                    else:
                        # Clicou em outra focal → mostrar
                        st.session_state.focal_selecionada = focal


        # Se alguma focal foi selecionada, exibir seus tickets
        focal_atual = st.session_state.get("focal_selecionada")
        if focal_atual:
            st.markdown(f"### 🎯 Tickets da focal: **{focal_atual}**")
            tickets_focal = focais[focal_atual]

            # Define número de colunas por linha
            num_colunas = 3
            for i in range(0, len(tickets_focal), num_colunas):
                linha = st.columns(num_colunas)
                for j, row in enumerate(tickets_focal[i:i+num_colunas]):
                    with linha[j]:
                        ticket_id = row["id"]

                        # Processa a data
                        try:
                            data_str = row.get("data_hora_abertura", "").replace('T', ' ')
                            data_dt = parser.parse(data_str)
                            data_formatada = data_dt.strftime("%d-%m-%Y %H:%M:%S")
                        except:
                            data_formatada = "Data inválida"

                        status, cor = classificar_ocorrencia_por_tempo(data_str)

                        # Gerencia checkboxes temporários
                        contato_motorista_key = f"contato_motorista_{ticket_id}"
                        contato_industria_key = f"contato_industria_{ticket_id}"
                        st.session_state.setdefault(contato_motorista_key, False)
                        st.session_state.setdefault(contato_industria_key, False)

                        with st.container():
                            st.markdown(
                                f"""
                                <div style='background-color:{cor};padding:10px;border-radius:10px;color:white;margin-bottom:10px;'>
                                    <strong>Ticket #:</strong> {row.get("numero_ticket", "-")}<br>
                                    <strong>Status:</strong> {status}<br>
                                    <strong>NF:</strong> {row.get("nota_fiscal", "-")}<br>
                                    <strong>Cliente:</strong> {row.get("cliente", "-")}<br>
                                    <strong>Focal:</strong> {row.get("focal", "-")}<br>
                                    <strong>Cidade:</strong> {row.get("cidade", "-")}<br>
                                    <strong>Motorista:</strong> {row.get("motorista", "-")}<br>
                                    <strong>Tipo:</strong> {row.get("tipo_de_ocorrencia", "-")}<br>
                                    <strong>Aberto por:</strong> {row.get("responsavel", "-")}<br>
                                    <strong>Data/Hora Abertura:</strong> {data_formatada}<br>
                                    <strong>Observações:</strong> {row.get("observacoes", "Sem observações.")}<br>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                            col1, col2 = st.columns(2)
                            with col1:
                                st.checkbox("✔️ Contato com motorista", key=contato_motorista_key)
                            with col2:
                                st.checkbox("✔️ Contato com indústria", key=contato_industria_key)

                            # Finalização
                            with st.expander("🔒 Finalizar Ocorrência"):
                                comp_key = f"complementar_final_{ticket_id}"
                                st.session_state.setdefault(comp_key, "")
                                st.text_area("Complementar (obrigatório)", key=comp_key)

                                if st.button("✅ Finalizar", key=f"finalizar_btn_{ticket_id}"):
                                    if not st.session_state[comp_key].strip():
                                        st.warning("⚠️ Campo 'Complementar' é obrigatório para finalizar.")
                                    else:
                                        ocorr_finalizada = {
                                            "ID": ticket_id,
                                            "Finalizado por": st.session_state.username,
                                            "Complementar": st.session_state[comp_key],
                                            "Data/Hora Abertura": row["abertura_timestamp"],
                                            "Data/Hora Finalização": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        }

                                        salvar_ocorrencia_finalizada(ocorr_finalizada, status="Finalizada")
                                        st.rerun()









