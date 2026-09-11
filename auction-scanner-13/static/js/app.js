/**
 * Scanner Encheres 13 - Frontend JavaScript
 */

let debounceTimer = null;

// Chargement initial
document.addEventListener("DOMContentLoaded", () => {
    loadAuctions();
    loadStats();
    // Refresh auto toutes les 2 minutes
    setInterval(() => {
        loadAuctions();
        loadStats();
    }, 120000);
});

/**
 * Charge et affiche les encheres depuis l'API.
 */
function loadAuctions() {
    const params = new URLSearchParams({
        category: document.getElementById("filter-category").value,
        search: document.getElementById("filter-search").value,
        ville: document.getElementById("filter-ville").value,
        sort: document.getElementById("filter-sort").value,
    });

    const priceMin = document.getElementById("filter-price-min").value;
    const priceMax = document.getElementById("filter-price-max").value;
    if (priceMin) params.set("price_min", priceMin);
    if (priceMax) params.set("price_max", priceMax);

    fetch(`/api/auctions?${params}`)
        .then(res => res.json())
        .then(data => {
            renderAuctions(data.auctions);
            updateScanStatus(data);
            updateLastUpdate(data.last_update);
            showErrors(data.errors);
        })
        .catch(err => {
            console.error("Erreur chargement:", err);
        });
}

/**
 * Charge les statistiques.
 */
function loadStats() {
    fetch("/api/stats")
        .then(res => res.json())
        .then(data => {
            document.getElementById("stat-total").textContent = data.total || 0;
            document.getElementById("stat-immo").textContent = data.by_category?.immobilier || 0;
            document.getElementById("stat-vehicules").textContent = data.by_category?.vehicules || 0;

            const objets = (data.by_category?.mobilier || 0) +
                          (data.by_category?.art || 0) +
                          (data.by_category?.autre || 0);
            document.getElementById("stat-objets").textContent = objets;

            const sources = Object.keys(data.by_source || {}).length;
            document.getElementById("stat-sources").textContent = sources || 3;
        })
        .catch(() => {});
}

/**
 * Affiche les encheres dans la grille.
 */
function renderAuctions(auctions) {
    const container = document.getElementById("auctions-list");

    if (!auctions || auctions.length === 0) {
        container.innerHTML = `
            <div class="no-results">
                <div class="no-results-icon">&#128269;</div>
                <h3>Aucune enchere trouvee</h3>
                <p>Modifiez vos filtres ou lancez un nouveau scan</p>
            </div>`;
        return;
    }

    container.innerHTML = auctions.map((a, i) => createAuctionCard(a, i)).join("");
}

/**
 * Cree le HTML d'une carte d'enchere.
 */
function createAuctionCard(auction, index) {
    const cat = auction.category || "autre";
    const catLabels = {
        immobilier: "Immobilier",
        vehicules: "Vehicules",
        mobilier: "Mobilier",
        art: "Art",
        bijoux: "Bijoux",
        electronique: "Electronique",
        autre: "Autre"
    };

    const priceHtml = auction.price_estimate
        ? `<span class="card-price">${formatPrice(auction.price_estimate)}</span>`
        : `<span class="card-price no-price">Prix non communique</span>`;

    const dateHtml = auction.date_vente
        ? `<span class="date-badge ${getDateClass(auction.date_vente)}">${formatDateIcon(auction.date_vente)} ${formatDate(auction.date_vente)}</span>`
        : "";

    const villeHtml = auction.ville
        ? `<div class="detail-item"><span class="detail-icon">&#128205;</span> ${escapeHtml(auction.ville)}</div>`
        : "";

    const addressHtml = auction.address
        ? `<div class="detail-item"><span class="detail-icon">&#127968;</span> ${escapeHtml(auction.address)}</div>`
        : "";

    const lotsHtml = auction.lot_count
        ? `<div class="detail-item"><span class="detail-icon">&#128230;</span> ${auction.lot_count} lots</div>`
        : "";

    const typeHtml = auction.auction_type
        ? `<div class="detail-item"><span class="detail-icon">&#9878;</span> ${escapeHtml(auction.auction_type)}</div>`
        : "";

    const linkHtml = auction.url
        ? `<a href="${escapeHtml(auction.url)}" target="_blank" rel="noopener" class="card-link">Voir &#8599;</a>`
        : "";

    return `
    <div class="auction-card cat-${cat}" style="animation-delay: ${Math.min(index * 0.05, 0.5)}s">
        <div class="card-header">
            <h3 class="card-title">${escapeHtml(auction.title)}</h3>
            <span class="card-badge badge-${cat}">${catLabels[cat] || cat}</span>
        </div>
        <div class="card-body">
            ${auction.description ? `<p class="card-description">${escapeHtml(auction.description)}</p>` : ""}
            <div class="card-details">
                ${dateHtml}
                ${villeHtml}
                ${addressHtml}
                ${lotsHtml}
                ${typeHtml}
            </div>
        </div>
        <div class="card-footer">
            ${priceHtml}
            <span class="card-source">${escapeHtml(auction.source)}</span>
            ${linkHtml}
        </div>
    </div>`;
}

