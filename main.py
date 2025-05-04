import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import time
from dateutil import parser
from streamlit_autorefresh import st_autorefresh
import yaml
import streamlit_authenticator as stauth
import pytz
import uuid

# --- DEVE SER A PRIMEIRA CHAMADA ---
st.set_page_config(page_title="Gestão de Ocorrências", layout="wide")

# ------------------------------------------------------TELA DE LOGIN --------------------------------------------------------
# --- USUÁRIOS E SENHAS (simples, não para produção) ---
USERS = {
    "rafael": "1234",
    "user2": "senha456"
}

# --- Função de autenticação ---
def autenticar(username, senha):
    return USERS.get(username) == senha

# --- Interface de Login ---
def login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>📝 Gestão de Ocorrências</h1>", unsafe_allow_html=True)


    if "login" not in st.session_state:
        st.session_state.login = False
    if "username" not in st.session_state:
        st.session_state.username = ""

    if not st.session_state.login:
        # Centralizar com colunas
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown("##### Login")
            username = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                if autenticar(username, senha):
                    st.session_state.login = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos")
            st.markdown(" ")

        st.stop()  # Impede que o app continue carregando sem login

    else:
        # Saudação no topo
        st.markdown(f"👋 **Bem-vindo, {st.session_state.username}!**")

        # Botão de sair alinhado à direita
        col1, col2, col3 = st.columns([6, 1, 1])  # Ajuste os pesos conforme preferir
        with col3:
            if st.button("🔒 Sair"):
                st.session_state.login = False
                st.session_state.username = ""
                st.rerun()


# --- Chama login antes de qualquer coisa ---
login()

# --- SE CHEGOU AQUI, USUÁRIO ESTÁ AUTENTICADO ---
#--------------------------------------------------------------------------INICIO APP --------------------------------------------------------------
# --- CARREGAMENTO DE DADOS Tabelas com nomes de motorista e clientes ---
clientes = pd.read_csv("data/clientes.csv")["Cliente"].dropna().tolist()
motoristas = pd.read_csv("data/motoristas.csv")["Motorista"].dropna().tolist()

# --- INICIALIZAÇÃO DE SESSÃO ---
if "ocorrencias_abertas" not in st.session_state:
    st.session_state.ocorrencias_abertas = []

if "ocorrencias_finalizadas" not in st.session_state:
    st.session_state.ocorrencias_finalizadas = []

# --- ABAS ---
aba1, aba2, aba3 = st.tabs(["📝 Nova Ocorrência", "📌 Ocorrências em Aberto", "✅ Ocorrências Finalizadas"])

# =========================
#       ABA 1 - NOVA
# =========================
with aba1:
    st.header("Nova Ocorrência")

    with st.form("form_nova_ocorrencia", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            # Campo de Nota Fiscal - Apenas números
            nf = st.text_input("Nota Fiscal", key="nf")

            # Verifica se a entrada da Nota Fiscal é válida
            nf_invalida = nf != "" and not nf.isdigit()
            if nf_invalida:
                st.error("Por favor, insira apenas números na Nota Fiscal.")

            cliente_opcao = st.selectbox("Cliente", options=clientes + ["Outro ()"], index=None, key="cliente_opcao")
            cliente = st.text_input("Digite o nome do cliente", key="cliente_manual") if cliente_opcao == "Outro (digitar manualmente)" else cliente_opcao
            destinatario = st.text_input("Destinatário", key="destinatario")
            cidade = st.text_input("Cidade", key="cidade")

        with col2:
            motorista_opcao = st.selectbox("Motorista", options=motoristas + ["Outro (digitar manualmente)"], index=None, key="motorista_opcao")
            motorista = st.text_input("Digite o nome do motorista", key="motorista_manual") if motorista_opcao == "Outro (digitar manualmente)" else motorista_opcao
            tipo = st.multiselect("Tipo de Ocorrência", options=["Chegada no Local", "Pedido Bloqueado", "Demora", "Divergência"], key="tipo_ocorrencia")
            obs = st.text_area("Observações", key="observacoes")
            responsavel = st.text_input("Quem está abrindo o ticket", key="responsavel")

        # Botão para enviar
        enviar = st.form_submit_button("Adicionar Ocorrência")

        if enviar:
            # Verifica se algum campo obrigatório está vazio
            campos_obrigatorios = {
                "Nota Fiscal": nf,
                "Cliente": cliente,
                "Destinatário": destinatario,
                "Cidade": cidade,
                "Motorista": motorista,
                "Tipo de Ocorrência": tipo,
                "Responsável": responsavel
            }

            faltando = [campo for campo, valor in campos_obrigatorios.items() if not valor]

            # Caso a Nota Fiscal seja inválida ou algum campo obrigatório esteja vazio
            if nf_invalida:
                st.error("Ocorrência não adicionada: Nota Fiscal deve conter apenas números.")
            elif faltando:
                st.error(f"❌ Preencha todos os campos obrigatórios: {', '.join(faltando)}")
            else:
                # Define fuso horário de São Paulo
                fuso_sp = pytz.timezone("America/Sao_Paulo")
                agora_sp = datetime.now(fuso_sp)

                # Adiciona a nova ocorrência
                nova_ocorrencia = {
                    "ID": str(uuid.uuid4()),  # ID único
                    "Nota Fiscal": nf,
                    "Cliente": cliente,
                    "Destinatario": destinatario,
                    "Cidade": cidade,
                    "Motorista": motorista,
                    "Tipo de Ocorrência": ", ".join(tipo),
                    "Observações": obs,
                    "Responsável": responsavel,
                    "Data/Hora Abertura": agora_sp.strftime("%d/%m/%Y %H:%M:%S"),
                    "Abertura Timestamp": agora_sp.replace(tzinfo=None),  # sem timezone para salvar no Excel
                    "Complementar": "",
                    "Data/Hora Finalização": ""
                }
                st.session_state.ocorrencias_abertas.append(nova_ocorrencia)

                # Exibe o sucesso
                sucesso = st.empty()
                sucesso.success("✅ Ocorrência aberta com sucesso!")
                time.sleep(2) 
                sucesso.empty()
                # Aguarda um tempo e limpa a mensagem de sucesso
                

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
        st.success("✅ Ocorrência finalizada com sucesso!")
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
        st.info("Nenhuma ocorrência aberta no momento.")
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
    st.markdown("### 🔎 Filtro por Nota Fiscal")

    col_filtro, _ = st.columns([1, 5])  # Campo no canto esquerdo
    with col_filtro:
        nf_busca = st.text_input("Nota Fiscal", placeholder="Nota Fiscal")

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

                        # Exibe o campo complementar
                        f"<strong>Complementar:</strong> {ocorr.get('Complementar', '-')}<br>"

                        # Exibe o tempo de permanência da ocorrência (tempo entre abertura e finalização)
                        f"<strong>Tempo de Permanência:</strong> {tempo_permanencia_str}<br>"

                        "</div>",
                        unsafe_allow_html=True
                    )

            # Salvando o tempo de permanência no relatório Excel
            ocorr["Tempo de Permanência"] = tempo_permanencia_str  # Adiciona o tempo de permanência à ocorrência



