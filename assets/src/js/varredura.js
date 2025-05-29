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
                const actionsCell = row.insertCell();

                actionsCell.innerHTML = `
                 <button class="action-link btn-icon" title="Analisar Detalhes" data-id="${ipInfo.ID_IPDescoberto}" data-ip="${ipInfo.EnderecoIP}" data-action="scan-details">
                        <i class="fas fa-search-plus"></i>
                    </button>
                    <button class="action-link btn-icon btn-success-icon" title="Inventariar" data-id="${ipInfo.ID_IPDescoberto}" data-ip="${ipInfo.EnderecoIP}" data-action="inventory">
                        <i class="fas fa-plus-circle"></i>
                    </button>
                    <button class="action-link btn-icon btn-danger-icon" title="Ignorar" data-id="${ipInfo.ID_IPDescoberto}" data-ip="${ipInfo.EnderecoIP}" data-action="ignore">
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
if (discoveredIpsTbody) {
        discoveredIpsTbody.addEventListener('click', async function(event) {
            const clickedElement = event.target; // O elemento que foi realmente clicado
            console.log("TBODY CLICK: Elemento clicado:", clickedElement); // LOG A: Veja o que foi clicado

            // Tenta encontrar o botão de ação mais próximo, subindo na árvore DOM
            // Isso ajuda se o clique foi no ícone <i> dentro do <button>
            const actionButton = clickedElement.closest('.action-link'); 
            console.log("TBODY CLICK: Botão de ação encontrado (closest):", actionButton); // LOG B: Veja se encontrou o botão

            if (actionButton && actionButton.dataset.action) { // Verifica se actionButton foi encontrado e tem data-action
                event.preventDefault(); // Mova o preventDefault para cá, após confirmar que é um link de ação
                
                const ipId = actionButton.dataset.id;
                const ipAddress = actionButton.dataset.ip;
                const action = actionButton.dataset.action;
                console.log("TBODY CLICK: Ação:", action, "ipId:", ipId, "ipAddress:", ipAddress); // LOG C: Veja os dados extraídos

                if (action === 'scan-details') {
                    console.log(`SCAN DETAILS ACTION: Iniciando para ipId: ${ipId}, ipAddress: ${ipAddress}`);
                    
                    const currentActionButton = actionButton; // Usa actionButton, que é o <button>
                    const originalButtonContent = currentActionButton.innerHTML; 

                    currentActionButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; // Modifica o botão
                    currentActionButton.disabled = true; // Desabilita o botão

                    if (typeof ipAddress === 'undefined' || ipAddress === null || ipAddress.trim() === "") {
                        console.error("SCAN DETAILS ACTION: ipAddress é indefinido ou vazio.");
                        alert("Erro: Endereço IP não encontrado para este item. Não é possível analisar.");
                        currentActionButton.innerHTML = originalButtonContent; // Restaura o botão
                        currentActionButton.disabled = false; // Reabilita o botão
                        return; 
                    }

                    try {
                        const response = await fetch(`http://127.0.0.1:5000/api/discovery/scan-ip-details`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ 
                                ip_address: ipAddress,
                                id_ip_descoberto: ipId 
                            })
                        });

                        const result = await response.json();
                        if (response.ok) {
                            alert(result.message || `Detalhes do IP ${ipAddress} analisados com sucesso.`);
                            fetchAndDisplayDiscoveredIPs(); // Isso vai recriar o botão, então a restauração manual abaixo pode não ser necessária se der sucesso.
                        } else {
                            alert(`Erro ao analisar detalhes: ${result.message || response.statusText}`);
                            currentActionButton.innerHTML = originalButtonContent; // Restaura o botão
                            currentActionButton.disabled = false; // Reabilita o botão
                        }
                    } catch (error) {
                        console.error('SCAN DETAILS ACTION: Erro durante a operação fetch/POST:', error);
                        alert('Erro de comunicação com o servidor ao tentar analisar detalhes.');
                        currentActionButton.innerHTML = originalButtonContent; // Restaura o botão
                        currentActionButton.disabled = false; // Reabilita o botão
                    }

                } else if (action === 'inventory') {
                    console.log(`VARREDURA_HANDLER: Ação 'Inventariar' clicada para ipId: ${ipId}, ipAddress: ${ipAddress}`); // LOG V1
                    
                    const currentActionButton = actionButton; // Usamos actionButton para modificar o botão
                    const originalButtonContent = currentActionButton.innerHTML; // Salva o ícone original

                    currentActionButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...'; // Muda o conteúdo do BOTÃO
                    currentActionButton.disabled = true; // Desabilita o BOTÃO

                    try {
                        // ... (resto da sua lógica fetch, sessionStorage.setItem, window.location.href) ...
                        // Exemplo:
                        const response = await fetch(`http://127.0.0.1:5000/api/discovery/discovered-ips/${ipId}`);
                        if (!response.ok) {
                            const errData = await response.json().catch(() => ({}));
                            alert(`Erro ao buscar detalhes do IP descoberto: ${errData.message || response.statusText}`);
                            currentActionButton.innerHTML = originalButtonContent; // Restaura o botão
                            currentActionButton.disabled = false;
                            return;
                        }
                        const discoveredIpDetails = await response.json();
                        console.log("VARREDURA_HANDLER: Detalhes do IP Descoberto recebidos do backend:", discoveredIpDetails); // LOG V2 (coloquei aqui para referência)

                        const prefillData = {
                            id_ip_descoberto: discoveredIpDetails.ID_IPDescoberto,
                            nomeHost: discoveredIpDetails.NomeHostResolvido || discoveredIpDetails.EnderecoIP,
                            enderecoIP: discoveredIpDetails.EnderecoIP,
                            enderecoMAC: discoveredIpDetails.MAC_Address_Estimado,
                            osEstimado: discoveredIpDetails.OS_Estimado,
                            descricaoInicial: `Dispositivo descoberto com IP ${discoveredIpDetails.EnderecoIP}. OS Estimado: ${discoveredIpDetails.OS_Estimado || 'N/D'}. MAC: ${discoveredIpDetails.MAC_Address_Estimado || 'N/D'}.`
                        };
                        
                        console.log("VARREDURA_HANDLER: Dados a serem salvos no sessionStorage (prefillData):", prefillData); // LOG V3
                        sessionStorage.setItem('prefillDeviceData', JSON.stringify(prefillData));
                        console.log("VARREDURA_HANDLER: Dados salvos no sessionStorage. Redirecionando para dispositivos.html..."); // LOG V4
                        
                        window.location.href = 'dispositivos.html';

                    } catch (error) {
                        console.error('VARREDURA_HANDLER: Erro ao preparar para inventariar IP:', error);
                        alert('Erro de comunicação com o servidor ao preparar para inventariar.');
                        currentActionButton.innerHTML = originalButtonContent; // Restaura o botão
                        currentActionButton.disabled = false;
                    }

                } else if (action === 'ignore') {
                    console.log("IGNORE ACTION: Botão 'Ignorar' clicado e ação confirmada."); 
                    console.log("  ID do IP a ignorar (ipId):", ipId);         // LOG 1.1
                    console.log("  Endereço IP (ipAddress):", ipAddress);    // LOG 1.2

                    if (confirm(`Tem certeza que deseja marcar o IP ${ipAddress} (ID: ${ipId}) como 'Ignorado'?`)) {
                        console.log("IGNORE ACTION: Usuário confirmou a ação."); // LOG 2
                        try {
                            console.log(`IGNORE ACTION: Enviando requisição PUT para /api/discovery/discovered-ips/${ipId}/status`); // LOG 3
                            
                            const response = await fetch(`http://127.0.0.1:5000/api/discovery/discovered-ips/${ipId}/status`, {
                                method: 'PUT',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({ status: 'Ignorado' })
                            });

                            console.log("IGNORE ACTION: Resposta recebida do backend:", response); // LOG 4

                            let result = {};
                            try {
                                result = await response.json();
                                console.log("IGNORE ACTION: Resultado JSON parseado da resposta:", result); // LOG 5
                            } catch (e) {
                                console.error("IGNORE ACTION: Falha ao parsear resposta JSON ou resposta vazia.", e);
                                if (!response.ok) {
                                     result.message = `Erro do servidor (status ${response.status}) sem corpo JSON detalhado.`;
                                }
                            }
                            
                            if (response.ok) {
                                console.log("IGNORE ACTION: Backend respondeu OK. Mensagem:", result.message); // LOG 6
                                alert(result.message || 'Status do IP atualizado para Ignorado.');
                                fetchAndDisplayDiscoveredIPs(); 
                            } else {
                                console.warn("IGNORE ACTION: Backend respondeu NÃO OK. Status:", response.status, "Mensagem:", result.message); // LOG 7
                                alert(`Erro ao ignorar IP: ${result.message || `Falha com status ${response.status}`}`);
                            }
                        } catch (error) {
                            console.error('IGNORE ACTION: Erro durante a operação fetch/PUT:', error); // LOG 8
                            alert('Erro de comunicação com o servidor ao tentar ignorar o IP.');
                        }
                    } else {
                        console.log("IGNORE ACTION: Usuário cancelou a ação."); // LOG 9
                    }
                }
            } else {
            console.log("TBODY CLICK: actionButton foi encontrado, mas actionButton.dataset.action está indefinido ou vazio.");
        }
        });
    }

    // Carrega a lista de IPs descobertos ao iniciar a página
    fetchAndDisplayDiscoveredIPs();
});