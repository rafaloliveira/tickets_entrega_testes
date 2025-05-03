import streamlit as st
import time
from datetime import datetime

# Função para definir a cor com base no tempo decorrido
def definir_cor(tempo_decorrido):
    if tempo_decorrido >= 3:
        return "red", "🚨 +3 minutos"  # Acima de 3 minutos
    elif tempo_decorrido >= 2:
        return "yellow", "🟡 2 a 3 minutos"  # Entre 2 e 3 minutos
    elif tempo_decorrido >= 1:
        return "orange", "🟠 1 a 2 minutos"  # Entre 1 e 2 minutos
    else:
        return "green", "🟢 Menos de 1 minuto"  # Menos de 1 minuto

# Inicializa o tempo decorrido se não foi iniciado ainda
if "start_time" not in st.session_state:  
    st.session_state.start_time = None
    st.session_state.tempo_decorrido = 0  # Inicializa o tempo decorrido

# Botão de start para iniciar o contador
if st.button("Iniciar Contagem"):
    st.session_state.start_time = datetime.now()  # Registra a hora de início

# Exibe a contagem de forma contínua
if st.session_state.start_time:
    # Cria um espaço para o contador
    contador = st.empty()

    while True:
        # Calcula o tempo decorrido em minutos
        tempo_decorrido = (datetime.now() - st.session_state.start_time).total_seconds() / 60
        st.session_state.tempo_decorrido = tempo_decorrido

        # Definir a cor dependendo do tempo decorrido
        cor, status = definir_cor(tempo_decorrido)

        # Atualiza o contador e a cor a cada segundo
        contador.markdown(f"<h3 style='color:{cor};'>{status}</h3>", unsafe_allow_html=True)
        
        # Aguarda 1 segundo
        time.sleep(1)
        
        # Atualiza a cada segundo
        if tempo_decorrido > 4:  # Para a contagem depois de 4 minutos (ajuste conforme necessário)
            break
else:
    # Caso o botão não tenha sido clicado ainda
    st.write("Clique em 'Iniciar Contagem' para começar o temporizador.")
