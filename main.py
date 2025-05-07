import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import time
from dateutil import parser
from streamlit_autorefresh import st_autorefresh
import streamlit_authenticator as stauth
import pytz
import uuid
from supabase import create_client, Client
import hashlib
import uuid


# --- CONEXÃO COM O SUPABASE ---
url = "https://vismjxhlsctehpvgmata.supabase.co"  # ✅ sua URL real, já sem o '>' no meio
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZpc21qeGhsc2N0ZWhwdmdtYXRhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY1NzA4NTIsImV4cCI6MjA2MjE0Njg1Mn0.zTjSWenfuVJTIixq2RThSUpqcHGfZWP2xkFDU3USPb0"  # ✅ sua chave real (evite expor em público!)
supabase: Client = create_client(url, key)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Ocorrências", layout="wide")

# --- Função de hash da senha ---
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()


# --- Autenticação com Supabase ---
def autenticar_usuario(usuario, senha):
    senha_hashed = hash_senha(senha)
    print("Hash gerado:", senha_hashed)
    print("Nome de usuário enviado para consulta:", repr(usuario.strip()))

    dados = supabase.table("usuarios").select("*") \
        .eq("nome_usuario", usuario.strip()) \
        .eq("senha_hash", senha_hashed) \
        .execute()

    print("Dados retornados:", dados.data)

    if dados.data:
        return dados.data[0]
    return None


# --- Interface de Login ---
def login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>📝 Gestão de Ocorrências</h1>", unsafe_allow_html=True)

    if "login" not in st.session_state:
        st.session_state.login = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    if not st.session_state.login:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("##### Login")
            username = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")

            if st.button("Entrar"):
                usuario = autenticar_usuario(username, senha)
                if usuario:
                    st.session_state.login = True
                    st.session_state.username = usuario["nome_usuario"]
                    st.session_state.is_admin = usuario.get("is_admin", False)
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos")
        st.stop()
    else:
        st.markdown(f"👋 **Bem-vindo, {st.session_state.username}!**")

        col1, col2, col3 = st.columns([6, 1, 1])
        with col3:
            if st.button("🔒 Sair"):
                st.session_state.login = False
                st.session_state.username = ""
                st.session_state.is_admin = False
                st.rerun()



# --- Chama login antes de qualquer coisa ---
login()

# --- SE CHEGOU AQUI, USUÁRIO ESTÁ AUTENTICADO ---
#--------------------------------------------------------------------------INICIO APP --------------------------------------------------------------

# --- CARREGAMENTO DE DADOS Tabelas com nomes de motorista e clientes ---

# Carrega a aba "clientes" do arquivo clientes.xlsx
df_clientes = pd.read_excel("data/clientes.xlsx", sheet_name="clientes")
df_clientes.columns = df_clientes.columns.str.strip()  # Remove espaços extras nas colunas
df_clientes = df_clientes[["Cliente", "Focal"]].dropna(subset=["Cliente"])

# Cria dicionário Cliente -> Focal e lista de clientes
cliente_to_focal = dict(zip(df_clientes["Cliente"], df_clientes["Focal"]))
clientes = df_clientes["Cliente"].tolist()

# Carrega a aba "motoristas" do arquivo motoristas.xlsx
df_motoristas = pd.read_excel("data/motoristas.xlsx", sheet_name="motoristas")
df_motoristas.columns = df_motoristas.columns.str.strip()
motoristas = df_motoristas["Motorista"].dropna().tolist()




# --- INICIALIZAÇÃO DE SESSÃO ---
if "ocorrencias_abertas" not in st.session_state:
    st.session_state.ocorrencias_abertas = []

if "ocorrencias_finalizadas" not in st.session_state:
    st.session_state.ocorrencias_finalizadas = []

# --- ABAS ---
aba1, aba2, aba3, aba4 = st.tabs(["📝 Nova Ocorrência", "📌 Ocorrências em Aberto", "✅ Ocorrências Finalizadas", "📊 Configurações"])

