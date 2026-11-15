document.addEventListener('DOMContentLoaded', () => {
    const data = PRODUCT_DATA;
    if (!data || !data.variations || data.variations.length === 0) return;

    const priceEl = document.getElementById('current-price');
    const availEl = document.getElementById('current-avail');
    const specsTable = document.getElementById('specs-table');
    const variantsContainer = document.getElementById('variants-container');
    const bomSection = document.getElementById('bom-section');
    const bomContainer = document.getElementById('bom-container');
    const mainImage = document.getElementById('main-image');
    const thumbnailsGrid = document.getElementById('thumbnails-grid');

    init();

    function init() {
        renderVariants();
        const urlParams = new URLSearchParams(window.location.search);
        const offerIdFromUrl = urlParams.get('offer_id');
        
        let initialOfferId = data.variations[0].offer_id;
        if (offerIdFromUrl && data.variations.some(v => v.offer_id == offerIdFromUrl)) {
            initialOfferId = parseInt(offerIdFromUrl);
        }
        selectVariant(initialOfferId);
    }

    function renderVariants() {
        variantsContainer.innerHTML = '';
        data.variations.forEach(v => {
            // Собираем ВСЕ характеристики, в названии которых есть "цвет"
            const colorAttrs = v.attributes ? v.attributes.filter(a => a.name.toLowerCase().includes('цвет')) : [];
            
            let label = "";
            if (colorAttrs.length > 0) {
                // Объединяем значения через слэш (например: "Белый / Дуб крафт")
                label = colorAttrs.map(a => a.value).join(" / ");
            } else {
                label = `Вариант ${v.offer_id}`;
            }

            const btn = document.createElement('button');
            btn.className = 'variant-btn';
            btn.dataset.id = v.offer_id;

            // Картинка для кружка
            const imgUrl = v.picture ? `/proxy_image?url=${encodeURIComponent(v.picture)}` : (v.images && v.images.length > 0 ? `/proxy_image?url=${encodeURIComponent(v.images[0])}` : null);
            
            let circleHtml = '';
            if (imgUrl) {
                circleHtml = `<div class="variant-circle" style="background-image: url('${imgUrl}');"></div>`;
            } else {
                circleHtml = `<div class="variant-circle" style="background-color: #eee;"></div>`;
            }

            // Вставляем кружок и текст
            btn.innerHTML = `${circleHtml}<span class="variant-label">${label}</span>`;
            
            btn.onclick = () => selectVariant(v.offer_id);
            variantsContainer.appendChild(btn);
        });
    }

    function selectVariant(offerId) {
        document.querySelectorAll('.variant-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.id == offerId) btn.classList.add('active');
        });

        const newUrl = new URL(window.location);
        newUrl.searchParams.set('offer_id', offerId);
        window.history.pushState({}, '', newUrl);

        const variant = data.variations.find(v => v.offer_id == offerId);
        if (!variant) return;

        priceEl.textContent = variant.price ? `${variant.price} ₽` : 'Цена по запросу';
        availEl.textContent = variant.available ? 'Есть в наличии' : 'Под заказ';
        availEl.className = variant.available ? 'availability in-stock' : 'availability out-stock';

        updateGallery(variant.images || []);
        renderSpecs(variant.attributes || []);
        renderBOM(variant.bom || []);
    }

    function updateGallery(images) {
        thumbnailsGrid.innerHTML = '';
        
        if (images.length === 0) {
            mainImage.src = 'https://via.placeholder.com/600x400?text=Нет+фото';
            return;
        }

        // Ставим главную картинку
        mainImage.src = `/proxy_image?url=${encodeURIComponent(images[0])}`;
        // Если главная битая - ставим заглушку
        mainImage.onerror = () => { mainImage.src = 'https://via.placeholder.com/600x400?text=Ошибка+фото'; };

        images.forEach((url, index) => {
            const img = document.createElement('img');
            img.src = `/proxy_image?url=${encodeURIComponent(url)}`;
            img.className = 'thumbnail-img';
            
            // Если превьюшка битая - ставим заглушку
            img.onerror = () => { img.src = 'https://via.placeholder.com/100x100?text=404'; };
            
            img.onclick = () => {
                mainImage.src = `/proxy_image?url=${encodeURIComponent(url)}`;
                mainImage.onerror = () => { mainImage.src = 'https://via.placeholder.com/600x400?text=Ошибка+фото'; };
                document.querySelectorAll('.thumbnail-img').forEach(t => t.classList.remove('active'));
                img.classList.add('active');
            };
            if (index === 0) img.classList.add('active');
            thumbnailsGrid.appendChild(img);
        });
    }

    function renderSpecs(attributes) {
        specsTable.innerHTML = '';
        if (attributes.length === 0) {
            specsTable.innerHTML = '<tr><td colspan="2">Нет данных</td></tr>';
            return;
        }
        attributes.forEach(attr => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td class="spec-name">${attr.name}</td><td class="spec-val">${attr.value}</td>`;
            specsTable.appendChild(tr);
        });
    }

    function renderBOM(bom) {
        bomContainer.innerHTML = '';
        if (bom.length === 0) {
            bomSection.style.display = 'none';
            return;
        }

        bomSection.style.display = 'block';
        bom.forEach(item => {
            const card = document.createElement('a');
            card.href = `/product/${item.target_group_id}?offer_id=${item.component_offer_id}`;
            card.className = 'bom-card';
            
            const imgHtml = item.picture 
                ? `<img src="/proxy_image?url=${encodeURIComponent(item.picture)}" referrerpolicy="no-referrer">` 
                : `<div class="no-image">Нет фото</div>`;

            // Добавляем блок с цветом, если он есть
            const colorHtml = item.module_color 
                ? `<div class="bom-color" style="font-size: 12px; color: #888; margin: 5px 0;">${item.module_color}</div>` 
                : '';

            card.innerHTML = `
                <div class="bom-img">${imgHtml}</div>
                <div class="bom-info">
                    <div class="bom-name">${item.name}</div>
                    ${colorHtml}
                    <div class="bom-qty">${item.quantity} шт.</div>
                </div>
            `;
            bomContainer.appendChild(card);
        });
    }
});