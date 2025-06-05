# NILDS - Sistema de Gerenciamento de Dispositivos em Redes

## Descrição

O NILDS - Sistema de Gerenciamento de Dispositivos em Rede é um sistema desenvolvido para auxiliar no inventário, descoberta, monitoramento e gerenciamento de dispositivos conectados à rede de uma organização. Ele visa fornecer uma visão centralizada dos ativos de rede, facilitando a administração e a tomada de decisões.

**Status do Projeto:** Em Desenvolvimento

## Funcionalidades Implementadas

Até o momento, o sistema conta com as seguintes funcionalidades:

* **Autenticação de Usuários:**
    * Página de login funcional com validação de credenciais no backend.
    * Backend com endpoint `/login` e hashing seguro de senhas (bcrypt), com geração de token JWT.
* **Dashboard (`index.html`):**
    * Exibição de cards com sumário da rede: Total de Dispositivos, Dispositivos Online, Dispositivos Offline, Novos Alertas.
    * Gráficos dinâmicos (usando Chart.js) para:
        * Distribuição de Sistemas Operacionais dos dispositivos inventariados.
        * Distribuição de Status dos dispositivos inventariados (Online, Offline, etc.).
    * Lista de alertas recentes (novos alertas).
* **Inventário de Dispositivos (`dispositivos.html`):**
    * Listagem completa de dispositivos do inventário principal com busca no lado do servidor.
    * Funcionalidade CRUD (Criar, Ler, Atualizar, Deletar) completa para dispositivos, protegida por token:
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
    * Integração da função de log em pontos chave (login, adição/edição/remoção de dispositivo, alteração de configuração de varredura).

## Tecnologias Utilizadas

* **Backend:**
    * Python 3.x
    * Flask (Framework Web)
    * Flask-CORS (Gerenciamento de Cross-Origin Resource Sharing)
    * PyJWT (Implementação de JSON Web Tokens)
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
    *(Substitua `[URL_DO_SEU_REPOSITORIO_AQUI]` e `Prototipo-Sistema-Gerenciamento` conforme necessário)*

