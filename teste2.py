import streamlit as st
import pandas as pd
import os
from datetime import datetime
import time
from dateutil import parser
from streamlit_autorefresh import st_autorefresh  # Importar o streamlit_autorefresh

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Gestão de Ocorrências", layout="wide")

# --- TEMA ESCURO PERSONALIZADO ---
st.markdown("""
<style>
    body {
        background-color: #121212;
        color: #FFFFFF;
    }
    .stTabs [role="tab"] {
        background-color: #1e1e1e;
        padding: 8px;
        border-radius: 5px;
        color: #ffffff;
    }
    .stTabs [aria-selected="true"] {
        background-color: #057a55 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO DE DADOS ---
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
            nf = st.text_input("Nota Fiscal", key="nf")
            cliente_opcao = st.selectbox("Cliente", options=clientes + ["Outro (digitar manualmente)"], index=None, key="cliente_opcao")
            cliente = st.text_input("Digite o nome do cliente", key="cliente_manual") if cliente_opcao == "Outro (digitar manualmente)" else cliente_opcao
            destinatario = st.text_input("Destinatário", key="destinatario")
            cidade = st.text_input("Cidade", key="cidade")

        with col2:
            motorista_opcao = st.selectbox("Motorista", options=motoristas + ["Outro (digitar manualmente)"], index=None, key="motorista_opcao")
            motorista = st.text_input("Digite o nome do motorista", key="motorista_manual") if motorista_opcao == "Outro (digitar manualmente)" else motorista_opcao
            tipo = st.multiselect("Tipo de Ocorrência", options=["Chegada no Local", "Pedido Bloqueado", "Demora", "Divergência"], key="tipo_ocorrencia")
            obs = st.text_area("Observações", key="observacoes")
            responsavel = st.text_input("Quem está abrindo o ticket", key="responsavel")

        enviar = st.form_submit_button("Adicionar Ocorrência")

        if enviar:
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

            if faltando:
                st.error(f"❌ Preencha todos os campos obrigatórios: {', '.join(faltando)}")
            else:
                nova_ocorrencia = {
                    "Nota Fiscal": nf,
                    "Cliente": cliente,
                    "Destinatario": destinatario,
                    "Cidade": cidade,
                    "Motorista": motorista,
                    "Tipo de Ocorrência": ", ".join(tipo),
                    "Observações": obs,
                    "Responsável": responsavel,
                    "Data/Hora Abertura": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "Abertura Timestamp": datetime.now(),
                    "Complementar": "",
                    "Data/Hora Finalização": ""
                }
                st.session_state.ocorrencias_abertas.append(nova_ocorrencia)

                sucesso = st.empty()
                sucesso.success("✅ Ocorrência aberta com sucesso!")
                time.sleep(2)
                sucesso.empty()


# =========================
#    FUNÇÃO CLASSIFICAÇÃO
# =========================
def classificar_ocorrencia_por_tempo(data_abertura_str):
    try:
        data_abertura = datetime.strptime(data_abertura_str, "%d/%m/%Y %H:%M:%S")
    except Exception as e:
        return "Erro", "gray"

    agora = datetime.now()
    tempo_decorrido = (agora - data_abertura).total_seconds() / 60

    if tempo_decorrido < 15:
        return "🟢 Até 15 min", "#2ecc71"
    elif tempo_decorrido < 30:
        return "🟡 15 a 30 min", "#f1c40f"
    elif tempo_decorrido < 45:
        return "🟠 30 a 45 min", "#e67e22"
    elif tempo_decorrido < 60:
        return "🔴 45 a 60 min", "#e74c3c"
    else:
        return "🚨 +60 min", "#c0392b"
    
    # Função para salvar ocorrência finalizada em Excel
def salvar_ocorrencia_finalizada(ocorr, status):
    pasta = os.path.join("data", "relatorio_de_tickets")
    caminho = os.path.join(pasta, "relatorio_ocorrencias.xlsx")
    os.makedirs(pasta, exist_ok=True)

    ocorr["Estágio"] = status  # Adiciona o status da ocorrência
    df_nova = pd.DataFrame([ocorr])

    if not os.path.exists(caminho):  # Se o arquivo não existir, cria um novo
        df_nova.to_excel(caminho, index=False)
    else:  # Se o arquivo já existir, adiciona a nova ocorrência
        df_existente = pd.read_excel(caminho)
        df_final = pd.concat([df_existente, df_nova], ignore_index=True)
        df_final.to_excel(caminho, index=False)

# =========================
#     ABA 2 - EM ABERTO
# =========================
with aba2:
    st.header("Ocorrências em Aberto")

    if not st.session_state.ocorrencias_abertas:
        st.info("Nenhuma ocorrência aberta no momento.")
    else:
        colunas = st.columns(4)

        # Atualiza a página a cada 10 segundos
        st_autorefresh(interval=10000, key="ocorrencias_abertas_refresh")

        for idx, ocorr in list(enumerate(st.session_state.ocorrencias_abertas)):
            data_abertura_str = ocorr.get("Data/Hora Abertura") or ocorr.get("Abertura Timestamp")

            try:
                # Classificar por tempo
                status, cor = classificar_ocorrencia_por_tempo(data_abertura_str)

                # Converte para datetime para exibir formatado
                data_abertura = datetime.strptime(data_abertura_str, "%d/%m/%Y %H:%M:%S")
                data_formatada = data_abertura.strftime('%d/%m/%Y %H:%M:%S')

            except Exception as e:
                st.error(f"Erro ao processar ocorrência (NF: {ocorr.get('Nota Fiscal', '-')}) — {e}")
                continue

            with colunas[idx % 4]:
                # Exibe a classificação e a cor
                st.markdown(f"### ⏱️ {status}")
                st.markdown(
                    f"<div style='background-color:{cor};padding:10px;border-radius:10px;color:white;box-shadow:0 0 10px rgba(0,0,0,0.3)'>"
                    f"<strong>NF:</strong> {ocorr.get('Nota Fiscal', '-')}<br>"
                    f"<strong>Cliente:</strong> {ocorr.get('Cliente', '-')}<br>"
                    f"<strong>Cidade:</strong> {ocorr.get('Cidade', '-')}<br>"
                    f"<strong>Motorista:</strong> {ocorr.get('Motorista', '-')}<br>"
                    f"<strong>Tipo:</strong> {ocorr.get('Tipo de Ocorrência', '-')}<br>"
                    f"<strong>Aberto por:</strong> {ocorr.get('Responsável', '-')}<br>"
                    f"<strong>Data/Hora Abertura:</strong> {data_formatada}"
                    "</div>", unsafe_allow_html=True)

        with st.expander("Finalizar Ocorrência"):
            complemento = st.text_area("Complemento", key=f"complemento_final_{idx}")
            if st.button("Finalizar", key=f"finalizar_{idx}"):
                if not complemento.strip():
                    st.error("❌ O campo 'Complementar' é obrigatório para finalizar a ocorrência.")
                else:
                    ocorr["Complementar"] = complemento
                    ocorr["Data/Hora Finalização"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    salvar_ocorrencia_finalizada(ocorr, status)
                    st.session_state.ocorrencias_finalizadas.append(ocorr)
                    st.session_state.ocorrencias_abertas.pop(idx)
                    st.success("✅ Ocorrência finalizada!")
                    st.rerun()  # Atualiza a tela com a nova lista de ocorrências

                    
# =========================
#     ABA 3 - FINALIZADAS
# =========================
with aba3:
    st.header("Ocorrências Finalizadas")

    if not st.session_state.ocorrencias_finalizadas:
        st.info("Nenhuma ocorrência finalizada no momento.")
    else:
        colunas = st.columns(4)

        # Atualiza a página a cada 10 segundos
        st_autorefresh(interval=10000, key="ocorrencias_finalizadas_refresh")

        for idx, ocorr in list(enumerate(st.session_state.ocorrencias_finalizadas)):
            data_abertura_str = ocorr.get("Data/Hora Abertura") or ocorr.get("Abertura Timestamp")
            data_finalizacao_str = ocorr.get("Data/Hora Finalização")

            try:
                # Classificar por tempo
                status, cor = classificar_ocorrencia_por_tempo(data_abertura_str)

                # Converte para datetime para exibir formatado
                data_abertura = datetime.strptime(data_abertura_str, "%d/%m/%Y %H:%M:%S")
                data_formatada_abertura = data_abertura.strftime('%d/%m/%Y %H:%M:%S')

                data_finalizacao = datetime.strptime(data_finalizacao_str, "%d/%m/%Y %H:%M:%S")
                data_formatada_finalizacao = data_finalizacao.strftime('%d/%m/%Y %H:%M:%S')

            except Exception as e:
                st.error(f"Erro ao processar ocorrência (NF: {ocorr.get('Nota Fiscal', '-')}) — {e}")
                continue

            with colunas[idx % 4]:
                status = ocorr.get("Status", "Desconhecido")
                cor = ocorr.get("Cor", "#777")

                st.markdown(
                    f"<div style='background-color:{cor};padding:10px;border-radius:10px;color:white;"
                    f"box-shadow: 0 4px 12px rgba(0,0,0,0.3);margin-bottom:10px;'>"
                    f"<strong>Status:</strong> <span style='background-color:#2c3e50;padding:4px 8px;border-radius:5px;color:white;'>{status}</span><br>"
                    f"<strong>NF:</strong> {ocorr.get('Nota Fiscal', '-')}<br>"
                    f"<strong>Cliente:</strong> {ocorr.get('Cliente', '-')}<br>"
                    f"<strong>Cidade:</strong> {ocorr.get('Cidade', '-')}<br>"
                    f"<strong>Motorista:</strong> {ocorr.get('Motorista', '-')}<br>"
                    f"<strong>Tipo:</strong> {ocorr.get('Tipo de Ocorrência', '-')}<br>"
                    f"<strong>Aberto por:</strong> {ocorr.get('Responsável', '-')}<br>"
                    f"<strong>Data/Hora Abertura:</strong> {ocorr.get('Data/Hora Abertura', '-')}<br>"
                    f"<strong>Finalizado em:</strong> {ocorr.get('Data/Hora Finalização', '-')}<br>"
                    f"<strong>Complementar:</strong> {ocorr.get('Complementar', '-')}"
                    "</div>",
                    unsafe_allow_html=True
                )