import { useState, useMemo, useCallback } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import {
  ChevronDown, ChevronUp, HelpCircle, AlertTriangle, CheckCircle,
  XCircle, Home, Landmark, Wrench, Shield, Plug, Sofa, PiggyBank,
  Copy, RotateCcw, TrendingUp, Info
} from 'lucide-react';

const formatEuro = (n) => {
  if (n == null || isNaN(n)) return '0 €';
  const fixed = Math.round(n * 100) / 100;
  const parts = fixed.toFixed(2).split('.');
  const intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0');
  return `${intPart},${parts[1]}\u00A0€`;
};

const formatEuroShort = (n) => {
  if (n == null || isNaN(n)) return '0 €';
  const fixed = Math.round(n);
  return fixed.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0') + '\u00A0€';
};

const clamp = (val, min, max) => Math.max(min, Math.min(max, val));

const CONSTRUCTION_RANGES = {
  traditionnelle: { min: 1400, max: 1800, default: 1600 },
  bois: { min: 1600, max: 2200, default: 1900 },
  contemporaine: { min: 2000, max: 3500, default: 2500 },
};

const PRESTATIONS_COEFF = { standard: 0.85, moyen: 1.0, haut: 1.25 };
const FONDATION_COEFF = { dalle: 1.0, videsan: 1.05, soussol: 1.2 };
const NIVEAUX_COEFF = { 1: 1.0, 2: 0.95 };
const CHAUFFAGE_SURCOUT = { pac_air: 0, pac_geo: 8000, poele: 3000, chaudiere_gaz: 5000 };
const GARAGE_COUT_M2 = { aucun: 0, integre: 800, attenant: 700, carport: 300 };

const CHART_COLORS = ['#d4a853', '#e8c778', '#2dd4bf', '#818cf8', '#f472b6', '#a78bfa', '#fb923c', '#34d399'];

function TooltipIcon({ text }) {
  const [show, setShow] = useState(false);
  return (
    <span className="relative inline-block ml-1">
      <HelpCircle
        size={14}
        className="text-gray-500 hover:text-amber-400 cursor-help inline"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
      />
      {show && (
        <span className="absolute z-50 bottom-6 left-1/2 -translate-x-1/2 bg-gray-800 border border-gray-600 text-xs text-gray-300 rounded px-3 py-2 w-56 shadow-lg">
          {text}
        </span>
      )}
    </span>
  );
}

function AccordionModule({ id, title, icon: Icon, isOpen, onToggle, children }) {
  return (
    <div className="mb-3 rounded-lg border border-gray-700/50 bg-gray-900/80 shadow-lg overflow-hidden border-l-4 border-l-amber-600/60">
      <button
        onClick={() => onToggle(id)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Icon size={18} className="text-amber-400" />
          <span className="font-display text-lg font-semibold text-amber-100">{title}</span>
        </div>
        {isOpen ? <ChevronUp size={18} className="text-gray-400" /> : <ChevronDown size={18} className="text-gray-400" />}
      </button>
      {isOpen && <div className="px-4 pb-4 fade-in space-y-4">{children}</div>}
    </div>
  );
}

function NumberInput({ label, value, onChange, min = 0, max, step = 1, suffix, tooltip }) {
  return (
    <div>
      <label className="block text-sm text-gray-400 mb-1">
        {label}{tooltip && <TooltipIcon text={tooltip} />}
      </label>
      <div className="flex items-center gap-2">
        <input
          type="number"
          value={value}
          min={min}
          max={max}
          step={step}
          onChange={(e) => onChange(Math.max(min, Number(e.target.value) || 0))}
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white font-mono text-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
        />
        {suffix && <span className="text-gray-500 text-sm whitespace-nowrap">{suffix}</span>}
      </div>
    </div>
  );
}

function SliderInput({ label, value, onChange, min, max, step = 1, suffix = '', displayValue, tooltip }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <label className="text-sm text-gray-400">
          {label}{tooltip && <TooltipIcon text={tooltip} />}
        </label>
        <span className="text-sm font-mono text-amber-300">{displayValue || value}{suffix}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full"
      />
    </div>
  );
}