3.  **Configurar o Backend:**
    * Navegue até a pasta do backend: `cd backend`
    * Crie um ambiente virtual:
        ```bash
        python -m venv venv
        ```
    * Ative o ambiente virtual:
        * Windows: `venv\Scripts\activate`
        * macOS/Linux: `source venv/bin/activate`
    * Instale as dependências Python. Crie um arquivo `requirements.txt` na pasta `backend` com o seguinte conteúdo:
        ```txt
        Flask
        Flask-CORS
        PyJWT
        python-dotenv
        mysql-connector-python
        bcrypt
        python-nmap
        APScheduler
        ```
        E então instale com:
        ```bash
        pip install -r requirements.txt
        ```
    * Crie um arquivo `.env` na pasta `backend` com base no exemplo abaixo, preenchendo com suas credenciais e configurações:
        ```ini
        DB_HOST=localhost
        DB_USER=seu_usuario_mysql
        DB_PASSWORD=sua_senha_mysql
        DB_NAME=NetworkAssetManagerDB
        SECRET_KEY=sua_chave_secreta_super_segura_e_longa
        DISCOVERY_IP_RANGES=192.168.1.1-192.168.1.254 # Ajuste para sua rede
        NMAP_USE_OS_DETECTION=false
        FLASK_APP=app.py
        FLASK_DEBUG=True
        ```
    * **Configuração do Banco de Dados:**
        1.  Conecte-se ao seu MySQL Server.
        2.  Crie o banco de dados `NetworkAssetManagerDB` se ele não existir:
            ```sql
            CREATE DATABASE IF NOT EXISTS NetworkAssetManagerDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            ```
        3.  **Criação das Tabelas:** Crie um arquivo chamado `schema.sql` na pasta `backend` (ou em `backend/database/schema.sql`) e cole todo o seu script `CREATE TABLE ...` nele.
            *Exemplo do início do `schema.sql`:*
            ```sql
            USE `NetworkAssetManagerDB`;

            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`fabricante`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`fabricante` (
              `ID_Fabricante` INT NOT NULL AUTO_INCREMENT,
              `Nome` VARCHAR(100) NOT NULL,
              PRIMARY KEY (`ID_Fabricante`),
              UNIQUE INDEX `UQ_NomeFabricante` (`Nome` ASC) VISIBLE)
            ENGINE = InnoDB
            AUTO_INCREMENT = 7
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Fabricantes de dispositivos e componentes de rede.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`sistemaoperacional`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`sistemaoperacional` (
              `ID_SistemaOperacional` INT NOT NULL AUTO_INCREMENT,
              `Nome` VARCHAR(100) NOT NULL,
              `Versao` VARCHAR(50) NULL DEFAULT NULL,
              `Familia` VARCHAR(50) NULL DEFAULT NULL COMMENT 'Ex: Windows, Linux, macOS, Android',
              PRIMARY KEY (`ID_SistemaOperacional`),
              UNIQUE INDEX `UQ_SO_NomeVersao` (`Nome` ASC, `Versao` ASC) VISIBLE)
            ENGINE = InnoDB
            AUTO_INCREMENT = 7
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Sistemas Operacionais dos dispositivos.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`tipodispositivo`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`tipodispositivo` (
              `ID_TipoDispositivo` INT NOT NULL AUTO_INCREMENT,
              `Nome` VARCHAR(100) NOT NULL,
              `Icone` VARCHAR(255) NULL DEFAULT NULL COMMENT 'Caminho para um ícone ou classe CSS',
              PRIMARY KEY (`ID_TipoDispositivo`),
              UNIQUE INDEX `UQ_NomeTipoDispositivo` (`Nome` ASC) VISIBLE)
            ENGINE = InnoDB
            AUTO_INCREMENT = 9
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Tipos de dispositivos (ex: Servidor, Desktop, Impressora).';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`perfilusuario`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`perfilusuario` (
              `ID_Perfil` INT NOT NULL AUTO_INCREMENT,
              `NomePerfil` VARCHAR(50) NOT NULL,
              `Descricao` TEXT NULL DEFAULT NULL,
              PRIMARY KEY (`ID_Perfil`),
              UNIQUE INDEX `UQ_NomePerfil` (`NomePerfil` ASC) VISIBLE)
            ENGINE = InnoDB
            AUTO_INCREMENT = 3
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Perfis de usuário para controle de acesso (ex: Administrador, Operador).';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`usuario`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`usuario` (
              `ID_Usuario` INT NOT NULL AUTO_INCREMENT,
              `NomeUsuario` VARCHAR(100) NOT NULL,
              `SenhaHash` VARCHAR(255) NOT NULL,
              `Email` VARCHAR(255) NOT NULL,
              `NomeCompleto` VARCHAR(255) NULL DEFAULT NULL,
              `ID_Perfil` INT NOT NULL,
              `Ativo` TINYINT(1) NOT NULL DEFAULT '1',
              `DataCriacao` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (`ID_Usuario`),
              UNIQUE INDEX `UQ_NomeUsuario` (`NomeUsuario` ASC) VISIBLE,
              UNIQUE INDEX `UQ_Email` (`Email` ASC) VISIBLE,
              INDEX `FK_Usuario_Perfil_idx` (`ID_Perfil` ASC) VISIBLE,
              CONSTRAINT `FK_Usuario_Perfil`
                FOREIGN KEY (`ID_Perfil`)
                REFERENCES `networkassetmanagerdb`.`perfilusuario` (`ID_Perfil`)
                ON DELETE RESTRICT
                ON UPDATE CASCADE)
            ENGINE = InnoDB
            AUTO_INCREMENT = 4
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Usuários do sistema.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`dispositivo`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`dispositivo` (
              `ID_Dispositivo` INT NOT NULL AUTO_INCREMENT,
              `NomeHost` VARCHAR(255) NULL DEFAULT NULL,
              `Descricao` TEXT NULL DEFAULT NULL,
              `Modelo` VARCHAR(100) NULL DEFAULT NULL,
              `ID_Fabricante` INT NULL DEFAULT NULL,
              `ID_SistemaOperacional` INT NULL DEFAULT NULL,
              `ID_TipoDispositivo` INT NULL DEFAULT NULL,
              `DataDescoberta` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `DataUltimaModificacao` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              `DataUltimaVarredura` TIMESTAMP NULL DEFAULT NULL,
              `StatusAtual` VARCHAR(50) NOT NULL DEFAULT 'Desconhecido' COMMENT 'Ex: Online, Offline, Com Falha',
              `LocalizacaoFisica` VARCHAR(255) NULL DEFAULT NULL,
              `Observacoes` TEXT NULL DEFAULT NULL,
              `GerenciadoPor` INT NULL DEFAULT NULL,
              PRIMARY KEY (`ID_Dispositivo`),
              UNIQUE INDEX `UQ_NomeHost` (`NomeHost` ASC) VISIBLE,
              INDEX `FK_Dispositivo_Fabricante_idx` (`ID_Fabricante` ASC) VISIBLE,
              INDEX `FK_Dispositivo_SO_idx` (`ID_SistemaOperacional` ASC) VISIBLE,
              INDEX `FK_Dispositivo_Tipo_idx` (`ID_TipoDispositivo` ASC) VISIBLE,
              INDEX `FK_Dispositivo_UsuarioGerente_idx` (`GerenciadoPor` ASC) VISIBLE,
              CONSTRAINT `FK_Dispositivo_Fabricante`
                FOREIGN KEY (`ID_Fabricante`)
                REFERENCES `networkassetmanagerdb`.`fabricante` (`ID_Fabricante`)
                ON DELETE SET NULL
                ON UPDATE CASCADE,
              CONSTRAINT `FK_Dispositivo_SO`
                FOREIGN KEY (`ID_SistemaOperacional`)
                REFERENCES `networkassetmanagerdb`.`sistemaoperacional` (`ID_SistemaOperacional`)
                ON DELETE SET NULL
                ON UPDATE CASCADE,
              CONSTRAINT `FK_Dispositivo_Tipo`
                FOREIGN KEY (`ID_TipoDispositivo`)
                REFERENCES `networkassetmanagerdb`.`tipodispositivo` (`ID_TipoDispositivo`)
                ON DELETE SET NULL
                ON UPDATE CASCADE,
              CONSTRAINT `FK_Dispositivo_UsuarioGerente`
                FOREIGN KEY (`GerenciadoPor`)
                REFERENCES `networkassetmanagerdb`.`usuario` (`ID_Usuario`)
                ON DELETE SET NULL
                ON UPDATE CASCADE)
            ENGINE = InnoDB
            AUTO_INCREMENT = 24
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Dispositivos inventariados na rede.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`interfacerede`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`interfacerede` (
              `ID_Interface` INT NOT NULL AUTO_INCREMENT,
              `ID_Dispositivo` INT NOT NULL,
              `NomeInterface` VARCHAR(100) NULL DEFAULT NULL COMMENT 'Ex: eth0, wlan0, GigabitEthernet0/1',
              `EnderecoMAC` VARCHAR(17) NOT NULL COMMENT 'Formato: XX:XX:XX:XX:XX:XX',
              `ID_Fabricante_MAC` INT NULL DEFAULT NULL COMMENT 'Derivado do OUI do MAC',
              `Ativa` TINYINT(1) NOT NULL DEFAULT '1',
              PRIMARY KEY (`ID_Interface`),
              UNIQUE INDEX `UQ_EnderecoMAC` (`EnderecoMAC` ASC) VISIBLE,
              INDEX `FK_Interface_Dispositivo_idx` (`ID_Dispositivo` ASC) VISIBLE,
              INDEX `FK_Interface_FabricanteMAC_idx` (`ID_Fabricante_MAC` ASC) VISIBLE,
              CONSTRAINT `FK_Interface_Dispositivo`
                FOREIGN KEY (`ID_Dispositivo`)
                REFERENCES `networkassetmanagerdb`.`dispositivo` (`ID_Dispositivo`)
                ON DELETE CASCADE
                ON UPDATE CASCADE,
              CONSTRAINT `FK_Interface_FabricanteMAC`
                FOREIGN KEY (`ID_Fabricante_MAC`)
                REFERENCES `networkassetmanagerdb`.`fabricante` (`ID_Fabricante`)
                ON DELETE SET NULL
                ON UPDATE CASCADE)
            ENGINE = InnoDB
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Interfaces de rede dos dispositivos.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`rede`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`rede` (
              `ID_Rede` INT NOT NULL AUTO_INCREMENT,
              `NomeRede` VARCHAR(100) NOT NULL,
              `SubRedeCIDR` VARCHAR(45) NOT NULL COMMENT 'Ex: 192.168.1.0/24 ou 2001:db8::/32',
              `GatewayPadrao` VARCHAR(45) NULL DEFAULT NULL,
              `ServidorDNSPrimario` VARCHAR(45) NULL DEFAULT NULL,
              `VLAN_ID` INT NULL DEFAULT NULL,
              `Descricao` TEXT NULL DEFAULT NULL,
              PRIMARY KEY (`ID_Rede`),
              UNIQUE INDEX `UQ_NomeRede` (`NomeRede` ASC) VISIBLE,
              UNIQUE INDEX `UQ_SubRedeCIDR` (`SubRedeCIDR` ASC) VISIBLE)
            ENGINE = InnoDB
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Informações sobre as redes/sub-redes gerenciadas.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`enderecoip`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`enderecoip` (
              `ID_EnderecoIP` INT NOT NULL AUTO_INCREMENT,
              `ID_Interface` INT NOT NULL,
              `EnderecoIPValor` VARCHAR(45) NOT NULL COMMENT 'Armazena o endereço IPv4 ou IPv6',
              `TipoIP` VARCHAR(4) NOT NULL COMMENT 'IPv4 ou IPv6',
              `TipoAtribuicao` VARCHAR(10) NULL DEFAULT NULL COMMENT 'Estatico, DHCP',
              `ID_Rede` INT NULL DEFAULT NULL,
              `Principal` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Indica se é o IP principal da interface',
              `DataPrimeiraDeteccao` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `DataUltimaDeteccao` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (`ID_EnderecoIP`),
              UNIQUE INDEX `UQ_Interface_IP` (`ID_Interface` ASC, `EnderecoIPValor` ASC) VISIBLE,
              INDEX `FK_IP_Interface_idx` (`ID_Interface` ASC) VISIBLE,
              INDEX `FK_IP_Rede_idx` (`ID_Rede` ASC) VISIBLE,
              CONSTRAINT `FK_IP_Interface`
                FOREIGN KEY (`ID_Interface`)
                REFERENCES `networkassetmanagerdb`.`interfacerede` (`ID_Interface`)
                ON DELETE CASCADE
                ON UPDATE CASCADE,
              CONSTRAINT `FK_IP_Rede`
                FOREIGN KEY (`ID_Rede`)
                REFERENCES `networkassetmanagerdb`.`rede` (`ID_Rede`)
                ON DELETE SET NULL
                ON UPDATE CASCADE)
            ENGINE = InnoDB
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Endereços IP associados às interfaces de rede.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`ipsdescobertos`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`ipsdescobertos` (
              `ID_IPDescoberto` INT NOT NULL AUTO_INCREMENT,
              `EnderecoIP` VARCHAR(45) NOT NULL,
              `DataPrimeiraDeteccao` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `DataUltimaDeteccao` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              `StatusResolucao` VARCHAR(50) NOT NULL DEFAULT 'Novo' COMMENT 'Ex: Novo, Em_Analise, Inventariado, Ignorado',
              `NomeHostResolvido` VARCHAR(255) NULL DEFAULT NULL,
              `MAC_Address_Estimado` VARCHAR(17) NULL DEFAULT NULL,
              `OS_Estimado` VARCHAR(255) NULL DEFAULT NULL,
              `Portas_Abertas` TEXT NULL DEFAULT NULL,
              `DetalhesVarreduraExtra` TEXT NULL DEFAULT NULL COMMENT 'Para armazenar outros detalhes do Nmap',
              PRIMARY KEY (`ID_IPDescoberto`),
              UNIQUE INDEX `UQ_EnderecoIPDescoberto` (`EnderecoIP` ASC) VISIBLE)
            ENGINE = InnoDB
            AUTO_INCREMENT = 14
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Armazena IPs detectados na rede que ainda não foram totalmente inventariados.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`tipoalerta`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`tipoalerta` (
              `ID_TipoAlerta` INT NOT NULL AUTO_INCREMENT,
              `Nome` VARCHAR(100) NOT NULL,
              `Descricao` TEXT NULL DEFAULT NULL,
              `SeveridadePadrao` VARCHAR(20) NOT NULL DEFAULT 'Media' COMMENT 'Baixa, Media, Alta, Critica',
              PRIMARY KEY (`ID_TipoAlerta`),
              UNIQUE INDEX `UQ_NomeTipoAlerta` (`Nome` ASC) VISIBLE)
            ENGINE = InnoDB
            AUTO_INCREMENT = 4
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Tipos de alertas que podem ser gerados pelo sistema.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`alerta`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`alerta` (
              `ID_Alerta` INT NOT NULL AUTO_INCREMENT,
              `ID_TipoAlerta` INT NOT NULL,
              `ID_Dispositivo` INT NULL DEFAULT NULL,
              `ID_IPDescoberto_FK` INT NULL DEFAULT NULL,
              `ID_Interface` INT NULL DEFAULT NULL,
              `ID_EnderecoIP` INT NULL DEFAULT NULL,
              `DescricaoCustomizada` TEXT NULL DEFAULT NULL,
              `DataHoraCriacao` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `StatusAlerta` VARCHAR(20) NOT NULL DEFAULT 'Novo' COMMENT 'Novo, Em Investigacao, Resolvido, Ignorado',
              `Severidade` VARCHAR(20) NOT NULL DEFAULT 'Media',
              `DataHoraResolucao` TIMESTAMP NULL DEFAULT NULL,
              `ID_UsuarioResponsavel` INT NULL DEFAULT NULL,
              `DetalhesTecnicos` JSON NULL DEFAULT NULL COMMENT 'Dados brutos do evento gerador',
              PRIMARY KEY (`ID_Alerta`),
              INDEX `FK_Alerta_Tipo_idx` (`ID_TipoAlerta` ASC) VISIBLE,
              INDEX `FK_Alerta_Dispositivo_idx` (`ID_Dispositivo` ASC) VISIBLE,
              INDEX `FK_Alerta_Interface_idx` (`ID_Interface` ASC) VISIBLE,
              INDEX `FK_Alerta_IP_idx` (`ID_EnderecoIP` ASC) VISIBLE,
              INDEX `FK_Alerta_UsuarioResponsavel_idx` (`ID_UsuarioResponsavel` ASC) VISIBLE,
              INDEX `FK_Alerta_IPDescoberto` (`ID_IPDescoberto_FK` ASC) VISIBLE,
              CONSTRAINT `FK_Alerta_Dispositivo`
                FOREIGN KEY (`ID_Dispositivo`)
                REFERENCES `networkassetmanagerdb`.`dispositivo` (`ID_Dispositivo`)
                ON DELETE SET NULL
                ON UPDATE CASCADE,
              CONSTRAINT `FK_Alerta_Interface`
                FOREIGN KEY (`ID_Interface`)
                REFERENCES `networkassetmanagerdb`.`interfacerede` (`ID_Interface`)
                ON DELETE SET NULL
                ON UPDATE CASCADE,
              CONSTRAINT `FK_Alerta_IP`
                FOREIGN KEY (`ID_EnderecoIP`)
                REFERENCES `networkassetmanagerdb`.`enderecoip` (`ID_EnderecoIP`)
                ON DELETE SET NULL
                ON UPDATE CASCADE,
              CONSTRAINT `FK_Alerta_IPDescoberto`
                FOREIGN KEY (`ID_IPDescoberto_FK`)
                REFERENCES `networkassetmanagerdb`.`ipsdescobertos` (`ID_IPDescoberto`)
                ON DELETE SET NULL
                ON UPDATE CASCADE,
              CONSTRAINT `FK_Alerta_Tipo`
                FOREIGN KEY (`ID_TipoAlerta`)
                REFERENCES `networkassetmanagerdb`.`tipoalerta` (`ID_TipoAlerta`)
                ON DELETE RESTRICT
                ON UPDATE CASCADE,
              CONSTRAINT `FK_Alerta_UsuarioResponsavel`
                FOREIGN KEY (`ID_UsuarioResponsavel`)
                REFERENCES `networkassetmanagerdb`.`usuario` (`ID_Usuario`)
                ON DELETE SET NULL
                ON UPDATE CASCADE)
            ENGINE = InnoDB
            AUTO_INCREMENT = 8
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Alertas gerados pelo sistema.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`configuracaovarredura`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`configuracaovarredura` (
              `ID_ConfigVarredura` INT NOT NULL AUTO_INCREMENT,
              `FaixasIP` TEXT NULL DEFAULT NULL COMMENT 'Faixas de IP a serem escaneadas, separadas por vírgula ou JSON',
              `FrequenciaMinutos` INT NULL DEFAULT '60' COMMENT 'Frequência da varredura em minutos (ex: 60 para cada hora)',
              `AgendamentoCron` VARCHAR(100) NULL DEFAULT NULL COMMENT 'Expressão CRON para agendamento avançado (opcional)',
              `VarreduraAtivada` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Se a varredura automática está ativada',
              `DataUltimaModificacao` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (`ID_ConfigVarredura`))
            ENGINE = InnoDB
            AUTO_INCREMENT = 2
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Armazena as configurações para a varredura automática de rede.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`logauditoria`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`logauditoria` (
              `ID_Log` INT NOT NULL AUTO_INCREMENT,
              `Timestamp` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `ID_Usuario_FK` INT NULL DEFAULT NULL COMMENT 'ID do usuário que realizou a ação, se aplicável',
              `NomeUsuario` VARCHAR(100) NULL DEFAULT NULL COMMENT 'Nome do usuário, para referência rápida',
              `Acao` VARCHAR(255) NOT NULL COMMENT 'Ex: LOGIN_SUCESSO, ADD_DEVICE, UPDATE_DEVICE_SETTINGS, SCAN_STARTED',
              `Detalhes` TEXT NULL DEFAULT NULL COMMENT 'Detalhes adicionais sobre a ação, ex: ID do dispositivo afetado, valores alterados (pode ser JSON)',
              `EnderecoIPOrigem` VARCHAR(45) NULL DEFAULT NULL COMMENT 'IP de onde a ação foi originada, se aplicável (ex: da requisição HTTP)',
              PRIMARY KEY (`ID_Log`),
              INDEX `FK_LogAuditoria_Usuario_idx` (`ID_Usuario_FK` ASC) VISIBLE,
              CONSTRAINT `FK_LogAuditoria_Usuario`
                FOREIGN KEY (`ID_Usuario_FK`)
                REFERENCES `networkassetmanagerdb`.`usuario` (`ID_Usuario`)
                ON DELETE SET NULL
                ON UPDATE CASCADE)
            ENGINE = InnoDB
            AUTO_INCREMENT = 17
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Registra eventos importantes e ações de usuários no sistema.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`logstatusdispositivo`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`logstatusdispositivo` (
              `ID_LogStatus` INT NOT NULL AUTO_INCREMENT,
              `ID_Dispositivo` INT NOT NULL,
              `StatusAnterior` VARCHAR(50) NULL DEFAULT NULL,
              `StatusNovo` VARCHAR(50) NOT NULL,
              `DataHoraMudanca` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `FonteMudanca` VARCHAR(100) NULL DEFAULT NULL COMMENT 'Ex: Varredura Automática, Edição Manual',
              `Detalhes` TEXT NULL DEFAULT NULL,
              PRIMARY KEY (`ID_LogStatus`),
              INDEX `FK_LogStatus_Dispositivo_idx` (`ID_Dispositivo` ASC) VISIBLE,
              CONSTRAINT `FK_LogStatus_Dispositivo`
                FOREIGN KEY (`ID_Dispositivo`)
                REFERENCES `networkassetmanagerdb`.`dispositivo` (`ID_Dispositivo`)
                ON DELETE CASCADE
                ON UPDATE CASCADE)
            ENGINE = InnoDB
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Histórico de mudanças de status dos dispositivos.';
            
            
            -- -----------------------------------------------------
            -- Table `networkassetmanagerdb`.`notificacaoalerta`
            -- -----------------------------------------------------
            CREATE TABLE IF NOT EXISTS `networkassetmanagerdb`.`notificacaoalerta` (
              `ID_Notificacao` INT NOT NULL AUTO_INCREMENT,
              `ID_Alerta` INT NOT NULL,
              `ID_Usuario` INT NOT NULL COMMENT 'Usuário notificado',
              `MetodoNotificacao` VARCHAR(50) NOT NULL COMMENT 'Ex: Email, Sistema, SMS',
              `DataHoraEnvio` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `StatusEnvio` VARCHAR(20) NOT NULL COMMENT 'Enviado, Falhou, Lido',
              PRIMARY KEY (`ID_Notificacao`),
              INDEX `FK_Notificacao_Alerta_idx` (`ID_Alerta` ASC) VISIBLE,
              INDEX `FK_Notificacao_Usuario_idx` (`ID_Usuario` ASC) VISIBLE,
              CONSTRAINT `FK_Notificacao_Alerta`
                FOREIGN KEY (`ID_Alerta`)
                REFERENCES `networkassetmanagerdb`.`alerta` (`ID_Alerta`)
                ON DELETE CASCADE
                ON UPDATE CASCADE,
              CONSTRAINT `FK_Notificacao_Usuario`
                FOREIGN KEY (`ID_Usuario`)
                REFERENCES `networkassetmanagerdb`.`usuario` (`ID_Usuario`)
                ON DELETE CASCADE
                ON UPDATE CASCADE)
            ENGINE = InnoDB
            DEFAULT CHARACTER SET = utf8mb4
            COLLATE = utf8mb4_unicode_ci
            COMMENT = 'Registros de notificações enviadas para usuários sobre alertas.';
            
            
            SET SQL_MODE=@OLD_SQL_MODE;
            SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
            SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
            ```
            Execute este script `schema.sql` no seu cliente MySQL (ex: MySQL Workbench) conectado ao banco `NetworkAssetManagerDB`.
        4.  **População Inicial de Dados:** Crie outro arquivo SQL, por exemplo, `initial_data.sql` na mesma pasta (`backend` ou `backend/database/`), com os comandos `INSERT INTO` para os dados iniciais.
            *Exemplo do `initial_data.sql`:*
            ```sql
            USE `NetworkAssetManagerDB`;

            -- 1. Tabela PerfilUsuario
            INSERT INTO PerfilUsuario (NomePerfil, Descricao) VALUES
            ('Administrador', 'Acesso total ao sistema'),
            ('Operador', 'Acesso para operações diárias e monitoramento'),
            ('Visualizador', 'Acesso apenas para visualização de dados')
            ON DUPLICATE KEY UPDATE NomePerfil=VALUES(NomePerfil);

            -- 2. Tabela TipoAlerta
            INSERT INTO TipoAlerta (Nome, Descricao, SeveridadePadrao) VALUES
            ('Novo IP Descoberto', 'Um novo endereço IP foi detectado na rede.', 'Media'),
            ('Dispositivo Offline', 'Um dispositivo do inventário ficou offline.', 'Alta'),
            ('Dispositivo Online', 'Um dispositivo que estava offline voltou a ficar online.', 'Informativo')
            ON DUPLICATE KEY UPDATE Nome=VALUES(Nome);

            -- 3. Tabelas de Lookup para Dispositivo
            -- Fabricante:
            INSERT INTO Fabricante (Nome) VALUES
            ('Dell'), ('HP'), ('Cisco'), ('Apple'), ('Samsung'), ('Intel'), ('TP-Link'), ('Desconhecido')
            ON DUPLICATE KEY UPDATE Nome=VALUES(Nome);

            -- SistemaOperacional:
            INSERT INTO SistemaOperacional (Nome, Versao, Familia) VALUES
            ('Windows 10 Pro', '22H2', 'Windows'), ('Windows 11 Pro', '23H2', 'Windows'),
            ('Windows Server 2019', NULL, 'Windows'), ('Ubuntu Desktop', '22.04 LTS', 'Linux'),
            ('Ubuntu Server', '20.04 LTS', 'Linux'), ('Debian', '12', 'Linux'),
            ('macOS Sonoma', '14', 'macOS'), ('Android', '13', 'Android'), ('iOS', '17', 'iOS'),
            ('RouterOS', '7.x', 'Outros'), ('Desconhecido', NULL, 'Outros')
            ON DUPLICATE KEY UPDATE Nome=VALUES(Nome), Versao=VALUES(Versao);

            -- TipoDispositivo:
            INSERT INTO TipoDispositivo (Nome, Icone) VALUES
            ('Desktop', 'fas fa-desktop'), ('Notebook', 'fas fa-laptop'),
            ('Servidor', 'fas fa-server'), ('Roteador', 'fas fa-network-wired'),
            ('Switch', 'fas fa-ethernet'), ('Impressora', 'fas fa-print'),
            ('Mobile', 'fas fa-mobile-alt'), ('Tablet', 'fas fa-tablet-alt'),
            ('Access Point', 'fas fa-wifi'), ('Firewall', 'fas fa-shield-alt'),
            ('Desconhecido', 'fas fa-question-circle')
            ON DUPLICATE KEY UPDATE Nome=VALUES(Nome);

            -- 4. Tabela ConfiguracaoVarredura (Registro Padrão)
            INSERT INTO `ConfiguracaoVarredura` (`ID_ConfigVarredura`, `FaixasIP`, `FrequenciaMinutos`, `VarreduraAtivada`)
            VALUES (1, '192.168.1.0/24', 60, FALSE)
            ON DUPLICATE KEY UPDATE FaixasIP=VALUES(FaixasIP);
            ```
            Execute este script `initial_data.sql` no seu cliente MySQL.
    * Rode o servidor Flask (ainda dentro da pasta `backend` com `venv` ativo):
        ```bash
        python app.py
        ```
        O backend estará rodando em `http://127.0.0.1:5000`.
        *Nota: Para testes consistentes do agendador APScheduler, pode ser útil rodar com `app.run(debug=True, use_reloader=False)` no final do `app.py`.*

