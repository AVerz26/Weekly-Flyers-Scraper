/**
 * Painel de Coleta de Encartes - Frontend Corporativo
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- ESTADO ---
    let currentConfig = {};
    let currentProfiles = [];
    let currentOffers = [];
    let currentScrapedImages = [];
    let eventSource = null;
    let isTaskRunning = false;
    let activeTestItem = null;

    // --- ELEMENTOS DOM ---
    const statusBadge = document.getElementById('status-badge');
    const statusText = document.getElementById('status-text');
    const profilesCount = document.getElementById('profiles-count');

    const selectDateMode = document.getElementById('select-date-mode');
    const customDateInputs = document.getElementById('custom-date-inputs');
    const inputDateStart = document.getElementById('input-date-start');
    const inputDateEnd = document.getElementById('input-date-end');
    const inputPostLimit = document.getElementById('input-post-limit');
    const selectAiModel = document.getElementById('select-ai-model');

    // Botões de Execução
    const btnStartScrapeOnly = document.getElementById('btn-start-scrape-only');
    const btnStartVisionOnly = document.getElementById('btn-start-vision-only');
    const btnStartFull = document.getElementById('btn-start-full');
    const btnStopScrape = document.getElementById('btn-stop-scrape');

    const progressWrapper = document.getElementById('progress-wrapper');
    const progressStepTitle = document.getElementById('progress-step-title');
    const progressPercentage = document.getElementById('progress-percentage');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const progressStepDetail = document.getElementById('progress-step-detail');

    // Tabela e Filtros de Ofertas
    const tabCountItems = document.getElementById('tab-count-items');
    const tableOffersBody = document.getElementById('table-offers-body');
    const inputSearchItems = document.getElementById('input-search-items');
    const filterCategory = document.getElementById('filter-category');
    const filterMarket = document.getElementById('filter-market');
    const btnDownloadExcel = document.getElementById('btn-download-excel');
    const btnDownloadCsv = document.getElementById('btn-download-csv');

    // Galeria de Encartes
    const tabCountImages = document.getElementById('tab-count-images');
    const galleryCountBadge = document.getElementById('gallery-count-badge');
    const galleryFilterMarket = document.getElementById('gallery-filter-market');
    const btnRefreshImages = document.getElementById('btn-refresh-images');
    const btnExtractAllFromGallery = document.getElementById('btn-extract-all-from-gallery');
    const galleryGrid = document.getElementById('gallery-grid');

    // Logs
    const terminalScreen = document.getElementById('terminal-screen');
    const chkAutoscroll = document.getElementById('chk-autoscroll');
    const btnClearLogs = document.getElementById('btn-clear-logs');
    const historyContainer = document.getElementById('history-container');

    // Comparador de Preços
    const tabCountComparator = document.getElementById('tab-count-comparator');
    const statTotalProducts = document.getElementById('stat-total-products');
    const statTotalOffers = document.getElementById('stat-total-offers');
    const statTotalMarkets = document.getElementById('stat-total-markets');
    const statMaxSavings = document.getElementById('stat-max-savings');
    const inputSearchComparator = document.getElementById('input-search-comparator');
    const filterComparatorCategory = document.getElementById('filter-comparator-category');
    const chkMultipleMarketsOnly = document.getElementById('chk-multiple-markets-only');
    const btnExportComparison = document.getElementById('btn-export-comparison');
    const tbodyComparator = document.getElementById('tbody-comparator');
    let currentComparisonData = [];

    // Modals
    const btnOpenConfig = document.getElementById('btn-open-config');
    const btnOpenProfiles = document.getElementById('btn-open-profiles');
    const modalConfig = document.getElementById('modal-config');
    const modalProfiles = document.getElementById('modal-profiles');
    const modalImagePreview = document.getElementById('modal-image-preview');
    const modalSingleAiTest = document.getElementById('modal-single-ai-test');

    // Modal Teste de IA
    const testImgPreview = document.getElementById('test-img-preview');
    const testImgMarket = document.getElementById('test-img-market');
    const testImgModel = document.getElementById('test-img-model');
    const testLoadingState = document.getElementById('test-loading-state');
    const testContentState = document.getElementById('test-content-state');
    const testOffersCount = document.getElementById('test-offers-count');
    const testTableBody = document.getElementById('test-table-body');
    const btnRetestImage = document.getElementById('btn-retest-image');

    // Config form
    const cfgApifyToken = document.getElementById('cfg-apify-token');
    const cfgVisionProvider = document.getElementById('cfg-vision-provider');
    const cfgGeminiKey = document.getElementById('cfg-gemini-key');
    const cfgOpenaiKey = document.getElementById('cfg-openai-key');
    const groupGeminiKey = document.getElementById('group-gemini-key');
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
        await loadScrapedImages();
        await loadLatestResults();
        await loadDatabaseStats();
        await loadPriceComparison();
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
                
                if (targetTab === 'tab-history') {
                    loadHistory();
                } else if (targetTab === 'tab-images') {
                    loadScrapedImages();
                } else if (targetTab === 'tab-comparator') {
                    loadDatabaseStats();
                    loadPriceComparison();
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

        // Modos de Execução
        if (btnStartScrapeOnly) btnStartScrapeOnly.addEventListener('click', () => startProcess('scrape_only'));
        if (btnStartVisionOnly) btnStartVisionOnly.addEventListener('click', () => startProcess('vision_only'));
        if (btnStartFull) btnStartFull.addEventListener('click', () => startProcess('full'));
        if (btnExtractAllFromGallery) btnExtractAllFromGallery.addEventListener('click', () => startProcess('vision_only'));

        btnStopScrape.addEventListener('click', stopScraping);
        btnSaveConfig.addEventListener('click', saveConfiguration);

        btnAddProfile.addEventListener('click', addNewProfile);
        btnSelectAllProfiles.addEventListener('click', () => toggleAllProfiles(true));
        btnDeselectAllProfiles.addEventListener('click', () => toggleAllProfiles(false));
        btnResetDefaultProfiles.addEventListener('click', resetDefaultProfiles);
        btnSaveProfiles.addEventListener('click', saveProfilesList);

        inputSearchItems.addEventListener('input', renderOffersTable);
        filterCategory.addEventListener('change', renderOffersTable);
        filterMarket.addEventListener('change', renderOffersTable);

        galleryFilterMarket.addEventListener('change', renderGalleryGrid);
        btnRefreshImages.addEventListener('click', loadScrapedImages);

        // Listeners do Comparador
        if (inputSearchComparator) inputSearchComparator.addEventListener('input', debounce(() => loadPriceComparison(), 300));
        if (filterComparatorCategory) filterComparatorCategory.addEventListener('change', () => loadPriceComparison());
        if (chkMultipleMarketsOnly) chkMultipleMarketsOnly.addEventListener('change', () => loadPriceComparison());
        if (btnExportComparison) btnExportComparison.addEventListener('click', exportComparisonToExcel);

        btnDownloadExcel.addEventListener('click', () => downloadFile('xlsx'));
        btnDownloadCsv.addEventListener('click', () => downloadFile('csv'));

        btnClearLogs.addEventListener('click', () => {
            terminalScreen.innerHTML = '<div class="log-row log-sys">[SISTEMA] Console limpo.</div>';
        });

        if (btnRetestImage) {
            btnRetestImage.addEventListener('click', () => {
                if (activeTestItem) runSingleAiTest(activeTestItem);
            });
        }
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

            selectDateMode.value = data.date_mode || 'yesterday_today';
            inputPostLimit.value = data.results_limit || 3;
            if (data.custom_start_date) inputDateStart.value = data.custom_start_date;
            if (data.custom_end_date) inputDateEnd.value = data.custom_end_date;
            selectDateMode.dispatchEvent(new Event('change'));

            // Sincroniza seletor de IA se configurado
            const provider = data.vision_provider || 'gemini';
            const model = data.gemini_model || 'gemini-flash-lite-latest';
            const val = `${provider}:${model}`;
            if (selectAiModel.querySelector(`option[value="${val}"]`)) {
                selectAiModel.value = val;
            }
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
        if (confirm('Restaurar lista de 11 supermercados padrão?')) {
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
        else if (line.includes('SUCESSO') || line.includes('✅') || line.includes('✨')) div.classList.add('log-success');
        else if (line.includes('[SISTEMA]') || line.includes('🚀')) div.classList.add('log-sys');

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

        const actionButtons = [btnStartScrapeOnly, btnStartVisionOnly, btnStartFull];

        if (st.is_running) {
            statusBadge.className = 'badge badge-running';
            statusText.textContent = 'Em execução';
            actionButtons.forEach(b => { if (b) b.style.display = 'none'; });
            btnStopScrape.style.display = 'inline-flex';
            progressWrapper.style.display = 'block';

            progressStepTitle.textContent = st.current_step || 'Processando';
            progressPercentage.textContent = `${st.progress || 0}%`;
            progressBarFill.style.width = `${st.progress || 0}%`;
            progressStepDetail.textContent = st.step_detail || '';
        } else {
            actionButtons.forEach(b => { if (b) b.style.display = 'inline-flex'; });
            btnStopScrape.style.display = 'none';

            if (st.status === 'completed') {
                statusBadge.className = 'badge badge-completed';
                statusText.textContent = 'Concluído';
                progressBarFill.style.width = '100%';
                progressPercentage.textContent = '100%';
                progressStepTitle.textContent = 'Concluído com Sucesso';
                if (wasRunning) {
                    loadLatestResults();
                    loadScrapedImages();
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

    // --- DISPARO DE PROCESSOS (MODOS) ---
    async function startProcess(mode = 'full') {
        try {
            const aiVal = selectAiModel ? selectAiModel.value : 'gemini:gemini-flash-lite-latest';
            const [provider, modelName] = aiVal.split(':');

            const payload = {
                mode: mode,
                date_mode: selectDateMode.value,
                custom_start_date: inputDateStart.value,
                custom_end_date: inputDateEnd.value,
                results_limit: parseInt(inputPostLimit.value) || 3,
                vision_provider: provider,
                gemini_model: modelName,
                openai_model: modelName
            };

            const resp = await fetch('/api/scrape/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await resp.json();
            if (resp.ok) {
                appendLog(`[SISTEMA] Modo '${mode}' iniciado com sucesso.`, 'log-sys');
                document.querySelector('[data-tab="tab-logs"]').click();
            } else {
                alert(data.message || 'Erro ao iniciar processo.');
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

    // --- GALERIA DE ENCARTES COLETADOS ---
    async function loadScrapedImages() {
        try {
            const resp = await fetch('/api/scraped-images');
            const data = await resp.json();
            currentScrapedImages = data.images || [];

            tabCountImages.textContent = currentScrapedImages.length;
            galleryCountBadge.textContent = `${currentScrapedImages.length} imagens`;

            populateGalleryMarketFilter(currentScrapedImages);
            renderGalleryGrid();
        } catch (e) {
            console.error('Erro ao carregar imagens salvas:', e);
        }
    }

    function populateGalleryMarketFilter(images) {
        const markets = [...new Set(images.map(i => i.supermercado).filter(Boolean))].sort();
        const curVal = galleryFilterMarket.value;
        galleryFilterMarket.innerHTML = '<option value="">Todos os supermercados</option>';
        markets.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = m;
            galleryFilterMarket.appendChild(opt);
        });
        if (markets.includes(curVal)) {
            galleryFilterMarket.value = curVal;
        }
    }

    function renderGalleryGrid() {
        const selectedMarket = galleryFilterMarket.value;
        const filtered = currentScrapedImages.filter(img => {
            return !selectedMarket || img.supermercado === selectedMarket;
        });

        if (filtered.length === 0) {
            galleryGrid.innerHTML = `
                <div class="empty-state-card">
                    <div class="empty-state-icon">🖼️</div>
                    <h3>${currentScrapedImages.length === 0 ? 'Nenhum encarte salvo no momento' : 'Nenhum encarte para o supermercado filtrado'}</h3>
                    <p>Clique em <strong>"1. Coletar Encartes"</strong> para obter as imagens do Instagram e salvá-las no disco para testes.</p>
                </div>
            `;
            return;
        }

        galleryGrid.innerHTML = '';
        filtered.forEach((item, idx) => {
            const card = document.createElement('div');
            card.className = 'flyer-card';
            card.innerHTML = `
                <div class="flyer-card-media" data-img="${escapeHtml(item.imagem)}" data-market="${escapeHtml(item.supermercado)}" data-post="${escapeHtml(item.post_url || '')}">
                    <img src="${escapeHtml(item.imagem)}" alt="Encarte de ${escapeHtml(item.supermercado)}" loading="lazy">
                    <div class="media-overlay">
                        <span>🔍 Ampliar Imagem</span>
                    </div>
                </div>
                <div class="flyer-card-body">
                    <div class="flyer-card-header">
                        <span class="flyer-market-name">${escapeHtml(item.supermercado)}</span>
                        <span class="flyer-date">${escapeHtml(item.data_formatada || '-')}</span>
                    </div>
                    <div class="flyer-caption" title="${escapeHtml(item.caption || '')}">
                        ${escapeHtml(item.caption || 'Sem legenda informada no post.')}
                    </div>
                    <div class="flyer-card-actions">
                        <button class="btn btn-primary btn-test-ai" data-idx="${idx}">
                            🔬 Testar c/ IA
                        </button>
                        ${item.post_url ? `<a href="${escapeHtml(item.post_url)}" target="_blank" class="btn btn-outline" title="Abrir publicação original no Instagram">Post ↗</a>` : ''}
                    </div>
                </div>
            `;
            galleryGrid.appendChild(card);
        });

        // Eventos de clique na imagem para zoom
        galleryGrid.querySelectorAll('.flyer-card-media').forEach(media => {
            media.addEventListener('click', () => {
                const imgUrl = media.getAttribute('data-img');
                const postUrl = media.getAttribute('data-post');
                const mkt = media.getAttribute('data-market');

                previewImgElement.src = imgUrl;
                btnOpenOriginalImg.href = imgUrl;
                btnOpenInstagramPost.href = postUrl || imgUrl;
                modalImageTitle.textContent = `Encarte: ${mkt}`;
                openModal(modalImagePreview);
            });
        });

        // Eventos de teste de IA
        galleryGrid.querySelectorAll('.btn-test-ai').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const i = parseInt(e.currentTarget.getAttribute('data-idx'));
                const imgItem = filtered[i];
                runSingleAiTest(imgItem);
            });
        });
    }

    // --- TESTE DE IA EM UMA ÚNICA IMAGEM ---
    async function runSingleAiTest(imgItem) {
        if (!imgItem) return;
        activeTestItem = imgItem;

        const aiVal = selectAiModel ? selectAiModel.value : 'gemini:gemini-flash-lite-latest';
        const [provider, modelName] = aiVal.split(':');

        testImgPreview.src = imgItem.imagem;
        testImgMarket.textContent = imgItem.supermercado;
        testImgModel.textContent = `${provider.toUpperCase()} (${modelName})`;

        testLoadingState.style.display = 'flex';
        testContentState.style.display = 'none';
        testTableBody.innerHTML = '';
        testOffersCount.textContent = '0';

        openModal(modalSingleAiTest);

        try {
            const resp = await fetch('/api/vision/test-single', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image_url: imgItem.imagem,
                    supermercado: imgItem.supermercado,
                    vision_provider: provider,
                    model_name: modelName
                })
            });

            const data = await resp.json();
            testLoadingState.style.display = 'none';
            testContentState.style.display = 'block';

            if (!resp.ok || data.status === 'warning') {
                testTableBody.innerHTML = `
                    <tr>
                        <td colspan="3" class="empty-state" style="color: var(--danger);">
                            ${escapeHtml(data.message || data.detail || 'Falha ao processar imagem ou nenhuma oferta legível.')}
                        </td>
                    </tr>
                `;
                return;
            }

            const offers = data.ofertas || [];
            testOffersCount.textContent = offers.length;

            if (offers.length === 0) {
                testTableBody.innerHTML = `
                    <tr>
                        <td colspan="3" class="empty-state">
                            Nenhum produto ou preço detectado pela IA nesta imagem.
                        </td>
                    </tr>
                `;
                return;
            }

            offers.forEach(of => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${escapeHtml(of.item)}</strong></td>
                    <td><span class="category-badge">${escapeHtml(of.categoria || 'Outros')}</span></td>
                    <td class="text-right price-text">${formatCurrency(of.valor)}</td>
                `;
                testTableBody.appendChild(tr);
            });

        } catch (err) {
            testLoadingState.style.display = 'none';
            testContentState.style.display = 'block';
            testTableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="empty-state" style="color: var(--danger);">
                        Erro de comunicação: ${escapeHtml(err.message)}
                    </td>
                </tr>
            `;
        }
    }

    // --- TABELA DE OFERTAS EXTRAÍDAS ---
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
        const targetBody = document.getElementById('tbody-offers') || document.getElementById('table-offers-body');
        if (!targetBody) return;

        const query = inputSearchItems.value.toLowerCase().trim();
        const selectedCat = filterCategory.value;
        const selectedMkt = filterMarket.value;

        const filtered = currentOffers.filter(item => {
            const matchesQuery = !query || 
                (item.item && item.item.toLowerCase().includes(query)) ||
                (item.produto_padronizado && item.produto_padronizado.toLowerCase().includes(query)) ||
                (item.supermercado && item.supermercado.toLowerCase().includes(query)) ||
                (item.categoria && item.categoria.toLowerCase().includes(query));

            const matchesCat = !selectedCat || item.categoria === selectedCat;
            const matchesMkt = !selectedMkt || item.supermercado === selectedMkt;

            return matchesQuery && matchesCat && matchesMkt;
        });

        if (filtered.length === 0) {
            targetBody.innerHTML = `
                <tr>
                    <td colspan="7" class="empty-state">
                        Nenhum registro encontrado para os filtros selecionados.
                    </td>
                </tr>
            `;
            return;
        }

        targetBody.innerHTML = '';
        filtered.forEach(item => {
            const tr = document.createElement('tr');
            const canon = item.produto_padronizado || item.item;
            tr.innerHTML = `
                <td><strong>${escapeHtml(item.supermercado)}</strong></td>
                <td><span class="category-badge">${escapeHtml(item.categoria || 'Outros')}</span></td>
                <td>
                    <div class="badge-canonical-product">
                        <span class="canonical-name">${escapeHtml(canon)}</span>
                        <div class="canonical-tags">
                            ${item.marca ? `<span class="tag-brand">${escapeHtml(item.marca)}</span>` : ''}
                            ${item.embalagem ? `<span class="tag-pack">${escapeHtml(item.embalagem)}</span>` : ''}
                        </div>
                    </div>
                </td>
                <td style="color: var(--text-secondary); font-size: 12px;">${escapeHtml(item.item)}</td>
                <td class="text-right price-text">${formatCurrency(item.valor)}</td>
                <td style="text-align: center;">${escapeHtml(item.data_postagem || '-')}</td>
                <td class="text-center">
                    ${item.link ? `<button class="btn btn-outline btn-sm btn-preview-flyer" data-img="${escapeHtml(item.link)}" data-post="${escapeHtml(item.post_url || '')}" data-market="${escapeHtml(item.supermercado)}">Ver</button>` : '-'}
                </td>
            `;
            targetBody.appendChild(tr);
        });

        targetBody.querySelectorAll('.btn-preview-flyer').forEach(btn => {
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

    // --- COMPARADOR DE PREÇOS E BANCO DE DADOS ---
    async function loadDatabaseStats() {
        try {
            const resp = await fetch('/api/database/stats');
            const data = await resp.json();
            if (statTotalProducts) statTotalProducts.textContent = data.total_produtos_unicos || 0;
            if (statTotalOffers) statTotalOffers.textContent = data.total_ofertas || 0;
            if (statTotalMarkets) statTotalMarkets.textContent = data.total_supermercados || 0;
            if (tabCountComparator) tabCountComparator.textContent = data.total_produtos_unicos || 0;
        } catch (e) {
            console.error('Erro ao obter estatísticas:', e);
        }
    }

    async function loadPriceComparison() {
        try {
            const search = inputSearchComparator ? inputSearchComparator.value.trim() : '';
            const cat = filterComparatorCategory ? filterComparatorCategory.value : '';
            const minMarkets = (chkMultipleMarketsOnly && chkMultipleMarketsOnly.checked) ? 2 : 1;

            const params = new URLSearchParams();
            if (search) params.append('search', search);
            if (cat) params.append('category', cat);
            params.append('min_markets', minMarkets);

            const resp = await fetch(`/api/database/comparison?${params.toString()}`);
            const data = await resp.json();
            currentComparisonData = data.comparison || [];

            populateComparatorCategoryFilter(currentComparisonData);
            renderComparisonTable();
        } catch (e) {
            console.error('Erro ao carregar comparativo:', e);
        }
    }

    function populateComparatorCategoryFilter(items) {
        if (!filterComparatorCategory) return;
        const curVal = filterComparatorCategory.value;
        const categories = [...new Set(items.map(i => i.categoria).filter(Boolean))].sort();

        // Preserva opção atual se existir
        const prevOpts = Array.from(filterComparatorCategory.options).map(o => o.value);
        if (categories.length > 0 && categories.some(c => !prevOpts.includes(c))) {
            filterComparatorCategory.innerHTML = '<option value="">Todas as categorias</option>';
            categories.forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat;
                opt.textContent = cat;
                filterComparatorCategory.appendChild(opt);
            });
            if (categories.includes(curVal)) {
                filterComparatorCategory.value = curVal;
            }
        }
    }

    function renderComparisonTable() {
        if (!tbodyComparator) return;

        let maxSavings = 0;
        if (currentComparisonData.length === 0) {
            tbodyComparator.innerHTML = `
                <tr>
                    <td colspan="7" class="empty-state">
                        Nenhum produto encontrado para os critérios de busca.
                    </td>
                </tr>
            `;
            if (statMaxSavings) statMaxSavings.textContent = '0%';
            return;
        }

        tbodyComparator.innerHTML = '';
        currentComparisonData.forEach(item => {
            if (item.economia_pct > maxSavings) {
                maxSavings = item.economia_pct;
            }

            const tr = document.createElement('tr');
            
            // Chips dos mercados
            let marketChipsHtml = '<div class="market-chips-container">';
            (item.mercados || []).forEach(m => {
                const isCheapestClass = m.is_cheapest ? 'is-cheapest' : '';
                marketChipsHtml += `
                    <div class="market-price-chip ${isCheapestClass}" title="${escapeHtml(m.item_original)} • ${escapeHtml(m.data)}">
                        <span class="chip-name">${escapeHtml(m.supermercado)}:</span>
                        <span class="chip-price">${formatCurrency(m.valor)}</span>
                    </div>
                `;
            });
            marketChipsHtml += '</div>';

            tr.innerHTML = `
                <td>
                    <div class="badge-canonical-product">
                        <span class="canonical-name">${escapeHtml(item.produto_padronizado)}</span>
                        <div class="canonical-tags">
                            ${item.marca ? `<span class="tag-brand">${escapeHtml(item.marca)}</span>` : ''}
                            ${item.embalagem ? `<span class="tag-pack">${escapeHtml(item.embalagem)}</span>` : ''}
                        </div>
                    </div>
                </td>
                <td><span class="category-badge">${escapeHtml(item.categoria || 'Outros')}</span></td>
                <td class="text-right"><span class="price-lowest">${formatCurrency(item.menor_preco)}</span></td>
                <td>
                    <span class="badge-cheapest-market">
                        🏷️ ${escapeHtml(item.supermercado_mais_barato || '-')}
                    </span>
                </td>
                <td class="text-right price-text" style="color: var(--text-secondary);">${formatCurrency(item.maior_preco)}</td>
                <td style="text-align: center;">
                    ${item.economia_pct > 0 ? `
                        <span class="badge-savings">
                            <span class="savings-pct">-${item.economia_pct}%</span>
                            <span class="savings-val">econ. ${formatCurrency(item.economia_reais)}</span>
                        </span>
                    ` : '<span style="color: var(--text-muted); font-size: 11px;">Preço único</span>'}
                </td>
                <td>${marketChipsHtml}</td>
            `;
            tbodyComparator.appendChild(tr);
        });

        if (statMaxSavings) {
            statMaxSavings.textContent = `${maxSavings}%`;
        }
    }

    async function exportComparisonToExcel() {
        try {
            btnExportComparison.disabled = true;
            btnExportComparison.textContent = '⏳ Gerando Excel...';

            const payload = {
                category: filterComparatorCategory ? filterComparatorCategory.value : '',
                search: inputSearchComparator ? inputSearchComparator.value.trim() : '',
                min_markets: (chkMultipleMarketsOnly && chkMultipleMarketsOnly.checked) ? 2 : 1
            };

            const resp = await fetch('/api/database/export-comparison', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await resp.json();
            if (resp.ok && data.download_url) {
                window.location.href = data.download_url;
                appendLog(`[SISTEMA] Relatório comparativo gerado: ${data.filename}`, 'log-success');
            } else {
                alert('Erro ao gerar relatório comparativo.');
            }
        } catch (e) {
            alert('Erro: ' + e.message);
        } finally {
            btnExportComparison.disabled = false;
            btnExportComparison.textContent = '📊 Exportar Comparativo Excel (.xlsx)';
        }
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

    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
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
