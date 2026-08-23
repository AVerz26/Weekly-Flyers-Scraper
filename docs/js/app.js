/**
 * FlyerScout - Visualização de Dados & Comparativo de Preços
 * GitHub Pages Dashboard
 */

document.addEventListener('DOMContentLoaded', () => {
    let allOffers = [];
    let currentFiltered = [];

    // Elementos DOM
    const lastUpdateText = document.getElementById('last-update-text');
    const metricTotalItems = document.getElementById('metric-total-items');
    const metricDateInfo = document.getElementById('metric-date-info');
    const metricMarketsCount = document.getElementById('metric-markets-count');
    const metricCategoriesCount = document.getElementById('metric-categories-count');
    const metricMinPrice = document.getElementById('metric-min-price');
    const metricMinItem = document.getElementById('metric-min-item');
    const tabCountItems = document.getElementById('tab-count-items');

    const searchInput = document.getElementById('search-input');
    const filterMarket = document.getElementById('filter-market');
    const filterCategory = document.getElementById('filter-category');
    const sortOrder = document.getElementById('sort-order');

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

    // Gerenciamento de Abas
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
        filterMarket.addEventListener('change', applyFilters);
        filterCategory.addEventListener('change', applyFilters);
        sortOrder.addEventListener('change', applyFilters);

        btnCloseModal.addEventListener('click', () => {
            modalImagePreview.style.display = 'none';
        });

        modalImagePreview.addEventListener('click', (e) => {
            if (e.target === modalImagePreview) modalImagePreview.style.display = 'none';
        });
    }

    async function loadData() {
        const possibleUrls = [
            'data/latest_results.json',
            '../output/latest_results.json',
            'https://raw.githubusercontent.com/AVerz26/Weekly-Flyers-Scraper/main/output/latest_results.json'
        ];

        let data = null;
        for (const url of possibleUrls) {
            try {
                const resp = await fetch(url);
                if (resp.ok) {
                    data = await resp.json();
                    break;
                }
            } catch (e) {
                // Continua para o próximo
            }
        }

        if (!data || !data.items || data.items.length === 0) {
            lastUpdateText.textContent = 'Aguardando primeira coleta';
            tableOffersBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">
                        Nenhum dado coletado ainda. O robô atualizará esta página automaticamente às 07:00 da manhã.
                    </td>
                </tr>
            `;
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

    function populateDropdowns(items) {
        const markets = [...new Set(items.map(i => i.supermercado).filter(Boolean))].sort();
        const categories = [...new Set(items.map(i => i.categoria).filter(Boolean))].sort();

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

    function applyFilters() {
        const query = searchInput.value.toLowerCase().trim();
        const selectedMkt = filterMarket.value;
        const selectedCat = filterCategory.value;
        const order = sortOrder.value;

        let filtered = allOffers.filter(item => {
            const matchQuery = !query || 
                (item.item && item.item.toLowerCase().includes(query)) ||
                (item.supermercado && item.supermercado.toLowerCase().includes(query)) ||
                (item.categoria && item.categoria.toLowerCase().includes(query));

            const matchMkt = !selectedMkt || item.supermercado === selectedMkt;
            const matchCat = !selectedCat || item.categoria === selectedCat;

            return matchQuery && matchMkt && matchCat;
        });

        // Ordenação
        filtered.sort((a, b) => {
            const pA = parseFloat(a.valor) || 0;
            const pB = parseFloat(b.valor) || 0;
            if (order === 'price-asc') return pA - pB;
            if (order === 'price-desc') return pB - pA;
            if (order === 'name-asc') return (a.item || '').localeCompare(b.item || '');
            if (order === 'market-asc') return (a.supermercado || '').localeCompare(b.supermercado || '');
            return 0;
        });

        currentFiltered = filtered;
        renderOffersTable(filtered);
    }

    // ABA 1: Renderiza Tabela de Ofertas
    function renderOffersTable(items) {
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
