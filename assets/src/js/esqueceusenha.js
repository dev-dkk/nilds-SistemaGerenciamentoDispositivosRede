document.addEventListener('DOMContentLoaded', function() {
    const forgotPasswordForm = document.getElementById('forgotPasswordForm');
    const emailInput = document.getElementById('email');
    const messageDiv = document.getElementById('forgot-password-message');

    if (forgotPasswordForm) {
        forgotPasswordForm.addEventListener('submit', async function(event) {
            event.preventDefault(); // Previne o envio padrão do formulário
            const email = emailInput.value.trim();

            // Limpa mensagens e classes anteriores
            messageDiv.textContent = '';
            messageDiv.className = 'login-message-placeholder'; 

            if (!email) {
                messageDiv.textContent = 'Por favor, insira seu endereço de e-mail.';
                messageDiv.classList.add('error-message'); // Reutiliza classe de erro do login_style.css
                return;
            }

            // --- INÍCIO DA SIMULAÇÃO DE CHAMADA AO BACKEND ---
            // Em uma aplicação real, aqui você faria uma chamada fetch para o seu backend:
            // Ex: POST para /api/request-password-reset com o email
            // e o backend cuidaria de enviar o email.

            console.log('Solicitação de redefinição de senha para:', email);
            
            // Apenas para o protótipo, exibimos uma mensagem genérica de sucesso.
            messageDiv.textContent = 'Se o endereço de e-mail fornecido estiver associado a uma conta em nosso sistema, um link para redefinição de senha foi enviado.';
            messageDiv.classList.add('success-message'); // Reutiliza classe de sucesso do login_style.css
            
            emailInput.value = ''; // Limpa o campo de e-mail após o "envio"
            // --- FIM DA SIMULAÇÃO ---
        });
    } else {
        console.error("Elemento do formulário com ID 'forgotPasswordForm' não foi encontrado.");
    }

    // Validação simples de e-mail no input (opcional)
    if(emailInput) {
        emailInput.addEventListener('input', function() {
            if (emailInput.validity.typeMismatch) {
                emailInput.setCustomValidity("Por favor, insira um endereço de e-mail válido.");
            } else {
                emailInput.setCustomValidity("");
            }
        });
    }
});