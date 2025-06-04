# NILDS - Sistema de Gerenciamento de Dispositivos em Redes

## Descrição

O NILDS - Sistema de Gerenciamento de Dispositivos em Rede é um sistema desenvolvido para auxiliar no inventário, descoberta, monitoramento e gerenciamento de dispositivos conectados à rede de uma organização. Ele visa fornecer uma visão centralizada dos ativos de rede, facilitando a administração e a tomada de decisões.

**Status do Projeto:** Em Desenvolvimento

## Funcionalidades Implementadas

Até o momento, o sistema conta com as seguintes funcionalidades:

* **Autenticação de Usuários:**
    * Página de login funcional com validação de credenciais no backend.
    * Backend com endpoint `/login` e hashing seguro de senhas (bcrypt).
* **Dashboard (`index.html`):**
    * Exibição de cards com sumário da rede: Total de Dispositivos, Dispositivos Online, Dispositivos Offline, Novos Alertas.
    * Gráficos dinâmicos (usando Chart.js) para:
        * Distribuição de Sistemas Operacionais dos dispositivos inventariados.
        * Distribuição de Status dos dispositivos inventariados (Online, Offline, etc.).
    * Lista de alertas recentes (novos alertas).
* **Inventário de Dispositivos (`dispositivos.html`):**
    * Listagem completa de dispositivos do inventário principal com busca no lado do servidor.
    * Funcionalidade CRUD (Criar, Ler, Atualizar, Deletar) completa para dispositivos:
        * **Adicionar:** Modal para inserção de novos dispositivos com campos de seleção (Fabricante, SO, Tipo) populados dinamicamente pelo backend.
        * **Editar:** Modal para edição dos dados de um dispositivo existente, com campos pré-preenchidos.
        * **Remover:** Confirmação e remoção de dispositivos.
        * **Ver Detalhes:** Modal para visualização de informações detalhadas de um dispositivo, incluindo suas interfaces de rede e IPs.
* **Descoberta de Rede (Página `varredura.html`):**
    * **Varredura Inicial (Ping Sweep):** Backend realiza varredura de ping em faixas de IP configuráveis para encontrar IPs ativos.
    * **Armazenamento de IPs Descobertos:** IPs ativos são salvos na tabela `IPsDescobertos` com data de detecção, status inicial 'Novo', e tentativa de resolução de hostname (rDNS).
    * **Análise Detalhada de IP:** Ação "Analisar Detalhes" para um IP descoberto aciona uma varredura Nmap no backend para obter mais informações (hostname, MAC, SO estimado, portas abertas). Essas informações atualizam a tabela `IPsDescobertos`.
    * **Gerenciamento de IPs Descobertos:**
        * Página para listar IPs da tabela `IPsDescobertos`.
        * Ação "Inventariar": Inicia o processo de adicionar um IP descoberto (com seus detalhes enriquecidos) ao inventário principal, pré-preenchendo o modal de "Adicionar Dispositivo". Após inventariar, o status do IP descoberto é atualizado.
        * Ação "Ignorar": Permite marcar um IP descoberto como 'Ignorado', atualizando seu status no banco.
* **Sistema de Alertas (`alerts.html`):**
    * **Geração Automática:** Alertas do tipo "Novo IP Descoberto" são gerados automaticamente pelo backend quando um IP verdadeiramente novo é encontrado pela varredura e inserido em `IPsDescobertos`.
    * **Visualização:** Página dedicada para listar todos os alertas do sistema, mostrando tipo, severidade, descrição, dispositivo/IP associado, data e status.
    * **Gerenciamento Básico:** Ações de "Ver Detalhes" (em modal), "Marcar como Lido" e "Resolver" para cada alerta, atualizando o status no banco de dados.
* **Relatórios (`reports.html`):**
    * Interface para selecionar e gerar diferentes tipos de relatórios.
    * **Relatórios Implementados:**
        * Inventário Completo de Dispositivos (reutiliza a listagem de dispositivos).
        * Sumário de Dispositivos por Sistema Operacional.
        * Lista de Dispositivos Online.
        * Lista de Dispositivos Offline.
    * Resultados exibidos em formato de tabela na própria página.