/**
 * Formate un prix en euros.
 */
function formatPrice(price) {
    if (!price && price !== 0) return "";
    return new Intl.NumberFormat("fr-FR", {
        style: "currency",
        currency: "EUR",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(price);
}

/**
 * Formate une date ISO en format lisible.
 */
function formatDate(dateStr) {
    if (!dateStr) return "";
    try {
        const d = new Date(dateStr + "T00:00:00");
        const options = { weekday: "short", day: "numeric", month: "short", year: "numeric" };
        return d.toLocaleDateString("fr-FR", options);
    } catch {
        return dateStr;
    }
}

/**
 * Retourne une icone selon la proximite de la date.
 */
function formatDateIcon(dateStr) {
    const days = getDaysUntil(dateStr);
    if (days <= 3) return "&#128308;"; // rouge
    if (days <= 7) return "&#128992;"; // orange
    return "&#128994;"; // vert
}

/**
 * Retourne une classe CSS selon la proximite de la date.
 */
function getDateClass(dateStr) {
    const days = getDaysUntil(dateStr);
    if (days <= 3) return "date-soon";
    if (days <= 10) return "date-upcoming";
    return "date-later";
}

/**
 * Calcule le nombre de jours avant une date.
 */
function getDaysUntil(dateStr) {
    try {
        const target = new Date(dateStr + "T00:00:00");
        const now = new Date();
        now.setHours(0, 0, 0, 0);
        return Math.ceil((target - now) / (1000 * 60 * 60 * 24));
    } catch {
        return 999;
    }
}

/**
 * Lance un scan manuel.
 */
function launchScan() {
    const btn = document.getElementById("btn-scan");
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px;"></div> Scan...';

    document.getElementById("scanning-indicator").style.display = "flex";

    fetch("/api/scan", { method: "POST" })
        .then(res => res.json())
        .then(() => {
            // Poll toutes les 3 secondes
            const poll = setInterval(() => {
                fetch("/api/auctions?category=all")
                    .then(res => res.json())
                    .then(data => {
                        if (!data.is_scanning) {
                            clearInterval(poll);
                            btn.disabled = false;
                            btn.innerHTML = '<span class="scan-icon">&#8635;</span> Scanner';
                            document.getElementById("scanning-indicator").style.display = "none";
                            loadAuctions();
                            loadStats();
                        }
                    });
            }, 3000);
        })
        .catch(() => {
            btn.disabled = false;
            btn.innerHTML = '<span class="scan-icon">&#8635;</span> Scanner';
            document.getElementById("scanning-indicator").style.display = "none";
        });
}

/**
 * Met a jour l'indicateur de scan.
 */
function updateScanStatus(data) {
    const indicator = document.getElementById("scanning-indicator");
    indicator.style.display = data.is_scanning ? "flex" : "none";
}

/**
 * Affiche la derniere mise a jour.
 */
function updateLastUpdate(timestamp) {
    const el = document.getElementById("last-update");
    if (!timestamp) {
        el.textContent = "Pas encore scanne";
        return;
    }
    try {
        const d = new Date(timestamp);
        el.textContent = `Maj: ${d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}`;
    } catch {
        el.textContent = "";
    }
}

/**
 * Affiche les erreurs de scan.
 */
function showErrors(errors) {
    const container = document.getElementById("errors-container");
    if (!errors || errors.length === 0) {
        container.style.display = "none";
        return;
    }
    container.style.display = "block";
    container.innerHTML = errors.map(e => `<div class="error-item">&#9888; ${escapeHtml(e)}</div>`).join("");
}

/**
 * Debounce pour la recherche.
 */
function debounceLoad() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(loadAuctions, 400);
}

/**
 * Echappe les caracteres HTML.
 */
function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
