import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, Cell } from "recharts";

const ANNONCES = [
  { id:1, score:91, niveau:"OPPORTUNITE EXCEPTIONNELLE", type:"Maison", ville:"Vitrolles", cp:"13127", prix:187000, surface:112, terrain:420, pieces:5, prix_m2:1669, median_m2:2450, decote:31.9, source:"LeBonCoin", vendeur:"particulier", age:"38min", dpe:"D", mots:["succession","urgent"], statut:"nouveau", est_enchere:false, url:"https://www.leboncoin.fr/ventes_immobilieres/vitrolles" },
  { id:2, score:84, niveau:"OPPORTUNITE EXCEPTIONNELLE", type:"Terrain", ville:"Marignane", cp:"13700", prix:95000, surface:1200, terrain:1200, pieces:null, prix_m2:79, median_m2:130, decote:39.2, source:"PAP", vendeur:"particulier", age:"1h12", dpe:null, mots:["mutation","vente rapide"], statut:"nouveau", est_enchere:false, url:"https://www.pap.fr/annonce/terrain-marignane" },
  { id:3, score:79, niveau:"FORTE OPPORTUNITE", type:"Maison", ville:"Gignac-la-Nerthe", cp:"13180", prix:265000, surface:135, terrain:600, pieces:6, prix_m2:1963, median_m2:2680, decote:26.8, source:"SeLoger", vendeur:"agence", age:"2h05", dpe:"E", mots:["travaux","à rénover"], statut:"nouveau", est_enchere:false, url:"https://www.seloger.com/annonces/achat/maison/gignac-la-nerthe-13" },
  { id:4, score:88, niveau:"OPPORTUNITE EXCEPTIONNELLE", type:"Local commercial", ville:"Marseille 14e", cp:"13014", prix:142000, surface:85, terrain:null, pieces:null, prix_m2:1671, median_m2:2200, decote:24.0, source:"BienIci", vendeur:"particulier", age:"47min", dpe:"F", mots:["divorce","urgent"], statut:"nouveau", est_enchere:false, url:"https://www.bienici.com/recherche/achat/marseille-13014" },
  { id:5, score:95, niveau:"OPPORTUNITE EXCEPTIONNELLE", type:"Maison", ville:"Les Pennes-Mirabeau", cp:"13170", prix:310000, surface:158, terrain:850, pieces:7, prix_m2:1962, median_m2:3100, decote:36.7, source:"LeBonCoin", vendeur:"particulier", age:"12min", dpe:"C", mots:["succession","liquidation"], statut:"nouveau", est_enchere:true, url:"https://www.leboncoin.fr/ventes_immobilieres/les-pennes-mirabeau" },
  { id:6, score:67, niveau:"FORTE OPPORTUNITE", type:"Maison", ville:"Rognac", cp:"13340", prix:298000, surface:140, terrain:380, pieces:5, prix_m2:2129, median_m2:2750, decote:22.6, source:"SeLoger", vendeur:"agence", age:"4h30", dpe:"D", mots:["baisse de prix"], statut:"en_cours", est_enchere:false, url:"https://www.seloger.com/annonces/achat/maison/rognac-13" },
  { id:7, score:72, niveau:"FORTE OPPORTUNITE", type:"Parking", ville:"Marseille 2e", cp:"13002", prix:8500, surface:12, terrain:null, pieces:null, prix_m2:708, median_m2:1000, decote:29.2, source:"PAP", vendeur:"particulier", age:"3h20", dpe:null, mots:["urgent"], statut:"nouveau", est_enchere:false, url:"https://www.pap.fr/annonce/parking-marseille-2e" },
  { id:8, score:58, niveau:"OPPORTUNITE", type:"Terrain", ville:"Carry-le-Rouet", cp:"13620", prix:185000, surface:780, terrain:780, pieces:null, prix_m2:237, median_m2:310, decote:23.5, source:"BienIci", vendeur:"agence", age:"6h00", dpe:null, mots:["à saisir"], statut:"nouveau", est_enchere:false, url:"https://www.bienici.com/recherche/achat/carry-le-rouet-13620" },
  { id:9, score:62, niveau:"FORTE OPPORTUNITE", type:"Immeuble", ville:"Marseille 3e", cp:"13003", prix:520000, surface:280, terrain:null, pieces:8, prix_m2:1857, median_m2:2400, decote:22.6, source:"SeLoger", vendeur:"agence", age:"5h15", dpe:"E", mots:["travaux"], statut:"traite", est_enchere:false, url:"https://www.seloger.com/annonces/achat/immeuble/marseille-3e-13" },
  { id:10, score:44, niveau:"A SURVEILLER", type:"Maison", ville:"Chateauneuf-les-Martigues", cp:"13220", prix:340000, surface:148, terrain:500, pieces:6, prix_m2:2297, median_m2:2600, decote:11.7, source:"LeBonCoin", vendeur:"particulier", age:"8h45", dpe:"C", mots:[], statut:"nouveau", est_enchere:false, url:"https://www.leboncoin.fr/ventes_immobilieres/chateauneuf-les-martigues" },
  { id:11, score:76, niveau:"FORTE OPPORTUNITE", type:"Local commercial", ville:"Aix-en-Provence", cp:"13100", prix:198000, surface:110, terrain:null, pieces:null, prix_m2:1800, median_m2:2500, decote:28.0, source:"PAP", vendeur:"particulier", age:"1h55", dpe:"D", mots:["divorce","vente rapide"], statut:"nouveau", est_enchere:false, url:"https://www.pap.fr/annonce/local-commercial-aix-en-provence" },
];

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

