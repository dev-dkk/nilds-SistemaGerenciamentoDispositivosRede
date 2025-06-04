document.addEventListener('DOMContentLoaded', function() {
    const scanConfigForm = document.getElementById('scanConfigForm');
    const scanIpRangesInput = document.getElementById('scanIpRanges');
    const scanFrequencySelect = document.getElementById('scanFrequency');
    const scanEnabledCheckbox = document.getElementById('scanEnabled');
    // const scanCronInput = document.getElementById('scanCron'); // Para o futuro
    const scanConfigMessageDiv = document.getElementById('scan-config-message');

    async function loadScanSettings() {
        if (!scanConfigForm) return; // Se não estiver na aba/página correta

        console.log("CONFIG_HANDLER: Buscando configurações de varredura...");
        try {
            const response = await fetch('http://127.0.0.1:5000/api/settings/scan-config');
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                console.error("Erro ao carregar configurações:", errData.message || response.statusText);
                scanConfigMessageDiv.textContent = `Erro ao carregar configurações: ${errData.message || 'Falha do servidor'}`;
                scanConfigMessageDiv.className = 'error-message'; // Garanta que .error-message está definido no seu style.css
                return;
            }
            const config = await response.json();
            console.log("CONFIG_HANDLER: Configurações recebidas:", config);

            if(scanIpRangesInput && config.FaixasIP !== null) scanIpRangesInput.value = config.FaixasIP;
            if(scanFrequencySelect && config.FrequenciaMinutos !== null) scanFrequencySelect.value = config.FrequenciaMinutos;
            if(scanEnabledCheckbox) scanEnabledCheckbox.checked = config.VarreduraAtivada || false;
            // if(scanCronInput && config.AgendamentoCron !== null) scanCronInput.value = config.AgendamentoCron;

        } catch (error) {
            console.error("Falha ao buscar configurações de varredura:", error);
            scanConfigMessageDiv.textContent = 'Falha ao carregar configurações. Erro de comunicação.';
            scanConfigMessageDiv.className = 'error-message';
        }
    }

    if (scanConfigForm) {
        scanConfigForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            scanConfigMessageDiv.textContent = 'Salvando...';
            scanConfigMessageDiv.className = 'form-message-placeholder info-message'; // Crie .info-message se quiser

            const settingsData = {
                FaixasIP: scanIpRangesInput ? scanIpRangesInput.value : null,
                FrequenciaMinutos: scanFrequencySelect ? parseInt(scanFrequencySelect.value, 10) : null,
                VarreduraAtivada: scanEnabledCheckbox ? scanEnabledCheckbox.checked : false
                // AgendamentoCron: scanCronInput ? scanCronInput.value : null // Para o futuro
            };
            console.log("CONFIG_HANDLER: Enviando configurações de varredura:", settingsData);

            try {
                const response = await fetch('http://127.0.0.1:5000/api/settings/scan-config', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        // Adicionar header de autenticação aqui se necessário
                    },
                    body: JSON.stringify(settingsData)
                });
                const result = await response.json();
                if (response.ok) {
                    scanConfigMessageDiv.textContent = result.message || 'Configurações salvas com sucesso!';
                    scanConfigMessageDiv.className = 'success-message'; // Garanta que .success-message está definido
                } else {
                    scanConfigMessageDiv.textContent = result.message || 'Erro ao salvar configurações.';
                    scanConfigMessageDiv.className = 'error-message';
                }
            } catch (error) {
                console.error("Erro ao salvar configurações de varredura:", error);
                scanConfigMessageDiv.textContent = 'Erro de comunicação ao salvar configurações.';
                scanConfigMessageDiv.className = 'error-message';
            }
        });
    }

    // Carrega as configurações quando a aba/página de configurações de varredura for visível.
    // Se 'tab-varredura' é o ID do container da aba, podemos observar quando ela se torna visível
    // ou simplesmente carregar se o formulário existir.
    if (document.getElementById('tab-varredura') && scanConfigForm) { // Ajuste se o ID da aba for diferente
        loadScanSettings();
    } else if (scanConfigForm) { // Se não houver sistema de abas e o form estiver sempre lá
        loadScanSettings();
    }
});