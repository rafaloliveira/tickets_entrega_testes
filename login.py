import streamlit as st
import streamlit_authenticator as stauth

def autenticar_usuario():
    # Informações dos usuários
    nomes = ["Admin", "João", "Maria", "Pedro"]
    usernames = ["admin", "joao", "maria", "pedro"]
    hashed_senhas = [
        '$2b$12$3y7V6dRIWTq9elK1SfjB2.xMyV3Yrb3Hd8LxXnIsy0m9XaaYdZBvy', # admin
        '$2b$12$K8gNBLP/q/TVhBvE2mJvZOrR7kMEyLM0GOBv3jEtxNzEwSgWyMJw6', # joao
        '$2b$12$wlCTW9GLBQa3VxgfNNDlae3PTU1vN3MieTzmn5g1cfwA7UpFOF1jq', # maria
        '$2b$12$U3jboG0eRO/yvEMRxCKtce1ATDKXrH0Ce/WSF1vMEz3z50fj0A8E6'  # pedro
    ]

    # Criando a instância de autenticação
    autenticar = stauth.Authenticate(
        credentials={"usernames": {usernames[i]: {"name": nomes[i], "password": hashed_senhas[i]} for i in range(len(usernames))}},
        cookie_name="ticket_app_cookie",
        key="ticket_app_chave",
        cookie_expiry_days=30
    )

    # Realizando o login com 'location' especificado
    nome, autenticado, username = autenticar.login("Login", location="main")  # Adicionando 'location="main"'

    if autenticado:
        autenticar.logout("Sair", location="sidebar")
        st.sidebar.success(f"Bem-vindo, {nome}")
        return nome, username
    else:
        st.warning("Por favor, faça login.")
        return None, None
