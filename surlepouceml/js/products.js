/* ═══════════════════════════════════════
   Sur Le Pouce ML — Product Catalog
   All products with Unsplash images
   ═══════════════════════════════════════ */

const PRODUCTS = [
    // ── FORMULES ──
    { id:1, name:"Formule Solo", desc:"Sandwich + boisson + dessert", price:9.50, cat:"formule",
      img:"https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600", badge:"Populaire", badgeType:"populaire" },
    { id:2, name:"Formule Duo", desc:"2 sandwichs + 2 boissons", price:17.00, cat:"formule",
      img:"https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600" },
    { id:3, name:"Plateau Mezzé Solo", desc:"Assortiment mezzé froid 5 pièces + pain", price:12.00, cat:"formule",
      img:"https://images.unsplash.com/photo-1541614101331-1a5a3a194e92?w=600", badge:"Fait Maison", badgeType:"fait-maison" },
    { id:4, name:"Plateau Mezzé Famille", desc:"Mezzé froid + chaud 10 pièces + pain", price:22.00, cat:"formule",
      img:"https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=600" },

    // ── SANDWICHS & BURGERS ──
    { id:10, name:"Chawarma Poulet", desc:"Poulet mariné, légumes frais, sauce yaourt", price:7.50, cat:"sandwich",
      img:"https://images.unsplash.com/photo-1561043433-aaf687c4cf04?w=600", badge:"Populaire", badgeType:"populaire" },
    { id:11, name:"Chawarma Veau", desc:"Veau aux épices, légumes, sauce ail", price:8.00, cat:"sandwich",
      img:"https://images.unsplash.com/photo-1529006557810-274b9b2fc783?w=600" },
    { id:12, name:"Burger Arménien", desc:"Steak haché épicé, fromage, oignons caramélisés", price:8.50, cat:"sandwich",
      img:"https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600", badge:"Nouveau", badgeType:"nouveau" },
    { id:13, name:"Kefta Sandwich", desc:"Brochette kefta, tomates, poivrons grillés", price:7.50, cat:"sandwich",
      img:"https://images.unsplash.com/photo-1600891964092-4316c288032e?w=600" },
    { id:14, name:"Végétarien Falafel", desc:"Falafel maison, hummus, salade fraîche", price:7.00, cat:"sandwich",
      img:"https://images.unsplash.com/photo-1593001872095-7d5b3868fb1d?w=600", badge:"Végétarien", badgeType:"vegetarien" },

    // ── SALADES & PÂTES ──
    { id:20, name:"Taboulé Maison", desc:"Taboulé arménien persillé, citron", price:5.50, cat:"salade",
      img:"https://images.unsplash.com/photo-1505253716362-afaea1d3d1af?w=600", badge:"Fait Maison", badgeType:"fait-maison" },
    { id:21, name:"Salade Grecque", desc:"Tomates, concombres, olives, feta", price:6.50, cat:"salade",
      img:"https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=600" },
    { id:22, name:"Salade César Poulet", desc:"Poulet grillé, parmesan, croûtons", price:7.50, cat:"salade",
      img:"https://images.unsplash.com/photo-1550304943-4f24f54ddde9?w=600" },
    { id:23, name:"Pâtes à la Féta", desc:"Pâtes fraîches, féta, tomates séchées", price:8.00, cat:"salade",
      img:"https://images.unsplash.com/photo-1473093295043-cdd812d0e601?w=600" },

    // ── SPÉCIALITÉS ARMÉNIENNES ──
    { id:30, name:"Dolmas (4 pcs)", desc:"Feuilles de vigne farcies riz et viande", price:6.50, cat:"armenien",
      img:"https://images.unsplash.com/photo-1621852004158-f3bc188ace2d?w=600", badge:"Populaire", badgeType:"populaire" },
    { id:31, name:"Lahmajoun (2 pcs)", desc:"Pizza arménienne à la viande épicée", price:7.00, cat:"armenien",
      img:"https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600", badge:"Populaire", badgeType:"populaire" },
    { id:32, name:"Börek Fromage", desc:"Feuilleté croustillant au fromage", price:5.50, cat:"armenien",
      img:"https://images.unsplash.com/photo-1598103442097-8b74394b95c3?w=600", badge:"Fait Maison", badgeType:"fait-maison" },
    { id:33, name:"Börek Épinards", desc:"Feuilleté croustillant aux épinards", price:5.50, cat:"armenien",
      img:"https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=600", badge:"Végétarien", badgeType:"vegetarien" },
    { id:34, name:"Manti", desc:"Raviolis arméniens bœuf, sauce yaourt-ail", price:9.00, cat:"armenien",
      img:"https://images.unsplash.com/photo-1563245372-f21724e3856d?w=600" },
    { id:35, name:"Hummus Maison", desc:"Hummus huile d'olive, paprika", price:4.50, cat:"armenien",
      img:"https://images.unsplash.com/photo-1576169498584-4f353c1f67d6?w=600", badge:"Végétarien", badgeType:"vegetarien" },
    { id:36, name:"Mutabbal", desc:"Caviar d'aubergines grillées", price:4.50, cat:"armenien",
      img:"https://images.unsplash.com/photo-1604152135912-04a022e23696?w=600", badge:"Végétarien", badgeType:"vegetarien" },

    // ── ACCOMPAGNEMENTS ──
    { id:40, name:"Frites Maison", desc:"Frites dorées faites maison", price:3.00, cat:"accompagnement",
      img:"https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=600" },
    { id:41, name:"Pain Pita (2 pcs)", desc:"Pain pita chaud maison", price:2.00, cat:"accompagnement",
      img:"https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600" },
    { id:42, name:"Riz Pilaf", desc:"Riz au beurre et vermicelles", price:3.50, cat:"accompagnement",
      img:"https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600" },
    { id:43, name:"Salade Verte", desc:"Salade verte assaisonnée", price:2.50, cat:"accompagnement",
      img:"https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600" },

    // ── DESSERTS ──
    { id:50, name:"Baklava (2 pcs)", desc:"Baklava au miel et aux noix", price:4.00, cat:"dessert",
      img:"https://images.unsplash.com/photo-1519676867240-f03562e64548?w=600", badge:"Fait Maison", badgeType:"fait-maison" },
    { id:51, name:"Gâteau Arménien", desc:"Part de gâteau tradition arménienne", price:3.50, cat:"dessert",
      img:"https://images.unsplash.com/photo-1563729784474-d77dbb933a9e?w=600", badge:"Fait Maison", badgeType:"fait-maison" },
    { id:52, name:"Yaourt au Miel", desc:"Yaourt grec, miel de fleurs", price:3.00, cat:"dessert",
      img:"https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600" },
    { id:53, name:"Fruit de Saison", desc:"Selon arrivage du marché", price:2.00, cat:"dessert",
      img:"https://images.unsplash.com/photo-1568702846914-96b305d2aaeb?w=600" },

    // ── BOISSONS ──
    { id:60, name:"Eau Minérale 50cl", desc:"Eau minérale naturelle", price:1.50, cat:"boisson",
      img:"https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=600" },
    { id:61, name:"Jus d'Orange", desc:"Jus d'orange pressé", price:2.50, cat:"boisson",
      img:"https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=600" },
    { id:62, name:"Ayran", desc:"Yaourt salé traditionnel arménien", price:2.00, cat:"boisson",
      img:"https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=600" },
    { id:63, name:"Citronnade Menthe", desc:"Citronnade fraîche à la menthe", price:2.50, cat:"boisson",
      img:"https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=600" },
    { id:64, name:"Limonade Artisanale", desc:"Limonade faite maison", price:2.50, cat:"boisson",
      img:"https://images.unsplash.com/photo-1621263764928-df1444c5e859?w=600", badge:"Fait Maison", badgeType:"fait-maison" },
    { id:65, name:"Café Turc", desc:"Café traditionnel turc", price:2.00, cat:"boisson",
      img:"https://images.unsplash.com/photo-1578374173713-64a3f4b73f9e?w=600" },
];
