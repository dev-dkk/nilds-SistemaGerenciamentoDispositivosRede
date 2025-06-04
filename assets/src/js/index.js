document.addEventListener('DOMContentLoaded', function() {
    // Elementos dos Cards de Sumário
    const totalDevicesEl = document.getElementById('totalDevices');
    const onlineDevicesEl = document.getElementById('onlineDevices');
    const offlineDevicesEl = document.getElementById('offlineDevices');
    const newAlertsEl = document.getElementById('newAlerts');

    // Lista de Alertas Recentes
    const recentAlertsListEl = document.getElementById('recentAlertsList');

    // --- GRÁFICOS ---
    const osChartCanvas = document.getElementById('osDistributionChart');
    const statusChartCanvas = document.getElementById('statusDistributionChart');

    let osChartInstance = null; // Para guardar a instância do gráfico e destruí-la antes de recriar
    let statusChartInstance = null;

    // Cores para os gráficos (você pode personalizar)
    const chartColors = [
        '#3498db', '#2ecc71', '#e74c3c', '#f1c40f', '#9b59b6',
        '#1abc9c', '#d35400', '#34495e', '#7f8c8d', '#bdc3c7'
    ];

    // Função para renderizar o gráfico de Distribuição de SO
    function renderOsDistributionChart(data) {
        if (!osChartCanvas) return;
        if (osChartInstance) {
            osChartInstance.destroy(); // Destrói o gráfico anterior se existir
        }

        const labels = data.map(item => item.os_name || 'Desconhecido');
        const counts = data.map(item => item.device_count);

        osChartInstance = new Chart(osChartCanvas.getContext('2d'), {
            type: 'doughnut', // ou 'pie'
            data: {
                labels: labels,
                datasets: [{
                    label: 'Distribuição de SO',
                    data: counts,
                    backgroundColor: chartColors.slice(0, data.length), // Usa um subconjunto de cores
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false, // Para controlar melhor o tamanho com CSS se necessário
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: false, // O título já está no H4 da seção
                        text: 'Distribuição de Sistemas Operacionais'
                    }
                }
            }
        });
    }

    // Função para buscar dados e renderizar o gráfico de Distribuição de SO
    async function fetchOsDistributionDataAndRenderChart() {
        if (!osChartCanvas) {
            console.warn("Elemento canvas 'osDistributionChart' não encontrado.");
            return;
        }
        try {
            const response = await fetch('http://127.0.0.1:5000/api/dashboard/os-distribution');
            if (!response.ok) {
                console.error("Erro ao buscar dados de distribuição de SO:", response.statusText);
                // Você pode querer mostrar uma mensagem de erro no lugar do gráfico
                return;
            }
            const data = await response.json();
            renderOsDistributionChart(data);
        } catch (error) {
            console.error('Falha ao buscar dados de distribuição de SO:', error);
        }
    }

    // Função para renderizar o gráfico de Distribuição de Status
    function renderStatusDistributionChart(data) {
        if (!statusChartCanvas) return;
        if (statusChartInstance) {
            statusChartInstance.destroy(); // Destrói o gráfico anterior se existir
        }

        const labels = data.map(item => item.status_name || 'Desconhecido');
        const counts = data.map(item => item.device_count);
        
        // Mapear status para cores específicas se desejar
        const backgroundColors = labels.map(label => {
            if (label.toLowerCase() === 'online') return '#2ecc71'; // Verde
            if (label.toLowerCase() === 'offline') return '#e74c3c'; // Vermelho
            if (label.toLowerCase() === 'com falha') return '#f39c12'; // Laranja
            // Adicione mais cores para outros status ou use o array chartColors
            const colorIndex = labels.indexOf(label) % chartColors.length;
            return chartColors[colorIndex];
        });


        statusChartInstance = new Chart(statusChartCanvas.getContext('2d'), {
            type: 'pie', // ou 'doughnut'
            data: {
                labels: labels,
                datasets: [{
                    label: 'Distribuição de Status',
                    data: counts,
                    backgroundColor: backgroundColors,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: false,
                        text: 'Distribuição de Status dos Dispositivos'
                    }
                }
            }
        });
    }

    // Função para buscar dados e renderizar o gráfico de Distribuição de Status
    async function fetchStatusDistributionDataAndRenderChart() {
         if (!statusChartCanvas) {
            console.warn("Elemento canvas 'statusDistributionChart' não encontrado.");
            return;
        }
        try {
            const response = await fetch('http://127.0.0.1:5000/api/dashboard/status-distribution');
            if (!response.ok) {
                console.error("Erro ao buscar dados de distribuição de status:", response.statusText);
                return;
            }
            const data = await response.json();
            renderStatusDistributionChart(data);
        } catch (error) {
            console.error('Falha ao buscar dados de distribuição de status:', error);
        }
    }

    // Função para buscar e exibir o sumário
    async function fetchDashboardSummary() {
        try {
            const response = await fetch('http://127.0.0.1:5000/api/dashboard/summary');
            if (!response.ok) {
                console.error("Erro ao buscar sumário do dashboard:", response.statusText);
                if(totalDevicesEl) totalDevicesEl.textContent = 'Erro';
                if(onlineDevicesEl) onlineDevicesEl.textContent = 'Erro';
                if(offlineDevicesEl) offlineDevicesEl.textContent = 'Erro';
                if(newAlertsEl) newAlertsEl.textContent = 'Erro';
                return;
            }
            const summary = await response.json();
            if(totalDevicesEl) totalDevicesEl.textContent = summary.total_devices !== undefined ? summary.total_devices : 'N/A';
            if(onlineDevicesEl) onlineDevicesEl.textContent = summary.online_devices !== undefined ? summary.online_devices : 'N/A';
            if(offlineDevicesEl) offlineDevicesEl.textContent = summary.offline_devices !== undefined ? summary.offline_devices : 'N/A';
            if(newAlertsEl) newAlertsEl.textContent = summary.new_alerts !== undefined ? summary.new_alerts : 'N/A';

        } catch (error) {
            console.error('Falha ao buscar sumário do dashboard:', error);
            if(totalDevicesEl) totalDevicesEl.textContent = 'Falha';
            if(onlineDevicesEl) onlineDevicesEl.textContent = 'Falha';
            if(offlineDevicesEl) offlineDevicesEl.textContent = 'Falha';
            if(newAlertsEl) newAlertsEl.textContent = 'Falha';
        }
    }

    // Função para buscar e exibir alertas recentes
    async function fetchRecentAlerts() {
        if (!recentAlertsListEl) return;
        recentAlertsListEl.innerHTML = '<li>Carregando alertas...</li>';

        try {
            const response = await fetch('http://127.0.0.1:5000/api/dashboard/recent-alerts');
            if (!response.ok) {
                console.error("Erro ao buscar alertas recentes:", response.statusText);
                recentAlertsListEl.innerHTML = '<li>Erro ao carregar alertas.</li>';
                return;
            }
            const alerts = await response.json();
            recentAlertsListEl.innerHTML = ''; // Limpa a lista

            if (alerts.length === 0) {
                recentAlertsListEl.innerHTML = '<li>Nenhum alerta novo encontrado.</li>';
                return;
            }

            alerts.forEach(alert => {
                const listItem = document.createElement('li');
                const alertDate = alert.DataHoraCriacao ? new Date(alert.DataHoraCriacao).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'}) : '';
                let subject = alert.DispositivoNomeHost || alert.IPDescobertoEndereco || 'Sistema';
                
                listItem.innerHTML = `
                    <span class="severity-badge ${getSeverityClass(alert.Severidade)}">${alert.Severidade || ''}</span>
                    <strong>${alert.TipoAlertaNome || 'Alerta'}:</strong> 
                    ${alert.DescricaoCustomizada} 
                    <em>(${subject})</em> 
                    <small class="text-muted">- ${alertDate}</small>
                `;
                recentAlertsListEl.appendChild(listItem);
            });

        } catch (error) {
            console.error('Falha ao buscar alertas recentes:', error);
            recentAlertsListEl.innerHTML = '<li>Falha ao carregar alertas.</li>';
        }
    }

    // Função auxiliar para classes de severidade (similar à de alerts_handler.js)
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

    // Carregar dados ao iniciar
    fetchDashboardSummary();
    fetchRecentAlerts();
    // Chamar as novas funções para carregar e renderizar os gráficos
    fetchOsDistributionDataAndRenderChart();
    fetchStatusDistributionDataAndRenderChart();
});