4.  **Configurar o Frontend:**
    * Abra os arquivos HTML (ex: `login.html`, `dispositivos.html`) diretamente no seu navegador.
    * **Recomendado:** Use uma extensão como "Live Server" no VS Code para servir os arquivos HTML. Isso evita problemas de CORS com a API rodando em `http://127.0.0.1:5000` quando os arquivos são abertos via `file:///`.

## Como Usar (Principais Fluxos)

1.  **Login:** Acesse a página `login.html` e entre com um usuário cadastrado. (Para criar um usuário inicial, você precisará inseri-lo manualmente no banco com uma senha "hasheada" usando bcrypt, ou criar um script Python auxiliar para isso, como `populate_user.py`).
2.  **Dashboard:** Após o login, o dashboard exibe um sumário da rede e gráficos.
3.  **Gerenciar Dispositivos:** Na página `dispositivos.html`, visualize, adicione, edite ou remova dispositivos do inventário principal.
4.  **Varredura de Rede:**
    * Configure as faixas de IP e frequência na página `config.html`.
    * Ative a varredura automática ou dispare uma varredura manual pela página `varredura.html`.
    * Visualize os IPs descobertos em `varredura.html`.
    * Use as ações "Analisar Detalhes" (para rodar Nmap), "Inventariar" ou "Ignorar".
5.  **Alertas:** A página `alerts.html` mostra os alertas gerados. Gerencie o status dos alertas.
6.  **Relatórios:** Gere relatórios básicos na página `reports.html`.

## Funcionalidades Futuras e TODOs

* **Monitoramento Contínuo de Dispositivos:** Implementar ping periódico para atualizar status online/offline.
* **Alertas de "Dispositivo Offline/Online":** Gerar alertas com base no monitoramento.
* **Notificações por E-mail:** Enviar e-mails para alertas e "Esqueceu a Senha".
* **Funcionalidade Completa de "Esqueceu a Senha".**
* **Sistema de Permissões (Autorização):** Proteger rotas e funcionalidades com base no perfil.
* **Logging Estruturado em Arquivos.**
* **Trilha de Auditoria (Frontend):** Interface para visualizar logs da `LogAuditoria`.
* **Exportação de Relatórios:** Opções para CSV, PDF.
* **Busca OUI:** Identificar fabricantes pelo MAC Address.
* **Gerenciamento de Usuários e Perfis.**
* **Melhorias na UI/UX:** Refinamentos visuais, feedback, paginação.
* **Tratamento de Erro Aprimorado.**
* **Testes Automatizados.**