* **Configurações (`config.html`):**
    * Interface para definir parâmetros da varredura automática de rede:
        * Faixas de IP a serem escaneadas.
        * Frequência da varredura (ex: a cada X minutos/horas, diariamente).
        * Opção para ativar/desativar a varredura automática.
    * As configurações são salvas e lidas do banco de dados.
* **Varredura Automática Agendada (Backend):**
    * Utilização da biblioteca APScheduler no backend para executar a função de descoberta de rede (`_execute_actual_network_scan`) automaticamente, com base na frequência e no status de ativação definidos na página de configurações.
    * O agendamento é dinamicamente atualizado quando as configurações são salvas.
* **Trilha de Auditoria (Fundação no Backend):**
    * Criação da tabela `LogAuditoria` no banco de dados.
    * Função auxiliar `registrar_log_auditoria(id_usuario, nome_usuario, acao, detalhes, ip_origem)` no `app.py`.
    * Exemplos de integração da função de log em pontos chave (login, adição de dispositivo, alteração de configuração de varredura).

## Tecnologias Utilizadas

* **Backend:**
    * Python 3.x
    * Flask (Framework Web)
    * APScheduler (Agendamento de tarefas)
    * `mysql-connector-python` (Conexão com MySQL)
    * `python-nmap` (Integração com Nmap para varreduras detalhadas)
    * `python-dotenv` (Gerenciamento de variáveis de ambiente)
    * `bcrypt` (Hashing de senhas)
    * `ipaddress`, `socket`, `subprocess`, `platform` (Módulos Python para rede e sistema)
* **Frontend:**
    * HTML5
    * CSS3
    * JavaScript (Vanilla)
    * Chart.js (Biblioteca para gráficos no dashboard)
    * Font Awesome (Biblioteca de ícones)
* **Banco de Dados:**
    * MySQL
* **Ferramentas de Desenvolvimento:**
    * VS Code (Editor de código)
    * MySQL Workbench (Gerenciamento de banco de dados)
    * Postman/Insomnia (Testes de API - recomendado)
    * Git & GitHub (Controle de versão e repositório)

## Configuração e Instalação (Ambiente de Desenvolvimento)

Siga os passos abaixo para configurar o ambiente de desenvolvimento local:

1.  **Pré-requisitos:**
    * Python 3.7+ instalado e configurado no PATH.
    * MySQL Server instalado e rodando.
    * Nmap instalado e o diretório de instalação adicionado ao PATH do sistema (para a funcionalidade "Analisar Detalhes").
    * Git instalado.

2.  **Clonar o Repositório:**
    ```bash
    git clone [URL_DO_SEU_REPOSITORIO_AQUI]
    cd Prototipo-Sistema-Gerenciamento 
    ```
    (Substitua `Prototipo-Sistema-Gerenciamento` pelo nome real da sua pasta raiz, se for diferente)

3.  **Configurar o Backend:**
    * Navegue até a pasta do backend: `cd backend`
    * Crie um ambiente virtual:
        ```bash
        python -m venv venv
        ```
    * Ative o ambiente virtual:
        * Windows: `venv\Scripts\activate`
        * macOS/Linux: `source venv/bin/activate`
    * Instale as dependências Python (crie um arquivo `requirements.txt` se ainda não tiver):
        ```bash
        pip install Flask Flask-CORS python-dotenv mysql-connector-python bcrypt nmap APScheduler ipaddress
        # Ou, se tiver um requirements.txt: pip install -r requirements.txt
        ```
    * Crie um arquivo `.env` na pasta `backend` com base no exemplo abaixo, preenchendo com suas credenciais e configurações:
        ```ini
        DB_HOST=localhost
        DB_USER=seu_usuario_mysql
        DB_PASSWORD=sua_senha_mysql
        DB_NAME=NetworkAssetManagerDB
        DISCOVERY_IP_RANGES=192.168.X.1-192.168.X.254 # Ajuste para sua rede
        NMAP_USE_OS_DETECTION=false # Mude para true se quiser tentar detecção de OS com Nmap (pode requerer privilégios)
        FLASK_APP=app.py
        FLASK_DEBUG=True 
        # Para email (se for implementar):
        # EMAIL_HOST=smtp.gmail.com
        # EMAIL_PORT=587
        # EMAIL_HOST_USER=seu_email@gmail.com
        # EMAIL_HOST_PASSWORD=sua_senha_de_app_do_gmail
        # EMAIL_USE_TLS=True
        ```
    * **Banco de Dados:**
        * Conecte-se ao seu MySQL Server.
        * Crie o banco de dados `NetworkAssetManagerDB` se ele não existir: `CREATE DATABASE IF NOT EXISTS NetworkAssetManagerDB;`
        * Execute o script SQL (que criamos e evoluímos) para criar todas as tabelas (`Usuario`, `PerfilUsuario`, `Dispositivo`, `IPsDescobertos`, `Alerta`, `ConfiguracaoVarredura`, etc.).
        * Popule tabelas de lookup como `TipoAlerta`, `PerfilUsuario` com dados iniciais.
    * Rode o servidor Flask (ainda dentro da pasta `backend` com `venv` ativo):
        ```bash
        python app.py
        ```
        O backend estará rodando em `http://127.0.0.1:5000`.
        *Nota: Para testes consistentes do agendador APScheduler, pode ser útil rodar com `app.run(debug=True, use_reloader=False)` no final do `app.py`.*

