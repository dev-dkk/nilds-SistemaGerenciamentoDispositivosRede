document.addEventListener('DOMContentLoaded', function() {
    const alertsTbody = document.getElementById('alerts-tbody');
    const alertsFooter = document.getElementById('alerts-footer');
    const refreshAlertsButton = document.getElementById('refreshAlertsButton');
    // const filterAlertStatusSelect = document.getElementById('filter-alert-status'); // Descomente se for usar

    // Variável para armazenar os dados dos alertas atualmente carregados
    let currentAlertsData = [];

    // Constantes para o modal de detalhes do alerta
    const alertDetailsModal = document.getElementById('alertDetailsModal');
    const alertDetailsBody = document.getElementById('alertDetailsBody');
    const closeAlertDetailsModalButton = document.getElementById('closeAlertDetailsModalButton');
    const cancelAlertDetailsModalButton = document.getElementById('cancelAlertDetailsModalButton'); // Verifique se o ID no HTML é este

    const loadingMessageRow = '<tr><td colspan="7" style="text-align:center;">Carregando alertas...</td></tr>';
    const errorMessageRow = '<tr><td colspan="7" style="text-align:center;">Erro ao carregar alertas. Tente novamente mais tarde.</td></tr>';
    const noAlertsMessageRow = '<tr><td colspan="7" style="text-align:center;">Nenhum alerta encontrado.</td></tr>';

    function getSeverityClass(severity) {
        if (!severity) return 'severity-unknown';
        switch (severity.toLowerCase()) {
            case 'critica': return 'severity-critical';
            case 'alta': return 'severity-high';
            case 'media': return 'severity-medium';
            case 'baixa': return 'severity-low';
            default: return 'severity-unknown';
        }
    }

    async function fetchAndDisplayAlerts() {
        if (!alertsTbody) {
            console.error("Elemento tbody com ID 'alerts-tbody' não foi encontrado!");
            return;
        }
        alertsTbody.innerHTML = loadingMessageRow;
        if(alertsFooter) alertsFooter.innerHTML = '<span>Carregando...</span>';

        // TODO: Adicionar filtro de status à URL da API no futuro, se o select de filtro for usado
        // const statusFilter = filterAlertStatusSelect ? filterAlertStatusSelect.value : '';
        // let apiUrl = `http://127.0.0.1:5000/api/alerts${statusFilter ? '?status=' + statusFilter : ''}`;
        let apiUrl = 'http://127.0.0.1:5000/api/alerts';

        console.log("ALERTS_HANDLER: Buscando alertas de:", apiUrl);

        try {
            const response = await fetch(apiUrl, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
                // Adicionar header de autenticação (token JWT) aqui se necessário
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: "Erro desconhecido do servidor." }));
                console.error("ALERTS_HANDLER: Erro na resposta da API:", response.status, errorData.message);
                alertsTbody.innerHTML = `<tr><td colspan="7" style="text-align:center;">Falha ao carregar: ${errorData.message || response.statusText}</td></tr>`;
                if(alertsFooter) alertsFooter.innerHTML = '<span>Falha ao carregar.</span>';
                return;
            }

            const alerts = await response.json();
            currentAlertsData = alerts; // Armazena os dados dos alertas
            alertsTbody.innerHTML = ''; // Limpa a tabela

            if (alerts.length === 0) {
                alertsTbody.innerHTML = noAlertsMessageRow;
                if(alertsFooter) alertsFooter.innerHTML = '<span>Nenhum alerta.</span>';
                return;
            }

            alerts.forEach(alert => {
                const row = alertsTbody.insertRow();
                
                const createCell = (content, className = '') => {
                    const cell = row.insertCell();
                    cell.innerHTML = content !== null && content !== undefined ? content : 'N/D';
                    if (className) cell.className = className;
                    return cell;
                };

                createCell(`<span class="severity-badge ${getSeverityClass(alert.Severidade)}">${alert.Severidade || 'N/D'}</span>`);
                createCell(alert.TipoAlertaNome);
                createCell(alert.DescricaoCustomizada);
                createCell(alert.DispositivoNomeHost || alert.IPDescobertoEndereco || 'N/A');
                createCell(alert.DataHoraCriacao ? new Date(alert.DataHoraCriacao).toLocaleString('pt-BR', {dateStyle: 'short', timeStyle: 'short'}) : 'N/D');
                createCell(alert.StatusAlerta);

                const actionsCell = row.insertCell();
                actionsCell.innerHTML = `
                    <button class="action-link btn-icon" title="Ver Detalhes" data-id="${alert.ID_Alerta}" data-action="view"><i class="fas fa-eye"></i></button>
                    <button class="action-link btn-icon" title="Marcar como Lido" data-id="${alert.ID_Alerta}" data-action="mark-read"><i class="fas fa-check-circle"></i></button>
                    <button class="action-link btn-icon btn-success-icon" title="Resolver Alerta" data-id="${alert.ID_Alerta}" data-action="resolve"><i class="fas fa-check-double"></i></button>
                `;
            });
            if(alertsFooter) alertsFooter.innerHTML = `<span>Exibindo ${alerts.length} alertas.</span>`;

        } catch (error) {
            console.error('ALERTS_HANDLER: Erro ao buscar alertas:', error);
            alertsTbody.innerHTML = errorMessageRow;
            if(alertsFooter) alertsFooter.innerHTML = '<span>Erro ao carregar.</span>';
        }
    }

    // Listener para o botão de atualizar alertas
    if (refreshAlertsButton) {
        refreshAlertsButton.addEventListener('click', fetchAndDisplayAlerts);
    }
    // Listener para o filtro de status (descomente se implementar)
    // if (filterAlertStatusSelect) {
    //     filterAlertStatusSelect.addEventListener('change', fetchAndDisplayAlerts);
    // }

    // Listeners para os botões de ação na tabela de alertas
    if(alertsTbody) {
        alertsTbody.addEventListener('click', async function(event){
            const actionButton = event.target.closest('.action-link'); 
            
            if(actionButton && actionButton.dataset.action) {
                event.preventDefault();
                const alertId = actionButton.dataset.id;
                const action = actionButton.dataset.action;
                const originalButtonContent = actionButton.innerHTML; // Para restaurar em caso de erro

                console.log(`ALERTS_HANDLER: Ação '${action}' clicada para Alerta ID: ${alertId}`);

                if (action === 'view') {
                    const alertData = currentAlertsData.find(a => a.ID_Alerta == alertId);

                    if (alertData && alertDetailsBody && alertDetailsModal) {
                        alertDetailsBody.innerHTML = '<p>Carregando...</p>';
                        
                        let detailsHtml = `
                            <p><strong>ID do Alerta:</strong> ${alertData.ID_Alerta}</p>
                            <p><strong>Tipo:</strong> ${alertData.TipoAlertaNome || 'N/D'}</p>
                            <p><strong>Descrição:</strong> ${alertData.DescricaoCustomizada || 'N/D'}</p>
                            <p><strong>Severidade:</strong> <span class="severity-badge ${getSeverityClass(alertData.Severidade)}">${alertData.Severidade || 'N/D'}</span></p>
                            <p><strong>Status:</strong> ${alertData.StatusAlerta || 'N/D'}</p>
                            <p><strong>Data de Criação:</strong> ${alertData.DataHoraCriacao ? new Date(alertData.DataHoraCriacao).toLocaleString('pt-BR', {dateStyle: 'full', timeStyle: 'medium'}) : 'N/D'}</p>
                        `;

                        if (alertData.DataHoraResolucao) {
                            detailsHtml += `<p><strong>Data de Resolução:</strong> ${new Date(alertData.DataHoraResolucao).toLocaleString('pt-BR', {dateStyle: 'full', timeStyle: 'medium'})}</p>`;
                        }

                        if (alertData.DispositivoNomeHost) {
                            detailsHtml += `<p><strong>Dispositivo Associado:</strong> ${alertData.DispositivoNomeHost}</p>`;
                        } else if (alertData.IPDescobertoEndereco) {
                            detailsHtml += `<p><strong>IP Descoberto Associado:</strong> ${alertData.IPDescobertoEndereco}</p>`;
                        }

                        if (alertData.DetalhesTecnicos) {
                            detailsHtml += `<h4>Detalhes Técnicos</h4>`;
                            try {
                                const techDetails = JSON.parse(alertData.DetalhesTecnicos);
                                detailsHtml += `<pre>${JSON.stringify(techDetails, null, 2)}</pre>`;
                            } catch (e) {
                                detailsHtml += `<div style="white-space: pre-wrap; word-break: break-all;">${alertData.DetalhesTecnicos}</div>`;
                            }
                        } else {
                            detailsHtml += `<p><strong>Detalhes Técnicos:</strong> N/D</p>`;
                        }

                        alertDetailsBody.innerHTML = detailsHtml;
                        alertDetailsModal.style.display = 'block';
                    } else {
                        alert('Detalhes do alerta não encontrados. Tente atualizar a lista.');
                        console.error(`ALERTS_HANDLER: Alerta com ID ${alertId} não encontrado em currentAlertsData ou elementos do modal ausentes.`);
                    }

                } else if (action === 'mark-read' || action === 'resolve') {
                    let novoStatus = '';
                    let confirmMessage = '';

                    if (action === 'mark-read') {
                        novoStatus = 'Lido';
                        confirmMessage = `Tem certeza que deseja marcar o alerta ID: ${alertId} como 'Lido'?`;
                    } else { // action === 'resolve'
                        novoStatus = 'Resolvido';
                        confirmMessage = `Tem certeza que deseja marcar o alerta ID: ${alertId} como 'Resolvido'?`;
                    }

                    if (confirm(confirmMessage)) {
                        console.log(`ALERTS_HANDLER: Confirmado. Enviando PUT para atualizar status para '${novoStatus}'`);
                        actionButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                        actionButton.disabled = true;

                        try {
                            const response = await fetch(`http://127.0.0.1:5000/api/alerts/${alertId}/status`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ status: novoStatus })
                            });

                            const result = await response.json();

                            if (response.ok) {
                                alert(result.message || `Status do alerta atualizado para '${novoStatus}'.`);
                                fetchAndDisplayAlerts(); // Atualiza a lista (recriará o botão)
                            } else {
                                alert(`Erro ao atualizar status: ${result.message || response.statusText}`);
                                actionButton.innerHTML = originalButtonContent; // Restaura em caso de erro
                                actionButton.disabled = false;
                            }
                        } catch (error) {
                            console.error(`ALERTS_HANDLER: Erro ao tentar atualizar status para '${novoStatus}':`, error);
                            alert(`Erro de comunicação ao tentar atualizar status do alerta.`);
                            actionButton.innerHTML = originalButtonContent; // Restaura em caso de erro
                            actionButton.disabled = false;
                        }
                    } else {
                        console.log(`ALERTS_HANDLER: Ação '${action}' cancelada pelo usuário.`);
                    }
                }
            }
        });
    }

    // Listeners para fechar o Modal de Detalhes do Alerta
    if (closeAlertDetailsModalButton) {
        closeAlertDetailsModalButton.addEventListener('click', () => {
            if (alertDetailsModal) alertDetailsModal.style.display = 'none';
        });
    }
    if (cancelAlertDetailsModalButton) {
        cancelAlertDetailsModalButton.addEventListener('click', () => {
            if (alertDetailsModal) alertDetailsModal.style.display = 'none';
        });
    }

    fetchAndDisplayAlerts();
});