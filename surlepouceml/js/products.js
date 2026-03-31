/* ═══════════════════════════════════════
   Sur Le Pouce ML — Product Catalog
   ═══════════════════════════════════════ */

const PRODUCTS = [
    // ── FORMULES ──
    { id:1, name:"Formule Solo", desc:"Sandwich + boisson + dessert", price:9.50, cat:"formule",
      img:"https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600", badge:"Populaire", badgeType:"populaire" },
    { id:2, name:"Formule Duo", desc:"2 sandwichs + 2 boissons", price:17.00, cat:"formule",
      img:"https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600" },
    { id:3, name:"Plateau Mezzé Solo", desc:"Assortiment mezzé froid 5 pièces + pain", price:12.00, cat:"formule",
      img:"https://images.unsplash.com/photo-1619941862585-cd4fa9a4c2cb?w=600", badge:"Fait Maison", badgeType:"fait-maison" },
    { id:4, name:"Plateau Mezzé Famille", desc:"Mezzé froid + chaud 10 pièces + pain", price:22.00, cat:"formule",
      img:"https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=600" },

    // ── SANDWICHS & BURGERS ──
    { id:10, name:"Chawarma Poulet", desc:"Poulet mariné, légumes frais, sauce yaourt", price:7.50, cat:"sandwich",
      img:"https://images.pexels.com/photos/5779787/pexels-photo-5779787.jpeg?auto=compress&cs=tinysrgb&w=600", badge:"Populaire", badgeType:"populaire" },
    { id:11, name:"Chawarma Veau", desc:"Veau aux épices, légumes, sauce ail", price:8.00, cat:"sandwich",
      img:"https://images.pexels.com/photos/5779787/pexels-photo-5779787.jpeg?auto=compress&cs=tinysrgb&w=600" },
    { id:12, name:"Burger Arménien", desc:"Steak haché épicé, fromage, oignons caramélisés", price:8.50, cat:"sandwich",
      img:"https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600", badge:"Nouveau", badgeType:"nouveau" },
    { id:13, name:"Kefta Sandwich", desc:"Brochette kefta, tomates, poivrons grillés", price:7.50, cat:"sandwich",
      img:"https://images.unsplash.com/photo-1694004602524-33c11ad120f2?w=600" },
    { id:14, name:"Végétarien Falafel", desc:"Falafel maison, hummus, salade fraîche", price:7.00, cat:"sandwich",
      img:"https://images.pexels.com/photos/6419753/pexels-photo-6419753.jpeg?auto=compress&cs=tinysrgb&w=600", badge:"Végétarien", badgeType:"vegetarien" },

    // ── SALADES & PÂTES ──
    { id:20, name:"Taboulé Maison", desc:"Taboulé arménien persillé, citron", price:5.50, cat:"salade",
      img:"https://images.unsplash.com/photo-1568897798550-91c8caffe391?w=600", badge:"Fait Maison", badgeType:"fait-maison" },
    { id:21, name:"Salade Grecque", desc:"Tomates, concombres, olives, feta", price:6.50, cat:"salade",
      img:"https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=600" },
    { id:22, name:"Salade César Poulet", desc:"Poulet grillé, parmesan, croûtons", price:7.50, cat:"salade",
      img:"https://images.unsplash.com/photo-1550304943-4f24f54ddde9?w=600" },
    { id:23, name:"Pâtes à la Féta", desc:"Pâtes fraîches, féta, tomates séchées", price:8.00, cat:"salade",
      img:"https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=600" },

    // ── SPÉCIALITÉS ARMÉNIENNES ──
    { id:30, name:"Dolmas (4 pcs)", desc:"Feuilles de vigne farcies riz et viande", price:6.50, cat:"armenien",
      img:"https://images.pexels.com/photos/6419747/pexels-photo-6419747.jpeg?auto=compress&cs=tinysrgb&w=600", badge:"Populaire", badgeType:"populaire" },
    { id:31, name:"Lahmajoun (2 pcs)", desc:"Pizza arménienne fine à la viande épicée", price:7.00, cat:"armenien",
      img:"https://images.pexels.com/photos/9609838/pexels-photo-9609838.jpeg?auto=compress&cs=tinysrgb&w=600", badge:"Populaire", badgeType:"populaire" },
    { id:32, name:"Börek Fromage", desc:"Feuilleté croustillant au fromage", price:5.50, cat:"armenien",
      img:"https://images.pexels.com/photos/8697541/pexels-photo-8697541.jpeg?auto=compress&cs=tinysrgb&w=600", badge:"Fait Maison", badgeType:"fait-maison" },
    { id:33, name:"Börek Épinards", desc:"Feuilleté croustillant aux épinards", price:5.50, cat:"armenien",
      img:"https://images.pexels.com/photos/8697541/pexels-photo-8697541.jpeg?auto=compress&cs=tinysrgb&w=600", badge:"Végétarien", badgeType:"vegetarien" },
    { id:34, name:"Manti", desc:"Raviolis arméniens bœuf, sauce yaourt-ail", price:9.00, cat:"armenien",
      img:"https://images.unsplash.com/photo-1616895427217-5318221a3e79?w=600" },
    { id:35, name:"Hummus Maison", desc:"Hummus crémeux, huile d'olive, paprika", price:4.50, cat:"armenien",
      img:"https://images.pexels.com/photos/1618898/pexels-photo-1618898.jpeg?auto=compress&cs=tinysrgb&w=600", badge:"Végétarien", badgeType:"vegetarien" },
    { id:36, name:"Mutabbal", desc:"Caviar d'aubergines grillées au tahini", price:4.50, cat:"armenien",
      img:"https://images.pexels.com/photos/5779787/pexels-photo-5779787.jpeg?auto=compress&cs=tinysrgb&w=600", badge:"Végétarien", badgeType:"vegetarien" },

    // ── ACCOMPAGNEMENTS ──
    { id:40, name:"Frites Maison", desc:"Frites dorées faites maison", price:3.00, cat:"accompagnement",
      img:"https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=600" },
    { id:41, name:"Pain Pita (2 pcs)", desc:"Pain pita chaud maison", price:2.00, cat:"accompagnement",
      img:"https://images.unsplash.com/photo-1586444248879-bc604bc77f34?w=600" },
    { id:42, name:"Riz Pilaf", desc:"Riz au beurre et vermicelles", price:3.50, cat:"accompagnement",
      img:"https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600" },
    { id:43, name:"Salade Verte", desc:"Salade verte assaisonnée", price:2.50, cat:"accompagnement",
      img:"https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600" },

    // ── DESSERTS ──
    { id:50, name:"Baklava (2 pcs)", desc:"Baklava au miel et aux noix", price:4.00, cat:"dessert",
      img:"https://images.pexels.com/photos/7250436/pexels-photo-7250436.jpeg?auto=compress&cs=tinysrgb&w=600", badge:"Fait Maison", badgeType:"fait-maison" },
    { id:51, name:"Gâteau Arménien", desc:"Part de gâteau tradition arménienne", price:3.50, cat:"dessert",
      img:"https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=600", badge:"Fait Maison", badgeType:"fait-maison" },
    { id:52, name:"Yaourt au Miel", desc:"Yaourt grec, miel de fleurs", price:3.00, cat:"dessert",
      img:"https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600" },
    { id:53, name:"Fruit de Saison", desc:"Selon arrivage du marché", price:2.00, cat:"dessert",
      img:"https://images.unsplash.com/photo-1619566636858-adf3ef46400b?w=600" },

    // ── BOISSONS ──
    { id:60, name:"Eau Minérale 50cl", desc:"Eau minérale naturelle", price:1.50, cat:"boisson",
      img:"https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=600" },
    { id:61, name:"Jus d'Orange", desc:"Jus d'orange frais", price:2.50, cat:"boisson",
      img:"https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=600" },
    { id:62, name:"Ayran", desc:"Boisson au yaourt salé traditionnelle", price:2.00, cat:"boisson",
      img:"https://images.pexels.com/photos/3622479/pexels-photo-3622479.jpeg?auto=compress&cs=tinysrgb&w=600" },
    { id:63, name:"Citronnade Menthe", desc:"Citronnade fraîche à la menthe", price:2.50, cat:"boisson",
      img:"https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=600" },
    { id:64, name:"Limonade Artisanale", desc:"Limonade faite maison", price:2.50, cat:"boisson",
      img:"https://images.unsplash.com/photo-1621263764928-df1444c5e859?w=600", badge:"Fait Maison", badgeType:"fait-maison" },
    { id:65, name:"Café Turc", desc:"Café traditionnel à la turque", price:2.00, cat:"boisson",
      img:"https://images.unsplash.com/photo-1506778020041-0ea35027d019?w=600" },
];

// Ingrédients par catégorie (ceux qu'on peut retirer)
const INGREDIENTS = {
    sandwich: ["Salade", "Tomates", "Oignons", "Sauce", "Cornichons", "Fromage"],
    formule:  ["Salade", "Tomates", "Oignons", "Sauce"],
    salade:   ["Oignons", "Olives", "Croûtons", "Fromage", "Sauce"],
    armenien: ["Oignons", "Persil", "Sauce yaourt", "Piment"],
    accompagnement: [],
    dessert:  [],
    boisson:  [],
};

// Suppléments disponibles (avec prix)
const SUPPLEMENTS = [
    { name:"Fromage", price:1.00 },
    { name:"Sauce supplémentaire", price:0.50 },
    { name:"Viande double", price:2.50 },
    { name:"Avocat", price:1.50 },
    { name:"Œuf", price:1.00 },
    { name:"Frites", price:1.50 },
    { name:"Piment", price:0.00 },
    { name:"Herbes fraîches", price:0.00 },
];
