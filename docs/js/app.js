/**
 * FlyerScout AI - GitHub Pages Interactive Dashboard
 */

document.addEventListener('DOMContentLoaded', () => {
    let allOffers = [];
    let currentFiltered = [];
    let currentView = 'cards'; // 'cards' ou 'table'

    // Elementos DOM
    const lastUpdateText = document.getElementById('last-update-text');
    const metricTotalItems = document.getElementById('metric-total-items');
    const metricDateRange = document.getElementById('metric-date-range');
    const metricMarketsCount = document.getElementById('metric-markets-count');
    const metricCategoriesCount = document.getElementById('metric-categories-count');
    const metricMinPrice = document.getElementById('metric-min-price');
    const metricMinItem = document.getElementById('metric-min-item');

    const searchInput = document.getElementById('search-input');
    const filterMarket = document.getElementById('filter-market');
    const filterCategory = document.getElementById('filter-category');
    const sortOrder = document.getElementById('sort-order');

    const btnViewCards = document.getElementById('btn-view-cards');
    const btnViewTable = document.getElementById('btn-view-table');
    const viewCardsContainer = document.getElementById('view-cards-container');
    const viewTableContainer = document.getElementById('view-table-container');
    const tableOffersBody = document.getElementById('table-offers-body');
    const emptyResults = document.getElementById('empty-results');

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
        setupEventListeners();
        await loadData();
    }

    function setupEventListeners() {
        searchInput.addEventListener('input', applyFilters);
        filterMarket.addEventListener('change', applyFilters);
        filterCategory.addEventListener('change', applyFilters);
        sortOrder.addEventListener('change', applyFilters);

        btnViewCards.addEventListener('click', () => setView('cards'));
        btnViewTable.addEventListener('click', () => setView('table'));

        btnCloseModal.addEventListener('click', () => {
            modalImagePreview.style.display = 'none';
        });

        modalImagePreview.addEventListener('click', (e) => {
            if (e.target === modalImagePreview) modalImagePreview.style.display = 'none';
        });
    }

    async function loadData() {
        // Tenta carregar os dados de docs/data/latest_results.json ou ../output/latest_results.json
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
            emptyResults.style.display = 'block';
            emptyResults.querySelector('h3').textContent = 'Nenhum dado coletado ainda';
            emptyResults.querySelector('p').textContent = 'Execute o workflow no GitHub Actions para carregar as ofertas.';
            return;
        }

        allOffers = data.items;
        
        // Atualiza timestamp
        if (data.timestamp) {
            const formattedDate = data.timestamp.replace(/_/g, ' às ').replace(/-/g, '/');
            lastUpdateText.textContent = formattedDate;
            metricDateRange.textContent = `Coleta: ${data.timestamp.split('_')[0]}`;
        } else {
            lastUpdateText.textContent = 'Hoje';
        }

        updateMetrics(allOffers);
        populateDropdowns(allOffers);
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
        renderData();
    }

    function renderData() {
        if (currentFiltered.length === 0) {
            viewCardsContainer.style.display = 'none';
            viewTableContainer.style.display = 'none';
            emptyResults.style.display = 'block';
            return;
        }

        emptyResults.style.display = 'none';

        if (currentView === 'cards') {
            viewCardsContainer.style.display = 'grid';
            viewTableContainer.style.display = 'none';
            renderCards(currentFiltered);
        } else {
            viewCardsContainer.style.display = 'none';
            viewTableContainer.style.display = 'block';
            renderTable(currentFiltered);
        }
    }

    function renderCards(items) {
        viewCardsContainer.innerHTML = '';
        items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'offer-card';
            card.innerHTML = `
                <div>
                    <div class="card-top">
                        <span class="market-badge">${escapeHtml(item.supermercado)}</span>
                        <span class="category-tag">${escapeHtml(item.categoria || 'Geral')}</span>
                    </div>
                    <div class="card-item-name">${escapeHtml(item.item)}</div>
                </div>
                <div class="card-bottom">
                    <div class="price-box">
                        <span class="price-label">Preço Promo</span>
                        <span class="price-val">${formatCurrency(item.valor)}</span>
                    </div>
                    ${item.link ? `
                        <button class="btn btn-outline btn-sm btn-view-flyer" data-img="${escapeHtml(item.link)}" data-post="${escapeHtml(item.post_url || '')}" data-market="${escapeHtml(item.supermercado)}">
                            🖼️ Encarte
                        </button>
                    ` : ''}
                </div>
            `;
            viewCardsContainer.appendChild(card);
        });

        bindPreviewButtons(viewCardsContainer);
    }

    function renderTable(items) {
        tableOffersBody.innerHTML = '';
        items.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${escapeHtml(item.supermercado)}</strong></td>
                <td><span class="category-tag">${escapeHtml(item.categoria || 'Geral')}</span></td>
                <td>${escapeHtml(item.item)}</td>
                <td class="text-right price-text">${formatCurrency(item.valor)}</td>
                <td>${escapeHtml(item.data_postagem || '-')}</td>
                <td class="text-center">
                    ${item.link ? `
                        <button class="btn btn-outline btn-sm btn-view-flyer" data-img="${escapeHtml(item.link)}" data-post="${escapeHtml(item.post_url || '')}" data-market="${escapeHtml(item.supermercado)}">
                            Ver
                        </button>
                    ` : '-'}
                </td>
            `;
            tableOffersBody.appendChild(tr);
        });

        bindPreviewButtons(tableOffersBody);
    }

    function bindPreviewButtons(container) {
        container.querySelectorAll('.btn-view-flyer').forEach(btn => {
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

    function setView(view) {
        currentView = view;
        if (view === 'cards') {
            btnViewCards.classList.add('active');
            btnViewTable.classList.remove('active');
        } else {
            btnViewTable.classList.add('active');
            btnViewCards.classList.remove('active');
        }
        renderData();
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