# =========================
#       ABA 1 - NOVA
# =========================
with aba1:
    st.header("Nova Ocorrência")

    # Reset do campo Focal após envio bem-sucedido
    if "focal_responsavel" not in st.session_state:
        st.session_state["focal_responsavel"] = ""

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

            # Atualiza automaticamente o campo Focal ao selecionar Cliente
            if cliente_opcao and cliente_opcao in cliente_to_focal:
                st.session_state["focal_responsavel"] = cliente_to_focal[cliente_opcao]
            elif cliente_opcao:
                st.session_state["focal_responsavel"] = ""
            
            #st.text_input("Focal Responsável", value=st.session_state["focal_responsavel"], key="focal_visivel", disabled=True)

            cidade = st.text_input("Cidade", key="cidade")

        with col2:
            motorista_opcao = st.selectbox("Motorista", options=motoristas + ["Outro (digitar manualmente)"], index=None, key="motorista_opcao")
            motorista = st.text_input("Digite o nome do motorista", key="motorista_manual") if motorista_opcao == "Outro (digitar manualmente)" else motorista_opcao
            tipo = st.multiselect("Tipo de Ocorrência", options=["Chegada no Local", "Pedido Bloqueado", "Demora", "Divergência"], key="tipo_ocorrencia")
            obs = st.text_area("Observações", key="observacoes")
            responsavel = st.session_state.username
            st.text_input("Quem está abrindo o ticket", value=responsavel, disabled=True)

        enviar = st.form_submit_button("Adicionar Ocorrência")

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
            else:
                fuso_sp = pytz.timezone("America/Sao_Paulo")
                agora_sp = datetime.now(fuso_sp)

                nova_ocorrencia = {
                    "ID": str(uuid.uuid4()),
                    "Nota Fiscal": nf,
                    "Cliente": cliente,
                    "Focal": st.session_state["focal_responsavel"],
                    "Destinatario": destinatario,
                    "Cidade": cidade,
                    "Motorista": motorista,
                    "Tipo de Ocorrência": ", ".join(tipo),
                    "Observações": obs,
                    "Responsável": responsavel,
                    "Data/Hora Abertura": agora_sp.strftime("%d/%m/%Y %H:%M:%S"),
                    "Abertura Timestamp": agora_sp.replace(tzinfo=None),
                    "Complementar": "",
                    "Data/Hora Finalização": ""
                }

                st.session_state.ocorrencias_abertas.append(nova_ocorrencia)

                # Reset do Focal após salvar
                st.session_state["focal_responsavel"] = ""

                sucesso = st.empty()
                sucesso.success("✅ Ocorrência aberta com sucesso!")
                time.sleep(2)
                sucesso.empty()

# =========================
#    FUNÇÃO CLASSIFICAÇÃO
# =========================
# Função para classificar a ocorrência com base no tempo decorrido entre abertura e finalização
# Função para classificar a ocorrência com base no tempo decorrido entre abertura e a hora atual
# Função para classificar a ocorrência com tratamento robusto
# Função para classificar a ocorrência de acordo com o tempo decorrido
def classificar_ocorrencia_por_tempo(data_abertura_str):
    try:
        tz_sp = pytz.timezone("America/Sao_Paulo")
        data_abertura = datetime.strptime(data_abertura_str, "%d/%m/%Y %H:%M:%S")
        data_abertura = tz_sp.localize(data_abertura)  # Torna data_abertura "aware"
    except Exception as e:
        return "Erro", "gray"

    agora = datetime.now(tz_sp)
    tempo_decorrido = (agora - data_abertura).total_seconds() / 60

    if tempo_decorrido < 15:
        return "🟢 Normal", "#2ecc71"
    elif tempo_decorrido < 30:
        return "🟡 Alerta", "#f1c40f"
    elif tempo_decorrido < 45:
        return "🟠 Urgente", "#e67e22"
    elif tempo_decorrido < 60:
        return "🔴 Crítico", "#e74c3c"
    else:
        return "🚨 +60 min", "#c0392b"

# ----------------------------------------------------------------Função para salvar ocorrência finalizada em Excel---------------------------------

# -------------------------------------------------------------------AINDA FUNÇÃO -----------------------------------------------------------
# =========================
#     ABA 2 - EM ABERTO
# =========================
with aba2:
    st.header("Ocorrências em Aberto")
    # Exibe mensagem de sucesso, se existir
    if st.session_state.get("mensagem_sucesso_finalizacao"):
        sucesso_msg = st.empty()
        sucesso_msg.success("✅ Ocorrência finalizada com sucesso!")
        time.sleep(2)
        sucesso_msg.empty()
        del st.session_state["mensagem_sucesso_finalizacao"]

