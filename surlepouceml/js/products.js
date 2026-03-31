// ========================================
// Sur Le Pouce ML - Product Catalog
// Real menu data from restaurant
// ========================================

const PRODUCTS = [
    // ---- FORMULES ----
    { id: 1, name: "Plat du Jour", desc: "Chaque jour, un plat du jour entierement fait maison", price: 11.00, category: "formule", emoji: "🍽️", badge: "Fait Maison" },
    { id: 2, name: "Formule Sandwich", desc: "Sandwich froid ou chaud + Boisson + Dessert", price: 3.50, category: "formule", emoji: "🥪", note: "Supplement sandwich" },
    { id: 3, name: "Formule Mezzes", desc: "Taboulé, feuilles de vigne, beurek, hamous, caviar d'aubergine, pain libanais, dessert", price: 13.00, category: "formule", emoji: "🥙", badge: "Populaire" },
    { id: 4, name: "Formule Plat du Jour Complet", desc: "Plat du jour + Boisson + Dessert", price: 14.50, category: "formule", emoji: "🍛" },
    { id: 5, name: "Formule Salade", desc: "Salade + Boisson + Dessert", price: 12.00, category: "formule", emoji: "🥗" },
    { id: 6, name: "Formule Pates", desc: "Pates + Boisson + Dessert", price: 11.50, category: "formule", emoji: "🍝" },
    { id: 7, name: "Formule Burger", desc: "Burger + Boisson + Dessert", price: 12.50, category: "formule", emoji: "🍔" },
    { id: 8, name: "Formule Wrap Froid", desc: "Wrap froid + Boisson + Dessert", price: 10.00, category: "formule", emoji: "🌯" },

    // ---- SANDWICHS FROIDS ----
    { id: 10, name: "Jambon Beurre", desc: "Sandwich classique jambon beurre", price: 5.00, category: "sandwich", emoji: "🥖" },
    { id: 11, name: "Saucisson", desc: "Saucisson, salade, fromage", price: 5.50, category: "sandwich", emoji: "🥖" },
    { id: 12, name: "Jambon Cru", desc: "Jambon cru, tomates, mozza, salade", price: 6.50, category: "sandwich", emoji: "🥖" },
    { id: 13, name: "Pain Bagnat", desc: "Salade, tomates, thon, oeuf, olives", price: 6.50, category: "sandwich", emoji: "🥖", badge: "Best-seller" },
    { id: 14, name: "Wrap Poulet", desc: "Dans le pain armenien lavache : poulet, oeuf, carottes, mayo, aneth, cebettes, coriandre", price: 6.50, category: "sandwich", emoji: "🌯" },
    { id: 15, name: "Wrap Falafel", desc: "Dans le pain armenien lavache : falafel, crudites, sauce", price: 6.50, category: "sandwich", emoji: "🌯" },
    { id: 16, name: "Poulet Parmesan", desc: "Salade, tomates, poulet et parmesan", price: 7.50, category: "sandwich", emoji: "🥖" },

    // ---- SANDWICHS CHAUDS ----
    { id: 20, name: "Steak Bouchere Frites", desc: "Steak bouchere 150g avec frites", price: 8.50, category: "sandwich", emoji: "🥩", badge: "Chaud" },
    { id: 21, name: "Hot Dog", desc: "Hot dog classique", price: 6.50, category: "sandwich", emoji: "🌭", badge: "Chaud" },
    { id: 22, name: "Escalope Poulet Pane Frites", desc: "Escalope de poulet panee avec frites", price: 8.50, category: "sandwich", emoji: "🍗", badge: "Chaud" },
    { id: 23, name: "Doner Kebab Frites", desc: "Salade, tomates - pain lavache ou baguette", price: 7.50, category: "sandwich", emoji: "🥙", badge: "Chaud" },
    { id: 24, name: "Keufte Frites", desc: "Keufte avec frites, salade, tomates", price: 7.50, category: "sandwich", emoji: "🥙", badge: "Chaud" },
    { id: 25, name: "Wrap Poulet Chaud", desc: "Blanc de poulet, salade, tomates, fromage", price: 8.00, category: "sandwich", emoji: "🌯", badge: "Chaud" },
    { id: 26, name: "Barquette de Frites", desc: "Portion de frites maison", price: 2.50, category: "accompagnement", emoji: "🍟" },
    { id: 27, name: "Doner Falafel", desc: "Falafel en doner avec garnitures", price: 7.50, category: "sandwich", emoji: "🥙", badge: "Chaud" },

    // ---- PANINIS ----
    { id: 30, name: "Panini Omelette", desc: "Omelette, gruyere, tomates", price: 6.50, category: "sandwich", emoji: "🫓" },
    { id: 31, name: "Panini Tomates Mozza", desc: "Tomates, mozza, huile d'olive", price: 6.00, category: "sandwich", emoji: "🫓" },
    { id: 32, name: "Panini Jambon Cru Chevre", desc: "Jambon cru, chevre", price: 6.50, category: "sandwich", emoji: "🫓" },
    { id: 33, name: "Panini Aubergine Mozza", desc: "Aubergine, tomates, mozza", price: 7.00, category: "sandwich", emoji: "🫓" },

    // ---- BURGERS ----
    { id: 35, name: "Burger Classique", desc: "Salade, oignons rouges, tomates, fromage, cornichons, steak bouchere 130g", price: 9.00, category: "sandwich", emoji: "🍔" },
    { id: 36, name: "Burger Falafel", desc: "Burger au falafel fait maison", price: 9.00, category: "sandwich", emoji: "🍔" },

    // ---- SALADES ----
    { id: 40, name: "Salade Italienne", desc: "Salade, tomates, mozza, basilic", price: 8.50, category: "plat", emoji: "🥗" },
    { id: 41, name: "Salade Pouce", desc: "Salade, tomates, crouton, chevre chaud, oeuf", price: 8.50, category: "plat", emoji: "🥗" },
    { id: 42, name: "Salade Cesar", desc: "Salade, tomates, poulet, parmesan, crouton, olives", price: 8.50, category: "plat", emoji: "🥗" },
    { id: 43, name: "Salade Pate", desc: "Salade, pate, tomates, olives, thon ou poulet", price: 8.50, category: "plat", emoji: "🥗" },
    { id: 44, name: "Salade Riz", desc: "Riz, mais, thon, poivron", price: 8.50, category: "plat", emoji: "🥗" },
    { id: 45, name: "Salade Gastronomique", desc: "Notre salade signature avec ingredients premium", price: 9.00, category: "plat", emoji: "🥗", badge: "Premium" },
    { id: 46, name: "Salade Composee (4 au choix)", desc: "Betteraves, carottes rapees, aubergine poivrons, taboulé, pois chiches, tomates concombres", price: 9.00, category: "plat", emoji: "🥗" },

    // ---- PATES ----
    { id: 50, name: "Penne Rigate Pistou", desc: "Penne rigate sauce pistou maison", price: 8.00, category: "plat", emoji: "🍝" },
    { id: 51, name: "Penne Rigate Bolognaise", desc: "Penne rigate sauce bolognaise maison", price: 8.00, category: "plat", emoji: "🍝" },
    { id: 52, name: "Penne Rigate Carbonara", desc: "Penne rigate sauce carbonara maison", price: 8.00, category: "plat", emoji: "🍝" },

    // ---- SPECIALITES ARMENIENNES SALEES ----
    { id: 60, name: "Lahmajoun", desc: "Pizza armenienne traditionnelle", price: 2.50, category: "mezze", emoji: "🫓", badge: "Armenien" },
    { id: 61, name: "Beurek Fromage", desc: "Beurek au fromage en pate filo", price: 2.00, category: "mezze", emoji: "🥟", badge: "Armenien" },
    { id: 62, name: "Beurek Viande", desc: "Beurek a la viande en pate filo", price: 2.00, category: "mezze", emoji: "🥟", badge: "Armenien" },
    { id: 63, name: "Pizza Fromage", desc: "Pizza au fromage", price: 2.50, category: "mezze", emoji: "🍕" },
    { id: 64, name: "Crepe a la Viande", desc: "Crepe farcie a la viande", price: 2.50, category: "mezze", emoji: "🫓", badge: "Armenien" },

    // ---- SPECIALITES SUCREES ----
    { id: 70, name: "Baklava", desc: "Patisserie feuilletee aux noix et miel", price: 2.20, category: "dessert", emoji: "🍯", badge: "Armenien" },
    { id: 71, name: "Sare Bourma", desc: "Rouleau feuillete aux noix - la portion", price: 2.20, category: "dessert", emoji: "🍯", badge: "Armenien" },
    { id: 72, name: "Kadaif", desc: "Patisserie aux cheveux d'ange et noix - la portion", price: 2.20, category: "dessert", emoji: "🍯", badge: "Armenien" },
    { id: 73, name: "Gata", desc: "Farcie de noix et cassonade", price: 2.20, category: "dessert", emoji: "🍪", badge: "Armenien" },
    { id: 74, name: "Cigarette", desc: "Farcie de noix, raisin sec, cannelle, cassonade", price: 2.20, category: "dessert", emoji: "🍪", badge: "Armenien" },
    { id: 75, name: "Kourabia (par 3)", desc: "Sables armeniens traditionnels", price: 2.20, category: "dessert", emoji: "🍪", badge: "Armenien" },
    { id: 76, name: "Tcheurek", desc: "Brioche armenienne traditionnelle", price: 2.20, category: "dessert", emoji: "🍞", badge: "Armenien" },

    // ---- DESSERTS ----
    { id: 80, name: "Panacotta", desc: "Panacotta maison", price: 3.00, category: "dessert", emoji: "🍮" },
    { id: 81, name: "Tiramisu au Cafe", desc: "Tiramisu au cafe fait maison", price: 3.00, category: "dessert", emoji: "🍰" },
    { id: 82, name: "Salade de Fruits", desc: "Salade de fruits frais de saison", price: 3.00, category: "dessert", emoji: "🍓" },
    { id: 83, name: "Yaourt", desc: "Yaourt nature", price: 2.20, category: "dessert", emoji: "🥛" },
    { id: 84, name: "Gateau au Yaourt", desc: "Gateau au yaourt fait maison", price: 2.20, category: "dessert", emoji: "🍰" },

    // ---- BOISSONS ----
    { id: 90, name: "Cafe", desc: "Cafe expresso", price: 2.00, category: "boisson", emoji: "☕" },
    { id: 91, name: "Chocolat Chaud", desc: "Chocolat chaud onctueux", price: 2.50, category: "boisson", emoji: "☕" },
    { id: 92, name: "Cappuccino", desc: "Cappuccino cremeux", price: 2.50, category: "boisson", emoji: "☕" },
    { id: 93, name: "Coca-Cola 33cl", desc: "Coca-Cola classique", price: 1.90, category: "boisson", emoji: "🥤" },
    { id: 94, name: "Coca Zero 33cl", desc: "Coca-Cola Zero sucre", price: 1.90, category: "boisson", emoji: "🥤" },
    { id: 95, name: "Orangina 33cl", desc: "Orangina", price: 1.90, category: "boisson", emoji: "🥤" },
    { id: 96, name: "Oasis 33cl", desc: "Oasis tropical", price: 1.90, category: "boisson", emoji: "🥤" },
    { id: 97, name: "Ice Tea 33cl", desc: "Ice Tea peche", price: 1.90, category: "boisson", emoji: "🥤" },
    { id: 98, name: "Sprite 33cl", desc: "Sprite", price: 1.90, category: "boisson", emoji: "🥤" },
    { id: 99, name: "Fanta 33cl", desc: "Fanta orange", price: 1.90, category: "boisson", emoji: "🥤" },
    { id: 100, name: "Biere", desc: "Biere pression", price: 2.50, category: "boisson", emoji: "🍺" },
    { id: 101, name: "Eau", desc: "Bouteille d'eau minerale", price: 1.50, category: "boisson", emoji: "💧" },
    { id: 102, name: "Pago", desc: "Jus de fruits Pago", price: 2.50, category: "boisson", emoji: "🧃" },

    // ---- ACCOMPAGNEMENTS ----
    { id: 110, name: "Supplement Frites", desc: "Frites en supplement pour sandwich", price: 1.50, category: "accompagnement", emoji: "🍟" },
];

// Category display names
const CATEGORY_LABELS = {
    all: "Tous",
    formule: "Formules",
    mezze: "Mezzes & Specialites",
    plat: "Salades & Plats",
    sandwich: "Sandwichs & Burgers",
    accompagnement: "Accompagnements",
    dessert: "Desserts & Patisseries",
    boisson: "Boissons"
};