function FluxTab({ S, colTpl, filtreType, setFiltreType, filtreScore, setFiltreScore, filtreVendeur, setFiltreVendeur, filtreFraicheur, setFiltreFraicheur, filteredAnnonces, selectedRow, setSelectedRow, handleStatut }) {
  return (
    <div className="si">
      {/* FILTRES */}
      <div style={{display:"flex",gap:"8px",marginBottom:"12px",flexWrap:"wrap",alignItems:"center"}}>
        <span style={{color:"#2a4060",fontSize:"10px"}}>TYPE</span>
        {[["tous","TOUS"],["maison","MAISONS"],["terrain","TERRAINS"],["local_commercial","LOCAUX"],["parking","PARKINGS"],["immeuble","IMMEUBLES"]].map(([v,l])=>(
          <button key={v} className={`fb ${filtreType===v?"on":""}`} onClick={()=>setFiltreType(v)}>{l}</button>
        ))}
        <div style={{width:"1px",height:"16px",background:"#0d2040",margin:"0 4px"}}/>
        <span style={{color:"#2a4060",fontSize:"10px"}}>SCORE</span>
        {[[0,"TOUS"],[50,">50"],[65,">65"],[80,">80"]].map(([v,l])=>(
          <button key={v} className={`fb ${filtreScore===v?"on":""}`} onClick={()=>setFiltreScore(v)}>{l}</button>
        ))}
        <div style={{width:"1px",height:"16px",background:"#0d2040",margin:"0 4px"}}/>
        <span style={{color:"#2a4060",fontSize:"10px"}}>VENDEUR</span>
        {[["tous","TOUS"],["particulier","PARTIC."],["agence","AGENCE"]].map(([v,l])=>(
          <button key={v} className={`fb ${filtreVendeur===v?"on":""}`} onClick={()=>setFiltreVendeur(v)}>{l}</button>
        ))}
        <div style={{width:"1px",height:"16px",background:"#0d2040",margin:"0 4px"}}/>
        <span style={{color:"#2a4060",fontSize:"10px"}}>FRAICHEUR</span>
        {[["tous","TOUS"],["1h","< 1H"],["24h","< 24H"]].map(([v,l])=>(
          <button key={v} className={`fb ${filtreFraicheur===v?"on":""}`} onClick={()=>setFiltreFraicheur(v)}>{l}</button>
        ))}
        <div style={{marginLeft:"auto",color:"#2a4060",fontSize:"10px"}}>{filteredAnnonces.length} résultats</div>
      </div>

      {/* TABLE */}
      <div style={{background:"#030c18",border:"1px solid #0d2040",borderRadius:"3px",overflow:"auto"}}>
        <div style={{display:"grid",gridTemplateColumns:colTpl,background:"#020810",borderBottom:"1px solid #0d2040",padding:"6px 0",minWidth:"1100px"}}>
          {["SCORE","NIVEAU","TYPE","VILLE","CP","PRIX","€/M²","MÉDIAN","DÉCOTE","M²","SOURCE","VENDEUR","PUB.","ACTIONS"].map((h,i)=>(
            <div key={i} style={{padding:"0 8px",color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",borderRight:i<13?"1px solid #0a1e30":"none"}}>{h}</div>
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
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"16px"}}>
        <div style={S.card}>
          <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"12px"}}>ZONE DE RECHERCHE</div>
          <div style={{color:"#c8d8e8",fontSize:"11px",lineHeight:2}}>
            <div><span style={{color:"#3a6080"}}>Centre:</span> Les Pennes-Mirabeau (13170)</div>
            <div><span style={{color:"#3a6080"}}>Rayon:</span> 30 km</div>
            <div><span style={{color:"#3a6080"}}>Département:</span> 13 - Bouches-du-Rhône</div>
            <div><span style={{color:"#3a6080"}}>Communes:</span> 45 communes surveillées</div>
          </div>
        </div>
        <div style={S.card}>
          <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"12px"}}>SOURCES ACTIVES</div>
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
          <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"12px"}}>CRITÈRES DE SCORING</div>
          <div style={{color:"#c8d8e8",fontSize:"11px",lineHeight:2}}>
            <div><span style={{color:"#3a6080"}}>Décote min:</span> 15% vs médiane DVF</div>
            <div><span style={{color:"#3a6080"}}>Mots-clés bonus:</span> succession, divorce, urgent, liquidation, mutation</div>
            <div><span style={{color:"#3a6080"}}>Vendeur bonus:</span> +5 pts si particulier</div>
            <div><span style={{color:"#3a6080"}}>Fraîcheur bonus:</span> +10 pts si {"<"} 1h</div>
            <div><span style={{color:"#3a6080"}}>DPE malus:</span> -5 pts si F/G</div>
          </div>
        </div>
        <div style={S.card}>
          <div style={{color:"#2a5070",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"12px"}}>ALERTES</div>
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

