/**
 * FlyerScout AI - Frontend Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- ESTADO GLOBAL ---
    let currentConfig = {};
    let currentProfiles = [];
    let currentOffers = [];
    let eventSource = null;
    let isTaskRunning = false;

    // --- ELEMENTOS DOM ---
    const statusBadge = document.getElementById('status-badge');
    const statusText = document.getElementById('status-text');
    const badgeApify = document.getElementById('badge-apify');
    const txtApify = document.getElementById('txt-apify');
    const badgeAi = document.getElementById('badge-ai');
    const txtAi = document.getElementById('txt-ai');
    const profilesCount = document.getElementById('profiles-count');

    const selectDateMode = document.getElementById('select-date-mode');
    const customDateInputs = document.getElementById('custom-date-inputs');
    const inputDateStart = document.getElementById('input-date-start');
    const inputDateEnd = document.getElementById('input-date-end');
    const inputPostLimit = document.getElementById('input-post-limit');
    const selectAiEngine = document.getElementById('select-ai-engine');
    const btnStartScrape = document.getElementById('btn-start-scrape');
    const btnStopScrape = document.getElementById('btn-stop-scrape');

    const progressWrapper = document.getElementById('progress-wrapper');
    const progressStepTitle = document.getElementById('progress-step-title');
    const progressPercentage = document.getElementById('progress-percentage');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const progressStepDetail = document.getElementById('progress-step-detail');

    // Stats
    const statTotalItems = document.getElementById('stat-total-items');
    const statTotalMarkets = document.getElementById('stat-total-markets');
    const statAvgPrice = document.getElementById('stat-avg-price');
    const statMinPrice = document.getElementById('stat-min-price');
    const tabCountItems = document.getElementById('tab-count-items');

    // Table & Filters
    const tableOffersBody = document.getElementById('table-offers-body');
    const inputSearchItems = document.getElementById('input-search-items');
    const filterCategory = document.getElementById('filter-category');
    const filterMarket = document.getElementById('filter-market');
    const btnDownloadExcel = document.getElementById('btn-download-excel');
    const btnDownloadCsv = document.getElementById('btn-download-csv');

    // Terminal
    const terminalScreen = document.getElementById('terminal-screen');
    const chkAutoscroll = document.getElementById('chk-autoscroll');
    const btnClearLogs = document.getElementById('btn-clear-logs');

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
    const cfgGeminiModel = document.getElementById('cfg-gemini-model');
    const cfgOpenaiKey = document.getElementById('cfg-openai-key');
    const groupGeminiKey = document.getElementById('group-gemini-key');
    const groupGeminiModel = document.getElementById('group-gemini-model');
    const groupOpenaiKey = document.getElementById('group-openai-key');
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

    // Image preview
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
        await loadHistory();
        connectLogStream();
    }

    // --- TABS ---
    function setupTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.getAttribute('data-tab');
                tabBtns.forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                
                btn.classList.add('active');
                const pane = document.getElementById(targetTab);
                if (pane) pane.classList.add('active');
                
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

        // Toggle Eye para senhas
        document.querySelectorAll('.btn-toggle-eye').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetId = btn.getAttribute('data-target');
                const input = document.getElementById(targetId);
                if (input) {
                    input.type = input.type === 'password' ? 'text' : 'password';
                }
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
        // Date mode change
        selectDateMode.addEventListener('change', () => {
            if (selectDateMode.value === 'custom') {
                customDateInputs.style.display = 'grid';
            } else {
                customDateInputs.style.display = 'none';
            }
        });

        // Vision Provider change no modal
        cfgVisionProvider.addEventListener('change', () => {
            const prov = cfgVisionProvider.value;
            if (prov === 'gemini') {
                groupGeminiKey.style.display = 'block';
                groupGeminiModel.style.display = 'block';
                groupOpenaiKey.style.display = 'none';
            } else if (prov === 'openai') {
                groupGeminiKey.style.display = 'none';
                groupGeminiModel.style.display = 'none';
                groupOpenaiKey.style.display = 'block';
            } else {
                groupGeminiKey.style.display = 'none';
                groupGeminiModel.style.display = 'none';
                groupOpenaiKey.style.display = 'none';
            }
        });

        // Start & Stop
        btnStartScrape.addEventListener('click', startScraping);
        btnStopScrape.addEventListener('click', stopScraping);

        // Save Config
        btnSaveConfig.addEventListener('click', saveConfiguration);

        // Profiles Actions
        btnAddProfile.addEventListener('click', addNewProfile);
        btnSelectAllProfiles.addEventListener('click', () => toggleAllProfiles(true));
        btnDeselectAllProfiles.addEventListener('click', () => toggleAllProfiles(false));
        btnResetDefaultProfiles.addEventListener('click', resetDefaultProfiles);
        btnSaveProfiles.addEventListener('click', saveProfilesList);

        // Table filters & search
        inputSearchItems.addEventListener('input', renderOffersTable);
        filterCategory.addEventListener('change', renderOffersTable);
        filterMarket.addEventListener('change', renderOffersTable);

        // Clear terminal
        btnClearLogs.addEventListener('click', () => {
            terminalScreen.innerHTML = '<div class="log-line log-system">[SISTEMA] Logs limpos.</div>';
        });

        // Downloads
        btnDownloadExcel.addEventListener('click', () => downloadFile('latest', 'xlsx'));
        btnDownloadCsv.addEventListener('click', () => downloadFile('latest', 'csv'));
    }

    // --- API CALLS & CARREGAMENTO ---

    async function loadConfiguration() {
        try {
            const resp = await fetch('/api/config');
            const data = await resp.json();
            currentConfig = data;

            // Atualiza indicadores do header
            if (data.has_apify_token) {
                badgeApify.className = 'pill-indicator ok';
                txtApify.textContent = 'Conectado ✓';
            } else {
                badgeApify.className = 'pill-indicator missing';
                txtApify.textContent = 'Pendente ⚠️';
            }

            const aiOk = (data.vision_provider === 'gemini' && data.has_gemini_key) ||
                         (data.vision_provider === 'openai' && data.has_openai_key) ||
                         (data.vision_provider === 'qwen');
            if (aiOk) {
                badgeAi.className = 'pill-indicator ok';
                txtAi.textContent = `${data.vision_provider.toUpperCase()} ✓`;
            } else {
                badgeAi.className = 'pill-indicator missing';
                txtAi.textContent = 'Sem Chave ⚠️';
            }

            // Preenche modal de config
            cfgApifyToken.value = data.apify_token_masked || '';
            cfgVisionProvider.value = data.vision_provider || 'gemini';
            cfgGeminiKey.value = data.gemini_api_key_masked || '';
            cfgGeminiModel.value = data.gemini_model || 'gemini-1.5-flash';
            cfgOpenaiKey.value = data.openai_api_key_masked || '';
            cfgVisionProvider.dispatchEvent(new Event('change'));

            // Preenche controles principais
            selectAiEngine.value = data.vision_provider || 'gemini';
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
                gemini_model: cfgGeminiModel.value,
                openai_api_key: cfgOpenaiKey.value.trim(),
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
                appendLog('[SISTEMA] Configurações e chaves salvas com sucesso!', 'log-success');
                closeModal(modalConfig);
                await loadConfiguration();
            } else {
                alert('Falha ao salvar configurações.');
            }
        } catch (e) {
            alert('Erro ao salvar: ' + e.message);
        }
    }

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
                <td class="text-center">
                    <input type="checkbox" class="chk-profile-active" data-idx="${idx}" ${p.enabled !== false ? 'checked' : ''}>
                </td>
                <td><strong>${escapeHtml(p.name)}</strong></td>
                <td><a href="${escapeHtml(p.url)}" target="_blank" class="link-hint">${escapeHtml(p.url)}</a></td>
                <td class="text-center">
                    <button class="btn btn-ghost btn-xs text-danger btn-delete-profile" data-idx="${idx}" title="Excluir perfil">🗑️</button>
                </td>
            `;
            tableProfilesBody.appendChild(tr);
        });

        // Eventos de toggle e delete
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
            alert('Por favor, informe o nome e a URL do perfil do Instagram.');
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
        if (confirm('Deseja restaurar a lista padrão de 11 supermercados?')) {
            loadConfiguration().then(() => {
                loadProfiles();
            });
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
                appendLog(`[SISTEMA] Lista de perfis (${currentProfiles.length}) atualizada com sucesso.`, 'log-success');
                closeModal(modalProfiles);
            }
        } catch (e) {
            alert('Erro ao salvar perfis: ' + e.message);
        }
    }

    // --- SSE & LOG STREAMING ---

    function connectLogStream() {
        if (eventSource) {
            eventSource.close();
        }

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
                console.error('Erro no parser SSE:', err);
            }
        };

        eventSource.onerror = () => {
            // Tenta reconectar em 3s
            setTimeout(connectLogStream, 3000);
        };
    }

    function appendLog(line, className = '') {
        const div = document.createElement('div');
        div.className = `log-line ${className}`;
        
        if (line.includes('❌') || line.includes('ERRO')) div.classList.add('log-error');
        else if (line.includes('⚠️') || line.includes('WARN')) div.classList.add('log-warn');
        else if (line.includes('✅') || line.includes('SUCESSO') || line.includes('✨')) div.classList.add('log-success');
        else if (line.includes('[SISTEMA]') || line.includes('🚀')) div.classList.add('log-system');

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
            statusText.textContent = 'Executando...';
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
                
                // Se acabou de finalizar, recarrega dados automaticamente
                if (wasRunning) {
                    loadLatestResults();
                    loadHistory();
                }
            } else if (st.status === 'error') {
                statusBadge.className = 'badge badge-error';
                statusText.textContent = 'Erro';
                progressStepTitle.textContent = 'Erro na Execução';
                progressStepDetail.textContent = st.error_message || 'Falha no processo';
            } else {
                statusBadge.className = 'badge badge-idle';
                statusText.textContent = 'Pronto';
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
                vision_provider: selectAiEngine.value
            };

            const resp = await fetch('/api/scrape/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await resp.json();
            if (resp.ok) {
                appendLog('[SISTEMA] Processamento iniciado em segundo plano!', 'log-system');
                // Alterna para aba de logs se estiver vazia
                if (currentOffers.length === 0) {
                    document.querySelector('[data-tab="tab-logs"]').click();
                }
            } else {
                alert(data.message || 'Erro ao iniciar raspagem.');
            }
        } catch (e) {
            alert('Erro: ' + e.message);
        }
    }

    async function stopScraping() {
        if (confirm('Deseja realmente cancelar o processo em andamento?')) {
            await fetch('/api/scrape/stop', { method: 'POST' });
        }
    }

    // --- CARREGAMENTO DE RESULTADOS & TABELA ---

    async function loadLatestResults() {
        try {
            const resp = await fetch('/api/results/latest');
            const data = await resp.json();
            currentOffers = data.items || [];
            
            updateStats(currentOffers, data.supermercados || []);
            populateFilterOptions(currentOffers);
            renderOffersTable();
        } catch (e) {
            console.error('Erro ao carregar ofertas:', e);
        }
    }

    function updateStats(items, markets) {
        statTotalItems.textContent = items.length;
        tabCountItems.textContent = items.length;
        
        const marketSet = new Set(markets.length ? markets : items.map(i => i.supermercado));
        statTotalMarkets.textContent = marketSet.size;

        if (items.length > 0) {
            const prices = items.map(i => parseFloat(i.valor)).filter(v => !isNaN(v) && v > 0);
            if (prices.length > 0) {
                const sum = prices.reduce((a, b) => a + b, 0);
                const avg = sum / prices.length;
                const min = Math.min(...prices);
                statAvgPrice.textContent = formatCurrency(avg);
                statMinPrice.textContent = formatCurrency(min);
                return;
            }
        }
        statAvgPrice.textContent = 'R$ 0,00';
        statMinPrice.textContent = 'R$ 0,00';
    }

    function populateFilterOptions(items) {
        const categories = [...new Set(items.map(i => i.categoria).filter(Boolean))].sort();
        const markets = [...new Set(items.map(i => i.supermercado).filter(Boolean))].sort();

        filterCategory.innerHTML = '<option value="">Todas as Categorias</option>';
        categories.forEach(cat => {
            const opt = document.createElement('option');
            opt.value = cat;
            opt.textContent = cat;
            filterCategory.appendChild(opt);
        });

        filterMarket.innerHTML = '<option value="">Todos os Mercados</option>';
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
                <tr class="empty-row">
                    <td colspan="6">
                        <div class="empty-state">
                            <span class="empty-icon">🔍</span>
                            <p>Nenhum produto encontrado com os filtros selecionados.</p>
                        </div>
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
                <td><span class="category-tag">${escapeHtml(item.categoria || 'Outros')}</span></td>
                <td>${escapeHtml(item.item)}</td>
                <td class="text-right"><span class="price-tag">${formatCurrency(item.valor)}</span></td>
                <td>${escapeHtml(item.data_postagem || '-')}</td>
                <td class="text-center">
                    ${item.link ? `<button class="btn btn-secondary btn-xs btn-preview-flyer" data-img="${escapeHtml(item.link)}" data-post="${escapeHtml(item.post_url || '')}" data-market="${escapeHtml(item.supermercado)}">🖼️ Ver</button>` : '-'}
                </td>
            `;
            tableOffersBody.appendChild(tr);
        });

        // Eventos de preview
        tableOffersBody.querySelectorAll('.btn-preview-flyer').forEach(btn => {
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
        const historyContainer = document.getElementById('history-container');
        try {
            const resp = await fetch('/api/results/history');
            const data = await resp.json();
            const history = data.history || [];

            if (history.length === 0) {
                historyContainer.innerHTML = '<p class="text-muted text-center">Nenhuma planilha gerada anteriormente.</p>';
                return;
            }

            historyContainer.innerHTML = '';
            history.forEach(h => {
                const div = document.createElement('div');
                div.className = 'history-item';
                div.innerHTML = `
                    <div>
                        <strong>📊 ${escapeHtml(h.filename)}</strong>
                        <div class="text-muted" style="font-size: 12px;">Gerado em: ${escapeHtml(h.date)} • ${h.size_kb} KB</div>
                    </div>
                    <a href="/api/download/${encodeURIComponent(h.filename)}" class="btn btn-primary btn-sm">
                        📥 Baixar Excel
                    </a>
                `;
                historyContainer.appendChild(div);
            });
        } catch (e) {
            historyContainer.innerHTML = '<p class="text-danger">Erro ao carregar histórico.</p>';
        }
    }

    function downloadFile(target, ext) {
        if (currentOffers.length === 0) {
            alert('Nenhum dado disponível para download. Execute uma extração primeiro.');
            return;
        }
        window.location.href = `/api/download/latest_results.${ext === 'xlsx' ? 'xlsx' : 'csv'}`;
    }

    // --- HELPERS ---
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