function CheckboxInput({ label, checked, onChange, tooltip }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer group">
      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${checked ? 'bg-amber-600 border-amber-500' : 'border-gray-600 bg-gray-800'}`}>
        {checked && <CheckCircle size={14} className="text-white" />}
      </div>
      <span className="text-sm text-gray-300 group-hover:text-gray-100">{label}</span>
      {tooltip && <TooltipIcon text={tooltip} />}
    </label>
  );
}

function ToggleGroup({ options, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-1">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1.5 rounded text-sm font-medium transition-all ${
            value === opt.value
              ? 'bg-amber-600 text-white shadow-lg shadow-amber-600/25'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}


export default function ConstructionCostCalculator() {
  // === MODULE 1 - TERRAIN ===
  const [prixTerrain, setPrixTerrain] = useState(80000);
  const [fraisNotairePct, setFraisNotairePct] = useState(7.5);
  const [fraisGeometre, setFraisGeometre] = useState(1500);
  const [etudeSol, setEtudeSol] = useState(true);
  const [etudeSolMontant, setEtudeSolMontant] = useState(2500);
  const [terrainViabilise, setTerrainViabilise] = useState(true);
  const [viabEau, setViabEau] = useState(3000);
  const [viabElec, setViabElec] = useState(3500);
  const [viabGaz, setViabGaz] = useState(4000);
  const [viabAssainissement, setViabAssainissement] = useState(6000);
  const [viabTelecom, setViabTelecom] = useState(1500);
  const [tauxCommunal, setTauxCommunal] = useState(1.7);

  // === MODULE 2 - CONSTRUCTION ===
  const [shab, setShab] = useState(100);
  const [sdpAuto, setSdpAuto] = useState(true);
  const [sdpManuel, setSdpManuel] = useState(110);
  const [typeConstruction, setTypeConstruction] = useState('traditionnelle');
  const [coutM2, setCoutM2] = useState(1600);
  const [niveaux, setNiveaux] = useState(1);
  const [fondation, setFondation] = useState('dalle');
  const [prestations, setPrestations] = useState('moyen');
  const [re2020, setRe2020] = useState(false);

  // === MODULE 3 - HONORAIRES ===
  const [architecte, setArchitecte] = useState(false);
  const [architectePct, setArchitectePct] = useState(12);
  const [maitreOeuvre, setMaitreOeuvre] = useState(true);
  const [maitreOeuvrePct, setMaitreOeuvrePct] = useState(6);
  const [dommagesOuvrage, setDommagesOuvrage] = useState(true);
  const [dommagesOuvragePct, setDommagesOuvragePct] = useState(3.5);
  const [bureauControle, setBureauControle] = useState(false);
  const [bureauControleMontant, setBureauControleMontant] = useState(2500);
  const [coordSPS, setCoordSPS] = useState(false);
  const [coordSPSMontant, setCoordSPSMontant] = useState(1500);

  // === MODULE 4 - RACCORDEMENTS ===
  const [raccElec, setRaccElec] = useState(2500);
  const [raccEau, setRaccEau] = useState(1500);
  const [assainissementType, setAssainissementType] = useState('collectif');
  const [raccAssCollectif, setRaccAssCollectif] = useState(3000);
  const [raccANC, setRaccANC] = useState(8000);
  const [redevanceArcheo, setRedevanceArcheo] = useState(false);

  // === MODULE 5 - EQUIPEMENTS ===
  const [cuisine, setCuisine] = useState(8000);
  const [nbSDB, setNbSDB] = useState(1);
  const [coutSDB, setCoutSDB] = useState(6000);
  const [chauffage, setChauffage] = useState('pac_air');
  const [climatisation, setClimatisation] = useState(false);
  const [climMontant, setClimMontant] = useState(6000);
  const [piscine, setPiscine] = useState(false);
  const [piscineMontant, setPiscineMontant] = useState(40000);
  const [terrasse, setTerrasse] = useState(5000);
  const [cloture, setCloture] = useState(3000);
  const [garage, setGarage] = useState('aucun');
  const [garageM2, setGarageM2] = useState(20);
  const [domotique, setDomotique] = useState(false);
  const [domotiqueMontant, setDomotiqueMontant] = useState(5000);

  // === MODULE 6 - PROVISIONS ===
  const [imprevusPct, setImprevusPct] = useState(10);
  const [ameublement, setAmeublement] = useState(15000);

  // === FINANCEMENT ===
  const [apport, setApport] = useState(30000);
  const [ptz, setPtz] = useState(false);
  const [ptzMontant, setPtzMontant] = useState(0);
  const [tauxNominal, setTauxNominal] = useState(3.5);
  const [duree, setDuree] = useState(25);
  const [revenuMensuel, setRevenuMensuel] = useState(4000);

  // === UI STATE ===
  const [openModules, setOpenModules] = useState(new Set(['terrain', 'construction']));
  const [showTVA, setShowTVA] = useState(false);
  const [financementOpen, setFinancementOpen] = useState(false);

  const toggleModule = useCallback((id) => {
    setOpenModules((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  const handleTypeChange = useCallback((type) => {
    setTypeConstruction(type);
    setCoutM2(CONSTRUCTION_RANGES[type].default);
  }, []);

  // === CALCULATIONS ===
  const sdp = useMemo(() => sdpAuto ? Math.round(shab * 1.1) : sdpManuel, [sdpAuto, shab, sdpManuel]);

  const calculations = useMemo(() => {
    const fraisNotaire = prixTerrain * fraisNotairePct / 100;
    const etudeSolCost = etudeSol ? etudeSolMontant : 0;
    const viabTotal = terrainViabilise ? 0 : (viabEau + viabElec + viabGaz + viabAssainissement + viabTelecom);
    const taxeAmenagement = 914 * sdp * tauxCommunal / 100;
    const terrainTotal = prixTerrain + fraisNotaire + fraisGeometre + etudeSolCost + viabTotal + taxeAmenagement;

    const prestCoeff = PRESTATIONS_COEFF[prestations];
    const fondCoeff = FONDATION_COEFF[fondation];
    const nivCoeff = NIVEAUX_COEFF[niveaux];
    const re2020Coeff = re2020 ? 1.08 : 1;
    const constructionBase = shab * coutM2 * prestCoeff * re2020Coeff * fondCoeff * nivCoeff;

    const honorairesTotal =
      (architecte ? constructionBase * architectePct / 100 : 0) +
      (maitreOeuvre ? constructionBase * maitreOeuvrePct / 100 : 0) +
      (bureauControle ? bureauControleMontant : 0) +
      (coordSPS ? coordSPSMontant : 0);

    const assurancesTotal = dommagesOuvrage ? constructionBase * dommagesOuvragePct / 100 : 0;

    const raccordementsTotal = raccElec + raccEau +
      (assainissementType === 'collectif' ? raccAssCollectif : raccANC) +
      (redevanceArcheo ? constructionBase * 0.004 : 0);

    const chauffSurcout = CHAUFFAGE_SURCOUT[chauffage] || 0;
    const garageCost = garage === 'aucun' ? 0 : garageM2 * (GARAGE_COUT_M2[garage] || 0);
    const equipementsTotal = cuisine + (nbSDB * coutSDB) + chauffSurcout +
      (climatisation ? climMontant : 0) + (piscine ? piscineMontant : 0) +
      terrasse + cloture + garageCost + (domotique ? domotiqueMontant : 0);

    const imprevusTotal = (constructionBase + equipementsTotal) * imprevusPct / 100;

    const totalHT = terrainTotal + constructionBase + honorairesTotal + assurancesTotal +
      raccordementsTotal + equipementsTotal + imprevusTotal + ameublement;

    const tva = showTVA ? totalHT * 0.055 : 0;
    const totalTTC = totalHT + tva;
    const coutM2SHAB = shab > 0 ? totalTTC / shab : 0;
    const coutM2SDP = sdp > 0 ? totalTTC / sdp : 0;

    return {
      terrainTotal, constructionBase, honorairesTotal, assurancesTotal,
      raccordementsTotal, equipementsTotal, imprevusTotal, totalHT,
      tva, totalTTC, coutM2SHAB, coutM2SDP, taxeAmenagement,
    };
  }, [prixTerrain, fraisNotairePct, fraisGeometre, etudeSol, etudeSolMontant,
    terrainViabilise, viabEau, viabElec, viabGaz, viabAssainissement, viabTelecom,
    tauxCommunal, sdp, shab, coutM2, prestations, fondation, niveaux, re2020,
    architecte, architectePct, maitreOeuvre, maitreOeuvrePct, bureauControle,
    bureauControleMontant, coordSPS, coordSPSMontant, dommagesOuvrage, dommagesOuvragePct,
    raccElec, raccEau, assainissementType, raccAssCollectif, raccANC, redevanceArcheo,
    cuisine, nbSDB, coutSDB, chauffage, climatisation, climMontant, piscine, piscineMontant,
    terrasse, cloture, garage, garageM2, domotique, domotiqueMontant, imprevusPct, ameublement, showTVA]);

  const financement = useMemo(() => {
    const montantEmprunt = Math.max(0, calculations.totalTTC - apport - (ptz ? ptzMontant : 0));
    const tauxMensuel = tauxNominal / 100 / 12;
    const nbMensualites = duree * 12;
    let mensualite = 0;
    if (tauxMensuel > 0 && montantEmprunt > 0) {
      mensualite = montantEmprunt * tauxMensuel / (1 - Math.pow(1 + tauxMensuel, -nbMensualites));
    } else if (montantEmprunt > 0) {
      mensualite = montantEmprunt / nbMensualites;
    }
    const coutInterets = mensualite * nbMensualites - montantEmprunt;
    const tauxEffort = revenuMensuel > 0 ? (mensualite / revenuMensuel) * 100 : 0;
    return { montantEmprunt, mensualite, coutInterets, tauxEffort };
  }, [calculations.totalTTC, apport, ptz, ptzMontant, tauxNominal, duree, revenuMensuel]);

  // === COHERENCE BADGE ===
  const coherence = useMemo(() => {
    const range = CONSTRUCTION_RANGES[typeConstruction];
    const coutConstM2 = shab > 0 ? calculations.constructionBase / shab : 0;
    const midRange = (range.min + range.max) / 2;
    const ecart = Math.abs(coutConstM2 - midRange) / midRange;
    if (imprevusPct < 8 || ecart > 0.3) return { color: 'red', label: 'Attention', icon: XCircle };
    if (ecart > 0.15) return { color: 'orange', label: 'À vérifier', icon: AlertTriangle };
    return { color: 'green', label: 'Cohérent', icon: CheckCircle };
  }, [typeConstruction, calculations.constructionBase, shab, imprevusPct]);

  const coherenceColors = { red: 'text-red-400 bg-red-900/30 border-red-500/50', orange: 'text-orange-400 bg-orange-900/30 border-orange-500/50', green: 'text-green-400 bg-green-900/30 border-green-500/50' };

  // === CHART DATA ===
  const chartData = useMemo(() => [
    { name: 'Terrain', value: calculations.terrainTotal, color: CHART_COLORS[0] },
    { name: 'Construction', value: calculations.constructionBase, color: CHART_COLORS[1] },
    { name: 'Honoraires', value: calculations.honorairesTotal, color: CHART_COLORS[2] },
    { name: 'Assurances', value: calculations.assurancesTotal, color: CHART_COLORS[3] },
    { name: 'Raccordements', value: calculations.raccordementsTotal, color: CHART_COLORS[4] },
    { name: 'Équipements', value: calculations.equipementsTotal, color: CHART_COLORS[5] },
    { name: 'Imprévus', value: calculations.imprevusTotal, color: CHART_COLORS[6] },
    { name: 'Ameublement', value: ameublement, color: CHART_COLORS[7] },
  ].filter(d => d.value > 0), [calculations, ameublement]);

  // === RESET ===
  const handleReset = useCallback(() => {
    setPrixTerrain(80000); setFraisNotairePct(7.5); setFraisGeometre(1500);
    setEtudeSol(true); setEtudeSolMontant(2500); setTerrainViabilise(true);
    setViabEau(3000); setViabElec(3500); setViabGaz(4000); setViabAssainissement(6000); setViabTelecom(1500);
    setTauxCommunal(1.7); setShab(100); setSdpAuto(true); setSdpManuel(110);
    setTypeConstruction('traditionnelle'); setCoutM2(1600); setNiveaux(1); setFondation('dalle');
    setPrestations('moyen'); setRe2020(false); setArchitecte(false); setArchitectePct(12);
    setMaitreOeuvre(true); setMaitreOeuvrePct(6); setDommagesOuvrage(true); setDommagesOuvragePct(3.5);
    setBureauControle(false); setBureauControleMontant(2500); setCoordSPS(false); setCoordSPSMontant(1500);
    setRaccElec(2500); setRaccEau(1500); setAssainissementType('collectif'); setRaccAssCollectif(3000);
    setRaccANC(8000); setRedevanceArcheo(false); setCuisine(8000); setNbSDB(1); setCoutSDB(6000);
    setChauffage('pac_air'); setClimatisation(false); setClimMontant(6000); setPiscine(false);
    setPiscineMontant(40000); setTerrasse(5000); setCloture(3000); setGarage('aucun'); setGarageM2(20);
    setDomotique(false); setDomotiqueMontant(5000); setImprevusPct(10); setAmeublement(15000);
    setApport(30000); setPtz(false); setPtzMontant(0); setTauxNominal(3.5); setDuree(25);
    setRevenuMensuel(4000); setShowTVA(false);
    setOpenModules(new Set(['terrain', 'construction']));
  }, []);

  // === COPY RECAP ===
  const handleCopy = useCallback(() => {
    const lines = [
      'RÉCAPITULATIF COÛT CONSTRUCTION',
      '═══════════════════════════════',
      `Terrain total : ${formatEuro(calculations.terrainTotal)}`,
      `Construction : ${formatEuro(calculations.constructionBase)}`,
      `Honoraires : ${formatEuro(calculations.honorairesTotal)}`,
      `Assurances : ${formatEuro(calculations.assurancesTotal)}`,
      `Raccordements : ${formatEuro(calculations.raccordementsTotal)}`,
      `Équipements : ${formatEuro(calculations.equipementsTotal)}`,
      `Imprévus : ${formatEuro(calculations.imprevusTotal)}`,
      `Ameublement : ${formatEuro(ameublement)}`,
      '───────────────────────────────',
      `TOTAL HT : ${formatEuro(calculations.totalHT)}`,
      showTVA ? `TVA 5,5% : ${formatEuro(calculations.tva)}` : '',
      `TOTAL TTC : ${formatEuro(calculations.totalTTC)}`,
      '',
      `Coût/m² SHAB : ${formatEuro(calculations.coutM2SHAB)}`,
      `Coût/m² SDP : ${formatEuro(calculations.coutM2SDP)}`,
    ].filter(Boolean).join('\n');
    navigator.clipboard.writeText(lines);
  }, [calculations, ameublement, showTVA]);

  const cRange = CONSTRUCTION_RANGES[typeConstruction];


  // === RENDER ===
  return (
    <div className="min-h-screen pb-12">
      {/* HEADER */}
      <header className="text-center py-8 px-4">
        <h1 className="font-display text-4xl md:text-5xl font-bold text-amber-100 tracking-tight">
          Calculette Coût Construction
        </h1>
        <p className="text-gray-400 mt-2 font-mono text-sm">
          Estimation complète pour maison individuelle en France
        </p>
      </header>

      <div className="max-w-7xl mx-auto px-4 flex flex-col lg:flex-row gap-6">
        {/* LEFT COLUMN - FORM */}
        <div className="lg:w-[55%] space-y-0">

          {/* MODULE 1 - TERRAIN */}
          <AccordionModule id="terrain" title="Terrain" icon={Home} isOpen={openModules.has('terrain')} onToggle={toggleModule}>
            <NumberInput label="Prix d'achat du terrain" value={prixTerrain} onChange={setPrixTerrain} suffix="€" />
            <SliderInput label="Frais de notaire" value={fraisNotairePct} onChange={setFraisNotairePct}
              min={2} max={9} step={0.1} suffix="%" displayValue={fraisNotairePct.toFixed(1)}
              tooltip="Frais de notaire pour l'acquisition du terrain (7,5% en moyenne)" />
            <div className="text-xs text-gray-500 -mt-2">= {formatEuroShort(prixTerrain * fraisNotairePct / 100)}</div>
            <NumberInput label="Frais de géomètre" value={fraisGeometre} onChange={setFraisGeometre} suffix="€" />
            <div className="flex items-center gap-4">
              <CheckboxInput label="Étude de sol G1/G2" checked={etudeSol} onChange={setEtudeSol}
                tooltip="Étude géotechnique obligatoire dans certaines zones (loi ELAN)" />
              {etudeSol && (
                <input type="number" value={etudeSolMontant} min={0}
                  onChange={(e) => setEtudeSolMontant(Math.max(0, Number(e.target.value) || 0))}
                  className="w-28 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white font-mono text-sm" />
              )}
            </div>
            <CheckboxInput label="Terrain viabilisé" checked={terrainViabilise} onChange={setTerrainViabilise}
              tooltip="Si non viabilisé, les frais de raccordement au réseau seront ajoutés" />
            {!terrainViabilise && (
              <div className="ml-4 space-y-2 border-l-2 border-gray-700 pl-4">
                <NumberInput label="Eau" value={viabEau} onChange={setViabEau} suffix="€" />
                <NumberInput label="Électricité" value={viabElec} onChange={setViabElec} suffix="€" />
                <NumberInput label="Gaz" value={viabGaz} onChange={setViabGaz} suffix="€" />
                <NumberInput label="Assainissement" value={viabAssainissement} onChange={setViabAssainissement} suffix="€" />
                <NumberInput label="Télécom" value={viabTelecom} onChange={setViabTelecom} suffix="€" />
              </div>
            )}
            <SliderInput label="Taux communal (taxe d'aménagement)" value={tauxCommunal} onChange={setTauxCommunal}
              min={1} max={5} step={0.1} suffix="%" displayValue={tauxCommunal.toFixed(1)}
              tooltip="Taux voté par la commune. Base forfaitaire : 914 €/m² × SDP × taux" />
            <div className="text-xs text-gray-500 -mt-2">
              Taxe d'aménagement estimée : <span className="text-amber-400 font-mono">{formatEuroShort(calculations.taxeAmenagement)}</span>
            </div>
          </AccordionModule>

          {/* MODULE 2 - CONSTRUCTION */}
          <AccordionModule id="construction" title="Construction" icon={Landmark} isOpen={openModules.has('construction')} onToggle={toggleModule}>
            <NumberInput label="Surface habitable (SHAB)" value={shab} onChange={setShab} min={1} suffix="m²" />
            <div className="flex items-center gap-4">
              <CheckboxInput label="SDP auto (+10%)" checked={sdpAuto} onChange={setSdpAuto}
                tooltip="Surface de plancher = SHAB + 10% (murs, cloisons)" />
              {!sdpAuto && (
                <NumberInput label="SDP manuelle" value={sdpManuel} onChange={setSdpManuel} min={1} suffix="m²" />
              )}
              {sdpAuto && <span className="text-sm font-mono text-gray-400">SDP = {sdp} m²</span>}
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Type de construction</label>
              <ToggleGroup
                options={[
                  { value: 'traditionnelle', label: 'Traditionnelle' },
                  { value: 'bois', label: 'Ossature bois' },
                  { value: 'contemporaine', label: 'Contemporaine' },
                ]}
                value={typeConstruction}
                onChange={handleTypeChange}
              />
            </div>

            <SliderInput label={`Coût au m² (${cRange.min} – ${cRange.max} €)`}
              value={coutM2} onChange={setCoutM2}
              min={cRange.min} max={cRange.max} step={10} suffix=" €/m²" />

            <div>
              <label className="block text-sm text-gray-400 mb-2">Nombre de niveaux</label>
              <ToggleGroup
                options={[{ value: 1, label: 'Plain-pied' }, { value: 2, label: 'R+1 (étage)' }]}
                value={niveaux} onChange={setNiveaux} />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Type de fondation</label>
              <ToggleGroup
                options={[
                  { value: 'dalle', label: 'Dalle' },
                  { value: 'videsan', label: 'Vide sanitaire' },
                  { value: 'soussol', label: 'Sous-sol' },
                ]}
                value={fondation} onChange={setFondation} />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Niveau de prestations</label>
              <ToggleGroup
                options={[
                  { value: 'standard', label: 'Standard (×0,85)' },
                  { value: 'moyen', label: 'Moyen gamme' },
                  { value: 'haut', label: 'Haut de gamme (×1,25)' },
                ]}
                value={prestations} onChange={setPrestations} />
            </div>

            <CheckboxInput label="RE2020 (+8%)" checked={re2020} onChange={setRe2020}
              tooltip="Surcoût lié à la réglementation environnementale RE2020" />

            {shab > 150 && (
              <div className="flex items-center gap-2 bg-orange-900/30 border border-orange-500/50 rounded px-3 py-2">
                <AlertTriangle size={16} className="text-orange-400 flex-shrink-0" />
                <span className="text-sm text-orange-300">Surface {'>'} 150 m² : recours à un architecte obligatoire (loi du 3 janvier 1977)</span>
              </div>
            )}
          </AccordionModule>

          {/* MODULE 3 - HONORAIRES ET ASSURANCES */}
          <AccordionModule id="honoraires" title="Honoraires et Assurances" icon={Shield} isOpen={openModules.has('honoraires')} onToggle={toggleModule}>
            <div className="space-y-3">
              <CheckboxInput label="Architecte" checked={architecte} onChange={setArchitecte}
                tooltip={shab > 150 ? 'Obligatoire au-delà de 150 m² SHAB' : 'Facultatif en dessous de 150 m² SHAB'} />
              {architecte && (
                <SliderInput label="Honoraires architecte" value={architectePct} onChange={setArchitectePct}
                  min={6} max={18} step={0.5} suffix="%" displayValue={architectePct.toFixed(1)} />
              )}
            </div>
            <div className="space-y-3">
              <CheckboxInput label="Maître d'œuvre" checked={maitreOeuvre} onChange={setMaitreOeuvre}
                tooltip="Pilotage du chantier si pas d'architecte" />
              {maitreOeuvre && (
                <SliderInput label="Honoraires MOE" value={maitreOeuvrePct} onChange={setMaitreOeuvrePct}
                  min={3} max={12} step={0.5} suffix="%" displayValue={maitreOeuvrePct.toFixed(1)} />
              )}
            </div>
            <div className="space-y-3">
              <CheckboxInput label="Assurance Dommages-Ouvrage" checked={dommagesOuvrage} onChange={setDommagesOuvrage}
                tooltip="Obligatoire pour le maître d'ouvrage (art. L242-1 Code des assurances)" />
              {dommagesOuvrage && (
                <>
                  <SliderInput label="Taux DO" value={dommagesOuvragePct} onChange={setDommagesOuvragePct}
                    min={1} max={8} step={0.1} suffix="%" displayValue={dommagesOuvragePct.toFixed(1)} />
                  <div className="flex items-center gap-2 bg-blue-900/20 border border-blue-500/30 rounded px-3 py-2">
                    <Info size={14} className="text-blue-400 flex-shrink-0" />
                    <span className="text-xs text-blue-300">L'assurance DO est légalement obligatoire (art. L242-1 Code des assurances)</span>
                  </div>
                </>
              )}
            </div>
            <div className="flex items-center gap-4">
              <CheckboxInput label="Bureau de contrôle" checked={bureauControle} onChange={setBureauControle} />
              {bureauControle && (
                <input type="number" value={bureauControleMontant} min={0}
                  onChange={(e) => setBureauControleMontant(Math.max(0, Number(e.target.value) || 0))}
                  className="w-28 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white font-mono text-sm" />
              )}
            </div>
            <div className="flex items-center gap-4">
              <CheckboxInput label="Coordinateur SPS" checked={coordSPS} onChange={setCoordSPS}
                tooltip="Sécurité et Protection de la Santé sur chantier" />
              {coordSPS && (
                <input type="number" value={coordSPSMontant} min={0}
                  onChange={(e) => setCoordSPSMontant(Math.max(0, Number(e.target.value) || 0))}
                  className="w-28 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white font-mono text-sm" />
              )}
            </div>
          </AccordionModule>


          {/* MODULE 4 - RACCORDEMENTS */}
          <AccordionModule id="raccordements" title="Raccordements et Taxes" icon={Plug} isOpen={openModules.has('raccordements')} onToggle={toggleModule}>
            <NumberInput label="Raccordement ENEDIS (électrique)" value={raccElec} onChange={setRaccElec} suffix="€" />
            <NumberInput label="Raccordement eau potable" value={raccEau} onChange={setRaccEau} suffix="€" />
            <div>
              <label className="block text-sm text-gray-400 mb-2">Type d'assainissement</label>
              <ToggleGroup
                options={[
                  { value: 'collectif', label: 'Collectif' },
                  { value: 'autonome', label: 'Autonome (ANC)' },
                ]}
                value={assainissementType} onChange={setAssainissementType} />
            </div>
            {assainissementType === 'collectif' ? (
              <NumberInput label="Raccordement assainissement collectif" value={raccAssCollectif} onChange={setRaccAssCollectif} suffix="€" />
            ) : (
              <NumberInput label="Assainissement autonome (ANC)" value={raccANC} onChange={setRaccANC} suffix="€"
                tooltip="Filière d'assainissement non collectif (fosse, micro-station...)" />
            )}
            <CheckboxInput label="Redevance d'archéologie préventive (0,40%)" checked={redevanceArcheo} onChange={setRedevanceArcheo}
              tooltip="0,40% du coût de construction, due pour les permis de construire" />
          </AccordionModule>

          {/* MODULE 5 - EQUIPEMENTS */}
          <AccordionModule id="equipements" title="Aménagements et Équipements" icon={Sofa} isOpen={openModules.has('equipements')} onToggle={toggleModule}>
            <SliderInput label="Cuisine équipée" value={cuisine} onChange={setCuisine}
              min={3000} max={30000} step={500} displayValue={formatEuroShort(cuisine)} />
            <div className="grid grid-cols-2 gap-3">
              <NumberInput label="Nombre de SDB" value={nbSDB} onChange={(v) => setNbSDB(clamp(v, 1, 5))} min={1} max={5} />
              <NumberInput label="Coût par SDB" value={coutSDB} onChange={setCoutSDB} suffix="€" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Système de chauffage</label>
              <select value={chauffage} onChange={(e) => setChauffage(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:border-amber-500 focus:outline-none">
                <option value="pac_air">PAC air/eau (+0 €)</option>
                <option value="pac_geo">PAC géothermique (+8 000 €)</option>
                <option value="poele">Poêle à granulés (+3 000 €)</option>
                <option value="chaudiere_gaz">Chaudière gaz (+5 000 €)</option>
              </select>
            </div>
            <div className="flex items-center gap-4">
              <CheckboxInput label="Climatisation réversible" checked={climatisation} onChange={setClimatisation} />
              {climatisation && (
                <input type="number" value={climMontant} min={0}
                  onChange={(e) => setClimMontant(Math.max(0, Number(e.target.value) || 0))}
                  className="w-28 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white font-mono text-sm" />
              )}
            </div>
            <div className="space-y-2">
              <CheckboxInput label="Piscine" checked={piscine} onChange={setPiscine} />
              {piscine && (
                <SliderInput label="Budget piscine" value={piscineMontant} onChange={setPiscineMontant}
                  min={25000} max={80000} step={1000} displayValue={formatEuroShort(piscineMontant)} />
              )}
            </div>
            <SliderInput label="Terrasse / aménagements extérieurs" value={terrasse} onChange={setTerrasse}
              min={0} max={30000} step={500} displayValue={formatEuroShort(terrasse)} />
            <SliderInput label="Clôture / portail" value={cloture} onChange={setCloture}
              min={0} max={15000} step={500} displayValue={formatEuroShort(cloture)} />
            <div>
              <label className="block text-sm text-gray-400 mb-2">Garage</label>
              <ToggleGroup
                options={[
                  { value: 'aucun', label: 'Aucun' },
                  { value: 'integre', label: 'Intégré' },
                  { value: 'attenant', label: 'Attenant' },
                  { value: 'carport', label: 'Carport' },
                ]}
                value={garage} onChange={setGarage} />
            </div>
            {garage !== 'aucun' && (
              <NumberInput label="Surface garage" value={garageM2} onChange={setGarageM2} min={10} max={60} suffix="m²" />
            )}
            <div className="flex items-center gap-4">
              <CheckboxInput label="Domotique" checked={domotique} onChange={setDomotique} />
              {domotique && (
                <input type="number" value={domotiqueMontant} min={0}
                  onChange={(e) => setDomotiqueMontant(Math.max(0, Number(e.target.value) || 0))}
                  className="w-28 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white font-mono text-sm" />
              )}
            </div>
          </AccordionModule>

          {/* MODULE 6 - PROVISIONS */}
          <AccordionModule id="provisions" title="Provisions et Imprévus" icon={PiggyBank} isOpen={openModules.has('provisions')} onToggle={toggleModule}>
            <SliderInput label="Provision pour imprévus" value={imprevusPct} onChange={setImprevusPct}
              min={5} max={20} step={0.5} suffix="%" displayValue={imprevusPct.toFixed(1)} />
            {imprevusPct < 8 && (
              <div className="flex items-center gap-2 bg-red-900/30 border border-red-500/50 rounded px-3 py-2">
                <AlertTriangle size={16} className="text-red-400 flex-shrink-0" />
                <span className="text-sm text-red-300">Provision inférieure à 8% — risque élevé de dépassement budgétaire</span>
              </div>
            )}
            <NumberInput label="Ameublement / déménagement" value={ameublement} onChange={setAmeublement} suffix="€" />
          </AccordionModule>

        </div>

        {/* RIGHT COLUMN - RECAP */}
        <div className="lg:w-[45%]">
          <div className="lg:sticky lg:top-4 space-y-4">

            {/* SUMMARY TABLE */}
            <div className="bg-gray-900/90 border border-gray-700/50 rounded-xl p-5 shadow-2xl">
              <h2 className="font-display text-2xl font-bold text-amber-100 mb-4">Récapitulatif</h2>

              <div className="space-y-2 text-sm">
                {[
                  { label: 'Terrain (achat + frais)', value: calculations.terrainTotal, color: CHART_COLORS[0] },
                  { label: 'Construction nette', value: calculations.constructionBase, color: CHART_COLORS[1] },
                  { label: 'Honoraires', value: calculations.honorairesTotal, color: CHART_COLORS[2] },
                  { label: 'Assurances', value: calculations.assurancesTotal, color: CHART_COLORS[3] },
                  { label: 'Raccordements & Taxes', value: calculations.raccordementsTotal, color: CHART_COLORS[4] },
                  { label: 'Équipements', value: calculations.equipementsTotal, color: CHART_COLORS[5] },
                  { label: 'Imprévus', value: calculations.imprevusTotal, color: CHART_COLORS[6] },
                  { label: 'Ameublement', value: ameublement, color: CHART_COLORS[7] },
                ].map((item) => (
                  <div key={item.label} className="flex justify-between items-center py-1">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                      <span className="text-gray-400">{item.label}</span>
                    </div>
                    <span className="font-mono text-gray-200">{formatEuroShort(item.value)}</span>
                  </div>
                ))}
              </div>

              <div className="border-t border-gray-700 mt-3 pt-3 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-300 font-medium">TOTAL HT</span>
                  <span className="font-mono text-gray-100 font-bold">{formatEuro(calculations.totalHT)}</span>
                </div>

                <div className="flex items-center gap-3">
                  <CheckboxInput label="TVA 5,5% (construction neuve)" checked={showTVA} onChange={setShowTVA}
                    tooltip="TVA à taux réduit sous conditions (accession sociale, zone ANRU...)" />
                </div>
                {showTVA && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">TVA 5,5%</span>
                    <span className="font-mono text-gray-300">{formatEuro(calculations.tva)}</span>
                  </div>
                )}

                <div className="flex justify-between items-center pt-2 border-t border-amber-600/30">
                  <span className="font-display text-xl font-bold text-amber-200">TOTAL TTC</span>
                  <span className="font-mono text-2xl font-bold text-amber-400">{formatEuroShort(calculations.totalTTC)}</span>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2">
                  <div className="bg-gray-800/50 rounded px-3 py-2 text-center">
                    <div className="text-xs text-gray-500">Coût/m² SHAB</div>
                    <div className="font-mono text-sm text-amber-300">{formatEuroShort(calculations.coutM2SHAB)}</div>
                  </div>
                  <div className="bg-gray-800/50 rounded px-3 py-2 text-center">
                    <div className="text-xs text-gray-500">Coût/m² SDP</div>
                    <div className="font-mono text-sm text-amber-300">{formatEuroShort(calculations.coutM2SDP)}</div>
                  </div>
                </div>
              </div>

              {/* COHERENCE BADGE */}
              <div className={`mt-4 flex items-center gap-2 rounded-lg border px-3 py-2 ${coherenceColors[coherence.color]}`}>
                <coherence.icon size={18} />
                <span className="text-sm font-medium">{coherence.label}</span>
                {coherence.color === 'red' && imprevusPct < 8 && (
                  <span className="text-xs ml-auto opacity-75">Provision imprévus trop faible</span>
                )}
              </div>
            </div>

            {/* DONUT CHART */}
            <div className="bg-gray-900/90 border border-gray-700/50 rounded-xl p-5 shadow-2xl">
              <h3 className="font-display text-lg font-semibold text-amber-100 mb-3">Répartition des coûts</h3>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} stroke="transparent" />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => formatEuroShort(value)}
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#e5e7eb',
                      fontSize: '13px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-1 mt-2">
                {chartData.map((d) => (
                  <div key={d.name} className="flex items-center gap-1.5 text-xs text-gray-400">
                    <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: d.color }} />
                    {d.name}
                  </div>
                ))}
              </div>
            </div>


            {/* FINANCEMENT */}
            <div className="bg-gray-900/90 border border-gray-700/50 rounded-xl shadow-2xl overflow-hidden">
              <button
                onClick={() => setFinancementOpen(!financementOpen)}
                className="w-full flex items-center justify-between px-5 py-3 hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <TrendingUp size={18} className="text-amber-400" />
                  <span className="font-display text-lg font-semibold text-amber-100">Financement</span>
                </div>
                {financementOpen ? <ChevronUp size={18} className="text-gray-400" /> : <ChevronDown size={18} className="text-gray-400" />}
              </button>
              {financementOpen && (
                <div className="px-5 pb-5 space-y-4 fade-in">
                  <NumberInput label="Apport personnel" value={apport} onChange={setApport} suffix="€" />
                  <div className="space-y-2">
                    <CheckboxInput label="Prêt à Taux Zéro (PTZ)" checked={ptz} onChange={setPtz}
                      tooltip="Primo-accédants, sous conditions de ressources et de zone" />
                    {ptz && (
                      <NumberInput label="Montant PTZ" value={ptzMontant} onChange={setPtzMontant} suffix="€" />
                    )}
                  </div>

                  <div className="bg-gray-800/50 rounded-lg px-3 py-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Montant à emprunter</span>
                      <span className="font-mono text-amber-300 font-bold">{formatEuro(financement.montantEmprunt)}</span>
                    </div>
                  </div>

                  <SliderInput label="Taux nominal" value={tauxNominal} onChange={setTauxNominal}
                    min={2.5} max={6} step={0.1} suffix="%" displayValue={tauxNominal.toFixed(1)} />
                  <SliderInput label="Durée du prêt" value={duree} onChange={setDuree}
                    min={15} max={30} step={1} suffix=" ans" />
                  <NumberInput label="Revenu net mensuel du foyer" value={revenuMensuel} onChange={setRevenuMensuel} suffix="€" />

                  <div className="bg-gray-800/60 rounded-lg p-4 space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Mensualité estimée</span>
                      <span className="font-mono text-amber-300 font-bold">{formatEuro(financement.mensualite)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Coût total des intérêts</span>
                      <span className="font-mono text-gray-300">{formatEuro(financement.coutInterets)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Taux d'effort</span>
                      <span className={`font-mono font-bold ${financement.tauxEffort > 35 ? 'text-red-400' : financement.tauxEffort > 33 ? 'text-orange-400' : 'text-green-400'}`}>
                        {financement.tauxEffort.toFixed(1)} %
                      </span>
                    </div>
                    {financement.tauxEffort > 35 && (
                      <div className="flex items-center gap-2 text-red-400 text-xs mt-1">
                        <AlertTriangle size={14} />
                        Taux d'effort supérieur à 35% — risque de refus bancaire
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* BUTTONS */}
            <div className="flex gap-3">
              <button
                onClick={handleReset}
                className="flex-1 flex items-center justify-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
              >
                <RotateCcw size={16} />
                Réinitialiser
              </button>
              <button
                onClick={handleCopy}
                className="flex-1 flex items-center justify-center gap-2 bg-amber-600/20 border border-amber-600/50 rounded-lg px-4 py-2.5 text-sm text-amber-300 hover:bg-amber-600/30 hover:text-amber-200 transition-colors"
              >
                <Copy size={16} />
                Copier le récapitulatif
              </button>
            </div>

          </div>
        </div>
      </div>

      {/* FOOTER */}
      <footer className="text-center py-6 mt-12 text-xs text-gray-600">
        <p>Estimation indicative — Les montants réels peuvent varier selon la localisation, les prestataires et les conditions du marché.</p>
        <p className="mt-1">TVA 5,5% applicable sous conditions spécifiques (accession sociale, zone ANRU). Consultez votre notaire.</p>
      </footer>
    </div>
  );
}