export default function ImmoSniperDashboard() {
  const [tab, setTab] = useState("flux");
  const [filtreType, setFiltreType] = useState("tous");
  const [filtreScore, setFiltreScore] = useState(0);
  const [filtreVendeur, setFiltreVendeur] = useState("tous");
  const [filtreFraicheur, setFiltreFraicheur] = useState("tous");
  const [selectedRow, setSelectedRow] = useState(null);
  const [now, setNow] = useState(new Date());
  const [annonces, setAnnonces] = useState(ANNONCES);

  useEffect(() => { const t = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(t); }, []);

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
  const decoteMoyenne = Math.round(annonces.reduce((s,a) => s+a.decote,0)/annonces.length*10)/10;
  const prixMedianMoyen = Math.round(annonces.filter(a=>a.median_m2).reduce((s,a)=>s+a.median_m2,0)/annonces.filter(a=>a.median_m2).length);
  const prochaine = [...ENCHERES].sort((a,b)=>a.date_audience-b.date_audience)[0];

  const handleStatut = (id, statut) => { setAnnonces(prev => prev.map(a => a.id===id ? {...a, statut} : a)); setSelectedRow(null); };

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
          <span style={{color:"#3a6080",fontSize:"10px"}}>SCAN SUIVANT</span>
          <span style={{color:"#60b8ff",fontSize:"11px"}}>42:17</span>
          <div style={{width:"1px",height:"18px",background:"#0d2040"}}/>
          <span style={{color:"#3a6080",fontSize:"10px"}}>HEURE</span>
          <span style={{color:"#c8d8e8",fontSize:"11px"}}>{now.toLocaleTimeString("fr-FR")}</span>
        </div>
      </div>

      {/* METRICS */}
      <div style={S.metrics}>
        {[
          {l:"ANNONCES SCANNÉES",v:"347",s:"Ce cycle",c:"#c8d8e8"},
          {l:"OPPORTUNITÉS",v:String(nbOpportunites),s:"Score ≥ 65",c:"#ffb300"},
          {l:"EXCEPTIONNELLES",v:String(nbExceptionnelles),s:"Score ≥ 80",c:"#00ff88"},
          {l:"ENCHÈRES ACTIVES",v:String(ENCHERES.length),s:"Dept. 13",c:"#ff6b35"},
          {l:"PRIX MÉDIAN",v:fmtM2(prixMedianMoyen),s:"DVF 2023",c:"#60b8ff"},
          {l:"DÉCOTE MOY.",v:"-"+decoteMoyenne+"%",s:"Annonces du jour",c:"#a78bfa"},
          {l:"PROCHAINE AUDIENCE",v:joursAvant(prochaine.date_audience)+"J",s:prochaine.ville,c:"#ff3b3b"},
        ].map((m,i)=>(
          <div key={i} style={{padding:"6px 12px",borderRight:i<6?"1px solid #0d2040":"none"}}>
            <div style={{color:"#3a6080",fontSize:"9px",letterSpacing:"0.1em",marginBottom:"2px"}}>{m.l}</div>
            <div className="mv" style={{fontSize:"22px",color:m.c,lineHeight:1}}>{m.v}</div>
            <div style={{color:"#2a4060",fontSize:"9px",marginTop:"2px"}}>{m.s}</div>
          </div>
        ))}
      </div>

      {/* NAV */}
      <div style={S.nav}>
        {[{id:"flux",l:"FLUX EN DIRECT",n:annonces.length},{id:"encheres",l:"ENCHÈRES ACTIVES",n:ENCHERES.length,u:true},{id:"stats",l:"STATISTIQUES"},{id:"params",l:"PARAMÈTRES"}].map(t=>(
          <button key={t.id} className="tb" onClick={()=>setTab(t.id)}
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
