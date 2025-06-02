document.addEventListener('DOMContentLoaded', function() {
    // --- CONSTANTES PARA ELEMENTOS DO DOM ---
    const deviceListTbody = document.getElementById('device-list-tbody');
    const searchInput = document.getElementById('searchInput');
    const loadingMessageRow = '<tr><td colspan="9" style="text-align:center;">Carregando dispositivos...</td></tr>';
    const errorMessageRow = '<tr><td colspan="9" style="text-align:center;">Erro ao carregar dispositivos. Tente novamente mais tarde.</td></tr>';
    const noDevicesMessageRow = '<tr><td colspan="9" style="text-align:center;">Nenhum dispositivo encontrado.</td></tr>';

    // Modal de Adicionar
    const addDeviceModal = document.getElementById('addDeviceModal');
    const addDeviceForm = document.getElementById('addDeviceForm');
    const openAddDeviceModalButton = document.querySelector('.content header .actions button.btn-primary');
    const addModalCloseButton = addDeviceModal.querySelector('.close-button');
    const addModalCancelButton = addDeviceModal.querySelector('.modal-footer button.btn-secondary');
    const addDeviceMessageDiv = document.getElementById('add-device-message');
    const addFabricanteSelect = document.getElementById('add-fabricante');
    const addSoSelect = document.getElementById('add-so');
    const addTipoDispositivoSelect = document.getElementById('add-tipoDispositivo');

    // Modal de Editar
    const editDeviceModal = document.getElementById('editDeviceModal');
    const editDeviceForm = document.getElementById('editDeviceForm');
    const editModalCloseButton = document.getElementById('closeEditModalButton');
    const editModalCancelButton = document.getElementById('cancelEditModalButton');
    const editDeviceMessageDiv = document.getElementById('edit-device-message');
    const hiddenDeviceIdInput = document.getElementById('edit-deviceId');
    const editFabricanteSelect = document.getElementById('edit-fabricante');
    const editSoSelect = document.getElementById('edit-so');
    const editTipoDispositivoSelect = document.getElementById('edit-tipoDispositivo');

    // Modal de Detalhes
    const deviceDetailsModal = document.getElementById('deviceDetailsModal');
    const deviceDetailsBody = document.getElementById('deviceDetailsBody');
    const detailsModalCloseButton = document.getElementById('closeDeviceDetailsModalButton');
    const detailsModalCancelButton = document.getElementById('cancelDeviceDetailsModalButton');


    // --- FUNÇÕES AUXILIARES ---

    function prefillAndOpenAddModal(data) {
        console.log("DEVICE HANDLER: Pré-preenchendo modal com dados:", data);
        addDeviceForm.reset();
        addDeviceMessageDiv.textContent = '';
        addDeviceMessageDiv.className = 'form-message-placeholder';

        if (data.nomeHost) document.getElementById('add-nomeHost').value = data.nomeHost;

        if (document.getElementById('add-enderecoIP') && data.enderecoIP) {
            document.getElementById('add-enderecoIP').value = data.enderecoIP;
        }
        if (document.getElementById('add-enderecoMAC') && data.enderecoMAC) {
            document.getElementById('add-enderecoMAC').value = data.enderecoMAC;
        }

        let descricao = data.descricaoInicial || '';
        document.getElementById('add-descricao').value = descricao;

        if (data.id_ip_descoberto) {
            addDeviceForm.dataset.idIpDescoberto = data.id_ip_descoberto; 
        } else {
            delete addDeviceForm.dataset.idIpDescoberto;
        }

        populateSelect(addFabricanteSelect, '/fabricantes', 'ID_Fabricante', 'Nome');
        populateSelect(addSoSelect, '/sistemasoperacionais', 'ID_SistemaOperacional', 'Nome', true);
        populateSelect(addTipoDispositivoSelect, '/tiposdispositivo', 'ID_TipoDispositivo', 'Nome');

        addDeviceModal.style.display = 'block';
    }

    const prefillDataString = sessionStorage.getItem('prefillDeviceData');
    if (prefillDataString) {
        const prefillData = JSON.parse(prefillDataString);
        prefillAndOpenAddModal(prefillData);
        sessionStorage.removeItem('prefillDeviceData');
    }
    
    async function fetchAndDisplayDevices(searchTerm = '') {
        if (!deviceListTbody) {
            console.error("Elemento tbody com ID 'device-list-tbody' não foi encontrado!");
            return;
        }
        deviceListTbody.innerHTML = loadingMessageRow;

        let apiURL = 'http://127.0.0.1:5000/devices';
        if (searchTerm) {
            apiURL += `?search=${encodeURIComponent(searchTerm)}`;
        }
        console.log("API URL para fetch (GET /devices):", apiURL);

        try {
            const response = await fetch(apiURL, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                console.error("Erro na resposta da API ao listar: ", response.status, response.statusText);
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
                        } else { dataFormatada = device.DataUltimaVarredura; }
                    } catch (e) {
                        console.warn("Erro ao formatar DataUltimaVarredura:", device.DataUltimaVarredura, e);
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
        if (!selectElement) {
            console.error("Elemento select não encontrado para popular:", selectElement);
            return;
        }
        try {
            const response = await fetch(`http://127.0.0.1:5000${endpoint}`);
            if (!response.ok) {
                console.error(`Erro ao buscar dados para ${selectElement.id}: ${response.statusText}`);
                selectElement.innerHTML = '<option value="">Erro ao carregar</option>';
                return;
            }
            const data = await response.json();
            selectElement.innerHTML = '<option value="">Selecione...</option>';
            data.forEach(item => {
                const option = document.createElement('option');
                option.value = item[valueField];
                option.textContent = nameWithVersion && item.Versao ? `${item[textField]} ${item.Versao || ''}`.trim() : item[textField];
                selectElement.appendChild(option);
            });
        } catch (error) {
            console.error(`Erro na chamada fetch para ${selectElement.id}:`, error);
            selectElement.innerHTML = '<option value="">Falha ao carregar</option>';
        }
    }

    // --- EVENT LISTENERS PARA CONTROLES DE MODAIS (ABRIR/FECHAR) ---
    if (openAddDeviceModalButton) {
        openAddDeviceModalButton.addEventListener('click', function() {
            console.log("Botão 'Adicionar Dispositivo' clicado - abrindo modal de adicionar.");
            addDeviceModal.style.display = 'block';
            addDeviceForm.reset();
            addDeviceMessageDiv.textContent = '';
            addDeviceMessageDiv.className = 'form-message-placeholder';
            populateSelect(addFabricanteSelect, '/fabricantes', 'ID_Fabricante', 'Nome');
            populateSelect(addSoSelect, '/sistemasoperacionais', 'ID_SistemaOperacional', 'Nome', true);
            populateSelect(addTipoDispositivoSelect, '/tiposdispositivo', 'ID_TipoDispositivo', 'Nome');
        });
    }

    if (addModalCloseButton) { addModalCloseButton.addEventListener('click', () => addDeviceModal.style.display = 'none'); }
    if (addModalCancelButton) { addModalCancelButton.addEventListener('click', () => addDeviceModal.style.display = 'none'); }
    if (editModalCloseButton) { editModalCloseButton.addEventListener('click', () => editDeviceModal.style.display = 'none'); }
    if (editModalCancelButton) { editModalCancelButton.addEventListener('click', () => editDeviceModal.style.display = 'none'); }
    if (detailsModalCloseButton) { detailsModalCloseButton.addEventListener('click', () => deviceDetailsModal.style.display = 'none'); }
    if (detailsModalCancelButton) { detailsModalCancelButton.addEventListener('click', () => deviceDetailsModal.style.display = 'none'); }

    window.addEventListener('click', function(event) {
        if (event.target == addDeviceModal) addDeviceModal.style.display = 'none';
        if (event.target == editDeviceModal) editDeviceModal.style.display = 'none';
        if (event.target == deviceDetailsModal) deviceDetailsModal.style.display = 'none';
    });

    // --- EVENT LISTENER PARA CAMPO DE BUSCA ---
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = searchInput.value.trim();
            console.log("Frontend: Termo de busca digitado:", searchTerm);
            fetchAndDisplayDevices(searchTerm);
        });
    }

    // --- EVENT LISTENER PARA SUBMISSÃO DO FORMULÁRIO DE ADICIONAR ---
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
                } else if (value.trim() !== "") {
                    deviceData[key] = value.trim();
                }
            });
            
            console.log("ADD FORM: Data to be sent:", deviceData);

            try {
                // --- INÍCIO DA CORREÇÃO ---
                const token = localStorage.getItem('authToken');
                if (!token) {
                    alert("Sua sessão expirou. Faça login novamente.");
                    window.location.href = 'login.html';
                    return;
                }
                // --- FIM DA CORREÇÃO ---
                const response = await fetch('http://127.0.0.1:5000/devices', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}` // <-- ADICIONE ESTA LINHA!
                },
                body: JSON.stringify(deviceData)
                });
                const result = await response.json();
                if (response.ok) {
                    addDeviceMessageDiv.textContent = result.message || 'Dispositivo adicionado com sucesso!';
                    addDeviceMessageDiv.className = 'success-message';

                    const idIpDescobertoOriginal = addDeviceForm.dataset.idIpDescoberto;

                    addDeviceForm.reset();
                    delete addDeviceForm.dataset.idIpDescoberto;

                    fetchAndDisplayDevices();

                    if (idIpDescobertoOriginal) {
                        try {
                            console.log(`DEVICE HANDLER: Atualizando status do IP Descoberto ID ${idIpDescobertoOriginal} para 'Inventariado'`);
                            const statusUpdateResponse = await fetch(`http://127.0.0.1:5000/api/discovery/discovered-ips/${idIpDescobertoOriginal}/status`, {
                                method: 'PUT',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({ status: 'Inventariado' })
                            });
                            if (!statusUpdateResponse.ok) {
                                const errStatusData = await statusUpdateResponse.json().catch(() => ({}));
                                console.error(`Falha ao atualizar status do IP descoberto: ${errStatusData.message || statusUpdateResponse.statusText}`);
                            } else {
                                console.log(`Status do IP Descoberto ID ${idIpDescobertoOriginal} atualizado para 'Inventariado'.`);
                            }
                        } catch (statusError) {
                            console.error('Erro ao tentar atualizar status do IP descoberto:', statusError);
                        }
                    }

                    setTimeout(() => { 
                        addDeviceModal.style.display = 'none';
                    }, 1500);
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
    } else {
        console.error("ADD FORM: Elemento do formulário com ID 'addDeviceForm' não foi encontrado.");
    }

    // --- EVENT LISTENER PARA SUBMISSÃO DO FORMULÁRIO DE EDITAR ---
    if (editDeviceForm) {
        editDeviceForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            console.log("EDIT FORM: Evento de submit disparado.");
            editDeviceMessageDiv.textContent = '';
            editDeviceMessageDiv.className = 'form-message-placeholder';

            // --- INÍCIO DA MODIFICAÇÃO (EDITAR) ---
            const token = localStorage.getItem('authToken');
            if (!token) {
                alert("Sua sessão expirou. Por favor, faça login novamente.");
                window.location.href = 'login.html';
                return;
            }
            // --- FIM DA MODIFICAÇÃO (EDITAR) ---

            const deviceId = hiddenDeviceIdInput.value;
            console.log("EDIT FORM: ID do Dispositivo para atualizar:", deviceId);

            if (!deviceId) {
                editDeviceMessageDiv.textContent = 'ID do dispositivo não encontrado para atualização.';
                editDeviceMessageDiv.className = 'error-message';
                console.error("EDIT FORM: ID do Dispositivo está faltando no input hidden.");
                return;
            }

            const formData = new FormData(editDeviceForm);
            const deviceDataToUpdate = {};
            formData.forEach((value, key) => {
                if (key === 'ID_Dispositivo') return; 

                if (key.startsWith('ID_') && value) {
                    deviceDataToUpdate[key] = parseInt(value, 10);
                } else if (key.startsWith('ID_') && !value) {
                    deviceDataToUpdate[key] = null;
                }
                 else {
                    deviceDataToUpdate[key] = value.trim();
                }
            });
            
            console.log("EDIT FORM: Dados coletados do formulário para enviar:", deviceDataToUpdate);

            try {
                console.log(`EDIT FORM: Enviando requisição PUT para /devices/${deviceId}`);
                
                // --- INÍCIO DA MODIFICAÇÃO (EDITAR) ---
                const response = await fetch(`http://127.0.0.1:5000/devices/${deviceId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(deviceDataToUpdate)
                });
                // --- FIM DA MODIFICAÇÃO (EDITAR) ---
                
                console.log("EDIT FORM: Resposta bruta do backend:", response);
                const result = await response.json(); 
                console.log("EDIT FORM: Resultado JSON parseado da resposta:", result);

                if (response.ok) {
                    console.log("EDIT FORM: Backend respondeu com SUCESSO. Mensagem:", result.message);
                    editDeviceMessageDiv.textContent = result.message || 'Dispositivo atualizado com sucesso!';
                    editDeviceMessageDiv.className = 'success-message';
                    fetchAndDisplayDevices(); 
                    setTimeout(() => {
                        editDeviceModal.style.display = 'none';
                    }, 1500);
                } else {
                    console.warn("EDIT FORM: Backend respondeu com ERRO. Status:", response.status, "Mensagem:", result.message);
                    editDeviceMessageDiv.textContent = result.message || 'Erro ao atualizar dispositivo.';
                    editDeviceMessageDiv.className = 'error-message';
                }
            } catch (error) {
                console.error('EDIT FORM: Erro durante a operação fetch/PUT:', error);
                editDeviceMessageDiv.textContent = 'Erro de comunicação com o servidor.';
                editDeviceMessageDiv.className = 'error-message';
            }
        });
    } else {
        console.error("EDIT FORM: Elemento do formulário com ID 'editDeviceForm' não foi encontrado.");
    }

    // --- EVENT LISTENER PARA OS LINKS DE AÇÃO NA TABELA ---
    if (deviceListTbody) {
        deviceListTbody.addEventListener('click', async function(event) {
            const target = event.target;
            if (target.classList.contains('action-link')) {
                event.preventDefault();
                const deviceId = target.dataset.id;
                const action = target.dataset.action;

                if (action === 'details') {
                    deviceDetailsBody.innerHTML = '<p>Carregando detalhes...</p>';
                    editDeviceMessageDiv.textContent = ''; 
                    addDeviceMessageDiv.textContent = '';
                    try {
                        console.log(`DETAILS ACTION: Buscando dados para dispositivo ID: ${deviceId}`);
                        const response = await fetch(`http://127.0.0.1:5000/devices/${deviceId}`);
                        if (!response.ok) { /* ... tratamento de erro ... */ return; }
                        const device = await response.json();
                        console.log("DETAILS ACTION: Dados recebidos:", device);
                        let detailsHtml = `
                            <h4>Informações Gerais</h4>
                            <p><strong>ID do Dispositivo:</strong> ${device.ID_Dispositivo}</p>
                            <p><strong>Nome do Host:</strong> ${device.NomeHost || 'N/D'}</p>
                            <p><strong>Descrição:</strong> ${device.Descricao || 'N/D'}</p>
                            <p><strong>Modelo:</strong> ${device.Modelo || 'N/D'}</p>
                            <p><strong>Fabricante:</strong> ${device.FabricanteNome || 'N/D'} (ID: ${device.ID_Fabricante || 'N/D'})</p>
                            <p><strong>Sistema Operacional:</strong> ${device.SistemaOperacionalNome || 'N/D'} ${device.SistemaOperacionalVersao || ''} (Família: ${device.SistemaOperacionalFamilia || 'N/D'}, ID: ${device.ID_SistemaOperacional || 'N/D'})</p>
                            <p><strong>Tipo de Dispositivo:</strong> ${device.TipoDispositivoNome || 'N/D'} (ID: ${device.ID_TipoDispositivo || 'N/D'})</p>
                            <p><strong>Status Atual:</strong> ${device.StatusAtual || 'N/D'}</p>
                            <p><strong>Localização Física:</strong> ${device.LocalizacaoFisica || 'N/D'}</p>
                            <p><strong>Gerenciado Por:</strong> ${device.GerenciadoPorNomeUsuario || 'N/D'}</p>
                            <p><strong>Data de Descoberta:</strong> ${device.DataDescoberta ? new Date(device.DataDescoberta).toLocaleString('pt-BR') : 'N/D'}</p>
                            <p><strong>Última Modificação:</strong> ${device.DataUltimaModificacao ? new Date(device.DataUltimaModificacao).toLocaleString('pt-BR') : 'N/D'}</p>
                            <p><strong>Última Varredura:</strong> ${device.DataUltimaVarredura ? new Date(device.DataUltimaVarredura).toLocaleString('pt-BR') : 'N/D'}</p>
                            <p><strong>Observações:</strong> ${device.Observacoes || 'N/D'}</p>
                        `;
                        if (device.interfaces && device.interfaces.length > 0) {
                            detailsHtml += `<h4>Interface de Rede (${device.interfaces.length})</h4>`;
                            device.interfaces.forEach((iface, index) => {
                                detailsHtml += `
                                    <div class="interface-details">
                                        <p><strong>Interface ${index + 1}:</strong> ${iface.NomeInterface || 'N/D'}</p>
                                        <p><strong>&nbsp;&nbsp;&nbsp;MAC Address:</strong> ${iface.EnderecoMAC || 'N/D'} (${iface.FabricanteMAC || 'N/D'})</p>
                                        <p><strong>&nbsp;&nbsp;&nbsp;Endereço IP:</strong> ${iface.EnderecoIPValor || 'N/D'} (${iface.TipoIP || 'N/D'})</p>
                                        <p><strong>&nbsp;&nbsp;&nbsp;Tipo Atribuição:</strong> ${iface.TipoAtribuicao || 'N/D'}</p>
                                        <p><strong>&nbsp;&nbsp;&nbsp;Rede:</strong> ${iface.NomeRede || 'N/D'}</p>
                                    </div>
                                `;
                            });
                        } else {
                            detailsHtml += `<h4>Interfaces de Rede</h4><p>Nenhuma interface de rede encontrada para este dispositivo.</p>`;
                        }
                        
                        deviceDetailsBody.innerHTML = detailsHtml;
                        deviceDetailsModal.style.display = 'block';
                    } catch (error) { /* ... tratamento de erro ... */ }
                } else if (action === 'edit') {
                    addDeviceMessageDiv.textContent = ''; 
                    editDeviceMessageDiv.textContent = ''; 
                    try {
                        // --- INÍCIO DA MODIFICAÇÃO (EDITAR) ---
                        const token = localStorage.getItem('authToken');
                        if (!token) {
                            alert("Sua sessão expirou. Por favor, faça login novamente.");
                            window.location.href = 'login.html';
                            return;
                        }

                        console.log(`EDIT ACTION: Buscando dados para dispositivo ID: ${deviceId}`);
                        const response = await fetch(`http://127.0.0.1:5000/devices/${deviceId}`, {
                           headers: {
                               'Content-Type': 'application/json',
                               'Authorization': `Bearer ${token}`
                           }
                        });
                        // --- FIM DA MODIFICAÇÃO (EDITAR) ---

                        if (!response.ok) { 
                             const errorData = await response.json();
                             alert(`Erro ao buscar dados do dispositivo: ${errorData.message || response.statusText}`);
                             return; 
                        }
                        const deviceData = await response.json();
                        console.log("EDIT ACTION: Dados recebidos para edição:", deviceData);

                        await populateSelect(editFabricanteSelect, '/fabricantes', 'ID_Fabricante', 'Nome');
                        await populateSelect(editSoSelect, '/sistemasoperacionais', 'ID_SistemaOperacional', 'Nome', true);
                        await populateSelect(editTipoDispositivoSelect, '/tiposdispositivo', 'ID_TipoDispositivo', 'Nome');
                        
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
                        console.error("Erro na ação de editar:", error);
                        alert("Ocorreu um erro ao tentar preparar a edição do dispositivo.");
                    }
                } else if (action === 'delete') {
                    if (confirm(`Tem certeza que deseja remover o dispositivo ID: ${deviceId}? Esta ação não pode ser desfeita.`)) {
                        try {
                            // --- INÍCIO DA MODIFICAÇÃO (DELETAR COM AUTORIZAÇÃO) ---
                            const token = localStorage.getItem('authToken');
                            if (!token) {
                                alert("Sua sessão expirou. Por favor, faça login novamente.");
                                window.location.href = 'login.html';
                                return;
                            }

                            const response = await fetch(`http://127.0.0.1:5000/devices/${deviceId}`, {
                                method: 'DELETE',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Authorization': `Bearer ${token}` // Adiciona o token ao cabeçalho
                                }
                            });
                            const result = await response.json();
                            if (response.ok) { 
                                alert(result.message || "Dispositivo removido com sucesso.");
                                fetchAndDisplayDevices();
                             } 
                            else { 
                                alert(`Erro ao remover: ${result.message || 'Erro desconhecido'}`);
                            }
                        } catch (error) { 
                            console.error("Erro ao deletar:", error);
                            alert("Erro de comunicação ao tentar remover o dispositivo.");
                        }
                    }
                }
            }
        });
    }

    // Carrega a lista de dispositivos inicial
    fetchAndDisplayDevices();
});