#-------------------------------------------------------------------------------------------------------------------------------
    def salvar_ocorrencia_finalizada(ocorr, status): ### função salva ocorrencia finalizada Excel
        pasta = os.path.join("data", "relatorio_de_tickets")
        caminho = os.path.join(pasta, "relatorio_ocorrencias.xlsx")
        os.makedirs(pasta, exist_ok=True)

        ocorr["Estágio"] = status
        df_nova = pd.DataFrame([ocorr])

        if not os.path.exists(caminho):
            df_nova.to_excel(caminho, index=False)
        else:
            df_existente = pd.read_excel(caminho)

            # Junta e remove duplicatas com base no ID exclusivo
            # Remover qualquer ocorrência com o mesmo ID antes de salvar
            df_existente = df_existente[df_existente["ID"] != ocorr["ID"]]
            # Concatenar a nova ocorrência
            df_final = pd.concat([df_existente, df_nova], ignore_index=True)

            

        # Remove timezone de todas as colunas datetimetz (caso existam)
        for col in df_final.select_dtypes(include=["datetimetz"]).columns:
            df_final[col] = df_final[col].dt.tz_localize(None)

        df_final.to_excel(caminho, index=False)
#------------------------------------------------------------------------
    if not st.session_state.ocorrencias_abertas:
        st.info("ℹ️ Nenhuma ocorrência aberta no momento.")
    else:
        colunas = st.columns(4)
        st_autorefresh(interval=10000, key="ocorrencias_abertas_refresh")

        for idx, ocorr in list(enumerate(st.session_state.ocorrencias_abertas)):
            data_abertura_str = ocorr.get("Data/Hora Abertura") or ocorr.get("Abertura Timestamp")

            try:
                status, cor = classificar_ocorrencia_por_tempo(data_abertura_str)
                data_abertura = datetime.strptime(data_abertura_str, "%d/%m/%Y %H:%M:%S")
                data_formatada = data_abertura.strftime('%d/%m/%Y %H:%M:%S')
            except Exception as e:
                st.error(f"Erro ao processar ocorrência (NF: {ocorr.get('Nota Fiscal', '-')}) — {e}")
                continue

            with colunas[idx % 4]:
                safe_idx = f"{idx}_{ocorr.get('Nota Fiscal', '')}"

                with st.container():
                    st.markdown(
                        f"<div style='background-color:{cor};padding:10px;border-radius:10px;color:white;"
                        f"box-shadow: 0 4px 10px rgba(0,0,0,0.3);margin-bottom:5px;min-height:250px;font-size:15px;'>"
                        f"<strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;border-radius:1px;color:white;'>{status}</span><br>"
                        f"<strong>NF:</strong> {ocorr.get('Nota Fiscal', '-')}<br>"
                        f"<strong>Cliente:</strong> {ocorr.get('Cliente', '-')}<br>"
                        f"<strong>Focal:</strong> {ocorr.get('Focal', '-')}<br>"
                        f"<strong>Cidade:</strong> {ocorr.get('Cidade', '-')}<br>"
                        f"<strong>Motorista:</strong> {ocorr.get('Motorista', '-')}<br>"
                        f"<strong>Tipo:</strong> {ocorr.get('Tipo de Ocorrência', '-')}<br>"
                        f"<strong>Aberto por:</strong> {ocorr.get('Responsável', '-')}<br>"
                        f"<strong>Data/Hora Abertura:</strong> {data_formatada}<br>"
                        "</div>",
                        unsafe_allow_html=True
                    )

                    with st.expander("Finalizar Ocorrência"):  # ❌ Sem controle de estado expandido
                        complemento = st.text_area("Complemento", key=f"complemento_final_{safe_idx}")
                        if st.button("Finalizar", key=f"finalizar_{safe_idx}"):
                            if not complemento.strip():
                                st.error("❌ O campo 'Complementar' é obrigatório para finalizar a ocorrência.")
                            else:
                                ocorr["Complementar"] = complemento
                                agora_sp = datetime.now(pytz.timezone("America/Sao_Paulo"))
                                ocorr["Data/Hora Finalização"] = agora_sp.strftime("%d/%m/%Y %H:%M:%S")
                                ocorr["Status"] = status
                                ocorr["Cor"] = cor
                                ocorr["Finalizada"] = True
                                ocorr["Finalizado por"] = st.session_state.username
                                 # 🕒 Calcula o tempo de permanência
                                try:
                                    dt_abertura = datetime.strptime(ocorr["Data/Hora Abertura"], "%d/%m/%Y %H:%M:%S")
                                    dt_fim = datetime.strptime(ocorr["Data/Hora Finalização"], "%d/%m/%Y %H:%M:%S")
                                    ocorr["Tempo de Permanência"] = str(dt_fim - dt_abertura)
                                except Exception as e:
                                    ocorr["Tempo de Permanência"] = "Erro ao calcular"

                                salvar_ocorrencia_finalizada(ocorr, status)

                                st.session_state.ocorrencias_finalizadas.append(ocorr)
                                st.session_state.ocorrencias_abertas.pop(idx)
                                st.session_state["mensagem_sucesso_finalizacao"] = True
                                st.rerun()  # Substituto oficial para experimental_rerun()



                            

