document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const messageDiv = document.getElementById('login-message');

    loginForm.addEventListener('submit', async function(event) {
        event.preventDefault(); // Previne o envio padrão do formulário

        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();

        messageDiv.textContent = '';
        messageDiv.className = 'login-message-placeholder';

        if (!username || !password) {
            messageDiv.textContent = 'Por favor, preencha o usuário e a senha.';
            messageDiv.classList.add('error-message');
            return;
        }

        try {
            const response = await fetch('http://127.0.0.1:5000/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const data = await response.json();

            if (response.ok && data.token) { // SUCESSO E TOKEN EXISTE
                messageDiv.textContent = data.message || 'Login bem-sucedido! Redirecionando...';
                messageDiv.classList.add('success-message');

                // ---- LÓGICA ADICIONADA ----
                // 1. Salva o token no localStorage do navegador
                localStorage.setItem('authToken', data.token);
                console.log('Token salvo no localStorage:', data.token);
                // -----------------------------

                // 2. Redireciona para a página principal após 1 segundo
                setTimeout(function() {
                    window.location.href = 'index.html';
                }, 1000);

            } else { // FALHA
                // Se a resposta não for OK ou não contiver um token
                messageDiv.textContent = data.message || 'Falha no login. Verifique suas credenciais.';
                messageDiv.classList.add('error-message');
            }

        } catch (error) {
            console.error('Erro ao tentar fazer login:', error);
            messageDiv.textContent = 'Erro ao conectar com o servidor. Tente novamente mais tarde.';
            messageDiv.classList.add('error-message');
        }
    });
});