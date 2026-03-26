import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, Cell } from "recharts";

// Mapping type de bien vers les paramètres de chaque plateforme
const LBC_TYPES = {"Maison":"1","Terrain":"4","Local commercial":"6","Parking":"3","Immeuble":"6","Appartement":"2"};
const PAP_TYPES = {"Maison":"maison","Terrain":"terrain","Local commercial":"local-commercial","Parking":"parking","Immeuble":"immeuble","Appartement":"appartement"};
const SELOGER_TYPES = {"Maison":"bien-maison","Terrain":"bien-terrain","Local commercial":"bien-local-commercial","Parking":"bien-parking","Immeuble":"bien-immeuble","Appartement":"bien-appartement"};
const BIENICI_TYPES = {"Maison":"maison","Terrain":"terrain","Local commercial":"local","Parking":"parking","Immeuble":"immeuble","Appartement":"appartement"};

// Génère l'URL de recherche réelle ciblée selon la source, le type, le prix et la surface
const buildSourceUrl = (source, ville, cp, type, prix, surface) => {
  const slug = ville.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/\s+/g,"-").replace(/'/g,"-");
  const prixMin = Math.round(prix * 0.8);
  const prixMax = Math.round(prix * 1.2);
  const surfMin = Math.round(surface * 0.8);
  const surfMax = Math.round(surface * 1.2);
  switch(source) {
    case "LeBonCoin": {
      const t = LBC_TYPES[type] || "1";
      return `https://www.leboncoin.fr/recherche?category=9&locations=${encodeURIComponent(ville)}__${cp}&real_estate_type=${t}&price=${prixMin}-${prixMax}&square=${surfMin}-${surfMax}`;
    }
    case "SeLoger": {
      const t = SELOGER_TYPES[type] || "";
      return `https://www.seloger.com/immobilier/achat/immo-${slug}-${cp.substring(0,2)}/${t}/?prix=${prixMin}_${prixMax}&surface=${surfMin}_${surfMax}`;
    }
    case "PAP": {
      const t = PAP_TYPES[type] || "immobilier";
      return `https://www.pap.fr/annonce/vente-${t}-${slug}-${cp}-g${cp}-du-${prixMin}-au-${prixMax}-euros-a-partir-de-${surfMin}-m2`;
    }
    case "BienIci": {
      const t = BIENICI_TYPES[type] || "";
      return `https://www.bienici.com/recherche/achat/${slug}-${cp}/${t}?prix-min=${prixMin}&prix-max=${prixMax}&surface-min=${surfMin}`;
    }
    default: return "#";
  }
};

const ANNONCES = [
  { id:1, score:91, niveau:"OPPORTUNITE EXCEPTIONNELLE", type:"Maison", ville:"Vitrolles", cp:"13127", prix:187000, surface:112, terrain:420, pieces:5, prix_m2:1669, median_m2:2450, decote:31.9, source:"LeBonCoin", vendeur:"particulier", age:"38min", dpe:"D", mots:["succession","urgent"], statut:"nouveau", est_enchere:false },
  { id:2, score:84, niveau:"OPPORTUNITE EXCEPTIONNELLE", type:"Terrain", ville:"Marignane", cp:"13700", prix:95000, surface:1200, terrain:1200, pieces:null, prix_m2:79, median_m2:130, decote:39.2, source:"PAP", vendeur:"particulier", age:"1h12", dpe:null, mots:["mutation","vente rapide"], statut:"nouveau", est_enchere:false },
  { id:3, score:79, niveau:"FORTE OPPORTUNITE", type:"Maison", ville:"Gignac-la-Nerthe", cp:"13180", prix:265000, surface:135, terrain:600, pieces:6, prix_m2:1963, median_m2:2680, decote:26.8, source:"SeLoger", vendeur:"agence", age:"2h05", dpe:"E", mots:["travaux","à rénover"], statut:"nouveau", est_enchere:false },
  { id:4, score:88, niveau:"OPPORTUNITE EXCEPTIONNELLE", type:"Local commercial", ville:"Marseille 14e", cp:"13014", prix:142000, surface:85, terrain:null, pieces:null, prix_m2:1671, median_m2:2200, decote:24.0, source:"BienIci", vendeur:"particulier", age:"47min", dpe:"F", mots:["divorce","urgent"], statut:"nouveau", est_enchere:false },
  { id:5, score:95, niveau:"OPPORTUNITE EXCEPTIONNELLE", type:"Maison", ville:"Les Pennes-Mirabeau", cp:"13170", prix:310000, surface:158, terrain:850, pieces:7, prix_m2:1962, median_m2:3100, decote:36.7, source:"LeBonCoin", vendeur:"particulier", age:"12min", dpe:"C", mots:["succession","liquidation"], statut:"nouveau", est_enchere:true },
  { id:6, score:67, niveau:"FORTE OPPORTUNITE", type:"Maison", ville:"Rognac", cp:"13340", prix:298000, surface:140, terrain:380, pieces:5, prix_m2:2129, median_m2:2750, decote:22.6, source:"SeLoger", vendeur:"agence", age:"4h30", dpe:"D", mots:["baisse de prix"], statut:"en_cours", est_enchere:false },
  { id:7, score:72, niveau:"FORTE OPPORTUNITE", type:"Parking", ville:"Marseille 2e", cp:"13002", prix:8500, surface:12, terrain:null, pieces:null, prix_m2:708, median_m2:1000, decote:29.2, source:"PAP", vendeur:"particulier", age:"3h20", dpe:null, mots:["urgent"], statut:"nouveau", est_enchere:false },
  { id:8, score:58, niveau:"OPPORTUNITE", type:"Terrain", ville:"Carry-le-Rouet", cp:"13620", prix:185000, surface:780, terrain:780, pieces:null, prix_m2:237, median_m2:310, decote:23.5, source:"BienIci", vendeur:"agence", age:"6h00", dpe:null, mots:["à saisir"], statut:"nouveau", est_enchere:false },
  { id:9, score:62, niveau:"FORTE OPPORTUNITE", type:"Immeuble", ville:"Marseille 3e", cp:"13003", prix:520000, surface:280, terrain:null, pieces:8, prix_m2:1857, median_m2:2400, decote:22.6, source:"SeLoger", vendeur:"agence", age:"5h15", dpe:"E", mots:["travaux"], statut:"traite", est_enchere:false },
  { id:10, score:44, niveau:"A SURVEILLER", type:"Maison", ville:"Chateauneuf-les-Martigues", cp:"13220", prix:340000, surface:148, terrain:500, pieces:6, prix_m2:2297, median_m2:2600, decote:11.7, source:"LeBonCoin", vendeur:"particulier", age:"8h45", dpe:"C", mots:[], statut:"nouveau", est_enchere:false },
  { id:11, score:76, niveau:"FORTE OPPORTUNITE", type:"Local commercial", ville:"Aix-en-Provence", cp:"13100", prix:198000, surface:110, terrain:null, pieces:null, prix_m2:1800, median_m2:2500, decote:28.0, source:"PAP", vendeur:"particulier", age:"1h55", dpe:"D", mots:["divorce","vente rapide"], statut:"nouveau", est_enchere:false },
].map(a => ({...a, url: buildSourceUrl(a.source, a.ville, a.cp, a.type, a.prix, a.surface)}));