# =========================
#     ABA 3 - FINALIZADAS
# =========================
with aba3:
    #st.markdown("### 🔎 Filtro por Nota Fiscal")
    st.header("Ocorrências Finalizadas")

    col_filtro, _ = st.columns([1, 5])  # Campo no canto esquerdo
    with col_filtro:
        nf_busca = st.text_input("Buscar", placeholder="Nota Fiscal")

    # Usa somente ocorrências finalizadas
    ocorrencias = st.session_state.get("ocorrencias_finalizadas", [])

    # Se houver algo digitado, aplica o filtro
    if nf_busca:
        ocorrencias_filtradas = [
            ocorr for ocorr in ocorrencias
            if nf_busca.strip() in str(ocorr.get("Nota Fiscal", ""))]
    else:
        ocorrencias_filtradas = ocorrencias

    # Caso não existam ocorrências finalizadas
    if not ocorrencias_filtradas:
        st.info("ℹ️ Nenhuma ocorrência finalizada encontrada.")
    else:
        # Divide o layout em 4 colunas
        colunas = st.columns(4)
        
        # Calculando o tempo de permanência
        for idx, ocorr in enumerate(ocorrencias_filtradas):

            # Obtém as datas de abertura e finalização da ocorrência
            data_abertura_str = ocorr.get("Data/Hora Abertura")
            data_finalizacao_str = ocorr.get("Data/Hora Finalização")
            
            try:
                # Cálculo do tempo de permanência
                data_abertura = datetime.strptime(data_abertura_str, "%d/%m/%Y %H:%M:%S")
                data_finalizacao = datetime.strptime(data_finalizacao_str, "%d/%m/%Y %H:%M:%S")
                
                tempo_permanencia = data_finalizacao - data_abertura
                tempo_permanencia_str = str(tempo_permanencia)

                status = ocorr.get("Status", "⏱️ Tempo desconhecido")
                cor = ocorr.get("Cor", "#95a5a6")

            except Exception as e:
                st.error(f"Erro ao processar ocorrência (NF: {ocorr.get('Nota Fiscal', '-')}) — {e}")
                continue

            # Seleciona uma das colunas disponíveis para exibir o card
            with colunas[idx % 4]:
                status = ocorr.get("Status", "Desconhecido")
                cor = ocorr.get("Cor", "#777")

                with st.container():
                    st.markdown(
                        f"<div style='background-color:{cor};padding:10px;border-radius:10px;color:white;"
                        f"box-shadow: 0 4px 12px rgba(0,0,0,0.3);margin-bottom:30px;min-height: 300px;font-size:14px;'>"
                        
                        # Exibe o status
                        f"<strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;border-radius:5px;color:white;'>{status}</span><br>"

                        # Exibe o número da nota fiscal
                        f"<strong>NF:</strong> {ocorr.get('Nota Fiscal', '-')}<br>"

                        # Exibe o nome do cliente
                        f"<strong>Cliente:</strong> {ocorr.get('Cliente', '-')}<br>"

                        # Exibe o nome Focal
                        f"<strong>Focal:</strong> {ocorr.get('Focal', '-')}<br>"
                        
                        # Exibe a cidade da ocorrência
                        f"<strong>Cidade:</strong> {ocorr.get('Cidade', '-')}<br>"

                        # Exibe o nome do motorista
                        f"<strong>Motorista:</strong> {ocorr.get('Motorista', '-')}<br>"

                        # Exibe o tipo de ocorrência
                        f"<strong>Tipo:</strong> {ocorr.get('Tipo de Ocorrência', '-')}<br>"

                        # Exibe quem abriu a ocorrência
                        f"<strong>Aberto por:</strong> {ocorr.get('Responsável', '-')}<br>"

                        # Exibe a data/hora de abertura
                        f"<strong>Data/Hora Abertura:</strong> {data_abertura.strftime('%d/%m/%Y %H:%M:%S')}<br>"

                        # Exibe a data/hora de finalização
                        f"<strong>Finalizado em:</strong> {ocorr.get('Data/Hora Finalização', '-')}<br>"

                        # Exibe quem finalizou
                        f"<strong>Finalizado por:</strong> {ocorr.get('Finalizado por', '-') }<br>"

                        # Exibe o campo complementar
                        f"<strong>Complementar:</strong> {ocorr.get('Complementar', '-')}<br>"

                        # Exibe o tempo de permanência da ocorrência (tempo entre abertura e finalização)
                        f"<strong>Tempo de Permanência:</strong> {tempo_permanencia_str}<br>"

                        "</div>",
                        unsafe_allow_html=True
                    )

            # Salvando o tempo de permanência no relatório Excel
            ocorr["Tempo de Permanência"] = tempo_permanencia_str  # Adiciona o tempo de permanência à ocorrência





