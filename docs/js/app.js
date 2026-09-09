/**
 * FlyerScout - Visualização de Dados & Comparativo de Preços de Produtos
 * GitHub Pages Dashboard
 */

document.addEventListener('DOMContentLoaded', () => {
    let allOffers = [];
    let groupedProducts = [];
    let productHistoryMap = {};
    let currentProductsList = [];
    let selectedProductName = '';
    let priceChartInstance = null;

    // Elementos DOM
    const lastUpdateText = document.getElementById('last-update-text');
    const metricTotalItems = document.getElementById('metric-total-items');
    const metricDateInfo = document.getElementById('metric-date-info');
    const metricMarketsCount = document.getElementById('metric-markets-count');
    const metricCategoriesCount = document.getElementById('metric-categories-count');
    const metricMinPrice = document.getElementById('metric-min-price');
    const metricMinItem = document.getElementById('metric-min-item');
    const tabCountItems = document.getElementById('tab-count-items');
    const tabCountCompared = document.getElementById('tab-count-compared');
    const tabCountHistory = document.getElementById('tab-count-history');

    const searchInput = document.getElementById('search-input');
    const filterDate = document.getElementById('filter-date');
    const filterMarket = document.getElementById('filter-market');
    const filterCategory = document.getElementById('filter-category');
    const sortOrder = document.getElementById('sort-order');
    const chkMultiMarketOnly = document.getElementById('chk-multi-market-only');

    const comparisonContainer = document.getElementById('comparison-list-container');
    const tableOffersBody = document.getElementById('table-offers-body');
    const tableMarketBody = document.getElementById('table-market-body');
    const tableCatBody = document.getElementById('table-cat-body');

    // Elementos do Histórico de Preços
    const filterHistoryCategory = document.getElementById('filter-history-category');
    const inputSearchHistoryProduct = document.getElementById('input-search-history-product');
    const selectHistoryProduct = document.getElementById('select-history-product');
    const selectChartMode = document.getElementById('select-chart-mode');
    const historyProductTitle = document.getElementById('history-product-title');
    const historyProductCategory = document.getElementById('history-product-category');
    const historyProductDates = document.getElementById('history-product-dates');
    const statHistMinPrice = document.getElementById('stat-hist-min-price');
    const statHistMinMarket = document.getElementById('stat-hist-min-market');
    const statHistMaxPrice = document.getElementById('stat-hist-max-price');
    const statHistMaxMarket = document.getElementById('stat-hist-max-market');
    const statHistAvgPrice = document.getElementById('stat-hist-avg-price');
    const statHistRecordsCount = document.getElementById('stat-hist-records-count');
    const statHistRecentPrice = document.getElementById('stat-hist-recent-price');
    const statHistTrendBadge = document.getElementById('stat-hist-trend-badge');
    const chartLegendCustom = document.getElementById('chart-legend-custom');
    const chartProductSubtitle = document.getElementById('chart-product-subtitle');
    const productPriceChartCanvas = document.getElementById('product-price-chart');
    const chartEmptyState = document.getElementById('chart-empty-state');
    const historyTableCount = document.getElementById('history-table-count');
    const tbodyProductHistory = document.getElementById('tbody-product-history');

    // Modal
    const modalImagePreview = document.getElementById('modal-image-preview');
    const modalImageTitle = document.getElementById('modal-image-title');
    const previewImgElement = document.getElementById('preview-img-element');
    const btnOpenOriginalImg = document.getElementById('btn-open-original-img');
    const btnOpenInstagramPost = document.getElementById('btn-open-instagram-post');
    const btnCloseModal = document.getElementById('btn-close-modal');

    // Inicialização
    init();

    async function init() {
        setupTabs();
        setupEventListeners();
        await loadData();
    }

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

                if (targetTab === 'tab-price-history' && priceChartInstance) {
                    setTimeout(() => priceChartInstance.resize(), 50);
                }
            });
        });
    }

    function setupEventListeners() {
        searchInput.addEventListener('input', applyFilters);
        if (filterDate) filterDate.addEventListener('change', applyFilters);
        filterMarket.addEventListener('change', applyFilters);
        filterCategory.addEventListener('change', applyFilters);
        sortOrder.addEventListener('change', applyFilters);
        if (chkMultiMarketOnly) chkMultiMarketOnly.addEventListener('change', applyFilters);

        // Listeners do Histórico de Preços
        if (filterHistoryCategory) filterHistoryCategory.addEventListener('change', () => filterAndRenderProductOptions());
        if (inputSearchHistoryProduct) inputSearchHistoryProduct.addEventListener('input', debounce(() => filterAndRenderProductOptions(), 250));
        if (selectHistoryProduct) selectHistoryProduct.addEventListener('change', (e) => renderProductPriceHistory(e.target.value));
        if (selectChartMode) selectChartMode.addEventListener('change', () => {
            if (selectedProductName && productHistoryMap[selectedProductName]) {
                renderProductPriceHistory(selectedProductName);
            }
        });

        const btnReload = document.getElementById('btn-reload-data');
        if (btnReload) {
            btnReload.addEventListener('click', async () => {
                btnReload.textContent = '⏳ Atualizando...';
                await loadData();
                btnReload.textContent = '🔄 Atualizar';
            });
        }

        btnCloseModal.addEventListener('click', () => {
            modalImagePreview.style.display = 'none';
        });

        modalImagePreview.addEventListener('click', (e) => {
            if (e.target === modalImagePreview) modalImagePreview.style.display = 'none';
        });
    }

    async function loadData() {
        const cacheBuster = `?_t=${new Date().getTime()}`;
        const possibleUrls = [
            `data/latest_results.json${cacheBuster}`,
            `https://raw.githubusercontent.com/AVerz26/Weekly-Flyers-Scraper/main/docs/data/latest_results.json${cacheBuster}`,
            `https://raw.githubusercontent.com/AVerz26/Weekly-Flyers-Scraper/main/output/latest_results.json${cacheBuster}`
        ];

        let data = null;
        for (const url of possibleUrls) {
            try {
                const resp = await fetch(url, { cache: 'no-store' });
                if (resp.ok) {
                    const parsed = await resp.json();
                    if (parsed && Array.isArray(parsed.items) && parsed.items.length > 0) {
                        data = parsed;
                        break;
                    } else if (parsed && parsed.items) {
                        data = parsed;
                    }
                }
            } catch (e) {
                console.warn('Falha ao obter dados de:', url, e);
            }
        }

        if (!data || !data.items || data.items.length === 0) {
            lastUpdateText.textContent = data && data.timestamp ? `Coleta em ${data.timestamp.split('_')[0]}` : 'Aguardando primeira coleta';
            metricDateInfo.textContent = 'Sem ofertas recentes';
            if (comparisonContainer) {
                comparisonContainer.innerHTML = `
                    <div class="empty-state" style="padding: 60px 20px; text-align: center;">
                        <div style="font-size: 32px; margin-bottom: 8px;">🛒</div>
                        <h3 style="margin-bottom: 6px; font-weight: 700;">Aguardando Coleta dos Encartes</h3>
                        <p style="font-size: 13px; color: var(--text-muted); max-width: 480px; margin: 0 auto;">
                            O robô executa a coleta diária e salvará automaticamente todos os produtos aqui para comparação lado a lado.
                        </p>
                    </div>
                `;
            }
            return;
        }

        allOffers = data.items;
        tabCountItems.textContent = allOffers.length.toLocaleString('pt-BR');

        // Atualiza data
        if (data.timestamp) {
            const parts = data.timestamp.split('_');
            const dataFmt = parts[0].replace(/-/g, '/');
            const horaFmt = parts[1] ? parts[1].replace(/-/g, ':') : '';
            lastUpdateText.textContent = `${dataFmt} ${horaFmt}`;
            metricDateInfo.textContent = `Coleta: ${dataFmt}`;
        } else {
            lastUpdateText.textContent = 'Hoje';
            metricDateInfo.textContent = 'Atualizado';
        }

        updateMetrics(allOffers);
        populateDropdowns(allOffers);
        processProductGrouping(allOffers);
        buildProductHistoryMap(allOffers);
        renderMarketSummary(allOffers);
        renderCategorySummary(allOffers);
        applyFilters();
    }

    function updateMetrics(items) {
        metricTotalItems.textContent = items.length.toLocaleString('pt-BR');

        const markets = [...new Set(items.map(i => i.supermercado).filter(Boolean))];
        metricMarketsCount.textContent = markets.length;

        const categories = [...new Set(items.map(i => i.categoria).filter(Boolean))];
        metricCategoriesCount.textContent = categories.length;

        // Menor preço
        let minPrice = Infinity;
        let minItemName = '-';
        items.forEach(i => {
            const val = parseFloat(i.valor);
            if (!isNaN(val) && val > 0 && val < minPrice) {
                minPrice = val;
                minItemName = `${i.item} (${i.supermercado})`;
            }
        });

        if (minPrice !== Infinity) {
            metricMinPrice.textContent = formatCurrency(minPrice);
            metricMinItem.textContent = minItemName;
        }
    }

    function parseDateString(str) {
        if (!str) return null;
        try {
            if (str.includes('/')) {
                const parts = str.split('/');
                return new Date(parseInt(parts[2]), parseInt(parts[1]) - 1, parseInt(parts[0]));
            }
            return new Date(str);
        } catch (e) {
            return null;
        }
    }

    function populateDropdowns(items) {
        const markets = [...new Set(items.map(i => i.supermercado).filter(Boolean))].sort();
        const categories = [...new Set(items.map(i => i.categoria).filter(Boolean))].sort();
        const dates = [...new Set(items.map(i => i.data_postagem).filter(Boolean))].sort((a, b) => {
            const dA = parseDateString(a) || new Date(0);
            const dB = parseDateString(b) || new Date(0);
            return dB - dA;
        });

        if (filterDate) {
            filterDate.innerHTML = `
                <option value="">📅 Todas as Datas</option>
                <option value="today">✨ Postados Hoje</option>
                <option value="last_3_days">🕒 Últimos 3 Dias</option>
                <option value="last_7_days">🗓️ Últimos 7 Dias</option>
            `;
            if (dates.length > 0) {
                const optGroup = document.createElement('optgroup');
                optGroup.label = 'Datas Específicas';
                dates.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d;
                    opt.textContent = `📅 ${d}`;
                    optGroup.appendChild(opt);
                });
                filterDate.appendChild(optGroup);
            }
        }

        filterMarket.innerHTML = '<option value="">Todos os Supermercados</option>';
        markets.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = m;
            filterMarket.appendChild(opt);
        });

        filterCategory.innerHTML = '<option value="">Todas as Categorias</option>';
        categories.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            filterCategory.appendChild(opt);
        });
    }

    // Normalizador inteligente de nome de produto para agrupamento e comparação
    function normalizeProductName(name) {
        if (!name) return '';
        let norm = name.toLowerCase().trim();
        // Remove acentos
        norm = norm.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        // Padroniza unidades (1 kg -> 1kg, 1 litro -> 1l)
        norm = norm.replace(/(\d+[\.,]?\d*)\s*(?:quilos?|kilos?|kgs?|kg\b)/g, '$1kg');
        norm = norm.replace(/(\d+[\.,]?\d*)\s*(?:gramas?|grs?|g\b)/g, '$1g');
        norm = norm.replace(/(\d+[\.,]?\d*)\s*(?:litros?|lts?|l\b)/g, '$1l');
        norm = norm.replace(/(\d+[\.,]?\d*)\s*(?:mililitros?|mls?|ml\b)/g, '$1ml');

        // Remove ruídos de corte e marketing
        const noise = [
            /\bfatiad[oa]s?\b/g, /\bem peda[cç]os?\b/g, /\bem postas?\b/g, /\ba v[aá]cuo\b/g,
            /\bcongelad[oa]s?\b/g, /\bresfriad[oa]s?\b/g, /\btemperad[oa]s?\b/g, /\bdesossad[oa]s?\b/g,
            /\bcom dorsal\b/g, /\bsem dorsal\b/g, /\bbandeja\b/g, /\bcada\b/g, /\bunidade\b/g,
            /\bo quilo\b/g, /\bpor kg\b/g, /\boferta\b/g, /\bespecial\b/g, /\bqualidade premium\b/g,
            /\btp\b/g, /\btetra pak\b/g, /\bpet\b/g, /\blata\b/g, /\bgarrafa\b/g, /\bpacote\b/g
        ];
        noise.forEach(rx => { norm = norm.replace(rx, ''); });

        // Sinônimos rápidos
        norm = norm.replace(/\bmussarela\b/g, 'queijo mussarela');
        norm = norm.replace(/\bqueijo tipo mussarela\b/g, 'queijo mussarela');
        norm = norm.replace(/\bqueijo tipo prato\b/g, 'queijo prato');

        // Padroniza separadores e espaços
        norm = norm.replace(/[\(\)\[\]\{\}\/\\,\-\:]+/g, ' ');
        norm = norm.replace(/\s+/g, ' ').trim();
        return norm;
    }

    // Agrupa os itens idênticos ou equivalentes entre múltiplos supermercados
    function processProductGrouping(items) {
        const groups = {};

        items.forEach(item => {
            const normName = normalizeProductName(item.item);
            if (!normName) return;

            // Chave de agrupamento baseada no nome normalizado
            const key = normName;
            if (!groups[key]) {
                groups[key] = {
                    displayName: item.item,
                    category: item.categoria || 'Geral',
                    offers: []
                };
            }
            groups[key].offers.push(item);
        });

        groupedProducts = Object.values(groups).map(g => {
            // Ordena as ofertas deste produto por preço (do menor para o maior)
            g.offers.sort((a, b) => (parseFloat(a.valor) || 0) - (parseFloat(b.valor) || 0));
            
            const minPrice = parseFloat(g.offers[0].valor) || 0;
            const maxPrice = parseFloat(g.offers[g.offers.length - 1].valor) || 0;
            const diff = maxPrice - minPrice;
            const diffPercent = maxPrice > 0 ? (diff / maxPrice) * 100 : 0;
            const uniqueMarkets = new Set(g.offers.map(o => o.supermercado)).size;

            return {
                displayName: g.displayName,
                category: g.category,
                offers: g.offers,
                minPrice,
                maxPrice,
                diff,
                diffPercent,
                uniqueMarkets,
                cheapestMarket: g.offers[0].supermercado,
                mostExpensiveMarket: g.offers[g.offers.length - 1].supermercado
            };
        });

        const multiCount = groupedProducts.filter(g => g.uniqueMarkets > 1).length;
        if (tabCountCompared) {
            tabCountCompared.textContent = multiCount > 0 ? multiCount : groupedProducts.length;
        }
    }

    function applyFilters() {
        const query = searchInput.value.toLowerCase().trim();
        const selectedDate = filterDate ? filterDate.value : '';
        const selectedMkt = filterMarket.value;
        const selectedCat = filterCategory.value;
        const order = sortOrder.value;
        const multiOnly = chkMultiMarketOnly ? chkMultiMarketOnly.checked : false;

        const now = new Date();
        now.setHours(23, 59, 59, 999);
        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());

        // 1. Filtra Lista Geral de Ofertas
        let filteredOffers = allOffers.filter(item => {
            // Checagem de Data
            let matchDate = true;
            if (selectedDate) {
                const itemDate = parseDateString(item.data_postagem);
                if (selectedDate === 'today') {
                    matchDate = itemDate && itemDate >= todayStart;
                } else if (selectedDate === 'last_3_days') {
                    const d3 = new Date(todayStart);
                    d3.setDate(d3.getDate() - 2);
                    matchDate = itemDate && itemDate >= d3;
                } else if (selectedDate === 'last_7_days') {
                    const d7 = new Date(todayStart);
                    d7.setDate(d7.getDate() - 6);
                    matchDate = itemDate && itemDate >= d7;
                } else {
                    matchDate = item.data_postagem === selectedDate;
                }
            }

            const matchQuery = !query || 
                (item.item && item.item.toLowerCase().includes(query)) ||
                (item.supermercado && item.supermercado.toLowerCase().includes(query)) ||
                (item.categoria && item.categoria.toLowerCase().includes(query));

            const matchMkt = !selectedMkt || item.supermercado === selectedMkt;
            const matchCat = !selectedCat || item.categoria === selectedCat;

            return matchDate && matchQuery && matchMkt && matchCat;
        });

        // Atualiza contadores e agrupamento dinâmico baseado na data filtrada
        tabCountItems.textContent = filteredOffers.length.toLocaleString('pt-BR');
        processProductGrouping(filteredOffers);

        // Ordenação de Ofertas
        filteredOffers.sort((a, b) => {
            const pA = parseFloat(a.valor) || 0;
            const pB = parseFloat(b.valor) || 0;
            if (order === 'price-asc') return pA - pB;
            if (order === 'price-desc') return pB - pA;
            if (order === 'name-asc') return (a.item || '').localeCompare(b.item || '');
            return pA - pB;
        });

        renderOffersTable(filteredOffers);
        renderMarketSummary(filteredOffers);
        renderCategorySummary(filteredOffers);

        // 2. Filtra Lista de Comparativo de Produtos
        let filteredGroups = groupedProducts.filter(group => {
            if (multiOnly && group.uniqueMarkets < 2) return false;
            
            const matchCat = !selectedCat || group.category === selectedCat;
            const matchMkt = !selectedMkt || group.offers.some(o => o.supermercado === selectedMkt);
            const matchQuery = !query || 
                group.displayName.toLowerCase().includes(query) ||
                group.category.toLowerCase().includes(query) ||
                group.offers.some(o => o.supermercado.toLowerCase().includes(query));

            return matchCat && matchMkt && matchQuery;
        });

        // Ordenação de Comparativo
        filteredGroups.sort((a, b) => {
            if (order === 'diff-desc') return b.diff - a.diff;
            if (order === 'price-asc') return a.minPrice - b.minPrice;
            if (order === 'price-desc') return b.minPrice - a.minPrice;
            if (order === 'name-asc') return a.displayName.localeCompare(b.displayName);
            return b.diff - a.diff;
        });

        renderComparisonList(filteredGroups);
    }

    // ABA 0: Renderiza Cards de Comparativo de Mesmo Produto entre Mercados
    function renderComparisonList(groups) {
        if (!comparisonContainer) return;

        if (groups.length === 0) {
            comparisonContainer.innerHTML = `
                <div class="empty-state" style="padding: 40px 20px; text-align: center;">
                    <div style="font-size: 28px; margin-bottom: 8px;">🔍</div>
                    <p style="color: var(--text-muted); font-size: 13.5px;">
                        Nenhum produto encontrado para os filtros selecionados.<br>
                        <small>Desmarque a opção <em>"Apenas itens em 2+ supermercados"</em> para visualizar todos os itens.</small>
                    </p>
                </div>
            `;
            return;
        }

        comparisonContainer.innerHTML = '';
        groups.forEach(group => {
            const card = document.createElement('div');
            card.className = 'comparison-card';

            const hasDiff = group.uniqueMarkets > 1 && group.diff > 0;

            let headerHTML = `
                <div class="compare-card-header">
                    <div class="compare-prod-info">
                        <span class="compare-prod-title cursor-pointer btn-jump-history" data-product="${escapeHtml(group.displayName)}" title="Clique para ver o gráfico de histórico de preços deste produto">${escapeHtml(group.displayName)} <span style="font-size: 11px; opacity: 0.7;">📈</span></span>
                        <span class="category-badge">${escapeHtml(group.category)}</span>
                        <span class="category-badge" style="background: var(--bg-subtle); color: var(--text-secondary); border: 1px solid var(--border-color);">
                            ${group.uniqueMarkets} ${group.uniqueMarkets === 1 ? 'mercado' : 'mercados concorrentes'}
                        </span>
                    </div>
                    <div class="compare-highlights">
                        ${hasDiff ? `
                            <span class="saving-badge" title="Economia máxima entre o menor e maior preço">
                                💰 Economize até ${formatCurrency(group.diff)} (${group.diffPercent.toFixed(0)}%)
                            </span>
                        ` : ''}
                        <span class="cheapest-badge">
                            🏆 Menor Preço: ${formatCurrency(group.minPrice)} (${escapeHtml(group.cheapestMarket)})
                        </span>
                    </div>
                </div>
            `;

            let rowsHTML = '';
            group.offers.forEach((offer, idx) => {
                const val = parseFloat(offer.valor) || 0;
                const isBest = idx === 0;
                const diffFromBest = val - group.minPrice;
                const diffPct = group.minPrice > 0 ? (diffFromBest / group.minPrice) * 100 : 0;

                rowsHTML += `
                    <tr class="${isBest ? 'compare-row-best' : ''}">
                        <td style="width: 260px;">
                            <strong>${escapeHtml(offer.supermercado)}</strong>
                            ${isBest ? ' <span class="status-badge-best">🏆 Menor Preço</span>' : ''}
                        </td>
                        <td class="text-right" style="width: 140px; font-weight: 700; font-size: 14px; color: ${isBest ? 'var(--success)' : 'var(--text-primary)'};">
                            ${formatCurrency(val)}
                        </td>
                        <td style="width: 160px;">
                            ${isBest ? `
                                <span style="color: var(--success); font-weight: 600; font-size: 11.5px;">✓ Mais Barato</span>
                            ` : `
                                <span class="status-badge-diff">+${formatCurrency(diffFromBest)} (+${diffPct.toFixed(0)}%)</span>
                            `}
                        </td>
                        <td style="width: 120px; color: var(--text-muted); font-size: 12px;">
                            ${escapeHtml(offer.data_postagem || '-')}
                        </td>
                        <td class="text-center" style="width: 100px;">
                            ${offer.link ? `
                                <button class="btn btn-outline btn-sm btn-preview-flyer" data-img="${escapeHtml(offer.link)}" data-post="${escapeHtml(offer.post_url || '')}" data-market="${escapeHtml(offer.supermercado)}">
                                    Ver Encarte
                                </button>
                            ` : '-'}
                        </td>
                    </tr>
                `;
            });

            const tableHTML = `
                <table class="compare-table">
                    <thead>
                        <tr>
                            <th>Supermercado</th>
                            <th class="text-right">Preço</th>
                            <th>Diferença</th>
                            <th>Data Post</th>
                            <th class="text-center">Encarte</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rowsHTML}
                    </tbody>
                </table>
            `;

            card.innerHTML = headerHTML + tableHTML;
            comparisonContainer.appendChild(card);
        });

        comparisonContainer.querySelectorAll('.btn-jump-history').forEach(el => {
            el.addEventListener('click', () => {
                const prod = el.getAttribute('data-product');
                if (prod) navigateToProductHistory(prod);
            });
        });

        bindPreviewButtons(comparisonContainer);
    }

    // ABA 1: Renderiza Tabela de Todas as Ofertas
    function renderOffersTable(items) {
        if (!tableOffersBody) return;

        if (items.length === 0) {
            tableOffersBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">
                        Nenhuma oferta encontrada para os filtros selecionados.
                    </td>
                </tr>
            `;
            return;
        }

        tableOffersBody.innerHTML = '';
        items.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${escapeHtml(item.supermercado)}</strong></td>
                <td><span class="category-badge">${escapeHtml(item.categoria || 'Geral')}</span></td>
                <td>
                    <span class="cursor-pointer btn-jump-history" data-product="${escapeHtml(item.item)}" title="Clique para ver o gráfico de histórico de preços">
                        ${escapeHtml(item.item)} <span style="font-size: 11px; opacity: 0.7;">📈</span>
                    </span>
                </td>
                <td class="text-right price-text">${formatCurrency(item.valor)}</td>
                <td>${escapeHtml(item.data_postagem || '-')}</td>
                <td class="text-center">
                    ${item.link ? `
                        <button class="btn btn-outline btn-sm btn-preview-flyer" data-img="${escapeHtml(item.link)}" data-post="${escapeHtml(item.post_url || '')}" data-market="${escapeHtml(item.supermercado)}">
                            Ver
                        </button>
                    ` : '-'}
                </td>
            `;
            tableOffersBody.appendChild(tr);
        });

        tableOffersBody.querySelectorAll('.btn-jump-history').forEach(el => {
            el.addEventListener('click', () => {
                const prod = el.getAttribute('data-product');
                if (prod) navigateToProductHistory(prod);
            });
        });

        bindPreviewButtons(tableOffersBody);
    }

    // ABA 2: Resumo por Supermercado
    function renderMarketSummary(items) {
        if (!tableMarketBody) return;
        const groups = {};
        items.forEach(item => {
            const m = item.supermercado || 'Outros';
            if (!groups[m]) {
                groups[m] = { count: 0, sum: 0, min: Infinity, max: -Infinity };
            }
            const val = parseFloat(item.valor) || 0;
            groups[m].count++;
            groups[m].sum += val;
            if (val < groups[m].min) groups[m].min = val;
            if (val > groups[m].max) groups[m].max = val;
        });

        tableMarketBody.innerHTML = '';
        Object.keys(groups).sort().forEach(mkt => {
            const g = groups[mkt];
            const avg = g.count > 0 ? g.sum / g.count : 0;
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${escapeHtml(mkt)}</strong></td>
                <td class="text-center"><span class="category-badge">${g.count} ofertas</span></td>
                <td class="text-right">${formatCurrency(avg)}</td>
                <td class="text-right text-success" style="font-weight: 700;">${formatCurrency(g.min)}</td>
                <td class="text-right">${formatCurrency(g.max)}</td>
            `;
            tableMarketBody.appendChild(tr);
        });
    }

    // ABA 3: Comparativo por Categoria
    function renderCategorySummary(items) {
        if (!tableCatBody) return;
        const groups = {};
        items.forEach(item => {
            const c = item.categoria || 'Geral';
            if (!groups[c]) {
                groups[c] = { count: 0, sum: 0, min: Infinity, cheapestMarket: '-', cheapestItem: '' };
            }
            const val = parseFloat(item.valor) || 0;
            groups[c].count++;
            groups[c].sum += val;
            if (val < groups[c].min) {
                groups[c].min = val;
                groups[c].cheapestMarket = item.supermercado;
                groups[c].cheapestItem = item.item;
            }
        });

        tableCatBody.innerHTML = '';
        Object.keys(groups).sort().forEach(cat => {
            const g = groups[cat];
            const avg = g.count > 0 ? g.sum / g.count : 0;
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="category-badge">${escapeHtml(cat)}</span></td>
                <td class="text-center">${g.count} itens</td>
                <td class="text-right">${formatCurrency(avg)}</td>
                <td class="text-right text-success" style="font-weight: 700;">${formatCurrency(g.min)}</td>
                <td><strong>${escapeHtml(g.cheapestMarket)}</strong> <span style="font-size: 11.5px; color: var(--text-muted);">(${escapeHtml(g.cheapestItem)})</span></td>
            `;
            tableCatBody.appendChild(tr);
        });
    }

    // ============================================================
    // HISTÓRICO DE PREÇOS POR PRODUTO E GRÁFICOS (CHART.JS)
    // ============================================================

    const MARKET_PALETTE = [
        { border: '#2563EB', bg: 'rgba(37, 99, 235, 0.12)' },
        { border: '#16A34A', bg: 'rgba(22, 163, 74, 0.12)' },
        { border: '#D97706', bg: 'rgba(217, 119, 6, 0.12)' },
        { border: '#9333EA', bg: 'rgba(147, 51, 234, 0.12)' },
        { border: '#DC2626', bg: 'rgba(220, 38, 38, 0.12)' },
        { border: '#0891B2', bg: 'rgba(8, 145, 178, 0.12)' },
        { border: '#4F46E5', bg: 'rgba(79, 70, 229, 0.12)' },
        { border: '#EA580C', bg: 'rgba(234, 88, 12, 0.12)' },
        { border: '#059669', bg: 'rgba(5, 150, 105, 0.12)' },
        { border: '#DB2777', bg: 'rgba(219, 39, 119, 0.12)' },
        { border: '#6366F1', bg: 'rgba(99, 102, 241, 0.12)' },
        { border: '#14B8A6', bg: 'rgba(20, 184, 166, 0.12)' }
    ];

    function parseDateTuple(dataPostagem) {
        if (!dataPostagem || dataPostagem === '-') return { iso: '1970-01-01', display: '-' };
        const clean = String(dataPostagem).trim();
        if (clean.includes('/')) {
            const parts = clean.split('/');
            if (parts.length === 3) {
                const y = parts[2].length === 2 ? `20${parts[2]}` : parts[2];
                return { iso: `${y}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`, display: clean };
            }
        }
        if (clean.includes('-')) {
            const parts = clean.split('-');
            if (parts.length === 3) {
                return { iso: clean, display: `${parts[2]}/${parts[1]}/${parts[0]}` };
            }
        }
        return { iso: '1970-01-01', display: clean };
    }

    function buildProductHistoryMap(items) {
        productHistoryMap = {};
        items.forEach(item => {
            const rawName = item.produto_padronizado || item.item || '';
            const normKey = normalizeProductName(rawName);
            if (!normKey) return;

            if (!productHistoryMap[normKey]) {
                productHistoryMap[normKey] = {
                    key: normKey,
                    displayName: item.produto_padronizado || item.item || rawName,
                    category: item.categoria || 'Geral',
                    records: []
                };
            }

            const dateObj = parseDateTuple(item.data_postagem || item.created_at);
            productHistoryMap[normKey].records.push({
                supermercado: item.supermercado || 'Supermercado',
                categoria: item.categoria || productHistoryMap[normKey].category,
                item_original: item.item || rawName,
                produto_padronizado: item.produto_padronizado || rawName,
                marca: item.marca || '',
                embalagem: item.embalagem || '',
                valor: parseFloat(item.valor) || 0,
                data_postagem: item.data_postagem || '-',
                iso_date: dateObj.iso,
                display_date: dateObj.display,
                link: item.link || '',
                post_url: item.post_url || ''
            });
        });

        currentProductsList = Object.values(productHistoryMap).map(p => {
            p.records.sort((a, b) => a.iso_date.localeCompare(b.iso_date));
            const uniqueMarkets = new Set(p.records.map(r => r.supermercado)).size;
            return {
                key: p.key,
                displayName: p.displayName,
                category: p.category,
                totalRecords: p.records.length,
                uniqueMarkets: uniqueMarkets
            };
        });

        currentProductsList.sort((a, b) => b.totalRecords - a.totalRecords || a.displayName.localeCompare(b.displayName));

        if (tabCountHistory) {
            tabCountHistory.textContent = currentProductsList.length;
        }

        populateHistoryCategoryFilter(currentProductsList);
        filterAndRenderProductOptions();
    }

    function populateHistoryCategoryFilter(products) {
        if (!filterHistoryCategory) return;
        const curVal = filterHistoryCategory.value;
        const categories = [...new Set(products.map(p => p.category).filter(Boolean))].sort();

        filterHistoryCategory.innerHTML = '<option value="">Todas as categorias</option>';
        categories.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            filterHistoryCategory.appendChild(opt);
        });
        if (categories.includes(curVal)) {
            filterHistoryCategory.value = curVal;
        }
    }

    function filterAndRenderProductOptions(preferredKey = null) {
        if (!selectHistoryProduct) return;

        const cat = filterHistoryCategory ? filterHistoryCategory.value : '';
        const query = inputSearchHistoryProduct ? inputSearchHistoryProduct.value.toLowerCase().trim() : '';

        const filtered = currentProductsList.filter(p => {
            const matchCat = !cat || p.category === cat;
            const matchQuery = !query || 
                p.displayName.toLowerCase().includes(query) ||
                p.category.toLowerCase().includes(query);
            return matchCat && matchQuery;
        });

        selectHistoryProduct.innerHTML = '';
        if (filtered.length === 0) {
            selectHistoryProduct.innerHTML = '<option value="">Nenhum produto encontrado</option>';
            if (historyProductTitle) historyProductTitle.textContent = 'Nenhum produto selecionado';
            if (chartEmptyState) chartEmptyState.style.display = 'flex';
            if (priceChartInstance) {
                priceChartInstance.destroy();
                priceChartInstance = null;
            }
            if (tbodyProductHistory) {
                tbodyProductHistory.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhum registro para os filtros selecionados.</td></tr>';
            }
            return;
        }

        filtered.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.key;
            opt.textContent = `${p.displayName} (${p.totalRecords} ofertas • ${p.uniqueMarkets} mercados)`;
            selectHistoryProduct.appendChild(opt);
        });

        let toSelect = filtered[0].key;
        if (preferredKey && filtered.some(p => p.key === preferredKey)) {
            toSelect = preferredKey;
        } else if (selectedProductName && filtered.some(p => p.key === selectedProductName)) {
            toSelect = selectedProductName;
        }

        selectHistoryProduct.value = toSelect;
        selectedProductName = toSelect;
        renderProductPriceHistory(toSelect);
    }

    function renderProductPriceHistory(productKey) {
        if (!productKey || !productHistoryMap[productKey]) return;
        selectedProductName = productKey;

        const product = productHistoryMap[productKey];
        const records = [...product.records];
        if (records.length === 0) return;

        // Estatísticas
        const prices = records.map(r => r.valor).filter(v => v > 0);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        const avgPrice = prices.length > 0 ? prices.reduce((a, b) => a + b, 0) / prices.length : 0;

        const recMin = records.find(r => r.valor === minPrice) || records[0];
        const recMax = records.find(r => r.valor === maxPrice) || records[0];
        const recRecent = records[records.length - 1];

        const varPct = avgPrice > 0 ? ((recRecent.valor - avgPrice) / avgPrice * 100) : 0;
        const uniqueMarkets = new Set(records.map(r => r.supermercado)).size;

        // 1. Atualizar Banner
        if (historyProductTitle) historyProductTitle.textContent = product.displayName;
        if (historyProductCategory) historyProductCategory.textContent = product.category;
        if (historyProductDates) {
            historyProductDates.textContent = `Registros de ${records[0].display_date} a ${recRecent.display_date}`;
        }

        // 2. Atualizar KPIs
        if (statHistMinPrice) statHistMinPrice.textContent = formatCurrency(minPrice);
        if (statHistMinMarket) statHistMinMarket.textContent = `No ${recMin.supermercado} (${recMin.display_date})`;

        if (statHistMaxPrice) statHistMaxPrice.textContent = formatCurrency(maxPrice);
        if (statHistMaxMarket) statHistMaxMarket.textContent = `No ${recMax.supermercado} (${recMax.display_date})`;

        if (statHistAvgPrice) statHistAvgPrice.textContent = formatCurrency(avgPrice);
        if (statHistRecordsCount) statHistRecordsCount.textContent = `${records.length} ofertas em ${uniqueMarkets} supermercado(s)`;

        if (statHistRecentPrice) statHistRecentPrice.textContent = formatCurrency(recRecent.valor);
        if (statHistTrendBadge) {
            if (varPct < -0.5) {
                statHistTrendBadge.innerHTML = `<span class="trend-badge trend-badge-down">↓ ${Math.abs(varPct).toFixed(1)}% vs média</span>`;
            } else if (varPct > 0.5) {
                statHistTrendBadge.innerHTML = `<span class="trend-badge trend-badge-up">↑ +${varPct.toFixed(1)}% vs média</span>`;
            } else {
                statHistTrendBadge.innerHTML = `<span class="trend-badge trend-badge-neutral">Na média histórica</span>`;
            }
        }

        // 3. Renderizar Gráfico
        renderHistoryChart(records, avgPrice);

        // 4. Renderizar Tabela Histórica
        renderHistoryTable(records, avgPrice);
    }

    function renderHistoryChart(records, avgPrice) {
        if (!productPriceChartCanvas) return;

        if (priceChartInstance) {
            priceChartInstance.destroy();
            priceChartInstance = null;
        }

        if (!records || records.length === 0) {
            if (chartEmptyState) chartEmptyState.style.display = 'flex';
            return;
        }
        if (chartEmptyState) chartEmptyState.style.display = 'none';

        // Obter datas únicas ordenadas
        const datesMap = {};
        records.forEach(r => {
            if (r.iso_date) datesMap[r.iso_date] = r.display_date;
        });
        const sortedIsoDates = Object.keys(datesMap).sort();
        const dateLabels = sortedIsoDates.map(d => datesMap[d]);

        const supermarkets = [...new Set(records.map(r => r.supermercado))].sort();
        const mode = selectChartMode ? selectChartMode.value : 'multi_market';

        let datasets = [];
        let legendHtml = '';

        if (mode === 'multi_market') {
            supermarkets.forEach((mkt, idx) => {
                const colorObj = MARKET_PALETTE[idx % MARKET_PALETTE.length];
                const mktRecords = records.filter(r => r.supermercado === mkt);
                const dateToVal = {};
                mktRecords.forEach(r => { dateToVal[r.iso_date] = r.valor; });

                const dataPoints = sortedIsoDates.map(d => dateToVal[d] !== undefined ? dateToVal[d] : null);

                datasets.push({
                    label: mkt,
                    data: dataPoints,
                    borderColor: colorObj.border,
                    backgroundColor: colorObj.bg,
                    borderWidth: 2.5,
                    tension: 0.25,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: colorObj.border,
                    pointBorderColor: '#FFFFFF',
                    pointBorderWidth: 2,
                    spanGaps: true
                });

                legendHtml += `
                    <div class="legend-item-chip">
                        <span class="legend-color-dot" style="background: ${colorObj.border};"></span>
                        <span>${escapeHtml(mkt)}</span>
                    </div>
                `;
            });
        } else if (mode === 'average_trend') {
            const avgPoints = sortedIsoDates.map(d => {
                const vals = records.filter(r => r.iso_date === d).map(r => r.valor).filter(v => v > 0);
                return vals.length > 0 ? (vals.reduce((a, b) => a + b, 0) / vals.length) : null;
            });

            datasets.push({
                label: 'Preço Médio nos Encartes',
                data: avgPoints,
                borderColor: '#2563EB',
                backgroundColor: 'rgba(37, 99, 235, 0.12)',
                borderWidth: 3,
                tension: 0.3,
                fill: true,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointBackgroundColor: '#2563EB',
                pointBorderColor: '#FFFFFF',
                pointBorderWidth: 2,
                spanGaps: true
            });

            legendHtml = `
                <div class="legend-item-chip">
                    <span class="legend-color-dot" style="background: #2563EB;"></span>
                    <span>Preço Médio dos Encartes</span>
                </div>
            `;
        } else if (mode === 'bar_comparison') {
            supermarkets.forEach((mkt, idx) => {
                const colorObj = MARKET_PALETTE[idx % MARKET_PALETTE.length];
                const mktRecords = records.filter(r => r.supermercado === mkt);
                const dateToVal = {};
                mktRecords.forEach(r => { dateToVal[r.iso_date] = r.valor; });

                const dataPoints = sortedIsoDates.map(d => dateToVal[d] !== undefined ? dateToVal[d] : null);

                datasets.push({
                    type: 'bar',
                    label: mkt,
                    data: dataPoints,
                    backgroundColor: colorObj.border,
                    borderColor: colorObj.border,
                    borderWidth: 1,
                    borderRadius: 4
                });

                legendHtml += `
                    <div class="legend-item-chip">
                        <span class="legend-color-dot" style="background: ${colorObj.border};"></span>
                        <span>${escapeHtml(mkt)}</span>
                    </div>
                `;
            });
        }

        if (chartLegendCustom) chartLegendCustom.innerHTML = legendHtml;
        if (chartProductSubtitle) chartProductSubtitle.textContent = `${dateLabels.length} data(s) • ${datasets.length} série(s) de dados`;

        const ctx = productPriceChartCanvas.getContext('2d');
        priceChartInstance = new Chart(ctx, {
            type: mode === 'bar_comparison' ? 'bar' : 'line',
            data: {
                labels: dateLabels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#0F172A',
                        titleColor: '#F8FAFC',
                        bodyColor: '#F1F5F9',
                        padding: 12,
                        cornerRadius: 6,
                        callbacks: {
                            label: function(context) {
                                const val = context.parsed.y;
                                if (val === null || val === undefined || isNaN(val)) return null;
                                const dsLabel = context.dataset.label || 'Preço';
                                return ` ${dsLabel}: ${formatCurrency(val)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grace: '10%',
                        grid: { color: '#EDF2F7' },
                        ticks: {
                            color: '#64748B',
                            font: { family: 'Inter', size: 11 },
                            callback: function(val) {
                                return 'R$ ' + parseFloat(val).toFixed(2).replace('.', ',');
                            }
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: '#64748B',
                            font: { family: 'Inter', size: 11 }
                        }
                    }
                }
            }
        });
    }

    function renderHistoryTable(records, avgPrice) {
        if (!tbodyProductHistory) return;

        const descRecords = [...records].reverse();
        if (historyTableCount) historyTableCount.textContent = descRecords.length;

        tbodyProductHistory.innerHTML = '';
        descRecords.forEach(item => {
            const tr = document.createElement('tr');
            const diff = item.valor - avgPrice;
            const diffPct = avgPrice > 0 ? (diff / avgPrice * 100) : 0;

            let diffTagHtml = '';
            if (diffPct < -0.5) {
                diffTagHtml = `<span class="diff-tag diff-tag-negative">↓ ${Math.abs(diffPct).toFixed(1)}% (${formatCurrency(Math.abs(diff))})</span>`;
            } else if (diffPct > 0.5) {
                diffTagHtml = `<span class="diff-tag diff-tag-positive">↑ +${diffPct.toFixed(1)}% (+${formatCurrency(diff)})</span>`;
            } else {
                diffTagHtml = `<span class="diff-tag diff-tag-neutral">≈ Na média</span>`;
            }

            tr.innerHTML = `
                <td style="text-align: center; font-weight: 600; color: var(--text-secondary);">${escapeHtml(item.display_date)}</td>
                <td><strong>${escapeHtml(item.supermercado)}</strong></td>
                <td style="font-size: 12.5px; color: var(--text-primary);">${escapeHtml(item.item_original)}</td>
                <td class="text-right price-text" style="font-size: 13.5px;">${formatCurrency(item.valor)}</td>
                <td style="text-align: center;">${diffTagHtml}</td>
                <td class="text-center">
                    ${item.link ? `
                        <button class="btn btn-outline btn-sm btn-preview-flyer" 
                                data-img="${escapeHtml(item.link)}" 
                                data-post="${escapeHtml(item.post_url || '')}" 
                                data-market="${escapeHtml(item.supermercado)}">
                            Ver
                        </button>
                    ` : '-'}
                </td>
            `;
            tbodyProductHistory.appendChild(tr);
        });

        bindPreviewButtons(tbodyProductHistory);
    }

    function navigateToProductHistory(productName) {
        if (!productName) return;
        const normKey = normalizeProductName(productName);
        const tabBtn = document.querySelector('[data-tab="tab-price-history"]');
        if (tabBtn) {
            tabBtn.click();
            filterAndRenderProductOptions(normKey);
        }
    }

    function bindPreviewButtons(container) {
        container.querySelectorAll('.btn-preview-flyer').forEach(btn => {
            btn.addEventListener('click', () => {
                const img = btn.getAttribute('data-img');
                const post = btn.getAttribute('data-post');
                const mkt = btn.getAttribute('data-market');

                previewImgElement.src = img;
                modalImageTitle.textContent = `Encarte: ${mkt}`;
                btnOpenOriginalImg.href = img;
                btnOpenInstagramPost.href = post || img;
                modalImagePreview.style.display = 'flex';
            });
        });
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
