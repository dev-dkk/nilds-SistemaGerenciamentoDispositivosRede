document.addEventListener('DOMContentLoaded', function() {
    const reportTypeSelect = document.getElementById('reportTypeSelect');
    const generateReportButton = document.getElementById('generateReportButton');
    const reportOutputDiv = document.getElementById('reportOutput');
    const reportTitle = document.getElementById('reportTitle');

    if (generateReportButton) {
        generateReportButton.addEventListener('click', async function() {
            const selectedReportType = reportTypeSelect.value;
            if (!selectedReportType) {
                reportOutputDiv.innerHTML = '<p style="color: orange;">Por favor, selecione um tipo de relatório.</p>';
                reportTitle.textContent = 'Resultados';
                return;
            }

            reportOutputDiv.innerHTML = '<p>Gerando relatório, por favor aguarde...</p>';
            reportTitle.textContent = 'Resultados'; 

            try {
                let data;
                let response; // Declarar response aqui para usá-la na checagem de erro

                if (selectedReportType === 'full_inventory') {
                    reportTitle.textContent = 'Relatório: Inventário Completo de Dispositivos';
                    response = await fetch('http://127.0.0.1:5000/devices'); 
                    if (!response.ok) throw new Error(`Erro HTTP: ${response.status} ao buscar inventário completo.`);
                    data = await response.json();
                    displayFullInventoryReport(data); // Reutiliza a função existente
                } else if (selectedReportType === 'os_summary') {
                    reportTitle.textContent = 'Relatório: Sumário de Dispositivos por Sistema Operacional';
                    response = await fetch('http://127.0.0.1:5000/api/reports/os-summary');
                    if (!response.ok) throw new Error(`Erro HTTP: ${response.status} ao buscar sumário por SO.`);
                    data = await response.json();
                    displayOsSummaryReport(data);
                } else if (selectedReportType === 'devices_online') { // <<< NOVO BLOCO
                    reportTitle.textContent = 'Relatório: Dispositivos Online';
                    response = await fetch('http://127.0.0.1:5000/api/reports/devices-online');
                    if (!response.ok) throw new Error(`Erro HTTP: ${response.status} ao buscar dispositivos online.`);
                    data = await response.json();
                    displayFullInventoryReport(data); // Reutiliza a função para listar dispositivos
                } else if (selectedReportType === 'devices_offline') { // <<< NOVO BLOCO
                    reportTitle.textContent = 'Relatório: Dispositivos Offline';
                    response = await fetch('http://127.0.0.1:5000/api/reports/devices-offline');
                    if (!response.ok) throw new Error(`Erro HTTP: ${response.status} ao buscar dispositivos offline.`);
                    data = await response.json();
                    displayFullInventoryReport(data); // Reutiliza a função para listar dispositivos
                } else {
                    reportOutputDiv.innerHTML = '<p style="color: red;">Tipo de relatório não implementado.</p>';
                }
            } catch (error) {
                console.error("Erro ao gerar relatório:", error);
                reportOutputDiv.innerHTML = `<p style="color: red;">Falha ao gerar relatório: ${error.message}</p>`;
                reportTitle.textContent = 'Erro ao Gerar Relatório';
            }
        });
    }

    function displayFullInventoryReport(devices) {
        if (!devices || devices.length === 0) {
            reportOutputDiv.innerHTML = '<p>Nenhum dispositivo encontrado para este relatório.</p>';
            return;
        }

        let tableHtml = `
            <table class="basic-table">
                <thead>
                    <tr>
                        <th>Nome do Host</th>
                        <th>IP Principal</th>
                        <th>MAC Principal</th>
                        <th>Sistema Operacional</th>
                        <th>Fabricante</th>
                        <th>Tipo</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        `;
        devices.forEach(device => {
            tableHtml += `
                <tr>
                    <td>${device.NomeHost || 'N/D'}</td>
                    <td>${device.IPPrincipal || 'N/D'}</td>
                    <td>${device.MACPrincipal || 'N/D'}</td>
                    <td>${device.SistemaOperacionalNome || 'N/D'}</td>
                    <td>${device.FabricanteNome || 'N/D'}</td>
                    <td>${device.TipoDispositivoNome || 'N/D'}</td>
                    <td class="${device.StatusAtual === 'Online' ? 'status-online' : (device.StatusAtual === 'Offline' ? 'status-offline' : 'status-warning')}">
                        ${device.StatusAtual || 'N/D'}
                    </td>
                </tr>
            `;
        });
        tableHtml += '</tbody></table>';
        reportOutputDiv.innerHTML = tableHtml;
    }

    function displayOsSummaryReport(summaryData) {
        // Sua função displayOsSummaryReport existente
        if (!summaryData || summaryData.length === 0) {
            reportOutputDiv.innerHTML = '<p>Nenhum dado de sumário de SO para exibir.</p>';
            return;
        }
        let tableHtml = `
            <table class="basic-table">
                <thead>
                    <tr>
                        <th>Sistema Operacional (Nome)</th>
                        <th>Família do SO</th>
                        <th>Total de Dispositivos</th>
                    </tr>
                </thead>
                <tbody>
        `;
        summaryData.forEach(item => {
            tableHtml += `
                <tr>
                    <td>${item.SistemaOperacionalNome || 'N/D'}</td>
                    <td>${item.SistemaOperacionalFamilia || 'N/D'}</td>
                    <td>${item.TotalDispositivos}</td>
                </tr>
            `;
        });
        tableHtml += '</tbody></table>';
        reportOutputDiv.innerHTML = tableHtml;
    }
});