const ENCHERES = [
  { id:1, type:"JUDICIAIRE", bien:"Maison T5 - 127m²", ville:"Vitrolles", cp:"13127", mise_a_prix:155000, estimation:280000, decote_potentielle:44.6, date_audience:new Date(Date.now()+3*24*3600*1000), tribunal:"TJ Aix-en-Provence", avocat:"Me. Rousseau", rg:"2024/00342", visites:"14 et 21 mars 14h-16h", score:94, surface:127, terrain:320 },
  { id:2, type:"NOTARIALE", bien:"Terrain constructible - 900m²", ville:"Marignane", cp:"13700", mise_a_prix:68000, estimation:135000, decote_potentielle:49.6, date_audience:new Date(Date.now()+8*24*3600*1000), tribunal:"Chambre Notaires 13", avocat:"Me. Fontaine", rg:"NOT-2024-1189", visites:"Sur RDV", score:87, surface:900, terrain:900 },
  { id:3, type:"JUDICIAIRE", bien:"Appartement T4 - 89m² + cave", ville:"Marseille 8e", cp:"13008", mise_a_prix:120000, estimation:210000, decote_potentielle:42.9, date_audience:new Date(Date.now()+14*24*3600*1000), tribunal:"TJ Marseille", avocat:"Me. Benedetti", rg:"2024/00891", visites:"Non communiquées", score:78, surface:89, terrain:null },
  { id:4, type:"NOTARIALE", bien:"Local commercial - 220m²", ville:"Aix-en-Provence", cp:"13100", mise_a_prix:245000, estimation:410000, decote_potentielle:40.2, date_audience:new Date(Date.now()+21*24*3600*1000), tribunal:"Chambre Notaires 13", avocat:"Me. Luccioni", rg:"NOT-2024-2201", visites:"12 et 19 mars 10h-12h", score:71, surface:220, terrain:null },
  { id:5, type:"JUDICIAIRE", bien:"Maison T4 - 98m² + garage", ville:"Berre-l'Etang", cp:"13130", mise_a_prix:89000, estimation:195000, decote_potentielle:54.4, date_audience:new Date(Date.now()+5*24*3600*1000), tribunal:"TJ Aix-en-Provence", avocat:"Me. Hernandez", rg:"2024/01102", visites:"Non autorisées (occupé)", score:82, surface:98, terrain:180 },
];

const STATS_SEMAINE = [
  { jour:"Lun", annonces:312, opportunites:8 },
  { jour:"Mar", annonces:287, opportunites:11 },
  { jour:"Mer", annonces:401, opportunites:14 },
  { jour:"Jeu", annonces:356, opportunites:9 },
  { jour:"Ven", annonces:498, opportunites:18 },
  { jour:"Sam", annonces:623, opportunites:22 },
  { jour:"Dim", annonces:189, opportunites:6 },
];

const PRIX_COMMUNES = [
  { ville:"Marseille", m2:2310 }, { ville:"Aix-en-Provence", m2:3450 }, { ville:"Marignane", m2:2180 },
  { ville:"Vitrolles", m2:2450 }, { ville:"Les Pennes", m2:3100 }, { ville:"Martigues", m2:2050 },
  { ville:"Gignac", m2:2680 }, { ville:"Rognac", m2:2750 },
];

const fmtPrix = (n) => n >= 1000000 ? (n/1000000).toFixed(2)+"M€" : n >= 1000 ? Math.round(n/1000)+"K€" : n+"€";
const fmtM2 = (n) => n ? Math.round(n)+"€/m²" : "-";
const scoreColor = (s) => { if (s>=80) return "#00ff88"; if (s>=65) return "#ffb300"; if (s>=50) return "#ff8c00"; return "#64748b"; };
const scoreBg = (s) => { if (s>=80) return "rgba(0,255,136,0.12)"; if (s>=65) return "rgba(255,179,0,0.12)"; if (s>=50) return "rgba(255,140,0,0.12)"; return "rgba(100,116,139,0.1)"; };
const niveauShort = (n) => { if (n==="OPPORTUNITE EXCEPTIONNELLE") return "EXCEPT."; if (n==="FORTE OPPORTUNITE") return "FORTE"; if (n==="OPPORTUNITE") return "OPPORT."; return "SURV."; };
const joursAvant = (d) => Math.ceil((d - Date.now()) / (1000*3600*24));

function InfoBulle({ text, children }) {
  const [show, setShow] = useState(false);
  return (
    <span style={{position:"relative",display:"inline-flex",alignItems:"center"}} onMouseEnter={()=>setShow(true)} onMouseLeave={()=>setShow(false)}>
      {children}
      {show && (
        <div style={{position:"absolute",bottom:"calc(100% + 8px)",left:"50%",transform:"translateX(-50%)",background:"#0a1e38",border:"1px solid #1a4070",borderRadius:"4px",padding:"8px 12px",color:"#c8d8e8",fontSize:"11px",lineHeight:1.5,whiteSpace:"normal",width:"260px",zIndex:1000,boxShadow:"0 4px 20px rgba(0,0,0,0.5)",pointerEvents:"none"}}>
          {text}
          <div style={{position:"absolute",bottom:"-5px",left:"50%",transform:"translateX(-50%) rotate(45deg)",width:"8px",height:"8px",background:"#0a1e38",borderRight:"1px solid #1a4070",borderBottom:"1px solid #1a4070"}}/>
        </div>
      )}
    </span>
  );
}

function HelpIcon({ text }) {
  return (
    <InfoBulle text={text}>
      <span style={{display:"inline-flex",alignItems:"center",justifyContent:"center",width:"14px",height:"14px",borderRadius:"50%",background:"rgba(96,184,255,0.1)",border:"1px solid #1a4070",color:"#60b8ff",fontSize:"9px",cursor:"help",marginLeft:"4px",flexShrink:0}}>?</span>
    </InfoBulle>
  );
}

