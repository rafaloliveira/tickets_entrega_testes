import streamlit as st

# Usuários e senhas pré-definidos (não use isso em produção)
USERS = {
    "user1": "senha123",
    "user2": "senha456"
}

# Função de autenticação
def autenticar(username, senha):
    return USERS.get(username) == senha

def main():
    st.title("🔐 Tela de Login")

    # Sessão para controle de login
    if 'login' not in st.session_state:
        st.session_state.login = False
    if 'username' not in st.session_state:
        st.session_state.username = ""

    if not st.session_state.login:
        st.subheader("Faça login para acessar o app")
        username = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if autenticar(username, senha):
                st.session_state.login = True
                st.session_state.username = username  # ✅ Salva o nome de usuário
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")
    else:
        st.success(f"Bem-vindo, {st.session_state.username}!")  # ✅ Usa o valor salvo
        st.write("🎉 Aqui está o conteúdo do seu app!")
        if st.button("Sair"):
            st.session_state.login = False
            st.session_state.username = ""  # Limpa o usuário
            st.rerun()

if __name__ == "__main__":
    main()
