/**
 * Painel de Coleta de Encartes - Frontend Corporativo & Automação
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- ESTADO ---
    let currentConfig = {};
    let currentProfiles = [];
    let currentOffers = [];
    let dbOffers = [];
    let eventSource = null;
    let isTaskRunning = false;

    // --- ELEMENTOS DOM ---
    const statusBadge = document.getElementById('status-badge');
    const statusText = document.getElementById('status-text');
    const profilesCount = document.getElementById('profiles-count');

    const selectDateMode = document.getElementById('select-date-mode');
    const customDateInputs = document.getElementById('custom-date-inputs');
    const inputDateStart = document.getElementById('input-date-start');
    const inputDateEnd = document.getElementById('input-date-end');
    const inputPostLimit = document.getElementById('input-post-limit');
    const btnStartScrape = document.getElementById('btn-start-scrape');
    const btnStopScrape = document.getElementById('btn-stop-scrape');

    const progressWrapper = document.getElementById('progress-wrapper');
    const progressStepTitle = document.getElementById('progress-step-title');
    const progressPercentage = document.getElementById('progress-percentage');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const progressStepDetail = document.getElementById('progress-step-detail');

    // Tabela e Filtros da Última Coleta
    const tabCountItems = document.getElementById('tab-count-items');
    const tableOffersBody = document.getElementById('table-offers-body');
    const inputSearchItems = document.getElementById('input-search-items');
    const filterCategory = document.getElementById('filter-category');
    const filterMarket = document.getElementById('filter-market');
    const btnDownloadExcel = document.getElementById('btn-download-excel');
    const btnDownloadCsv = document.getElementById('btn-download-csv');
    const resultsActions = document.getElementById('results-actions');
    const databaseActions = document.getElementById('database-actions');

    // Banco de Dados
    const tabCountDb = document.getElementById('tab-count-db');
    const dbStatTotal = document.getElementById('db-stat-total');
    const dbStatMarkets = document.getElementById('db-stat-markets');
    const dbStatCategories = document.getElementById('db-stat-categories');
    const dbStatRuns = document.getElementById('db-stat-runs');
    const tableDbOffersBody = document.getElementById('table-db-offers-body');
    const inputSearchDb = document.getElementById('input-search-db');
    const filterDbMarket = document.getElementById('filter-db-market');
    const btnRefreshDb = document.getElementById('btn-refresh-db');

    // Logs e Histórico
    const terminalScreen = document.getElementById('terminal-screen');
    const chkAutoscroll = document.getElementById('chk-autoscroll');
    const btnClearLogs = document.getElementById('btn-clear-logs');
    const historyContainer = document.getElementById('history-container');

    // Modals
    const btnOpenConfig = document.getElementById('btn-open-config');
    const btnOpenProfiles = document.getElementById('btn-open-profiles');
    const modalConfig = document.getElementById('modal-config');
    const modalProfiles = document.getElementById('modal-profiles');
    const modalImagePreview = document.getElementById('modal-image-preview');

    // Config form
    const cfgApifyToken = document.getElementById('cfg-apify-token');
    const cfgVisionProvider = document.getElementById('cfg-vision-provider');
    const cfgGeminiKey = document.getElementById('cfg-gemini-key');
    const cfgOpenaiKey = document.getElementById('cfg-openai-key');
    const groupGeminiKey = document.getElementById('group-gemini-key');
    const groupOpenaiKey = document.getElementById('group-openai-key');
    
    // Telegram Form
    const cfgTelegramToken = document.getElementById('cfg-telegram-token');
    const cfgTelegramChatId = document.getElementById('cfg-telegram-chat-id');
    const cfgTelegramEnabled = document.getElementById('cfg-telegram-enabled');
    const cfgTelegramSendExcel = document.getElementById('cfg-telegram-send-excel');
    const btnTestTelegram = document.getElementById('btn-test-telegram');
    const telegramTestFeedback = document.getElementById('telegram-test-feedback');
    const btnSaveConfig = document.getElementById('btn-save-config');

    // Profiles form
    const tableProfilesBody = document.getElementById('table-profiles-body');
    const newProfileName = document.getElementById('new-profile-name');
    const newProfileUrl = document.getElementById('new-profile-url');
    const btnAddProfile = document.getElementById('btn-add-profile');
    const btnSelectAllProfiles = document.getElementById('btn-select-all-profiles');
    const btnDeselectAllProfiles = document.getElementById('btn-deselect-all-profiles');
    const btnResetDefaultProfiles = document.getElementById('btn-reset-default-profiles');
    const btnSaveProfiles = document.getElementById('btn-save-profiles');

    // Preview
    const previewImgElement = document.getElementById('preview-img-element');
    const btnOpenOriginalImg = document.getElementById('btn-open-original-img');
    const btnOpenInstagramPost = document.getElementById('btn-open-instagram-post');
    const modalImageTitle = document.getElementById('modal-image-title');

    // --- INICIALIZAÇÃO ---
    init();

    async function init() {
        setupTabs();
        setupModals();
        setupEventListeners();
        await loadConfiguration();
        await loadProfiles();
        await loadLatestResults();
        await loadDatabaseData();
        await loadHistory();
        connectLogStream();
    }

    // --- TABS ---
    function setupTabs() {
        const tabBtns = document.querySelectorAll('.tab-button');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.getAttribute('data-tab');
                tabBtns.forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(p => p.classList.remove('active'));
                
                btn.classList.add('active');
                const pane = document.getElementById(targetTab);
                if (pane) pane.classList.add('active');
                
                // Mostra a barra de ações correspondente
                if (targetTab === 'tab-results') {
                    resultsActions.style.display = 'flex';
                    databaseActions.style.display = 'none';
                } else if (targetTab === 'tab-database') {
                    resultsActions.style.display = 'none';
                    databaseActions.style.display = 'flex';
                    loadDatabaseData();
                } else {
                    resultsActions.style.display = 'none';
                    databaseActions.style.display = 'none';
                }

                if (targetTab === 'tab-history') {
                    loadHistory();
                }
            });
        });
    }

    // --- MODALS ---
    function setupModals() {
        btnOpenConfig.addEventListener('click', () => openModal(modalConfig));
        btnOpenProfiles.addEventListener('click', () => openModal(modalProfiles));

        document.querySelectorAll('[data-close]').forEach(btn => {
            btn.addEventListener('click', () => {
                const modalId = btn.getAttribute('data-close');
                const modal = document.getElementById(modalId);
                if (modal) closeModal(modal);
            });
        });
    }

    function openModal(modal) {
        modal.style.display = 'flex';
    }

    function closeModal(modal) {
        modal.style.display = 'none';
    }

    // --- EVENT LISTENERS ---
    function setupEventListeners() {
        selectDateMode.addEventListener('change', () => {
            customDateInputs.style.display = selectDateMode.value === 'custom' ? 'flex' : 'none';
        });

        cfgVisionProvider.addEventListener('change', () => {
            const prov = cfgVisionProvider.value;
            if (prov === 'gemini') {
                groupGeminiKey.style.display = 'block';
                groupOpenaiKey.style.display = 'none';
            } else {
                groupGeminiKey.style.display = 'none';
                groupOpenaiKey.style.display = 'block';
            }
        });

        btnStartScrape.addEventListener('click', startScraping);
        btnStopScrape.addEventListener('click', stopScraping);
        btnSaveConfig.addEventListener('click', saveConfiguration);

        btnTestTelegram.addEventListener('click', testTelegramConnection);

        btnAddProfile.addEventListener('click', addNewProfile);
        btnSelectAllProfiles.addEventListener('click', () => toggleAllProfiles(true));
        btnDeselectAllProfiles.addEventListener('click', () => toggleAllProfiles(false));
        btnResetDefaultProfiles.addEventListener('click', resetDefaultProfiles);
        btnSaveProfiles.addEventListener('click', saveProfilesList);

        inputSearchItems.addEventListener('input', renderOffersTable);
        filterCategory.addEventListener('change', renderOffersTable);
        filterMarket.addEventListener('change', renderOffersTable);

        inputSearchDb.addEventListener('input', renderDatabaseTable);
        filterDbMarket.addEventListener('change', renderDatabaseTable);
        btnRefreshDb.addEventListener('click', loadDatabaseData);

        btnDownloadExcel.addEventListener('click', () => downloadFile('xlsx'));
        btnDownloadCsv.addEventListener('click', () => downloadFile('csv'));

        btnClearLogs.addEventListener('click', () => {
            terminalScreen.innerHTML = '<div class="log-row log-sys">[SISTEMA] Console limpo.</div>';
        });
    }

    // --- CONFIGURAÇÕES ---
    async function loadConfiguration() {
        try {
            const resp = await fetch('/api/config');
            const data = await resp.json();
            currentConfig = data;

            cfgApifyToken.value = data.apify_token_masked || '';
            cfgVisionProvider.value = data.vision_provider || 'gemini';
            cfgGeminiKey.value = data.gemini_api_key_masked || '';
            cfgOpenaiKey.value = data.openai_api_key_masked || '';
            cfgVisionProvider.dispatchEvent(new Event('change'));

            cfgTelegramToken.value = data.telegram_token_masked || '';
            cfgTelegramChatId.value = data.telegram_chat_id || '';
            cfgTelegramEnabled.checked = data.telegram_enabled !== false;
            cfgTelegramSendExcel.checked = data.telegram_send_excel !== false;

            selectDateMode.value = data.date_mode || 'yesterday_today';
            inputPostLimit.value = data.results_limit || 3;
            if (data.custom_start_date) inputDateStart.value = data.custom_start_date;
            if (data.custom_end_date) inputDateEnd.value = data.custom_end_date;
            selectDateMode.dispatchEvent(new Event('change'));
        } catch (e) {
            console.error('Erro ao carregar configurações:', e);
        }
    }

    async function saveConfiguration() {
        try {
            const payload = {
                apify_token: cfgApifyToken.value.trim(),
                vision_provider: cfgVisionProvider.value,
                gemini_api_key: cfgGeminiKey.value.trim(),
                openai_api_key: cfgOpenaiKey.value.trim(),
                telegram_token: cfgTelegramToken.value.trim(),
                telegram_chat_id: cfgTelegramChatId.value.trim(),
                telegram_enabled: cfgTelegramEnabled.checked,
                telegram_send_excel: cfgTelegramSendExcel.checked,
                date_mode: selectDateMode.value,
                custom_start_date: inputDateStart.value,
                custom_end_date: inputDateEnd.value,
                results_limit: parseInt(inputPostLimit.value) || 3
            };

            const resp = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (resp.ok) {
                appendLog('[SISTEMA] Configurações atualizadas com sucesso.', 'log-success');
                closeModal(modalConfig);
                await loadConfiguration();
            } else {
                alert('Erro ao salvar configurações.');
            }
        } catch (e) {
            alert('Erro: ' + e.message);
        }
    }

    async function testTelegramConnection() {
        telegramTestFeedback.style.color = 'var(--text-muted)';
        telegramTestFeedback.textContent = 'Enviando mensagem de teste...';
        btnTestTelegram.disabled = true;

        try {
            const payload = {
                telegram_token: cfgTelegramToken.value.trim(),
                telegram_chat_id: cfgTelegramChatId.value.trim()
            };

            const resp = await fetch('/api/telegram/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();

            if (resp.ok) {
                telegramTestFeedback.style.color = 'var(--success)';
                telegramTestFeedback.textContent = '✅ ' + data.message;
            } else {
                telegramTestFeedback.style.color = 'var(--danger)';
                telegramTestFeedback.textContent = '❌ ' + (data.message || 'Falha no teste');
            }
        } catch (e) {
            telegramTestFeedback.style.color = 'var(--danger)';
            telegramTestFeedback.textContent = '❌ Erro: ' + e.message;
        } finally {
            btnTestTelegram.disabled = false;
        }
    }

    // --- PERFIS ---
    async function loadProfiles() {
        try {
            const resp = await fetch('/api/profiles');
            const data = await resp.json();
            currentProfiles = data.profiles || [];
            renderProfilesTable();
            updateProfilesCountBadge();
        } catch (e) {
            console.error('Erro ao carregar perfis:', e);
        }
    }

    function renderProfilesTable() {
        tableProfilesBody.innerHTML = '';
        currentProfiles.forEach((p, idx) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="text-align: center;">
                    <input type="checkbox" class="chk-profile-active" data-idx="${idx}" ${p.enabled !== false ? 'checked' : ''}>
                </td>
                <td><strong>${escapeHtml(p.name)}</strong></td>
                <td><span style="font-family: var(--font-mono); font-size: 11.5px; color: var(--text-secondary);">${escapeHtml(p.url)}</span></td>
                <td style="text-align: center;">
                    <button class="btn-text btn-delete-profile" data-idx="${idx}" style="color: var(--danger);">Remover</button>
                </td>
            `;
            tableProfilesBody.appendChild(tr);
        });

        tableProfilesBody.querySelectorAll('.chk-profile-active').forEach(chk => {
            chk.addEventListener('change', (e) => {
                const i = parseInt(e.target.getAttribute('data-idx'));
                currentProfiles[i].enabled = e.target.checked;
                updateProfilesCountBadge();
            });
        });

        tableProfilesBody.querySelectorAll('.btn-delete-profile').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const i = parseInt(e.currentTarget.getAttribute('data-idx'));
                currentProfiles.splice(i, 1);
                renderProfilesTable();
                updateProfilesCountBadge();
            });
        });
    }

    function updateProfilesCountBadge() {
        const activeCount = currentProfiles.filter(p => p.enabled !== false).length;
        profilesCount.textContent = `${activeCount}/${currentProfiles.length}`;
    }

    function addNewProfile() {
        const name = newProfileName.value.trim();
        const url = newProfileUrl.value.trim();
        if (!name || !url) {
            alert('Informe o nome e a URL do perfil.');
            return;
        }
        currentProfiles.push({ name, url, enabled: true });
        newProfileName.value = '';
        newProfileUrl.value = '';
        renderProfilesTable();
        updateProfilesCountBadge();
    }

    function toggleAllProfiles(active) {
        currentProfiles.forEach(p => p.enabled = active);
        renderProfilesTable();
        updateProfilesCountBadge();
    }

    function resetDefaultProfiles() {
        if (confirm('Restaurar lista de supermercados padrão?')) {
            loadConfiguration().then(() => loadProfiles());
        }
    }

    async function saveProfilesList() {
        try {
            const resp = await fetch('/api/profiles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ profiles: currentProfiles })
            });
            if (resp.ok) {
                appendLog(`[SISTEMA] Lista de perfis (${currentProfiles.length}) atualizada.`, 'log-success');
                closeModal(modalProfiles);
            }
        } catch (e) {
            alert('Erro ao salvar: ' + e.message);
        }
    }

    // --- BANCO DE DADOS PERSISTIDO ---
    async function loadDatabaseData() {
        try {
            // Carrega Estatísticas
            const respStats = await fetch('/api/database/stats');
            const stats = await respStats.json();
            dbStatTotal.textContent = (stats.total_offers || 0).toLocaleString('pt-BR');
            dbStatMarkets.textContent = (stats.total_supermercados || 0).toLocaleString('pt-BR');
            dbStatCategories.textContent = (stats.total_categorias || 0).toLocaleString('pt-BR');
            dbStatRuns.textContent = (stats.total_runs || 0).toLocaleString('pt-BR');
            tabCountDb.textContent = (stats.total_offers || 0).toLocaleString('pt-BR');

            // Carrega Ofertas Persistidas
            const respOffers = await fetch('/api/database/offers?limit=300');
            const offersData = await respOffers.json();
            dbOffers = offersData.items || [];
            
            // Popula filtro de mercados no BD
            const dbMarkets = [...new Set(dbOffers.map(i => i.supermercado).filter(Boolean))].sort();
            filterDbMarket.innerHTML = '<option value="">Todos os mercados</option>';
            dbMarkets.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                filterDbMarket.appendChild(opt);
            });

            renderDatabaseTable();
        } catch (e) {
            console.error('Erro ao carregar dados do banco:', e);
        }
    }

    function renderDatabaseTable() {
        const query = inputSearchDb.value.toLowerCase().trim();
        const selectedMkt = filterDbMarket.value;

        const filtered = dbOffers.filter(item => {
            const matchesQuery = !query || 
                (item.item && item.item.toLowerCase().includes(query)) ||
                (item.supermercado && item.supermercado.toLowerCase().includes(query)) ||
                (item.categoria && item.categoria.toLowerCase().includes(query));

            const matchesMkt = !selectedMkt || item.supermercado === selectedMkt;
            return matchesQuery && matchesMkt;
        });

        if (filtered.length === 0) {
            tableDbOffersBody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-state">
                        Nenhum registro encontrado no banco de dados.
                    </td>
                </tr>
            `;
            return;
        }

        tableDbOffersBody.innerHTML = '';
        filtered.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span style="font-family: var(--font-mono); color: var(--text-muted); font-size: 11px;">#${item.id}</span></td>
                <td><strong>${escapeHtml(item.supermercado)}</strong></td>
                <td><span class="category-badge">${escapeHtml(item.categoria || 'Outros')}</span></td>
                <td>${escapeHtml(item.item)}</td>
                <td class="text-right price-text">${formatCurrency(item.valor)}</td>
                <td>${escapeHtml(item.data_postagem || '-')}</td>
                <td><span style="font-size: 11.5px; color: var(--text-secondary);">${escapeHtml(item.created_at ? item.created_at.substring(0, 16) : '-')}</span></td>
                <td class="text-center">
                    ${item.link ? `<button class="btn btn-outline btn-sm btn-preview-flyer" data-img="${escapeHtml(item.link)}" data-post="${escapeHtml(item.post_url || '')}" data-market="${escapeHtml(item.supermercado)}">Ver</button>` : '-'}
                </td>
            `;
            tableDbOffersBody.appendChild(tr);
        });

        bindPreviewButtons(tableDbOffersBody);
    }

    // --- SSE & LOGS ---
    function connectLogStream() {
        if (eventSource) eventSource.close();
        eventSource = new EventSource('/api/scrape/logs/stream');

        eventSource.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.type === 'log') {
                    appendLog(data.text);
                } else if (data.type === 'status' || data.type === 'init') {
                    updateStatusUI(data.status);
                }
            } catch (err) {
                console.error(err);
            }
        };

        eventSource.onerror = () => {
            setTimeout(connectLogStream, 3000);
        };
    }

    function appendLog(line, customClass = '') {
        const div = document.createElement('div');
        div.className = `log-row ${customClass}`;
        
        if (line.includes('ERRO') || line.includes('❌')) div.classList.add('log-error');
        else if (line.includes('WARN') || line.includes('⚠️')) div.classList.add('log-warn');
        else if (line.includes('SUCESSO') || line.includes('✅') || line.includes('✨') || line.includes('🎉')) div.classList.add('log-success');
        else if (line.includes('[SISTEMA]') || line.includes('🚀') || line.includes('💾') || line.includes('📲')) div.classList.add('log-sys');

        div.textContent = line;
        terminalScreen.appendChild(div);

        if (chkAutoscroll.checked) {
            terminalScreen.scrollTop = terminalScreen.scrollHeight;
        }
    }

    function updateStatusUI(st) {
        if (!st) return;
        const wasRunning = isTaskRunning;
        isTaskRunning = st.is_running;

        if (st.is_running) {
            statusBadge.className = 'badge badge-running';
            statusText.textContent = 'Em execução';
            btnStartScrape.style.display = 'none';
            btnStopScrape.style.display = 'inline-flex';
            progressWrapper.style.display = 'block';

            progressStepTitle.textContent = st.current_step || 'Processando';
            progressPercentage.textContent = `${st.progress || 0}%`;
            progressBarFill.style.width = `${st.progress || 0}%`;
            progressStepDetail.textContent = st.step_detail || '';
        } else {
            btnStartScrape.style.display = 'inline-flex';
            btnStopScrape.style.display = 'none';

            if (st.status === 'completed') {
                statusBadge.className = 'badge badge-completed';
                statusText.textContent = 'Concluído';
                progressBarFill.style.width = '100%';
                progressPercentage.textContent = '100%';
                progressStepTitle.textContent = 'Concluído com Sucesso';
                if (wasRunning) {
                    loadLatestResults();
                    loadDatabaseData();
                    loadHistory();
                }
            } else if (st.status === 'error') {
                statusBadge.className = 'badge badge-error';
                statusText.textContent = 'Falha';
                progressStepTitle.textContent = 'Erro na Execução';
                progressStepDetail.textContent = st.error_message || 'Falha no processo';
            } else {
                statusBadge.className = 'badge badge-idle';
                statusText.textContent = 'Ocioso';
            }
        }
    }

    async function startScraping() {
        try {
            const payload = {
                date_mode: selectDateMode.value,
                custom_start_date: inputDateStart.value,
                custom_end_date: inputDateEnd.value,
                results_limit: parseInt(inputPostLimit.value) || 3,
                vision_provider: cfgVisionProvider.value
            };

            const resp = await fetch('/api/scrape/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await resp.json();
            if (resp.ok) {
                appendLog('[SISTEMA] Coleta iniciada em segundo plano.', 'log-sys');
                document.querySelector('[data-tab="tab-logs"]').click();
            } else {
                alert(data.message || 'Erro ao iniciar coleta.');
            }
        } catch (e) {
            alert('Erro: ' + e.message);
        }
    }

    async function stopScraping() {
        if (confirm('Deseja interromper o processo em andamento?')) {
            await fetch('/api/scrape/stop', { method: 'POST' });
        }
    }

    // --- TABELA DE OFERTAS (ÚLTIMA EXECUÇÃO) ---
    async function loadLatestResults() {
        try {
            const resp = await fetch('/api/results/latest');
            const data = await resp.json();
            currentOffers = data.items || [];
            tabCountItems.textContent = currentOffers.length;
            populateFilterOptions(currentOffers);
            renderOffersTable();
        } catch (e) {
            console.error('Erro ao carregar ofertas:', e);
        }
    }

    function populateFilterOptions(items) {
        const categories = [...new Set(items.map(i => i.categoria).filter(Boolean))].sort();
        const markets = [...new Set(items.map(i => i.supermercado).filter(Boolean))].sort();

        filterCategory.innerHTML = '<option value="">Todas as categorias</option>';
        categories.forEach(cat => {
            const opt = document.createElement('option');
            opt.value = cat;
            opt.textContent = cat;
            filterCategory.appendChild(opt);
        });

        filterMarket.innerHTML = '<option value="">Todos os supermercados</option>';
        markets.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = m;
            filterMarket.appendChild(opt);
        });
    }

    function renderOffersTable() {
        const query = inputSearchItems.value.toLowerCase().trim();
        const selectedCat = filterCategory.value;
        const selectedMkt = filterMarket.value;

        const filtered = currentOffers.filter(item => {
            const matchesQuery = !query || 
                (item.item && item.item.toLowerCase().includes(query)) ||
                (item.supermercado && item.supermercado.toLowerCase().includes(query)) ||
                (item.categoria && item.categoria.toLowerCase().includes(query));

            const matchesCat = !selectedCat || item.categoria === selectedCat;
            const matchesMkt = !selectedMkt || item.supermercado === selectedMkt;

            return matchesQuery && matchesCat && matchesMkt;
        });

        if (filtered.length === 0) {
            tableOffersBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">
                        Nenhum registro encontrado para os filtros selecionados.
                    </td>
                </tr>
            `;
            return;
        }

        tableOffersBody.innerHTML = '';
        filtered.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${escapeHtml(item.supermercado)}</strong></td>
                <td><span class="category-badge">${escapeHtml(item.categoria || 'Outros')}</span></td>
                <td>${escapeHtml(item.item)}</td>
                <td class="text-right price-text">${formatCurrency(item.valor)}</td>
                <td>${escapeHtml(item.data_postagem || '-')}</td>
                <td class="text-center">
                    ${item.link ? `<button class="btn btn-outline btn-sm btn-preview-flyer" data-img="${escapeHtml(item.link)}" data-post="${escapeHtml(item.post_url || '')}" data-market="${escapeHtml(item.supermercado)}">Ver</button>` : '-'}
                </td>
            `;
            tableOffersBody.appendChild(tr);
        });

        bindPreviewButtons(tableOffersBody);
    }

    function bindPreviewButtons(container) {
        container.querySelectorAll('.btn-preview-flyer').forEach(btn => {
            btn.addEventListener('click', () => {
                const imgUrl = btn.getAttribute('data-img');
                const postUrl = btn.getAttribute('data-post');
                const mkt = btn.getAttribute('data-market');

                previewImgElement.src = imgUrl;
                btnOpenOriginalImg.href = imgUrl;
                btnOpenInstagramPost.href = postUrl || imgUrl;
                modalImageTitle.textContent = `Encarte: ${mkt}`;
                openModal(modalImagePreview);
            });
        });
    }

    async function loadHistory() {
        try {
            const resp = await fetch('/api/results/history');
            const data = await resp.json();
            const history = data.history || [];

            if (history.length === 0) {
                historyContainer.innerHTML = '<p class="empty-state">Nenhum arquivo histórico gerado.</p>';
                return;
            }

            historyContainer.innerHTML = '';
            history.forEach(h => {
                const div = document.createElement('div');
                div.className = 'history-item';
                div.innerHTML = `
                    <div>
                        <div class="history-name">${escapeHtml(h.filename)}</div>
                        <div class="history-meta">Gerado em: ${escapeHtml(h.date)} • ${h.size_kb} KB</div>
                    </div>
                    <a href="/api/download/${encodeURIComponent(h.filename)}" class="btn btn-success btn-sm">
                        Download (.xlsx)
                    </a>
                `;
                historyContainer.appendChild(div);
            });
        } catch (e) {
            historyContainer.innerHTML = '<p class="empty-state">Falha ao obter histórico.</p>';
        }
    }

    function downloadFile(ext) {
        if (currentOffers.length === 0) {
            alert('Nenhum dado disponível para download.');
            return;
        }
        window.location.href = `/api/download/latest_results.${ext}`;
    }

    function formatCurrency(val) {
        if (val === undefined || val === null || isNaN(val)) return 'R$ 0,00';
        return parseFloat(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});