function FluxTab({ S, colTpl, filtreType, setFiltreType, filtreScore, setFiltreScore, filtreVendeur, setFiltreVendeur, filtreFraicheur, setFiltreFraicheur, filteredAnnonces, selectedRow, setSelectedRow, handleStatut }) {
  return (
    <div className="si">
      {/* FILTRES */}
      <div style={{display:"flex",gap:"8px",marginBottom:"12px",flexWrap:"wrap",alignItems:"center"}}>
        <InfoBulle text="Filtrer par type de bien immobilier"><span style={{color:"#2a4060",fontSize:"10px",cursor:"help"}}>TYPE</span></InfoBulle>
        {[["tous","TOUS"],["maison","MAISONS"],["terrain","TERRAINS"],["local_commercial","LOCAUX"],["parking","PARKINGS"],["immeuble","IMMEUBLES"]].map(([v,l])=>(
          <button key={v} className={`fb ${filtreType===v?"on":""}`} onClick={()=>setFiltreType(v)}>{l}</button>
        ))}
        <div style={{width:"1px",height:"16px",background:"#0d2040",margin:"0 4px"}}/>
        <InfoBulle text="Filtrer par score minimum. >80 = exceptionnelles, >65 = fortes opportunités, >50 = à surveiller"><span style={{color:"#2a4060",fontSize:"10px",cursor:"help"}}>SCORE</span></InfoBulle>
        {[[0,"TOUS"],[50,">50"],[65,">65"],[80,">80"]].map(([v,l])=>(
          <button key={v} className={`fb ${filtreScore===v?"on":""}`} onClick={()=>setFiltreScore(v)}>{l}</button>
        ))}
        <div style={{width:"1px",height:"16px",background:"#0d2040",margin:"0 4px"}}/>
        <InfoBulle text="Filtrer par type de vendeur. Les particuliers offrent souvent de meilleures marges de négociation que les agences."><span style={{color:"#2a4060",fontSize:"10px",cursor:"help"}}>VENDEUR</span></InfoBulle>
        {[["tous","TOUS"],["particulier","PARTIC."],["agence","AGENCE"]].map(([v,l])=>(
          <button key={v} className={`fb ${filtreVendeur===v?"on":""}`} onClick={()=>setFiltreVendeur(v)}>{l}</button>
        ))}
        <div style={{width:"1px",height:"16px",background:"#0d2040",margin:"0 4px"}}/>
        <InfoBulle text="Filtrer par ancienneté de publication. Les annonces de moins d'1h sont les plus intéressantes : moins de concurrence."><span style={{color:"#2a4060",fontSize:"10px",cursor:"help"}}>FRAICHEUR</span></InfoBulle>
        {[["tous","TOUS"],["1h","< 1H"],["24h","< 24H"]].map(([v,l])=>(
          <button key={v} className={`fb ${filtreFraicheur===v?"on":""}`} onClick={()=>setFiltreFraicheur(v)}>{l}</button>
        ))}
        <div style={{marginLeft:"auto",color:"#2a4060",fontSize:"10px"}}>{filteredAnnonces.length} résultats</div>
      </div>

      {/* TABLE */}
      <div style={{background:"#030c18",border:"1px solid #0d2040",borderRadius:"3px",overflow:"auto"}}>
        <div style={{display:"grid",gridTemplateColumns:colTpl,background:"#020810",borderBottom:"1px solid #0d2040",padding:"6px 0",minWidth:"1100px"}}>
          {[
            {h:"SCORE",tip:"Score d'opportunité de 0 à 100. Calculé automatiquement selon la décote, les mots-clés, le type de vendeur, la fraîcheur et le DPE."},
            {h:"NIVEAU",tip:"Niveau d'opportunité : EXCEPT. (≥80), FORTE (≥65), OPPORT. (≥50), SURV. (<50). Plus le score est élevé, plus l'affaire est intéressante."},
            {h:"TYPE",tip:"Type de bien immobilier : Maison, Terrain, Local commercial, Parking, Immeuble. L'icône ⚡ indique un bien aussi en vente aux enchères."},
            {h:"VILLE",tip:"Commune où se situe le bien. Le bot surveille 45 communes dans un rayon de 30km autour des Pennes-Mirabeau."},
            {h:"CP",tip:"Code postal de la commune."},
            {h:"PRIX",tip:"Prix de vente affiché sur l'annonce."},
            {h:"€/M²",tip:"Prix au mètre carré calculé à partir du prix et de la surface du bien."},
            {h:"MÉDIAN",tip:"Prix médian au m² dans cette commune selon les données DVF (Demandes de Valeurs Foncières) 2023. Sert de référence pour calculer la décote."},
            {h:"DÉCOTE",tip:"Pourcentage de décote par rapport au prix médian DVF. Ex: -30% signifie que le bien est 30% moins cher que la médiane du marché."},
            {h:"M²",tip:"Surface habitable ou surface du terrain en mètres carrés."},
            {h:"SOURCE",tip:"Site d'origine de l'annonce : LeBonCoin, SeLoger, PAP, BienIci. Le bot scrape ces plateformes automatiquement."},
            {h:"VENDEUR",tip:"PART. = particulier (bonus +5 pts au score), AGCE = agence immobilière. Les particuliers proposent souvent de meilleures affaires."},
            {h:"PUB.",tip:"Ancienneté de la publication. Les annonces récentes (<1h) sont les plus intéressantes car moins de concurrence."},
            {h:"ACTIONS",tip:"✓ = Marquer en cours de traitement, ✕ = Marquer comme traité (grisé), ↗ = Ouvrir l'annonce sur le site source."},
          ].map((col,i)=>(
            <div key={i} style={{padding:"0 8px",color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",borderRight:i<13?"1px solid #0a1e30":"none",display:"flex",alignItems:"center"}}>
              <InfoBulle text={col.tip}><span style={{cursor:"help",borderBottom:"1px dotted #2a5070"}}>{col.h}</span></InfoBulle>
            </div>
          ))}
        </div>
        {filteredAnnonces.map((a,idx)=>(
          <div key={a.id}>
            <div className="rh" onClick={()=>setSelectedRow(selectedRow===a.id?null:a.id)}
              style={{display:"grid",gridTemplateColumns:colTpl,borderBottom:"1px solid #091828",cursor:"pointer",minWidth:"1100px",background:selectedRow===a.id?"rgba(0,80,200,0.1)":a.statut==="traite"?"rgba(0,0,0,0.3)":idx%2===0?"#030c18":"#020810",opacity:a.statut==="traite"?0.5:1}}>
              {/* SCORE */}
              <div style={{padding:"8px",display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",borderRight:"1px solid #0a1e30"}}>
                <div className="mv" style={{fontSize:"18px",color:scoreColor(a.score),lineHeight:1}}>{a.score}</div>
                <div style={{width:"36px",height:"2px",background:"#0a1e30",marginTop:"3px",borderRadius:"1px"}}>
                  <div style={{width:`${a.score}%`,height:"100%",background:scoreColor(a.score),borderRadius:"1px"}}/>
                </div>
              </div>
              {/* NIVEAU */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",borderRight:"1px solid #0a1e30"}}>
                <span style={{background:scoreBg(a.score),color:scoreColor(a.score),padding:"2px 5px",borderRadius:"2px",fontSize:"9px",border:`1px solid ${scoreColor(a.score)}22`}}>{niveauShort(a.niveau)}</span>
              </div>
              {/* TYPE */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",color:"#a0b8d0",fontSize:"11px",borderRight:"1px solid #0a1e30",gap:"4px"}}>
                {a.est_enchere&&<span style={{color:"#ff6b35",fontSize:"9px"}}>⚡</span>}{a.type}
              </div>
              {/* VILLE */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",color:"#c8d8e8",fontSize:"11px",fontWeight:"600",borderRight:"1px solid #0a1e30"}}>{a.ville}</div>
              {/* CP */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",color:"#3a6080",fontSize:"11px",borderRight:"1px solid #0a1e30"}}>{a.cp}</div>
              {/* PRIX */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",color:"#60b8ff",fontSize:"11px",fontWeight:"600",borderRight:"1px solid #0a1e30"}}>{fmtPrix(a.prix)}</div>
              {/* €/M² */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",color:"#a0b8d0",fontSize:"11px",borderRight:"1px solid #0a1e30"}}>{fmtM2(a.prix_m2)}</div>
              {/* MÉDIAN */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",color:"#3a6080",fontSize:"11px",borderRight:"1px solid #0a1e30"}}>{fmtM2(a.median_m2)}</div>
              {/* DÉCOTE */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",color:a.decote>=30?"#00ff88":a.decote>=20?"#ffb300":"#ff8c00",fontSize:"11px",fontWeight:"600",borderRight:"1px solid #0a1e30"}}>-{a.decote}%</div>
              {/* M² */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",color:"#a0b8d0",fontSize:"11px",borderRight:"1px solid #0a1e30"}}>{a.surface}</div>
              {/* SOURCE */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",color:"#3a6080",fontSize:"10px",borderRight:"1px solid #0a1e30"}}>{a.source}</div>
              {/* VENDEUR */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",borderRight:"1px solid #0a1e30"}}>
                <span style={{color:a.vendeur==="particulier"?"#a78bfa":"#3a6080",fontSize:"10px"}}>{a.vendeur==="particulier"?"PART.":"AGCE"}</span>
              </div>
              {/* PUB */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",color:a.age.includes("min")?"#00ff88":"#3a6080",fontSize:"10px",borderRight:"1px solid #0a1e30"}}>{a.age}</div>
              {/* ACTIONS */}
              <div style={{padding:"8px",display:"flex",alignItems:"center",gap:"4px"}}>
                <button className="ab abg" onClick={(e)=>{e.stopPropagation();handleStatut(a.id,"en_cours")}} title="Marquer en cours">✓</button>
                <button className="ab abr" onClick={(e)=>{e.stopPropagation();handleStatut(a.id,"traite")}} title="Marquer traité">✕</button>
                <a href={a.url} target="_blank" rel="noopener noreferrer" className="ab" onClick={(e)=>{e.stopPropagation()}} title="Voir l'annonce" style={{textDecoration:"none",display:"inline-flex",alignItems:"center",justifyContent:"center"}}>↗</a>
              </div>
            </div>

            {/* DETAIL ROW */}
            {selectedRow===a.id && (
              <div className="si" style={{background:"#020810",borderBottom:"2px solid #0d2040",padding:"14px 20px",display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:"20px"}}>
                <div>
                  <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"6px"}}>DÉTAILS DU BIEN</div>
                  <div style={{color:"#c8d8e8",fontSize:"11px",lineHeight:1.8}}>
                    <div><span style={{color:"#3a6080"}}>Type:</span> {a.type}</div>
                    <div><span style={{color:"#3a6080"}}>Surface:</span> {a.surface}m²{a.terrain ? ` (terrain: ${a.terrain}m²)` : ""}</div>
                    {a.pieces && <div><span style={{color:"#3a6080"}}>Pièces:</span> {a.pieces}</div>}
                    {a.dpe && <div><span style={{color:"#3a6080"}}>DPE:</span> <span style={{color:a.dpe<="C"?"#00ff88":a.dpe<="D"?"#ffb300":"#ff5555"}}>{a.dpe}</span></div>}
                  </div>
                </div>
                <div>
                  <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"6px"}}>ANALYSE PRIX</div>
                  <div style={{color:"#c8d8e8",fontSize:"11px",lineHeight:1.8}}>
                    <div><span style={{color:"#3a6080"}}>Prix demandé:</span> <span style={{color:"#60b8ff"}}>{a.prix.toLocaleString("fr-FR")}€</span></div>
                    <div><span style={{color:"#3a6080"}}>Prix/m²:</span> {a.prix_m2}€/m²</div>
                    <div><span style={{color:"#3a6080"}}>Médiane DVF:</span> {a.median_m2}€/m²</div>
                    <div><span style={{color:"#3a6080"}}>Décote:</span> <span style={{color:"#00ff88",fontWeight:"700"}}>-{a.decote}%</span></div>
                  </div>
                </div>
                <div>
                  <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"6px"}}>SIGNAUX</div>
                  <div style={{display:"flex",flexWrap:"wrap",gap:"4px",marginBottom:"8px"}}>
                    {a.mots.map((m,i)=>(
                      <span key={i} style={{background:"rgba(255,59,59,0.12)",color:"#ff5555",padding:"2px 6px",borderRadius:"2px",fontSize:"9px",border:"1px solid rgba(255,59,59,0.2)"}}>{m}</span>
                    ))}
                    {a.mots.length===0 && <span style={{color:"#2a4060",fontSize:"10px"}}>Aucun signal détecté</span>}
                  </div>
                  <div style={{color:"#3a6080",fontSize:"10px"}}>Statut: <span style={{color:a.statut==="nouveau"?"#00ff88":a.statut==="en_cours"?"#ffb300":"#64748b"}}>{a.statut.toUpperCase()}</span></div>
                  <a href={a.url} target="_blank" rel="noopener noreferrer" style={{display:"inline-block",marginTop:"8px",background:"rgba(0,150,255,0.15)",color:"#60b8ff",padding:"4px 10px",borderRadius:"2px",fontSize:"10px",textDecoration:"none",border:"1px solid #0088ff33"}}>VOIR L'ANNONCE SUR {a.source.toUpperCase()} ↗</a>
                </div>
              </div>
            )}
          </div>
        ))}
        {filteredAnnonces.length===0 && (
          <div style={{padding:"40px",textAlign:"center",color:"#2a4060"}}>Aucune annonce ne correspond aux filtres sélectionnés</div>
        )}
      </div>
    </div>
  );
}

function EncheresTab({ S }) {
  return (
    <div className="si">
      <div style={{display:"grid",gap:"12px"}}>
        {ENCHERES.sort((a,b)=>a.date_audience-b.date_audience).map(e=>{
          const jours = joursAvant(e.date_audience);
          const urgentColor = jours<=5 ? "#ff3b3b" : jours<=10 ? "#ffb300" : "#60b8ff";
          return (
            <div key={e.id} style={{...S.card,borderLeft:`3px solid ${urgentColor}`}}>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr 1fr",gap:"16px"}}>
                <div>
                  <div style={{display:"flex",alignItems:"center",gap:"8px",marginBottom:"8px"}}>
                    <span style={{background:e.type==="JUDICIAIRE"?"rgba(255,59,59,0.12)":"rgba(255,107,53,0.12)",color:e.type==="JUDICIAIRE"?"#ff5555":"#ff6b35",padding:"2px 6px",borderRadius:"2px",fontSize:"9px",border:`1px solid ${e.type==="JUDICIAIRE"?"rgba(255,59,59,0.2)":"rgba(255,107,53,0.2)"}`}}>{e.type}</span>
                    <span className="mv" style={{fontSize:"16px",color:scoreColor(e.score)}}>{e.score}</span>
                  </div>
                  <div style={{color:"#c8d8e8",fontSize:"13px",fontWeight:"600",marginBottom:"4px"}}>{e.bien}</div>
                  <div style={{color:"#60b8ff",fontSize:"11px"}}>{e.ville} ({e.cp})</div>
                </div>
                <div>
                  <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"6px"}}>PRIX</div>
                  <div style={{color:"#c8d8e8",fontSize:"11px",lineHeight:1.8}}>
                    <div><span style={{color:"#3a6080"}}>Mise à prix:</span> <span style={{color:"#ff6b35",fontWeight:"700"}}>{fmtPrix(e.mise_a_prix)}</span></div>
                    <div><span style={{color:"#3a6080"}}>Estimation:</span> {fmtPrix(e.estimation)}</div>
                    <div><span style={{color:"#3a6080"}}>Décote potentielle:</span> <span style={{color:"#00ff88",fontWeight:"700"}}>-{e.decote_potentielle}%</span></div>
                  </div>
                </div>
                <div>
                  <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"6px"}}>AUDIENCE</div>
                  <div style={{color:"#c8d8e8",fontSize:"11px",lineHeight:1.8}}>
                    <div><span style={{color:"#3a6080"}}>Date:</span> <span style={{color:urgentColor,fontWeight:"700"}}>{e.date_audience.toLocaleDateString("fr-FR")} (J-{jours})</span></div>
                    <div><span style={{color:"#3a6080"}}>Tribunal:</span> {e.tribunal}</div>
                    <div><span style={{color:"#3a6080"}}>RG:</span> {e.rg}</div>
                  </div>
                </div>
                <div>
                  <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"6px"}}>INFOS</div>
                  <div style={{color:"#c8d8e8",fontSize:"11px",lineHeight:1.8}}>
                    <div><span style={{color:"#3a6080"}}>Avocat:</span> {e.avocat}</div>
                    <div><span style={{color:"#3a6080"}}>Visites:</span> {e.visites}</div>
                    <div><span style={{color:"#3a6080"}}>Surface:</span> {e.surface}m²{e.terrain?` (terrain: ${e.terrain}m²)`:""}</div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatsTab({ S }) {
  return (
    <div className="si">
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"16px",marginBottom:"16px"}}>
        <div style={S.card}>
          <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"12px"}}>ANNONCES SCANNÉES — 7 DERNIERS JOURS</div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={STATS_SEMAINE}>
              <defs>
                <linearGradient id="gAnn" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#60b8ff" stopOpacity={0.3}/>
                  <stop offset="100%" stopColor="#60b8ff" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="jour" tick={{fill:"#3a6080",fontSize:10}} axisLine={{stroke:"#0d2040"}} tickLine={false}/>
              <YAxis tick={{fill:"#3a6080",fontSize:10}} axisLine={false} tickLine={false}/>
              <Tooltip contentStyle={{background:"#030c18",border:"1px solid #0d2040",borderRadius:"3px",fontSize:"11px",color:"#c8d8e8"}}/>
              <Area type="monotone" dataKey="annonces" stroke="#60b8ff" fill="url(#gAnn)" strokeWidth={2}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div style={S.card}>
          <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"12px"}}>OPPORTUNITÉS DÉTECTÉES — 7 DERNIERS JOURS</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={STATS_SEMAINE}>
              <XAxis dataKey="jour" tick={{fill:"#3a6080",fontSize:10}} axisLine={{stroke:"#0d2040"}} tickLine={false}/>
              <YAxis tick={{fill:"#3a6080",fontSize:10}} axisLine={false} tickLine={false}/>
              <Tooltip contentStyle={{background:"#030c18",border:"1px solid #0d2040",borderRadius:"3px",fontSize:"11px",color:"#c8d8e8"}}/>
              <Bar dataKey="opportunites" radius={[2,2,0,0]}>
                {STATS_SEMAINE.map((entry,i) => (
                  <Cell key={i} fill={entry.opportunites>=15?"#00ff88":entry.opportunites>=10?"#ffb300":"#60b8ff"}/>
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div style={S.card}>
        <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"12px"}}>PRIX MÉDIAN AU M² — COMMUNES SURVEILLÉES (DVF 2023)</div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={PRIX_COMMUNES} layout="vertical">
            <XAxis type="number" tick={{fill:"#3a6080",fontSize:10}} axisLine={{stroke:"#0d2040"}} tickLine={false}/>
            <YAxis type="category" dataKey="ville" tick={{fill:"#c8d8e8",fontSize:10}} axisLine={false} tickLine={false} width={110}/>
            <Tooltip contentStyle={{background:"#030c18",border:"1px solid #0d2040",borderRadius:"3px",fontSize:"11px",color:"#c8d8e8"}} formatter={(v)=>[`${v}€/m²`,"Prix médian"]}/>
            <Bar dataKey="m2" radius={[0,2,2,0]}>
              {PRIX_COMMUNES.map((entry,i) => (
                <Cell key={i} fill={entry.m2>=3000?"#a78bfa":entry.m2>=2500?"#60b8ff":"#00ff88"}/>
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ParamsTab({ S }) {
  return (
    <div className="si">
      {/* EXPLICATION DU BOT */}
      <div style={{...S.card,marginBottom:"16px",borderLeft:"3px solid #60b8ff"}}>
        <div style={{color:"#60b8ff",fontSize:"11px",letterSpacing:"0.1em",marginBottom:"10px",fontWeight:"600",display:"flex",alignItems:"center",gap:"8px"}}>
          <span style={{fontSize:"16px"}}>&#9432;</span> COMMENT FONCTIONNE IMMOSNIPER
        </div>
        <div style={{color:"#a0b8d0",fontSize:"12px",lineHeight:1.9}}>
          <p style={{margin:"0 0 10px 0"}}>
            <strong style={{color:"#c8d8e8"}}>ImmoSniper</strong> est un bot automatisé de détection d'opportunités immobilières. Il scanne en continu les principales plateformes d'annonces (LeBonCoin, SeLoger, PAP, BienIci) ainsi que les ventes aux enchères judiciaires et notariales.
          </p>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"16px",margin:"12px 0"}}>
            <div>
              <div style={{color:"#00ff88",fontSize:"10px",letterSpacing:"0.08em",marginBottom:"6px",fontWeight:"600"}}>1. SCAN AUTOMATIQUE</div>
              <div style={{fontSize:"11px",color:"#8aa8c8"}}>Toutes les 45 minutes, le bot parcourt les sites immobiliers et collecte les nouvelles annonces dans votre zone géographique (45 communes, rayon 30km).</div>
            </div>
            <div>
              <div style={{color:"#ffb300",fontSize:"10px",letterSpacing:"0.08em",marginBottom:"6px",fontWeight:"600"}}>2. ANALYSE & SCORING</div>
              <div style={{fontSize:"11px",color:"#8aa8c8"}}>Chaque annonce est analysée et reçoit un score de 0 à 100 basé sur : la décote par rapport aux prix DVF, les mots-clés d'urgence (succession, divorce...), le type de vendeur et la fraîcheur.</div>
            </div>
            <div>
              <div style={{color:"#ff6b35",fontSize:"10px",letterSpacing:"0.08em",marginBottom:"6px",fontWeight:"600"}}>3. ENCHÈRES IMMOBILIÈRES</div>
              <div style={{fontSize:"11px",color:"#8aa8c8"}}>Le bot surveille aussi les ventes aux enchères judiciaires (TJ) et notariales. Ces ventes offrent des décotes de 40 à 55% mais nécessitent un avocat pour enchérir.</div>
            </div>
            <div>
              <div style={{color:"#a78bfa",fontSize:"10px",letterSpacing:"0.08em",marginBottom:"6px",fontWeight:"600"}}>4. ALERTES EN TEMPS RÉEL</div>
              <div style={{fontSize:"11px",color:"#8aa8c8"}}>Quand une opportunité exceptionnelle est détectée (score ≥ 80), vous recevez une alerte par email et SMS pour agir rapidement avant la concurrence.</div>
            </div>
          </div>
          <div style={{background:"rgba(0,255,136,0.06)",border:"1px solid rgba(0,255,136,0.15)",borderRadius:"3px",padding:"10px 14px",marginTop:"8px"}}>
            <div style={{color:"#00ff88",fontSize:"10px",letterSpacing:"0.08em",marginBottom:"4px",fontWeight:"600"}}>DONNÉES DVF — RÉFÉRENCE DE PRIX</div>
            <div style={{fontSize:"11px",color:"#8aa8c8"}}>Les prix médians proviennent de la base DVF (Demandes de Valeurs Foncières), qui recense toutes les transactions immobilières réelles enregistrées par les notaires. C'est la référence la plus fiable pour évaluer si un bien est en dessous du marché.</div>
          </div>
        </div>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"16px"}}>
        <div style={S.card}>
          <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"12px",display:"flex",alignItems:"center"}}>ZONE DE RECHERCHE<HelpIcon text="Zone géographique surveillée par le bot. Toutes les annonces dans ce périmètre sont automatiquement scannées et analysées."/></div>
          <div style={{color:"#c8d8e8",fontSize:"11px",lineHeight:2}}>
            <div><span style={{color:"#3a6080"}}>Centre:</span> Les Pennes-Mirabeau (13170)</div>
            <div><span style={{color:"#3a6080"}}>Rayon:</span> 30 km</div>
            <div><span style={{color:"#3a6080"}}>Département:</span> 13 - Bouches-du-Rhône</div>
            <div><span style={{color:"#3a6080"}}>Communes:</span> 45 communes surveillées</div>
          </div>
        </div>
        <div style={S.card}>
          <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"12px",display:"flex",alignItems:"center"}}>SOURCES ACTIVES<HelpIcon text="Plateformes immobilières que le bot scrape automatiquement. Chaque source est vérifiée toutes les 45 minutes pour détecter les nouvelles annonces."/></div>
          <div style={{display:"flex",flexDirection:"column",gap:"6px"}}>
            {[["LeBonCoin","Actif","#00ff88"],["SeLoger","Actif","#00ff88"],["PAP","Actif","#00ff88"],["BienIci","Actif","#00ff88"],["Enchères judiciaires","Actif","#00ff88"],["Enchères notariales","Actif","#00ff88"]].map(([nom,st,c],i)=>(
              <div key={i} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"4px 0",borderBottom:"1px solid #0a1e30"}}>
                <span style={{color:"#c8d8e8",fontSize:"11px"}}>{nom}</span>
                <span style={{color:c,fontSize:"10px",display:"flex",alignItems:"center",gap:"4px"}}>
                  <span style={{width:"5px",height:"5px",background:c,borderRadius:"50%",display:"inline-block"}}/>
                  {st}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div style={S.card}>
          <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"12px",display:"flex",alignItems:"center"}}>CRITÈRES DE SCORING<HelpIcon text="Règles utilisées pour calculer le score de chaque annonce. Le score combine la décote DVF, les signaux d'urgence, le vendeur et la fraîcheur de l'annonce."/></div>
          <div style={{color:"#c8d8e8",fontSize:"11px",lineHeight:2}}>
            <div><span style={{color:"#3a6080"}}>Décote min:</span> 15% vs médiane DVF</div>
            <div><span style={{color:"#3a6080"}}>Mots-clés bonus:</span> succession, divorce, urgent, liquidation, mutation</div>
            <div><span style={{color:"#3a6080"}}>Vendeur bonus:</span> +5 pts si particulier</div>
            <div><span style={{color:"#3a6080"}}>Fraîcheur bonus:</span> +10 pts si {"<"} 1h</div>
            <div><span style={{color:"#3a6080"}}>DPE malus:</span> -5 pts si F/G</div>
          </div>
        </div>
        <div style={S.card}>
          <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"12px",display:"flex",alignItems:"center"}}>ALERTES<HelpIcon text="Notifications envoyées quand une opportunité exceptionnelle (score ≥ 80) est détectée. Vous êtes alerté par email et SMS pour agir rapidement."/></div>
          <div style={{color:"#c8d8e8",fontSize:"11px",lineHeight:2}}>
            <div><span style={{color:"#3a6080"}}>Email:</span> alert@immosniper.fr</div>
            <div><span style={{color:"#3a6080"}}>SMS:</span> +33 6 XX XX XX XX</div>
            <div><span style={{color:"#3a6080"}}>Seuil alerte:</span> Score ≥ 80</div>
            <div><span style={{color:"#3a6080"}}>Fréquence scan:</span> Toutes les 45 min</div>
            <div><span style={{color:"#3a6080"}}>Notifications:</span> <span style={{color:"#00ff88"}}>Activées</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// URL de l'API backend (même serveur en production, localhost en dev)
const API_BASE = import.meta.env.VITE_API_URL || "";

export default function ImmoSniperDashboard() {
  const [tab, setTab] = useState("flux");
  const [filtreType, setFiltreType] = useState("tous");
  const [filtreScore, setFiltreScore] = useState(0);
  const [filtreVendeur, setFiltreVendeur] = useState("tous");
  const [filtreFraicheur, setFiltreFraicheur] = useState("tous");
  const [selectedRow, setSelectedRow] = useState(null);
  const [now, setNow] = useState(new Date());
  const [annonces, setAnnonces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastScan, setLastScan] = useState(0);
  const [nextScanIn, setNextScanIn] = useState(0);
  const [scanCount, setScanCount] = useState(0);
  const [scanning, setScanning] = useState(false);

  // Fetch annonces depuis l'API backend
  const fetchAnnonces = async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/annonces`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setAnnonces(data.annonces || []);
      setLastScan(data.last_scan || 0);
      setNextScanIn(data.next_scan_in || 0);
      setScanCount(data.scan_count || 0);
      setLoading(false);
    } catch (e) {
      console.error("[API] Erreur fetch annonces:", e);
      // Fallback sur données locales si l'API n'est pas dispo
      if (annonces.length === 0) {
        setAnnonces(ANNONCES);
      }
      setLoading(false);
    }
  };

  // Forcer un scan
  const forceScan = async () => {
    setScanning(true);
    try {
      await fetch(`${API_BASE}/api/scan`, { method: "POST" });
      // Attendre un peu puis rafraîchir
      setTimeout(fetchAnnonces, 3000);
      setTimeout(fetchAnnonces, 10000);
      setTimeout(fetchAnnonces, 30000);
    } catch (e) {
      console.error("[API] Erreur force scan:", e);
    }
    setTimeout(() => setScanning(false), 5000);
  };

  // Mettre à jour le statut via l'API
  const handleStatut = async (id, statut) => {
    setAnnonces(prev => prev.map(a => a.id === id ? { ...a, statut } : a));
    setSelectedRow(null);
    try {
      await fetch(`${API_BASE}/api/annonces/${id}/statut`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ statut }),
      });
    } catch (e) {
      console.error("[API] Erreur update statut:", e);
    }
  };

  // Polling : fetch les annonces toutes les 30s
  useEffect(() => {
    fetchAnnonces();
    const t = setInterval(fetchAnnonces, 30000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => { const t = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(t); }, []);

  // Countdown du prochain scan
  const [countdown, setCountdown] = useState("");
  useEffect(() => {
    const t = setInterval(() => {
      if (lastScan > 0) {
        const elapsed = Date.now() / 1000 - lastScan;
        const remaining = Math.max(0, 45 * 60 - elapsed);
        const m = Math.floor(remaining / 60);
        const s = Math.floor(remaining % 60);
        setCountdown(`${m}:${s.toString().padStart(2, "0")}`);
      }
    }, 1000);
    return () => clearInterval(t);
  }, [lastScan]);

  const filteredAnnonces = annonces.filter(a => {
    if (filtreType !== "tous" && a.type.toLowerCase().replace(/ /g,"_") !== filtreType) return false;
    if (filtreScore > 0 && a.score < filtreScore) return false;
    if (filtreVendeur !== "tous" && a.vendeur !== filtreVendeur) return false;
    if (filtreFraicheur === "1h" && !a.age.includes("min")) { const h = parseFloat(a.age); if (h > 1) return false; }
    if (filtreFraicheur === "24h") { const h = a.age.includes("min") ? 0 : parseFloat(a.age); if (h > 24) return false; }
    return true;
  }).sort((a,b) => b.score - a.score);

  const nbOpportunites = annonces.filter(a => a.score >= 65).length;
  const nbExceptionnelles = annonces.filter(a => a.score >= 80).length;
  const decoteMoyenne = annonces.length > 0 ? Math.round(annonces.reduce((s,a) => s+(a.decote||0),0)/annonces.length*10)/10 : 0;
  const prixMedianMoyen = (() => { const withMedian = annonces.filter(a=>a.median_m2); return withMedian.length > 0 ? Math.round(withMedian.reduce((s,a)=>s+a.median_m2,0)/withMedian.length) : 0; })();
  const prochaine = ENCHERES.length > 0 ? [...ENCHERES].sort((a,b)=>a.date_audience-b.date_audience)[0] : null;

  const S = {
    root: { background:"#040d18", minHeight:"100vh", fontFamily:"'IBM Plex Mono','Courier New',monospace", color:"#c8d8e8", fontSize:"12px", backgroundImage:"radial-gradient(ellipse at 20% 0%, rgba(0,80,200,0.07) 0%, transparent 60%), radial-gradient(ellipse at 80% 100%, rgba(0,200,100,0.04) 0%, transparent 60%)" },
    topbar: { background:"#020810", borderBottom:"1px solid #0d2040", padding:"0 20px", display:"flex", alignItems:"center", justifyContent:"space-between", height:"38px" },
    metrics: { background:"#030c18", borderBottom:"1px solid #0d2040", padding:"10px 20px", display:"grid", gridTemplateColumns:"repeat(7,1fr)", gap:"1px" },
    nav: { background:"#020810", borderBottom:"1px solid #0d2040", padding:"0 20px", display:"flex" },
    content: { padding:"16px 20px" },
    card: { background:"#030c18", border:"1px solid #0d2040", borderRadius:"3px", padding:"14px" },
  };

  const colTpl = "56px 90px 80px 120px 55px 90px 78px 78px 72px 60px 72px 65px 55px 1fr";

  return (
    <div style={S.root}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&family=Bebas+Neue&display=swap');
        *{box-sizing:border-box} ::-webkit-scrollbar{width:4px;height:4px} ::-webkit-scrollbar-track{background:#060f1e} ::-webkit-scrollbar-thumb{background:#1a3050;border-radius:2px}
        .rh:hover{background:rgba(0,100,255,0.07)!important}
        .fb{background:rgba(255,255,255,0.04);border:1px solid #1a3050;cursor:pointer;font-family:inherit;font-size:10px;border-radius:2px;color:#8aa8c8;padding:3px 8px;transition:all 0.15s}
        .fb:hover{background:rgba(0,100,255,0.1);border-color:#2a5080;color:#c8d8e8}
        .fb.on{background:rgba(0,150,255,0.15);border-color:#0088ff;color:#60b8ff}
        .ab{background:none;border:1px solid #1a3050;cursor:pointer;font-family:inherit;font-size:10px;border-radius:2px;color:#8aa8c8;padding:2px 7px;transition:all 0.15s}
        .ab:hover{border-color:#0088ff;color:#60b8ff}
        .abg{border-color:#003320!important;color:#00aa55!important}
        .abg:hover{background:rgba(0,200,80,0.12)!important;border-color:#00cc66!important;color:#00ff88!important}
        .abr{border-color:#330000!important;color:#aa3333!important}
        .abr:hover{background:rgba(200,0,0,0.12)!important;border-color:#cc3333!important;color:#ff5555!important}
        .pd{animation:pd 1.2s ease-in-out infinite} @keyframes pd{0%,100%{opacity:1}50%{opacity:0.2}}
        .si{animation:si 0.3s ease-out} @keyframes si{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
        .ub{animation:ub 2s ease-in-out infinite} @keyframes ub{0%,100%{opacity:1}50%{opacity:0.6}}
        .mv{font-family:'Bebas Neue',monospace;letter-spacing:0.05em}
        .tb{background:none;border:none;cursor:pointer;font-family:inherit;font-size:10px;letter-spacing:0.12em;padding:10px 16px;transition:all 0.15s}
        input{outline:none}
      `}</style>

      {/* BANDEAU STATUS */}
      {loading && (
        <div style={{background:"linear-gradient(90deg,#0066ff,#0088ff,#0066ff)",padding:"6px 20px",textAlign:"center",fontSize:"11px",color:"#fff",fontWeight:"600",letterSpacing:"0.08em"}}>
          CHARGEMENT DES ANNONCES EN COURS... Scan des plateformes immobilières.
        </div>
      )}
      {!loading && annonces.length === 0 && (
        <div style={{background:"linear-gradient(90deg,#ff6b35,#ff3b3b,#ff6b35)",padding:"6px 20px",textAlign:"center",fontSize:"11px",color:"#fff",fontWeight:"600",letterSpacing:"0.08em"}}>
          AUCUNE ANNONCE — Le premier scan est en cours. Les résultats apparaîtront dans quelques instants.
        </div>
      )}

      {/* TOP BAR */}
      <div style={S.topbar}>
        <div style={{display:"flex",alignItems:"center",gap:"16px"}}>
          <div style={{display:"flex",alignItems:"center",gap:"8px"}}>
            <div style={{width:"6px",height:"6px",background:"#00ff88",borderRadius:"50%",boxShadow:"0 0 8px #00ff88"}} className="pd"/>
            <span style={{fontFamily:"'Bebas Neue',monospace",fontSize:"16px",color:"#60b8ff",letterSpacing:"0.15em"}}>IMMOSNIPER</span>
            <span style={{color:"#1a4060",fontSize:"10px",letterSpacing:"0.1em"}}>MDB v1.0</span>
          </div>
          <div style={{width:"1px",height:"18px",background:"#0d2040"}}/>
          <span style={{color:"#3a6080",fontSize:"10px"}}>DEPT. 13 — LES PENNES-MIRABEAU +30KM</span>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:"16px"}}>
          <InfoBulle text="Temps restant avant le prochain scan automatique des plateformes immobilières. Le bot scrape toutes les sources toutes les 45 minutes."><span style={{color:"#3a6080",fontSize:"10px",cursor:"help"}}>SCAN SUIVANT</span></InfoBulle>
          <span style={{color:"#60b8ff",fontSize:"11px"}}>{countdown || "--:--"}</span>
          <button onClick={forceScan} disabled={scanning} style={{background:scanning?"#1a3050":"rgba(0,150,255,0.15)",border:"1px solid #0088ff44",borderRadius:"2px",color:scanning?"#3a6080":"#60b8ff",fontSize:"9px",padding:"2px 8px",cursor:scanning?"wait":"pointer",fontFamily:"inherit",letterSpacing:"0.05em"}}>{scanning?"SCAN...":"SCANNER"}</button>
          <span style={{color:"#2a4060",fontSize:"9px"}}>#{scanCount}</span>
          <div style={{width:"1px",height:"18px",background:"#0d2040"}}/>
          <span style={{color:"#3a6080",fontSize:"10px"}}>HEURE</span>
          <span style={{color:"#c8d8e8",fontSize:"11px"}}>{now.toLocaleTimeString("fr-FR")}</span>
        </div>
      </div>

      {/* METRICS */}
      <div style={S.metrics}>
        {[
          {l:"ANNONCES SCANNÉES",v:String(annonces.length),s:`Scan #${scanCount}`,c:"#c8d8e8",tip:"Nombre total d'annonces analysées lors du dernier cycle de scan (toutes les 45 min). Le bot parcourt LeBonCoin et BienIci."},
          {l:"OPPORTUNITÉS",v:String(nbOpportunites),s:"Score ≥ 65",c:"#ffb300",tip:"Nombre d'annonces avec un score ≥ 65. Ces biens présentent une décote significative par rapport au marché et méritent votre attention."},
          {l:"EXCEPTIONNELLES",v:String(nbExceptionnelles),s:"Score ≥ 80",c:"#00ff88",tip:"Annonces avec un score ≥ 80. Ce sont les meilleures affaires détectées : forte décote, vendeur particulier, mots-clés d'urgence. À traiter en priorité !"},
          {l:"ENCHÈRES ACTIVES",v:String(ENCHERES.length),s:"Dept. 13",c:"#ff6b35",tip:"Ventes aux enchères judiciaires et notariales en cours dans le département 13. Souvent des décotes de 40-55% par rapport à l'estimation."},
          {l:"PRIX MÉDIAN",v:fmtM2(prixMedianMoyen),s:"DVF 2023",c:"#60b8ff",tip:"Prix médian au m² moyen des communes surveillées, basé sur les données DVF (transactions réelles enregistrées par les notaires en 2023)."},
          {l:"DÉCOTE MOY.",v:"-"+decoteMoyenne+"%",s:"Annonces du jour",c:"#a78bfa",tip:"Décote moyenne de toutes les annonces affichées par rapport au prix médian DVF de leur commune. Plus c'est élevé, meilleures sont les affaires."},
          {l:"PROCHAINE AUDIENCE",v:prochaine?joursAvant(prochaine.date_audience)+"J":"--",s:prochaine?prochaine.ville:"--",c:"#ff3b3b",tip:"Compte à rebours avant la prochaine audience d'enchères. Pensez à mandater un avocat et à visiter le bien avant cette date."},
        ].map((m,i)=>(
          <div key={i} style={{padding:"6px 12px",borderRight:i<6?"1px solid #0d2040":"none",cursor:"help"}} title={m.tip}>
            <div style={{color:"#3a6080",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"2px",display:"flex",alignItems:"center"}}>{m.l}<HelpIcon text={m.tip}/></div>
            <div className="mv" style={{fontSize:"22px",color:m.c,lineHeight:1}}>{m.v}</div>
            <div style={{color:"#2a4060",fontSize:"9px",marginTop:"2px"}}>{m.s}</div>
          </div>
        ))}
      </div>

      {/* NAV */}
      <div style={S.nav}>
        {[
          {id:"flux",l:"FLUX EN DIRECT",n:annonces.length,tip:"Toutes les annonces immobilières détectées par le bot, triées par score d'opportunité. Cliquez sur une ligne pour voir le détail."},
          {id:"encheres",l:"ENCHÈRES ACTIVES",n:ENCHERES.length,u:true,tip:"Ventes aux enchères judiciaires et notariales à venir. Les décotes peuvent atteindre 40 à 55% par rapport à l'estimation."},
          {id:"stats",l:"STATISTIQUES",tip:"Graphiques d'activité du bot : nombre d'annonces scannées, opportunités détectées et prix médians par commune."},
          {id:"params",l:"PARAMÈTRES",tip:"Configuration du bot : zone de recherche, sources actives, critères de scoring et paramètres d'alertes."},
        ].map(t=>(
          <button key={t.id} className="tb" onClick={()=>setTab(t.id)} title={t.tip}
            style={{color:tab===t.id?"#60b8ff":"#3a6080",borderBottom:tab===t.id?"2px solid #60b8ff":"2px solid transparent",display:"flex",alignItems:"center",gap:"6px"}}>
            {t.l}
            {t.n!==undefined && <span style={{background:tab===t.id?"rgba(96,184,255,0.15)":"rgba(255,255,255,0.05)",color:tab===t.id?"#60b8ff":"#3a6080",padding:"1px 5px",borderRadius:"2px",fontSize:"9px"}}>{t.n}</span>}
            {t.u && <span style={{width:"5px",height:"5px",background:"#ff3b3b",borderRadius:"50%",boxShadow:"0 0 6px #ff3b3b"}} className="pd"/>}
          </button>
        ))}
      </div>

      <div style={S.content}>
        {/* TAB: FLUX */}
        {tab==="flux" && <FluxTab S={S} colTpl={colTpl} filtreType={filtreType} setFiltreType={setFiltreType} filtreScore={filtreScore} setFiltreScore={setFiltreScore} filtreVendeur={filtreVendeur} setFiltreVendeur={setFiltreVendeur} filtreFraicheur={filtreFraicheur} setFiltreFraicheur={setFiltreFraicheur} filteredAnnonces={filteredAnnonces} selectedRow={selectedRow} setSelectedRow={setSelectedRow} handleStatut={handleStatut} />}
        {/* TAB: ENCHERES */}
        {tab==="encheres" && <EncheresTab S={S} />}
        {/* TAB: STATS */}
        {tab==="stats" && <StatsTab S={S} />}
        {/* TAB: PARAMS */}
        {tab==="params" && <ParamsTab S={S} />}
      </div>
    </div>
  );
}
