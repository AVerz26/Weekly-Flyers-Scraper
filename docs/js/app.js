/**
 * FlyerScout - Visualização de Dados & Comparativo de Preços de Produtos
 * GitHub Pages Dashboard
 */

document.addEventListener('DOMContentLoaded', () => {
    let allOffers = [];
    let groupedProducts = [];

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
                        <span class="compare-prod-title">${escapeHtml(group.displayName)}</span>
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
                <td>${escapeHtml(item.item)}</td>
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