4.  **Executar o Frontend:**
    * Abra os arquivos HTML localizados na pasta `pages` diretamente no seu navegador web (ex: `pages/login.html` ou `pages/index.html` após o login).
    * Alternativamente, para uma melhor experiência e para evitar alguns problemas com `file:///` e CORS (embora o `Flask-CORS` no backend ajude), você pode servir a pasta raiz do projeto (`Prototipo Sistema Gerenciamento`) com um servidor HTTP simples:
        ```bash
        # Navegue para a pasta raiz Prototipo Sistema Gerenciamento
        python -m http.server 8080 
        ```
        E então acesse `http://localhost:8080/pages/login.html`.

## Como Usar (Principais Fluxos)

1.  **Login:** Acesse a página `login.html` e entre com um usuário cadastrado (após popular a tabela `Usuario` com senhas "hasheadas" usando o script `populate_user.py`).
2.  **Dashboard:** Após o login, o dashboard exibe um sumário da rede e gráficos.
3.  **Gerenciar Dispositivos:** Na página `dispositivos.html`, visualize, adicione, edite ou remova dispositivos do inventário principal.
4.  **Varredura de Rede:**
    * Configure as faixas de IP e frequência na página `config.html`.
    * Ative a varredura automática ou dispare uma varredura manual pela página `varredura.html` (botão "Iniciar Nova Varredura").
    * Visualize os IPs descobertos em `varredura.html`.
    * Use as ações "Analisar Detalhes" (para rodar Nmap), "Inventariar" (para mover para o inventário principal) ou "Ignorar".
5.  **Alertas:** A página `alerts.html` mostra os alertas gerados (atualmente, "Novo IP Descoberto"). Gerencie o status dos alertas.
6.  **Relatórios:** Gere relatórios básicos na página `reports.html`.

## Funcionalidades Futuras e TODOs

* **Monitoramento Contínuo de Dispositivos:** Implementar ping periódico nos dispositivos do inventário principal para atualizar status online/offline.
* **Alertas de "Dispositivo Offline/Online":** Gerar alertas com base no monitoramento.
* **Notificações por E-mail:** Enviar e-mails para alertas críticos e para o fluxo de "Esqueceu a Senha".
* **Funcionalidade Completa de "Esqueceu a Senha":** Incluir envio de token por e-mail e página para redefinição.
* **Sistema de Permissões (Autorização):** Proteger rotas da API e funcionalidades do frontend com base no perfil do usuário logado.
* **Logging Estruturado em Arquivos:** Configurar o módulo `logging` do Python para salvar logs de forma mais robusta e persistente.
* **Trilha de Auditoria (Frontend):** Criar uma interface para visualizar os logs da tabela `LogAuditoria`.
* **Exportação de Relatórios:** Adicionar opções para exportar relatórios para CSV, PDF, etc.
* **Busca OUI:** Implementar lookup de OUI para identificar fabricantes a partir do MAC Address durante a análise detalhada ou ao adicionar dispositivos.
* **Gerenciamento de Usuários e Perfis:** Interface para administrar usuários e seus papéis.
* **Melhorias na UI/UX:** Refinamentos visuais, melhor feedback ao usuário, paginação para listas longas.
* **Tratamento de Erro:** Melhorar o tratamento de erros no frontend e backend.
* **Testes Automatizados.**

---
