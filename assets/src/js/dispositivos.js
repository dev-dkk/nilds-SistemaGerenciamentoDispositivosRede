document.addEventListener('DOMContentLoaded', function() {
    // --- CONSTANTES PARA ELEMENTOS DO DOM ---
    const deviceListTbody = document.getElementById('device-list-tbody');
    const loadingMessageRow = '<tr><td colspan="9" style="text-align:center;">Carregando dispositivos...</td></tr>';
    const errorMessageRow = '<tr><td colspan="9" style="text-align:center;">Erro ao carregar dispositivos. Tente novamente mais tarde.</td></tr>';
    const noDevicesMessageRow = '<tr><td colspan="9" style="text-align:center;">Nenhum dispositivo encontrado.</td></tr>';

    // Modal de Adicionar
    const addDeviceModal = document.getElementById('addDeviceModal');
    const addDeviceForm = document.getElementById('addDeviceForm');
    const openAddDeviceModalButton = document.querySelector('.content header .actions button.btn-primary');
    const closeModalButton = addDeviceModal.querySelector('.close-button');
    const cancelModalButton = addDeviceModal.querySelector('.modal-footer button.btn-secondary');
    const addDeviceMessageDiv = document.getElementById('add-device-message');
    const fabricanteSelect = document.getElementById('add-fabricante');
    const soSelect = document.getElementById('add-so');
    const tipoDispositivoSelect = document.getElementById('add-tipoDispositivo');

    // Modal de Editar
    const editDeviceModal = document.getElementById('editDeviceModal');
    const editDeviceForm = document.getElementById('editDeviceForm');
    const closeEditModalButton = document.getElementById('closeEditModalButton'); // ID que você definiu no HTML do modal de edição
    const cancelEditModalButton = document.getElementById('cancelEditModalButton'); // ID que você definiu no HTML do modal de edição
    const editDeviceMessageDiv = document.getElementById('edit-device-message');
    const hiddenDeviceIdInput = document.getElementById('edit-deviceId');
    const editFabricanteSelect = document.getElementById('edit-fabricante');
    const editSoSelect = document.getElementById('edit-so');
    const editTipoDispositivoSelect = document.getElementById('edit-tipoDispositivo');

    // --- FUNÇÕES AUXILIARES ---
    async function fetchAndDisplayDevices() {
        // ... seu código fetchAndDisplayDevices (parece OK como está) ...
        // Cole ele aqui
        if (!deviceListTbody) {
            console.error("Elemento tbody com ID 'device-list-tbody' não foi encontrado!");
            return;
        }
        deviceListTbody.innerHTML = loadingMessageRow;
        try {
            const response = await fetch('http://127.0.0.1:5000/devices', { /* ... headers ... */ });
            if (!response.ok) {
                console.error("Erro na resposta da API: ", response.status, response.statusText);
                const errorData = await response.json().catch(() => ({ message: "Erro desconhecido do servidor." }));
                deviceListTbody.innerHTML = `<tr><td colspan="9" style="text-align:center;">Falha ao carregar: ${errorData.message || response.statusText}</td></tr>`;
                return;
            }
            const devices = await response.json();
            deviceListTbody.innerHTML = '';
            if (devices.length === 0) {
                deviceListTbody.innerHTML = noDevicesMessageRow;
                return;
            }
            devices.forEach(device => {
                const row = deviceListTbody.insertRow();
                const cellCheckbox = row.insertCell();
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.classList.add('row-select');
                checkbox.value = device.ID_Dispositivo;
                cellCheckbox.appendChild(checkbox);
                
                const createCell = (data) => {
                    const cell = row.insertCell();
                    cell.textContent = data !== null && data !== undefined ? data : 'N/D';
                    return cell;
                };
                createCell(device.NomeHost);
                createCell(device.IPPrincipal);
                createCell(device.MACPrincipal);
                createCell(device.SistemaOperacionalNome);
                createCell(device.FabricanteNome);
                const statusCell = createCell(device.StatusAtual);
                if (device.StatusAtual === 'Online') statusCell.className = 'status-online';
                else if (device.StatusAtual === 'Offline') statusCell.className = 'status-offline';
                else if (device.StatusAtual === 'Com Falha' || device.StatusAtual === 'Lento') statusCell.className = 'status-warning';
                
                let dataFormatada = 'N/D';
                if (device.DataUltimaVarredura) {
                    try {
                        const dateObj = new Date(device.DataUltimaVarredura);
                        if (!isNaN(dateObj)) {
                           dataFormatada = dateObj.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
                        }
                    } catch (e) {
                        console.warn("Erro formatar DataUltimaVarredura:", device.DataUltimaVarredura, e);
                        dataFormatada = device.DataUltimaVarredura;
                    }
                }
                createCell(dataFormatada);
                const actionsCell = row.insertCell();
                actionsCell.innerHTML = `
                    <a href="#" class="action-link" data-id="${device.ID_Dispositivo}" data-action="details">Detalhes</a>
                    <a href="#" class="action-link" data-id="${device.ID_Dispositivo}" data-action="edit">Editar</a>
                    <a href="#" class="action-link" data-id="${device.ID_Dispositivo}" data-action="delete" style="color:red;">Remover</a>
                `;
            });
        } catch (error) {
            console.error('Erro ao buscar dispositivos:', error);
            deviceListTbody.innerHTML = errorMessageRow;
        }
    }

    async function populateSelect(selectElement, endpoint, valueField, textField, nameWithVersion = false) {
        // ... seu código populateSelect (parece OK como está) ...
        // Cole ele aqui
        try {
            const response = await fetch(`http://127.0.0.1:5000${endpoint}`);
            if (!response.ok) {
                console.error(`Erro ao buscar dados para ${selectElement.id}: ${response.statusText}`);
                return;
            }
            const data = await response.json();
            selectElement.innerHTML = '<option value="">Selecione...</option>';
            data.forEach(item => {
                const option = document.createElement('option');
                option.value = item[valueField];
                option.textContent = nameWithVersion && item.Versao ? `${item[textField]} ${item.Versao}` : item[textField];
                selectElement.appendChild(option);
            });
        } catch (error) {
            console.error(`Erro na chamada fetch para ${selectElement.id}:`, error);
        }
    }

    // --- EVENT LISTENERS PARA MODAIS E FORMULÁRIOS ---

    // Lógica para o botão "Adicionar Dispositivo" (botão principal da página)
    if (openAddDeviceModalButton) {
        openAddDeviceModalButton.addEventListener('click', function() {
            console.log("Botão Adicionar Dispositivo clicado - abrindo modal.");
            addDeviceModal.style.display = 'block';
            addDeviceForm.reset();
            addDeviceMessageDiv.textContent = '';
            addDeviceMessageDiv.className = 'form-message-placeholder';
            populateSelect(fabricanteSelect, '/fabricantes', 'ID_Fabricante', 'Nome');
            populateSelect(soSelect, '/sistemasoperacionais', 'ID_SistemaOperacional', 'Nome', true);
            populateSelect(tipoDispositivoSelect, '/tiposdispositivo', 'ID_TipoDispositivo', 'Nome');
        });
    }

    // Fechar modal de ADICIONAR
    if (closeModalButton) {
        closeModalButton.addEventListener('click', function() {
            addDeviceModal.style.display = 'none';
        });
    }
    if (cancelModalButton) {
        cancelModalButton.addEventListener('click', function() {
            addDeviceModal.style.display = 'none';
        });
    }

    // Fechar modal de EDITAR
    if (closeEditModalButton) {
        closeEditModalButton.addEventListener('click', function() {
            editDeviceModal.style.display = 'none';
        });
    }
    if (cancelEditModalButton) {
        cancelEditModalButton.addEventListener('click', function() {
            editDeviceModal.style.display = 'none';
        });
    }

    // Fechar qualquer modal clicando fora
    window.addEventListener('click', function(event) {
        if (event.target == addDeviceModal) {
            addDeviceModal.style.display = 'none';
        }
        if (event.target == editDeviceModal) {
            editDeviceModal.style.display = 'none';
        }
    });

    // Submeter formulário de ADICIONAR dispositivo
    if (addDeviceForm) {
        addDeviceForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            console.log("ADD FORM: Submit event triggered.");
            addDeviceMessageDiv.textContent = '';
            addDeviceMessageDiv.className = 'form-message-placeholder';

            const formData = new FormData(addDeviceForm);
            const deviceData = {};
            formData.forEach((value, key) => {
                if (key.startsWith('ID_') && value) {
                    deviceData[key] = parseInt(value, 10);
                } else if (value) {
                    deviceData[key] = value;
                }
            });
            
            const allFields = ['NomeHost', 'Descricao', 'Modelo', 'ID_Fabricante', 'ID_SistemaOperacional', 'ID_TipoDispositivo', 'StatusAtual', 'LocalizacaoFisica', 'Observacoes'];
            allFields.forEach(field => {
                if (!deviceData.hasOwnProperty(field)) {
                    if (!field.startsWith('ID_')) {
                         deviceData[field] = null;
                    }
                }
            });
            console.log("ADD FORM: Data to be sent:", deviceData);

            try {
                const response = await fetch('http://127.0.0.1:5000/devices', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(deviceData)
                });
                const result = await response.json();
                if (response.ok) {
                    addDeviceMessageDiv.textContent = result.message || 'Dispositivo adicionado com sucesso!';
                    addDeviceMessageDiv.className = 'success-message';
                    addDeviceForm.reset();
                    fetchAndDisplayDevices();
                    setTimeout(() => { addDeviceModal.style.display = 'none'; }, 1500);
                } else {
                    addDeviceMessageDiv.textContent = result.message || 'Erro ao adicionar dispositivo.';
                    addDeviceMessageDiv.className = 'error-message';
                }
            } catch (error) {
                console.error('Erro ao submeter novo dispositivo:', error);
                addDeviceMessageDiv.textContent = 'Erro de comunicação com o servidor.';
                addDeviceMessageDiv.className = 'error-message';
            }
        });
    }

    // Submeter formulário de EDITAR dispositivo (AGORA NO NÍVEL CORRETO)
    if (editDeviceForm) {
        editDeviceForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            console.log("EDIT FORM: Evento de submit disparado."); // LOG A (da sua depuração anterior)

            editDeviceMessageDiv.textContent = '';
            editDeviceMessageDiv.className = 'form-message-placeholder';

            const deviceId = hiddenDeviceIdInput.value;
            console.log("EDIT FORM: ID do Dispositivo para atualizar:", deviceId); // LOG B

            if (!deviceId) {
                editDeviceMessageDiv.textContent = 'ID do dispositivo não encontrado para atualização.';
                editDeviceMessageDiv.className = 'error-message';
                console.error("EDIT FORM: ID do Dispositivo está faltando no input hidden."); // LOG C
                return;
            }

            const formData = new FormData(editDeviceForm);
            const deviceDataToUpdate = {};
            formData.forEach((value, key) => {
                if (key === 'ID_Dispositivo') return; 

                if (key.startsWith('ID_') && value) {
                    deviceDataToUpdate[key] = parseInt(value, 10);
                } else if (value || key === 'Descricao' || key === 'Modelo' || key === 'LocalizacaoFisica' || key === 'Observacoes') { 
                    deviceDataToUpdate[key] = value;
                }
            });
            
            console.log("EDIT FORM: Dados coletados do formulário para enviar:", deviceDataToUpdate); // LOG D

            try {
                console.log(`EDIT FORM: Enviando requisição PUT para /devices/${deviceId}`); // LOG E
                const response = await fetch(`http://127.0.0.1:5000/devices/${deviceId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(deviceDataToUpdate)
                });
                
                console.log("EDIT FORM: Resposta bruta do backend:", response); // LOG F

                const result = await response.json(); 
                console.log("EDIT FORM: Resultado JSON parseado da resposta:", result); // LOG G

                if (response.ok) {
                    console.log("EDIT FORM: Backend respondeu com SUCESSO (response.ok é true). Mensagem:", result.message); // LOG H
                    editDeviceMessageDiv.textContent = result.message || 'Dispositivo atualizado com sucesso!';
                    editDeviceMessageDiv.className = 'success-message';
                    fetchAndDisplayDevices(); 
                    setTimeout(() => {
                        editDeviceModal.style.display = 'none';
                    }, 1500);
                } else {
                    console.warn("EDIT FORM: Backend respondeu com ERRO (response.ok é false). Status:", response.status, "Mensagem:", result.message); // LOG I
                    editDeviceMessageDiv.textContent = result.message || 'Erro ao atualizar dispositivo.';
                    editDeviceMessageDiv.className = 'error-message';
                }
            } catch (error) {
                console.error('EDIT FORM: Erro durante a operação fetch/PUT:', error); // LOG J
                editDeviceMessageDiv.textContent = 'Erro de comunicação com o servidor.';
                editDeviceMessageDiv.className = 'error-message';
            }
        });
    } else {
        console.error("EDIT FORM: Elemento do formulário com ID 'editDeviceForm' não foi encontrado.");
    }

    // Event listener para os links de ação na tabela (Detalhes, Editar, Remover)
    if (deviceListTbody) {
        deviceListTbody.addEventListener('click', async function(event) {
            const target = event.target;
            if (target.classList.contains('action-link')) {
                event.preventDefault();
                const deviceId = target.dataset.id;
                const action = target.dataset.action;

                if (action === 'details') {
                    alert(`Ação: Ver Detalhes do dispositivo ID: ${deviceId} (implementar)`);
                } else if (action === 'edit') {
                    // Limpa mensagens de erro/sucesso de modais anteriores
                    addDeviceMessageDiv.textContent = ''; 
                    addDeviceMessageDiv.className = 'form-message-placeholder';
                    editDeviceMessageDiv.textContent = ''; 
                    editDeviceMessageDiv.className = 'form-message-placeholder';

                    try {
                        console.log(`EDIT ACTION: Buscando dados para dispositivo ID: ${deviceId}`);
                        const response = await fetch(`http://127.0.0.1:5000/devices/${deviceId}`);
                        if (!response.ok) {
                            const errData = await response.json().catch(() => ({}));
                            alert(`Erro ao buscar dados do dispositivo para edição: ${errData.message || response.statusText}`);
                            return;
                        }
                        const deviceData = await response.json();
                        console.log("EDIT ACTION: Dados recebidos para edição:", deviceData);

                        // Popular selects ANTES de definir seus valores
                        await populateSelect(editFabricanteSelect, '/fabricantes', 'ID_Fabricante', 'Nome');
                        await populateSelect(editSoSelect, '/sistemasoperacionais', 'ID_SistemaOperacional', 'Nome', true);
                        await populateSelect(editTipoDispositivoSelect, '/tiposdispositivo', 'ID_TipoDispositivo', 'Nome');
                        
                        // Preencher o formulário de edição
                        hiddenDeviceIdInput.value = deviceData.ID_Dispositivo;
                        document.getElementById('edit-nomeHost').value = deviceData.NomeHost || '';
                        document.getElementById('edit-descricao').value = deviceData.Descricao || '';
                        document.getElementById('edit-modelo').value = deviceData.Modelo || '';
                        document.getElementById('edit-statusAtual').value = deviceData.StatusAtual || 'Desconhecido';
                        document.getElementById('edit-localizacao').value = deviceData.LocalizacaoFisica || '';
                        document.getElementById('edit-observacoes').value = deviceData.Observacoes || '';

                        editFabricanteSelect.value = deviceData.ID_Fabricante || '';
                        editSoSelect.value = deviceData.ID_SistemaOperacional || '';
                        editTipoDispositivoSelect.value = deviceData.ID_TipoDispositivo || '';
                        
                        editDeviceModal.style.display = 'block';
                    } catch (error) {
                        console.error(`Erro ao preparar edição do dispositivo ID ${deviceId}:`, error);
                        alert('Não foi possível carregar os dados para edição.');
                    }
                } else if (action === 'delete') {
                    if (confirm(`Tem certeza que deseja remover o dispositivo ID: ${deviceId}? Esta ação não pode ser desfeita.`)) {
                        try {
                            const response = await fetch(`http://127.0.0.1:5000/devices/${deviceId}`, {
                                method: 'DELETE',
                                headers: {'Content-Type': 'application/json'}
                            });
                            const result = await response.json();
                            if (response.ok) {
                                alert(result.message || 'Dispositivo removido com sucesso!');
                                fetchAndDisplayDevices();
                            } else {
                                alert(`Erro ao remover dispositivo: ${result.message || response.statusText}`);
                            }
                        } catch (error) {
                            console.error('Erro ao tentar remover dispositivo:', error);
                            alert('Erro de comunicação com o servidor ao tentar remover o dispositivo.');
                        }
                    }
                }
            }
        });
    }

    // Carrega a lista de dispositivos inicial
    fetchAndDisplayDevices();
});