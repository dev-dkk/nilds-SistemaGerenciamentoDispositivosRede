document.addEventListener('DOMContentLoaded', function() {
    const discoveredIpsTbody = document.getElementById('discovered-ips-tbody');
    const discoveredIpsFooter = document.getElementById('discovered-ips-footer');
    const startNewScanButton = document.getElementById('startNewScanButton');

    const loadingMessageRow = '<tr><td colspan="6" style="text-align:center;">Carregando IPs descobertos...</td></tr>';
    const errorMessageRow = '<tr><td colspan="6" style="text-align:center;">Erro ao carregar IPs. Tente novamente mais tarde.</td></tr>';
    const noIPsMessageRow = '<tr><td colspan="6" style="text-align:center;">Nenhum IP descoberto encontrado. Execute uma varredura.</td></tr>';

    async function fetchAndDisplayDiscoveredIPs() {
        if (!discoveredIpsTbody) {
            console.error("Elemento tbody com ID 'discovered-ips-tbody' não foi encontrado!");
            return;
        }
        discoveredIpsTbody.innerHTML = loadingMessageRow;
        discoveredIpsFooter.innerHTML = '<span>Carregando...</span>';

        try {
            const response = await fetch('http://127.0.0.1:5000/api/discovery/discovered-ips', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                    // Adicionar cabeçalho de autenticação (token JWT) aqui se necessário
                }
            });

            if (!response.ok) {
                console.error("Erro na resposta da API: ", response.status, response.statusText);
                const errorData = await response.json().catch(() => ({ message: "Erro desconhecido do servidor." }));
                discoveredIpsTbody.innerHTML = `<tr><td colspan="6" style="text-align:center;">Falha ao carregar: ${errorData.message || response.statusText}</td></tr>`;
                discoveredIpsFooter.innerHTML = '<span>Falha ao carregar.</span>';
                return;
            }

            const discoveredIPs = await response.json();
            discoveredIpsTbody.innerHTML = ''; // Limpar

            if (discoveredIPs.length === 0) {
                discoveredIpsTbody.innerHTML = noIPsMessageRow;
                discoveredIpsFooter.innerHTML = '<span>Nenhum IP descoberto.</span>';
                return;
            }

            discoveredIPs.forEach(ipInfo => {
                const row = discoveredIpsTbody.insertRow();

                const createCell = (data) => {
                    const cell = row.insertCell();
                    cell.textContent = data !== null && data !== undefined ? data : 'N/D';
                    return cell;
                };

                createCell(ipInfo.EnderecoIP);
                createCell(ipInfo.NomeHostResolvido); // Pode ser null inicialmente
                createCell(ipInfo.DataPrimeiraDeteccao ? new Date(ipInfo.DataPrimeiraDeteccao).toLocaleString('pt-BR') : 'N/D');
                createCell(ipInfo.DataUltimaDeteccao ? new Date(ipInfo.DataUltimaDeteccao).toLocaleString('pt-BR') : 'N/D');

                const statusCell = createCell(ipInfo.StatusResolucao);
                // Você pode adicionar classes CSS para diferentes status aqui se desejar
                // if (ipInfo.StatusResolucao === 'Novo') statusCell.classList.add('status-novo');

                const actionsCell = row.insertCell();
                actionsCell.innerHTML = `
                <button class="action-link btn-icon" title="Analisar Detalhes" data-id="<span class="math-inline">
                    <i class="fas fa-search-plus"></i>
                </button>
                <button class="action-link btn-icon btn-success-icon" title="Adicionar" data-id="<span class="math-inline">
                    <i class="fas fa-plus-circle"></i>
                </button>
                <button class="action-link btn-icon btn-danger-icon" title="Ignorar" data-id="<span class="math-inline">
                    <i class="fas fa-ban"></i>
                </button>
            `;
            });
            discoveredIpsFooter.innerHTML = `<span>Exibindo ${discoveredIPs.length} IPs descobertos.</span>`;

        } catch (error) {
            console.error('Erro ao buscar IPs descobertos:', error);
            discoveredIpsTbody.innerHTML = errorMessageRow;
            discoveredIpsFooter.innerHTML = '<span>Erro ao carregar.</span>';
        }
    }

    // Lógica para o botão "Iniciar Nova Varredura"
    if (startNewScanButton) {
        startNewScanButton.addEventListener('click', async function() {
            startNewScanButton.disabled = true;
            startNewScanButton.textContent = 'Varrendo...';
            discoveredIpsFooter.innerHTML = '<span>Iniciando nova varredura de rede...</span>';
            discoveredIpsTbody.innerHTML = loadingMessageRow;

            try {
                const response = await fetch('http://127.0.0.1:5000/api/discovery/start-scan', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                        // Adicionar header de autenticação se necessário
                    }
                });
                const result = await response.json();
                if (response.ok) {
                    alert(result.message || "Varredura concluída!");
                    fetchAndDisplayDiscoveredIPs(); // Recarrega a lista de IPs descobertos
                } else {
                    alert(result.message || "Erro ao iniciar varredura.");
                    discoveredIpsFooter.innerHTML = `<span>Erro: ${result.message || "Falha na varredura."}</span>`;
                }
            } catch (error) {
                console.error("Erro ao iniciar nova varredura:", error);
                alert("Erro de comunicação ao tentar iniciar a varredura.");
                discoveredIpsFooter.innerHTML = '<span>Erro de comunicação.</span>';
            } finally {
                startNewScanButton.disabled = false;
                startNewScanButton.textContent = 'Iniciar Nova Varredura';
            }
        });
    }

    // Placeholder para ações nos IPs descobertos (delegação de eventos)
    if(discoveredIpsTbody) {
        discoveredIpsTbody.addEventListener('click', function(event) {
            const target = event.target;
            if (target.classList.contains('action-link') && target.dataset.action) {
                const ipId = target.dataset.id;
                const ipAddress = target.dataset.ip;
                const action = target.dataset.action;

                if (action === 'scan-details') {
                    alert(`Ação: Analisar Detalhes para IP ID: ${ipId}, Endereço: ${ipAddress} (implementar)`);
                    // TODO: Chamar backend para varredura detalhada deste IP
                } else if (action === 'inventory') {
                    alert(`Ação: Inventariar IP ID: ${ipId}, Endereço: ${ipAddress} (implementar - abrir modal de adicionar dispositivo pré-preenchido?)`);
                    // TODO: Abrir modal de Adicionar Dispositivo, talvez pré-preenchendo com o IP
                    // ou com dados de uma varredura detalhada prévia.
                } else if (action === 'ignore') {
                    if (confirm(`Tem certeza que deseja ignorar o IP ${ipAddress} (ID: ${ipId})?`)) {
                        alert(`Ação: Ignorar IP ID: ${ipId} (implementar - chamar backend para mudar status)`);
                        // TODO: Chamar backend para mudar StatusResolucao para 'Ignorado' e recarregar lista
                    }
                }
            }
        });
    }

    // Carrega a lista de IPs descobertos ao iniciar a página
    fetchAndDisplayDiscoveredIPs();
});