# ======================
#     ABA 4 - USUÁRIOS
# ======================
with aba4:
    st.header("🔐 Gestão de Usuários")

    usuario_logado = st.session_state.username
    dados_usuario = supabase.table("usuarios").select("*").eq("nome_usuario", usuario_logado).execute().data[0]
    admin = dados_usuario["is_admin"]

    if admin:
        st.subheader("👤 Criar Novo Usuário")
        novo_usuario = st.text_input("Nome do novo usuário")
        nova_senha = st.text_input("Senha do novo usuário", type="password")
        admin_checkbox = st.checkbox("É administrador?")

        if st.button("Criar usuário"):
            if not novo_usuario or not nova_senha:
                st.error("Preencha todos os campos.")
            else:
                senha_hashed = hash_senha(nova_senha)
                try:
                    supabase.table("usuarios").insert({
                        "nome_usuario": novo_usuario,
                        "senha_hash": senha_hashed,
                        "is_admin": admin_checkbox
                    }).execute()
                    msg = st.empty()
                    msg.success("✅ Usuário criado com sucesso!")
                    time.sleep(2)
                    msg.empty()
                except Exception as e:
                    st.error(f"Erro ao criar usuário: {e}")

        # Excluir usuários - Usando Selectbox para listar os usuários existentes
        st.subheader("🗑️ Deletar Usuário")

        usuarios = supabase.table("usuarios").select("nome_usuario").execute().data
        lista_usuarios = [usuario['nome_usuario'] for usuario in usuarios if usuario['nome_usuario'] != usuario_logado]

        selectbox_key = str(uuid.uuid4())
        usuario_para_deletar = st.selectbox("Selecione o usuário para excluir", lista_usuarios, key=selectbox_key)

        if st.button("Deletar Usuário"):
            if not usuario_para_deletar:
                st.error("Selecione um usuário para excluir.")
            else:
                try:
                    # Buscar ID do usuário a ser deletado
                    resultado = supabase.table("usuarios").select("id").eq("nome_usuario", usuario_para_deletar).execute()
                    dados_usuario_para_deletar = resultado.data

                    if not dados_usuario_para_deletar:
                        st.error(f"Erro: usuário '{usuario_para_deletar}' não encontrado.")
                    else:
                        usuario_id = dados_usuario_para_deletar[0]["id"]

                        # Deletar o usuário
                        response = supabase.table("usuarios").delete().eq("id", usuario_id).execute()
                        print("Resposta da exclusão:", response)

                        time.sleep(1)  # Delay para garantir sincronização

                        # Verificar se foi excluído
                        usuario_excluido = supabase.table("usuarios").select("id").eq("id", usuario_id).execute().data
                        msg = st.empty()
                        if usuario_excluido:
                            msg.error(f"Erro ao deletar usuário: O usuário '{usuario_para_deletar}' ainda existe na base.")
                        else:
                            msg.success(f"✅ O usuário '{usuario_para_deletar}' foi excluído com sucesso!")
                            time.sleep(2)
                            msg.empty()

                except Exception as e:
                    st.error(f"Erro ao deletar usuário: {e}")

    # Alterar senha do próprio usuário
    st.subheader("🔒 Alterar Minha Senha")
    senha_atual = st.text_input("Senha atual", type="password")
    nova_senha1 = st.text_input("Nova senha", type="password")
    nova_senha2 = st.text_input("Confirme a nova senha", type="password")

    if st.button("Atualizar Senha"):
        if not senha_atual or not nova_senha1 or not nova_senha2:
            st.error("Todos os campos são obrigatórios.")
        elif nova_senha1 != nova_senha2:
            st.error("As novas senhas não coincidem.")
        elif hash_senha(senha_atual) != dados_usuario["senha_hash"]:
            st.error("Senha atual incorreta.")
        else:
            nova_senha_hash = hash_senha(nova_senha1)
            supabase.table("usuarios").update({"senha_hash": nova_senha_hash}).eq("nome_usuario", usuario_logado).execute()
            msg = st.empty()
            msg.success("🔐 Senha atualizada com sucesso.")
            time.sleep(2)
            msg.empty()








