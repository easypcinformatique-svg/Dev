import { useState, useMemo, useCallback, useEffect } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import {
  ChevronDown, ChevronUp, HelpCircle, AlertTriangle, CheckCircle,
  XCircle, Home, Landmark, Wrench, Shield, Plug, Sofa, PiggyBank,
  Copy, RotateCcw, TrendingUp, Info, Save, Download, Upload, Trash2
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
const ANC_TYPES = {
  fosse: { label: 'Fosse toutes eaux + épandage', default: 6000, min: 4000, max: 12000 },
  microstation: { label: 'Micro-station', default: 8000, min: 6000, max: 15000 },
  filtre_compact: { label: 'Filtre compact', default: 9000, min: 7000, max: 14000 },
  filtre_plante: { label: 'Filtre planté (phytoépuration)', default: 10000, min: 8000, max: 18000 },
};

const CHART_COLORS = ['#d4a853', '#e8c778', '#2dd4bf', '#818cf8', '#f472b6', '#a78bfa', '#fb923c', '#34d399'];

// Données par département : taux communal moyen, zone PTZ, taux départemental TA
const DEPT_DATA = {
  '01': { nom: 'Ain', taux: 3.0, tauxDept: 2.5, zone: 'C' },
  '02': { nom: 'Aisne', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '03': { nom: 'Allier', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '04': { nom: 'Alpes-de-Haute-Provence', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '05': { nom: 'Hautes-Alpes', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '06': { nom: 'Alpes-Maritimes', taux: 5.0, tauxDept: 2.5, zone: 'A' },
  '07': { nom: 'Ardèche', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '08': { nom: 'Ardennes', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '09': { nom: 'Ariège', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '10': { nom: 'Aube', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '11': { nom: 'Aude', taux: 3.0, tauxDept: 2.5, zone: 'C' },
  '12': { nom: 'Aveyron', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '13': { nom: 'Bouches-du-Rhône', taux: 5.0, tauxDept: 2.5, zone: 'A' },
  '14': { nom: 'Calvados', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '15': { nom: 'Cantal', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '16': { nom: 'Charente', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '17': { nom: 'Charente-Maritime', taux: 3.0, tauxDept: 2.5, zone: 'C' },
  '18': { nom: 'Cher', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '19': { nom: 'Corrèze', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '21': { nom: 'Côte-d\'Or', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '22': { nom: 'Côtes-d\'Armor', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '23': { nom: 'Creuse', taux: 1.5, tauxDept: 2.5, zone: 'C' },
  '24': { nom: 'Dordogne', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '25': { nom: 'Doubs', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '26': { nom: 'Drôme', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '27': { nom: 'Eure', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '28': { nom: 'Eure-et-Loir', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '29': { nom: 'Finistère', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '2A': { nom: 'Corse-du-Sud', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '2B': { nom: 'Haute-Corse', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '30': { nom: 'Gard', taux: 3.5, tauxDept: 2.5, zone: 'B2' },
  '31': { nom: 'Haute-Garonne', taux: 5.0, tauxDept: 2.5, zone: 'B1' },
  '32': { nom: 'Gers', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '33': { nom: 'Gironde', taux: 5.0, tauxDept: 2.5, zone: 'B1' },
  '34': { nom: 'Hérault', taux: 5.0, tauxDept: 2.5, zone: 'A' },
  '35': { nom: 'Ille-et-Vilaine', taux: 4.0, tauxDept: 2.5, zone: 'B1' },
  '36': { nom: 'Indre', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '37': { nom: 'Indre-et-Loire', taux: 3.0, tauxDept: 2.5, zone: 'B1' },
  '38': { nom: 'Isère', taux: 4.0, tauxDept: 2.5, zone: 'B1' },
  '39': { nom: 'Jura', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '40': { nom: 'Landes', taux: 3.0, tauxDept: 2.5, zone: 'C' },
  '41': { nom: 'Loir-et-Cher', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '42': { nom: 'Loire', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '43': { nom: 'Haute-Loire', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '44': { nom: 'Loire-Atlantique', taux: 5.0, tauxDept: 2.5, zone: 'B1' },
  '45': { nom: 'Loiret', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '46': { nom: 'Lot', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '47': { nom: 'Lot-et-Garonne', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '48': { nom: 'Lozère', taux: 1.5, tauxDept: 2.5, zone: 'C' },
  '49': { nom: 'Maine-et-Loire', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '50': { nom: 'Manche', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '51': { nom: 'Marne', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '52': { nom: 'Haute-Marne', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '53': { nom: 'Mayenne', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '54': { nom: 'Meurthe-et-Moselle', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '55': { nom: 'Meuse', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '56': { nom: 'Morbihan', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '57': { nom: 'Moselle', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '58': { nom: 'Nièvre', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '59': { nom: 'Nord', taux: 5.0, tauxDept: 2.5, zone: 'B1' },
  '60': { nom: 'Oise', taux: 3.5, tauxDept: 2.5, zone: 'B1' },
  '61': { nom: 'Orne', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '62': { nom: 'Pas-de-Calais', taux: 3.5, tauxDept: 2.5, zone: 'B2' },
  '63': { nom: 'Puy-de-Dôme', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '64': { nom: 'Pyrénées-Atlantiques', taux: 3.5, tauxDept: 2.5, zone: 'B2' },
  '65': { nom: 'Hautes-Pyrénées', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '66': { nom: 'Pyrénées-Orientales', taux: 3.5, tauxDept: 2.5, zone: 'B2' },
  '67': { nom: 'Bas-Rhin', taux: 4.0, tauxDept: 2.5, zone: 'B1' },
  '68': { nom: 'Haut-Rhin', taux: 3.5, tauxDept: 2.5, zone: 'B2' },
  '69': { nom: 'Rhône', taux: 5.0, tauxDept: 2.5, zone: 'A' },
  '70': { nom: 'Haute-Saône', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '71': { nom: 'Saône-et-Loire', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '72': { nom: 'Sarthe', taux: 2.5, tauxDept: 2.5, zone: 'B2' },
  '73': { nom: 'Savoie', taux: 3.5, tauxDept: 2.5, zone: 'B1' },
  '74': { nom: 'Haute-Savoie', taux: 5.0, tauxDept: 2.5, zone: 'A' },
  '75': { nom: 'Paris', taux: 5.0, tauxDept: 2.5, zone: 'Abis' },
  '76': { nom: 'Seine-Maritime', taux: 3.5, tauxDept: 2.5, zone: 'B1' },
  '77': { nom: 'Seine-et-Marne', taux: 4.0, tauxDept: 2.5, zone: 'A' },
  '78': { nom: 'Yvelines', taux: 5.0, tauxDept: 2.5, zone: 'Abis' },
  '79': { nom: 'Deux-Sèvres', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '80': { nom: 'Somme', taux: 3.0, tauxDept: 2.5, zone: 'B2' },
  '81': { nom: 'Tarn', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '82': { nom: 'Tarn-et-Garonne', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '83': { nom: 'Var', taux: 5.0, tauxDept: 2.5, zone: 'A' },
  '84': { nom: 'Vaucluse', taux: 3.5, tauxDept: 2.5, zone: 'B1' },
  '85': { nom: 'Vendée', taux: 3.0, tauxDept: 2.5, zone: 'C' },
  '86': { nom: 'Vienne', taux: 2.5, tauxDept: 2.5, zone: 'B2' },
  '87': { nom: 'Haute-Vienne', taux: 2.5, tauxDept: 2.5, zone: 'B2' },
  '88': { nom: 'Vosges', taux: 2.0, tauxDept: 2.5, zone: 'C' },
  '89': { nom: 'Yonne', taux: 2.5, tauxDept: 2.5, zone: 'C' },
  '90': { nom: 'Territoire de Belfort', taux: 2.5, tauxDept: 2.5, zone: 'B2' },
  '91': { nom: 'Essonne', taux: 5.0, tauxDept: 2.5, zone: 'A' },
  '92': { nom: 'Hauts-de-Seine', taux: 5.0, tauxDept: 2.5, zone: 'Abis' },
  '93': { nom: 'Seine-Saint-Denis', taux: 5.0, tauxDept: 2.5, zone: 'Abis' },
  '94': { nom: 'Val-de-Marne', taux: 5.0, tauxDept: 2.5, zone: 'Abis' },
  '95': { nom: 'Val-d\'Oise', taux: 5.0, tauxDept: 2.5, zone: 'A' },
  '971': { nom: 'Guadeloupe', taux: 3.0, tauxDept: 2.5, zone: 'C' },
  '972': { nom: 'Martinique', taux: 3.0, tauxDept: 2.5, zone: 'C' },
  '973': { nom: 'Guyane', taux: 3.0, tauxDept: 2.5, zone: 'C' },
  '974': { nom: 'La Réunion', taux: 3.0, tauxDept: 2.5, zone: 'B1' },
  '976': { nom: 'Mayotte', taux: 3.0, tauxDept: 2.5, zone: 'C' },
};

const getDeptFromCP = (cp) => {
  if (!cp || cp.length < 2) return null;
  if (cp.startsWith('97') && cp.length >= 3) return cp.substring(0, 3);
  if (cp.startsWith('20')) return cp[2] <= '1' ? '2A' : '2B';
  return cp.substring(0, 2);
};

const PTZ_LABELS = {
  'Abis': 'Zone A bis (Île-de-France)',
  'A': 'Zone A (grandes agglos)',
  'B1': 'Zone B1 (villes moyennes)',
  'B2': 'Zone B2 (périurbain)',
  'C': 'Zone C (rural)',
};

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

const formatThousands = (n) => {
  if (n == null || isNaN(n)) return '0';
  const s = String(Math.round(n * 100) / 100);
  const [int, dec] = s.split('.');
  const formatted = int.replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0');
  return dec ? `${formatted},${dec}` : formatted;
};

function NumberInput({ label, value, onChange, min = 0, max, step = 1, suffix, tooltip }) {
  const [focused, setFocused] = useState(false);
  const [rawValue, setRawValue] = useState(String(value));
  const handleChange = (e) => {
    const raw = e.target.value;
    setRawValue(raw);
    const cleaned = raw.replace(/\s/g, '').replace(',', '.');
    if (cleaned === '' || cleaned === '-') return;
    const num = Number(cleaned);
    if (!isNaN(num)) onChange(Math.max(min, max != null ? Math.min(max, num) : num));
  };
  const handleBlur = () => {
    setFocused(false);
    const cleaned = rawValue.replace(/\s/g, '').replace(',', '.');
    if (cleaned === '' || cleaned === '-' || isNaN(Number(cleaned))) {
      setRawValue(String(min));
      onChange(min);
    } else {
      const clamped = Math.max(min, max != null ? Math.min(max, Number(cleaned)) : Number(cleaned));
      setRawValue(String(clamped));
      onChange(clamped);
    }
  };
  const displayValue = focused ? rawValue : formatThousands(value);
  return (
    <div>
      <label className="block text-sm text-gray-400 mb-1">
        {label}{tooltip && <TooltipIcon text={tooltip} />}
      </label>
      <div className="flex items-center gap-2">
        <input
          type="text"
          inputMode="decimal"
          data-input-for={label}
          value={displayValue}
          onChange={handleChange}
          onBlur={handleBlur}
          onFocus={() => { setFocused(true); setRawValue(String(value)); }}
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white font-mono text-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
        />
        {suffix && <span className="text-gray-500 text-sm whitespace-nowrap">{suffix}</span>}
      </div>
    </div>
  );
}

function SliderInput({ label, value, onChange, min, max, step = 1, suffix = '', displayValue, tooltip }) {
  const [editing, setEditing] = useState(false);
  const [editVal, setEditVal] = useState('');
  const handleEditStart = () => {
    setEditing(true);
    setEditVal(String(value));
  };
  const handleEditEnd = () => {
    setEditing(false);
    const num = Number(editVal);
    if (!isNaN(num)) onChange(Math.max(min, Math.min(max, num)));
  };
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <label className="text-sm text-gray-400">
          {label}{tooltip && <TooltipIcon text={tooltip} />}
        </label>
        {editing ? (
          <input
            type="number"
            autoFocus
            value={editVal}
            min={min}
            max={max}
            step={step}
            onChange={(e) => setEditVal(e.target.value)}
            onBlur={handleEditEnd}
            onKeyDown={(e) => e.key === 'Enter' && handleEditEnd()}
            className="w-28 bg-gray-700 border border-amber-500 rounded px-2 py-0.5 text-amber-200 font-mono text-sm text-right focus:outline-none"
          />
        ) : (
          <button
            onClick={handleEditStart}
            className="bg-gray-800 border border-gray-600 rounded px-3 py-0.5 text-sm font-mono text-amber-300 hover:border-amber-500 hover:text-amber-200 transition-colors cursor-text min-w-[80px] text-right"
          >
            {displayValue || value}{suffix}
          </button>
        )}
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

function InlineNumberInput({ value, onChange }) {
  const [focused, setFocused] = useState(false);
  const [raw, setRaw] = useState(String(value));
  return (
    <input
      type="text"
      inputMode="decimal"
      value={focused ? raw : formatThousands(value)}
      onChange={(e) => {
        const v = e.target.value;
        setRaw(v);
        const cleaned = v.replace(/\s/g, '').replace(',', '.');
        if (cleaned === '') return;
        const num = Number(cleaned);
        if (!isNaN(num)) onChange(Math.max(0, num));
      }}
      onFocus={() => { setFocused(true); setRaw(String(value)); }}
      onBlur={() => { setFocused(false); if (raw.replace(/\s/g, '') === '') onChange(0); }}
      className="w-32 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white font-mono text-sm text-right focus:border-amber-500 focus:outline-none"
    />
  );
}

function CheckboxInput({ label, checked, onChange, tooltip }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex items-center gap-2 cursor-pointer group text-left"
    >
      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors flex-shrink-0 ${checked ? 'bg-amber-600 border-amber-500' : 'border-gray-600 bg-gray-800'}`}>
        {checked && <CheckCircle size={14} className="text-white" />}
      </div>
      <span className="text-sm text-gray-300 group-hover:text-gray-100">{label}</span>
      {tooltip && <TooltipIcon text={tooltip} />}
    </button>
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
  // === LOCALISATION ===
  const [codePostal, setCodePostal] = useState('');
  const [deptInfo, setDeptInfo] = useState(null);

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
  const [surfaceTerrain, setSurfaceTerrain] = useState(500);
  const [cesMax, setCesMax] = useState(40);

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
  const [ancType, setAncType] = useState('fosse');
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
  const [fraisDossier, setFraisDossier] = useState(1500);
  const [garantiePct, setGarantiePct] = useState(1.5);
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

  const handleCodePostalChange = useCallback((cp) => {
    const cleaned = cp.replace(/\D/g, '').slice(0, 5);
    setCodePostal(cleaned);
    if (cleaned.length >= 2) {
      const dept = getDeptFromCP(cleaned);
      const info = dept ? DEPT_DATA[dept] : null;
      setDeptInfo(info);
      if (info && cleaned.length === 5) {
        setTauxCommunal(info.taux);
      }
    } else {
      setDeptInfo(null);
    }
  }, []);

  // === CALCULATIONS ===
  const sdp = useMemo(() => sdpAuto ? Math.round(shab * 1.1) : sdpManuel, [sdpAuto, shab, sdpManuel]);
  const empriseAuSol = useMemo(() => {
    const shabParNiveau = niveaux === 2 ? Math.ceil(shab / 2) : shab;
    return Math.round(shabParNiveau * 1.15);
  }, [shab, niveaux]);
  const ces = useMemo(() => surfaceTerrain > 0 ? (empriseAuSol / surfaceTerrain * 100) : 0, [empriseAuSol, surfaceTerrain]);
  const empriseMaxAutorisee = useMemo(() => Math.round(surfaceTerrain * cesMax / 100), [surfaceTerrain, cesMax]);
  const empriseDepasse = empriseAuSol > empriseMaxAutorisee;

  const calculations = useMemo(() => {
    const fraisNotaire = prixTerrain * fraisNotairePct / 100;
    const etudeSolCost = etudeSol ? etudeSolMontant : 0;
    const viabTotal = terrainViabilise ? 0 : (viabEau + viabElec + viabGaz + viabAssainissement + viabTelecom);
    const taxeAmenagement = 914 * sdp * tauxCommunal / 100;
    const terrainTotal = prixTerrain + fraisNotaire + fraisGeometre + etudeSolCost + viabTotal + taxeAmenagement;

    const prestCoeff = PRESTATIONS_COEFF[prestations];
    const fondCoeff = FONDATION_COEFF[fondation];
    const nivCoeff = NIVEAUX_COEFF[niveaux];
    const re2020Coeff = re2020 ? 1.10 : 1;
    const constructionBase = shab * coutM2 * prestCoeff * re2020Coeff * fondCoeff * nivCoeff;

    const honorairesTotal =
      (architecte ? constructionBase * architectePct / 100 : 0) +
      (maitreOeuvre ? constructionBase * maitreOeuvrePct / 100 : 0) +
      (bureauControle ? bureauControleMontant : 0) +
      (coordSPS ? coordSPSMontant : 0);

    const assurancesTotal = dommagesOuvrage ? constructionBase * dommagesOuvragePct / 100 : 0;

    const ancCost = assainissementType === 'collectif' ? raccAssCollectif : raccANC;
    const raccordementsTotal = raccElec + raccEau + ancCost +
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
    const garantie = montantEmprunt * garantiePct / 100;
    const fraisBancairesTotal = fraisDossier + garantie;
    const tauxMensuel = tauxNominal / 100 / 12;
    const nbMensualites = duree * 12;
    let mensualite = 0;
    if (tauxMensuel > 0 && montantEmprunt > 0) {
      mensualite = montantEmprunt * tauxMensuel / (1 - Math.pow(1 + tauxMensuel, -nbMensualites));
    } else if (montantEmprunt > 0) {
      mensualite = montantEmprunt / nbMensualites;
    }
    const coutInterets = mensualite * nbMensualites - montantEmprunt;
    const coutTotalCredit = coutInterets + fraisBancairesTotal;
    const tauxEffort = revenuMensuel > 0 ? (mensualite / revenuMensuel) * 100 : 0;
    return { montantEmprunt, mensualite, coutInterets, coutTotalCredit, fraisBancairesTotal, garantie, tauxEffort };
  }, [calculations.totalTTC, apport, ptz, ptzMontant, tauxNominal, duree, revenuMensuel, fraisDossier, garantiePct]);

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
    setCodePostal(''); setDeptInfo(null);
    setPrixTerrain(80000); setFraisNotairePct(7.5); setFraisGeometre(1500);
    setEtudeSol(true); setEtudeSolMontant(2500); setTerrainViabilise(true);
    setViabEau(3000); setViabElec(3500); setViabGaz(4000); setViabAssainissement(6000); setViabTelecom(1500);
    setTauxCommunal(1.7); setSurfaceTerrain(500); setCesMax(40); setShab(100); setSdpAuto(true); setSdpManuel(110);
    setTypeConstruction('traditionnelle'); setCoutM2(1600); setNiveaux(1); setFondation('dalle');
    setPrestations('moyen'); setRe2020(false); setArchitecte(false); setArchitectePct(12);
    setMaitreOeuvre(true); setMaitreOeuvrePct(6); setDommagesOuvrage(true); setDommagesOuvragePct(3.5);
    setBureauControle(false); setBureauControleMontant(2500); setCoordSPS(false); setCoordSPSMontant(1500);
    setRaccElec(2500); setRaccEau(1500); setAssainissementType('collectif'); setRaccAssCollectif(3000);
    setRaccANC(8000); setAncType('fosse'); setRedevanceArcheo(false); setCuisine(8000); setNbSDB(1); setCoutSDB(6000);
    setChauffage('pac_air'); setClimatisation(false); setClimMontant(6000); setPiscine(false);
    setPiscineMontant(40000); setTerrasse(5000); setCloture(3000); setGarage('aucun'); setGarageM2(20);
    setDomotique(false); setDomotiqueMontant(5000); setImprevusPct(10); setAmeublement(15000);
    setFraisDossier(1500); setGarantiePct(1.5); setApport(30000); setPtz(false); setPtzMontant(0); setTauxNominal(3.5); setDuree(25);
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

  // === SAVE / LOAD ===
  const [saveMsg, setSaveMsg] = useState('');

  const getAllState = useCallback(() => ({
    codePostal, prixTerrain, fraisNotairePct, fraisGeometre, etudeSol, etudeSolMontant,
    terrainViabilise, viabEau, viabElec, viabGaz, viabAssainissement, viabTelecom,
    tauxCommunal, surfaceTerrain, cesMax, shab, sdpAuto, sdpManuel, typeConstruction,
    coutM2, niveaux, fondation, prestations, re2020, architecte, architectePct,
    maitreOeuvre, maitreOeuvrePct, dommagesOuvrage, dommagesOuvragePct, bureauControle,
    bureauControleMontant, coordSPS, coordSPSMontant, raccElec, raccEau,
    assainissementType, raccAssCollectif, raccANC, ancType, redevanceArcheo,
    cuisine, nbSDB, coutSDB, chauffage, climatisation, climMontant, piscine,
    piscineMontant, terrasse, cloture, garage, garageM2, domotique, domotiqueMontant,
    imprevusPct, ameublement, fraisDossier, garantiePct, apport, ptz, ptzMontant,
    tauxNominal, duree, revenuMensuel, showTVA,
    _savedAt: new Date().toISOString(),
  }), [codePostal, prixTerrain, fraisNotairePct, fraisGeometre, etudeSol, etudeSolMontant,
    terrainViabilise, viabEau, viabElec, viabGaz, viabAssainissement, viabTelecom,
    tauxCommunal, surfaceTerrain, cesMax, shab, sdpAuto, sdpManuel, typeConstruction,
    coutM2, niveaux, fondation, prestations, re2020, architecte, architectePct,
    maitreOeuvre, maitreOeuvrePct, dommagesOuvrage, dommagesOuvragePct, bureauControle,
    bureauControleMontant, coordSPS, coordSPSMontant, raccElec, raccEau,
    assainissementType, raccAssCollectif, raccANC, ancType, redevanceArcheo,
    cuisine, nbSDB, coutSDB, chauffage, climatisation, climMontant, piscine,
    piscineMontant, terrasse, cloture, garage, garageM2, domotique, domotiqueMontant,
    imprevusPct, ameublement, fraisDossier, garantiePct, apport, ptz, ptzMontant,
    tauxNominal, duree, revenuMensuel, showTVA]);

  const restoreState = useCallback((data) => {
    if (!data) return;
    if (data.codePostal != null) { setCodePostal(data.codePostal); const d = getDeptFromCP(data.codePostal); setDeptInfo(d ? DEPT_DATA[d] : null); }
    if (data.prixTerrain != null) setPrixTerrain(data.prixTerrain);
    if (data.fraisNotairePct != null) setFraisNotairePct(data.fraisNotairePct);
    if (data.fraisGeometre != null) setFraisGeometre(data.fraisGeometre);
    if (data.etudeSol != null) setEtudeSol(data.etudeSol);
    if (data.etudeSolMontant != null) setEtudeSolMontant(data.etudeSolMontant);
    if (data.terrainViabilise != null) setTerrainViabilise(data.terrainViabilise);
    if (data.viabEau != null) setViabEau(data.viabEau);
    if (data.viabElec != null) setViabElec(data.viabElec);
    if (data.viabGaz != null) setViabGaz(data.viabGaz);
    if (data.viabAssainissement != null) setViabAssainissement(data.viabAssainissement);
    if (data.viabTelecom != null) setViabTelecom(data.viabTelecom);
    if (data.tauxCommunal != null) setTauxCommunal(data.tauxCommunal);
    if (data.surfaceTerrain != null) setSurfaceTerrain(data.surfaceTerrain);
    if (data.cesMax != null) setCesMax(data.cesMax);
    if (data.shab != null) setShab(data.shab);
    if (data.sdpAuto != null) setSdpAuto(data.sdpAuto);
    if (data.sdpManuel != null) setSdpManuel(data.sdpManuel);
    if (data.typeConstruction != null) setTypeConstruction(data.typeConstruction);
    if (data.coutM2 != null) setCoutM2(data.coutM2);
    if (data.niveaux != null) setNiveaux(data.niveaux);
    if (data.fondation != null) setFondation(data.fondation);
    if (data.prestations != null) setPrestations(data.prestations);
    if (data.re2020 != null) setRe2020(data.re2020);
    if (data.architecte != null) setArchitecte(data.architecte);
    if (data.architectePct != null) setArchitectePct(data.architectePct);
    if (data.maitreOeuvre != null) setMaitreOeuvre(data.maitreOeuvre);
    if (data.maitreOeuvrePct != null) setMaitreOeuvrePct(data.maitreOeuvrePct);
    if (data.dommagesOuvrage != null) setDommagesOuvrage(data.dommagesOuvrage);
    if (data.dommagesOuvragePct != null) setDommagesOuvragePct(data.dommagesOuvragePct);
    if (data.bureauControle != null) setBureauControle(data.bureauControle);
    if (data.bureauControleMontant != null) setBureauControleMontant(data.bureauControleMontant);
    if (data.coordSPS != null) setCoordSPS(data.coordSPS);
    if (data.coordSPSMontant != null) setCoordSPSMontant(data.coordSPSMontant);
    if (data.raccElec != null) setRaccElec(data.raccElec);
    if (data.raccEau != null) setRaccEau(data.raccEau);
    if (data.assainissementType != null) setAssainissementType(data.assainissementType);
    if (data.raccAssCollectif != null) setRaccAssCollectif(data.raccAssCollectif);
    if (data.raccANC != null) setRaccANC(data.raccANC);
    if (data.ancType != null) setAncType(data.ancType);
    if (data.redevanceArcheo != null) setRedevanceArcheo(data.redevanceArcheo);
    if (data.cuisine != null) setCuisine(data.cuisine);
    if (data.nbSDB != null) setNbSDB(data.nbSDB);
    if (data.coutSDB != null) setCoutSDB(data.coutSDB);
    if (data.chauffage != null) setChauffage(data.chauffage);
    if (data.climatisation != null) setClimatisation(data.climatisation);
    if (data.climMontant != null) setClimMontant(data.climMontant);
    if (data.piscine != null) setPiscine(data.piscine);
    if (data.piscineMontant != null) setPiscineMontant(data.piscineMontant);
    if (data.terrasse != null) setTerrasse(data.terrasse);
    if (data.cloture != null) setCloture(data.cloture);
    if (data.garage != null) setGarage(data.garage);
    if (data.garageM2 != null) setGarageM2(data.garageM2);
    if (data.domotique != null) setDomotique(data.domotique);
    if (data.domotiqueMontant != null) setDomotiqueMontant(data.domotiqueMontant);
    if (data.imprevusPct != null) setImprevusPct(data.imprevusPct);
    if (data.ameublement != null) setAmeublement(data.ameublement);
    if (data.fraisDossier != null) setFraisDossier(data.fraisDossier);
    if (data.garantiePct != null) setGarantiePct(data.garantiePct);
    if (data.apport != null) setApport(data.apport);
    if (data.ptz != null) setPtz(data.ptz);
    if (data.ptzMontant != null) setPtzMontant(data.ptzMontant);
    if (data.tauxNominal != null) setTauxNominal(data.tauxNominal);
    if (data.duree != null) setDuree(data.duree);
    if (data.revenuMensuel != null) setRevenuMensuel(data.revenuMensuel);
    if (data.showTVA != null) setShowTVA(data.showTVA);
  }, []);

  const handleSave = useCallback(() => {
    const data = getAllState();
    localStorage.setItem('construction-calculator-save', JSON.stringify(data));
    setSaveMsg('Sauvegardé');
    setTimeout(() => setSaveMsg(''), 2500);
  }, [getAllState]);

  const handleLoad = useCallback(() => {
    const raw = localStorage.getItem('construction-calculator-save');
    if (!raw) { setSaveMsg('Aucune sauvegarde'); setTimeout(() => setSaveMsg(''), 2500); return; }
    try {
      restoreState(JSON.parse(raw));
      setSaveMsg('Restauré');
      setTimeout(() => setSaveMsg(''), 2500);
    } catch { setSaveMsg('Erreur de lecture'); setTimeout(() => setSaveMsg(''), 2500); }
  }, [restoreState]);

  const handleExportJSON = useCallback(() => {
    const data = getAllState();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `projet-construction-${codePostal || 'estimation'}-${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [getAllState, codePostal]);

  const handleImportJSON = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          restoreState(JSON.parse(ev.target.result));
          setSaveMsg('Importé');
          setTimeout(() => setSaveMsg(''), 2500);
        } catch { setSaveMsg('Fichier invalide'); setTimeout(() => setSaveMsg(''), 2500); }
      };
      reader.readAsText(file);
    };
    input.click();
  }, [restoreState]);

  const handleDeleteSave = useCallback(() => {
    localStorage.removeItem('construction-calculator-save');
    setSaveMsg('Sauvegarde supprimée');
    setTimeout(() => setSaveMsg(''), 2500);
  }, []);

  // Auto-load on mount
  useEffect(() => {
    const raw = localStorage.getItem('construction-calculator-save');
    if (raw) {
      try { restoreState(JSON.parse(raw)); } catch { /* corrupted save */ }
    }
  }, [restoreState]);

  const hasSavedData = typeof window !== 'undefined' && !!localStorage.getItem('construction-calculator-save');
  const savedDate = useMemo(() => {
    try {
      const raw = localStorage.getItem('construction-calculator-save');
      if (!raw) return null;
      const d = JSON.parse(raw)._savedAt;
      return d ? new Date(d).toLocaleString('fr-FR') : null;
    } catch { return null; }
  }, [saveMsg]);

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

          {/* CODE POSTAL - LOCALISATION */}
          <div className="mb-3 rounded-lg border border-amber-600/40 bg-gray-900/90 shadow-lg p-4 border-l-4 border-l-amber-500">
            <div className="flex items-center gap-2 mb-3">
              <Landmark size={18} className="text-amber-400" />
              <span className="font-display text-lg font-semibold text-amber-100">Localisation du projet</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Code postal
                  <TooltipIcon text="Permet de pré-remplir le taux communal de taxe d'aménagement et la zone PTZ" />
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={5}
                  value={codePostal}
                  onChange={(e) => handleCodePostalChange(e.target.value)}
                  placeholder="Ex : 33000"
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white font-mono text-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50 placeholder-gray-600"
                />
              </div>
              <div className="flex flex-col justify-end">
                {deptInfo ? (
                  <div className="space-y-1">
                    <div className="text-sm text-amber-300 font-medium">{deptInfo.nom}</div>
                    <div className="text-xs text-gray-400">
                      Zone PTZ : <span className="text-amber-200 font-mono">{deptInfo.zone}</span>
                      <span className="text-gray-600 ml-1">({PTZ_LABELS[deptInfo.zone]})</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-gray-600">Saisissez un code postal pour auto-remplir les données locales</div>
                )}
              </div>
            </div>
            {deptInfo && codePostal.length === 5 && (
              <div className="mt-2 flex items-center gap-2 bg-green-900/20 border border-green-700/30 rounded px-3 py-1.5">
                <CheckCircle size={14} className="text-green-400" />
                <span className="text-xs text-green-300">Taux communal TA mis à jour : {deptInfo.taux}% (moyenne départementale)</span>
              </div>
            )}
          </div>

          {/* MODULE 1 - TERRAIN */}
          <AccordionModule id="terrain" title="Terrain" icon={Home} isOpen={openModules.has('terrain')} onToggle={toggleModule}>
            <div className="grid grid-cols-2 gap-3">
              <NumberInput label="Prix d'achat du terrain" value={prixTerrain} onChange={setPrixTerrain} suffix="€" />
              <NumberInput label="Surface du terrain" value={surfaceTerrain} onChange={setSurfaceTerrain} min={1} suffix="m²"
                tooltip="Surface cadastrale de la parcelle" />
            </div>

            {/* CES et emprise autorisée */}
            <div className="bg-gray-800/50 rounded-lg p-3 space-y-2">
              <SliderInput label="CES max (PLU de votre commune)" value={cesMax} onChange={setCesMax}
                min={1} max={80} step={1} suffix="%"
                tooltip="Coefficient d'Emprise au Sol maximum autorisé par le Plan Local d'Urbanisme. Consultez le PLU de votre commune." />
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-700/40 rounded px-3 py-2 text-center">
                  <div className="text-xs text-gray-500">Emprise max autorisée</div>
                  <div className="font-mono text-lg text-green-400 font-bold">{empriseMaxAutorisee} m²</div>
                  <div className="text-xs text-gray-600">{surfaceTerrain} m² × {cesMax}%</div>
                </div>
                <div className={`rounded px-3 py-2 text-center ${empriseDepasse ? 'bg-red-900/30 border border-red-500/40' : 'bg-gray-700/40'}`}>
                  <div className="text-xs text-gray-500">Emprise projetée</div>
                  <div className={`font-mono text-lg font-bold ${empriseDepasse ? 'text-red-400' : 'text-amber-300'}`}>{empriseAuSol} m²</div>
                  <div className={`text-xs ${empriseDepasse ? 'text-red-400' : 'text-gray-600'}`}>
                    CES réel : {ces.toFixed(1)}%
                  </div>
                </div>
              </div>
              {empriseDepasse && (
                <div className="flex items-center gap-2 bg-red-900/30 border border-red-500/50 rounded px-3 py-2">
                  <AlertTriangle size={16} className="text-red-400 flex-shrink-0" />
                  <span className="text-sm text-red-300">
                    Emprise au sol ({empriseAuSol} m²) dépasse le maximum autorisé ({empriseMaxAutorisee} m²).
                    {niveaux === 1 ? ' Passez en R+1 pour réduire l\'emprise.' : ' Réduisez la SHAB ou augmentez la surface du terrain.'}
                  </span>
                </div>
              )}
            </div>
            <SliderInput label="Frais de notaire" value={fraisNotairePct} onChange={setFraisNotairePct}
              min={2} max={9} step={0.1} suffix="%" displayValue={fraisNotairePct.toFixed(1)}
              tooltip="Frais de notaire pour l'acquisition du terrain (7,5% en moyenne)" />
            <div className="text-xs text-gray-500 -mt-2">= {formatEuroShort(prixTerrain * fraisNotairePct / 100)}</div>
            <NumberInput label="Frais de géomètre" value={fraisGeometre} onChange={setFraisGeometre} suffix="€" />
            <div className="flex items-center gap-4">
              <CheckboxInput label="Étude de sol G1/G2" checked={etudeSol} onChange={setEtudeSol}
                tooltip="Étude géotechnique obligatoire dans certaines zones (loi ELAN)" />
              {etudeSol && (
                <InlineNumberInput value={etudeSolMontant} onChange={setEtudeSolMontant} />
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
              <div className="mt-1 text-xs text-gray-500">
                {niveaux === 1
                  ? 'Plain-pied : coût fondations plus élevé (emprise totale au sol)'
                  : 'R+1 : économie de -5% sur le coût/m² (emprise réduite, fondations plus petites)'}
                {' — '}
                <span className={`font-mono ${niveaux === 2 ? 'text-green-400' : 'text-gray-400'}`}>
                  coeff. ×{NIVEAUX_COEFF[niveaux].toFixed(2)}
                </span>
              </div>
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
              <div className="mt-1 text-xs text-gray-500">
                {fondation === 'dalle' && 'Dalle sur terre-plein : solution la plus économique'}
                {fondation === 'videsan' && 'Vide sanitaire : surcoût +5% (protection humidité, passage réseaux)'}
                {fondation === 'soussol' && 'Sous-sol : surcoût +20% (terrassement, murs enterrés, étanchéité)'}
                {' — '}
                <span className={`font-mono ${FONDATION_COEFF[fondation] > 1 ? 'text-orange-400' : 'text-gray-400'}`}>
                  coeff. ×{FONDATION_COEFF[fondation].toFixed(2)}
                </span>
                {FONDATION_COEFF[fondation] > 1 && (
                  <span className="text-orange-400 font-mono ml-1">
                    (+{formatEuroShort(Math.round(shab * coutM2 * PRESTATIONS_COEFF[prestations] * (FONDATION_COEFF[fondation] - 1)))})
                  </span>
                )}
              </div>
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

            <div className="space-y-2">
              <CheckboxInput label="RE2020" checked={re2020} onChange={(v) => {
                setRe2020(v);
                if (v && chauffage === 'chaudiere_gaz') setChauffage('pac_air');
              }}
                tooltip="Obligatoire depuis 2022. Surcoût ~10% (isolation renforcée, VMC double flux, ENR). Interdit la chaudière gaz en chauffage principal." />
              {re2020 && (
                <div className="ml-6 space-y-1 text-xs text-gray-500">
                  <div className="flex items-center gap-1"><CheckCircle size={12} className="text-green-500" /> Isolation renforcée (Bbio optimisé)</div>
                  <div className="flex items-center gap-1"><CheckCircle size={12} className="text-green-500" /> VMC double flux recommandée</div>
                  <div className="flex items-center gap-1"><CheckCircle size={12} className="text-green-500" /> Énergie renouvelable obligatoire</div>
                  <div className="flex items-center gap-1"><XCircle size={12} className="text-red-500" /> Chaudière gaz seule interdite</div>
                  <div className="flex items-center gap-1"><Info size={12} className="text-blue-400" /> Surcoût estimé : +10% sur le coût construction</div>
                </div>
              )}
            </div>

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
                <>
                  <SliderInput label="Honoraires architecte" value={architectePct} onChange={setArchitectePct}
                    min={6} max={18} step={0.5} suffix="%" displayValue={architectePct.toFixed(1)} />
                  <div className="text-xs text-gray-500 -mt-2">= {formatEuroShort(calculations.constructionBase * architectePct / 100)}</div>
                </>
              )}
            </div>
            <div className="space-y-3">
              <CheckboxInput label="Maître d'œuvre" checked={maitreOeuvre} onChange={setMaitreOeuvre}
                tooltip="Pilotage du chantier si pas d'architecte" />
              {maitreOeuvre && (
                <>
                  <SliderInput label="Honoraires MOE" value={maitreOeuvrePct} onChange={setMaitreOeuvrePct}
                    min={3} max={12} step={0.5} suffix="%" displayValue={maitreOeuvrePct.toFixed(1)} />
                  <div className="text-xs text-gray-500 -mt-2">= {formatEuroShort(calculations.constructionBase * maitreOeuvrePct / 100)}</div>
                </>
              )}
            </div>
            <div className="space-y-3">
              <CheckboxInput label="Assurance Dommages-Ouvrage" checked={dommagesOuvrage} onChange={setDommagesOuvrage}
                tooltip="Obligatoire pour le maître d'ouvrage (art. L242-1 Code des assurances)" />
              {dommagesOuvrage && (
                <>
                  <SliderInput label="Taux DO" value={dommagesOuvragePct} onChange={setDommagesOuvragePct}
                    min={1} max={8} step={0.1} suffix="%" displayValue={dommagesOuvragePct.toFixed(1)} />
                  <div className="text-xs text-gray-500 -mt-2">= {formatEuroShort(calculations.constructionBase * dommagesOuvragePct / 100)}</div>
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
                <InlineNumberInput value={bureauControleMontant} onChange={setBureauControleMontant} />
              )}
            </div>
            <div className="flex items-center gap-4">
              <CheckboxInput label="Coordinateur SPS" checked={coordSPS} onChange={setCoordSPS}
                tooltip="Sécurité et Protection de la Santé sur chantier" />
              {coordSPS && (
                <InlineNumberInput value={coordSPSMontant} onChange={setCoordSPSMontant} />
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
              <NumberInput label="Raccordement assainissement collectif" value={raccAssCollectif} onChange={setRaccAssCollectif} suffix="€"
                tooltip="Participation au raccordement au réseau collectif (PRE)" />
            ) : (
              <div className="space-y-3 ml-2 border-l-2 border-gray-700 pl-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Type de filière ANC</label>
                  <select value={ancType} onChange={(e) => { setAncType(e.target.value); setRaccANC(ANC_TYPES[e.target.value].default); }}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:border-amber-500 focus:outline-none">
                    {Object.entries(ANC_TYPES).map(([k, v]) => (
                      <option key={k} value={k}>{v.label} ({formatEuroShort(v.default)})</option>
                    ))}
                  </select>
                </div>
                <SliderInput label="Coût installation ANC" value={raccANC} onChange={setRaccANC}
                  min={ANC_TYPES[ancType].min} max={ANC_TYPES[ancType].max} step={500}
                  displayValue={formatEuroShort(raccANC)}
                  tooltip="Inclut fourniture, pose, étude de filière et contrôle SPANC" />
                <div className="text-xs text-gray-500">
                  <Info size={12} className="inline text-blue-400 mr-1" />
                  Étude de filière ANC (~500 €) et contrôle SPANC (~200 €) inclus dans l'estimation
                </div>
              </div>
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
                <option value="chaudiere_gaz" disabled={re2020}>Chaudière gaz (+5 000 €){re2020 ? ' — interdit RE2020' : ''}</option>
              </select>
              {re2020 && chauffage === 'chaudiere_gaz' && (
                <div className="flex items-center gap-2 bg-red-900/30 border border-red-500/50 rounded px-3 py-1.5 mt-1">
                  <XCircle size={14} className="text-red-400" />
                  <span className="text-xs text-red-300">La chaudière gaz seule est interdite en RE2020</span>
                </div>
              )}
            </div>
            <div className="flex items-center gap-4">
              <CheckboxInput label="Climatisation réversible" checked={climatisation} onChange={setClimatisation} />
              {climatisation && (
                <InlineNumberInput value={climMontant} onChange={setClimMontant} />
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
                <InlineNumberInput value={domotiqueMontant} onChange={setDomotiqueMontant} />
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

                  <div className="grid grid-cols-2 gap-3">
                    <NumberInput label="Frais de dossier" value={fraisDossier} onChange={setFraisDossier} suffix="€"
                      tooltip="Frais facturés par la banque pour le montage du dossier" />
                    <SliderInput label="Garantie hypothécaire" value={garantiePct} onChange={setGarantiePct}
                      min={0.5} max={2.5} step={0.1} suffix="%" displayValue={garantiePct.toFixed(1)}
                      tooltip="Caution ou hypothèque, environ 1 à 2% du montant emprunté" />
                    <div className="text-xs text-gray-500 -mt-2">= {formatEuroShort(financement.garantie)}</div>
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
                      <span className="text-gray-400">Frais bancaires (dossier + garantie)</span>
                      <span className="font-mono text-gray-300">{formatEuro(financement.fraisBancairesTotal)}</span>
                    </div>
                    <div className="flex justify-between text-sm border-t border-gray-700 pt-1">
                      <span className="text-gray-300 font-medium">Coût total du crédit</span>
                      <span className="font-mono text-amber-300 font-bold">{formatEuro(financement.coutTotalCredit)}</span>
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

            {/* SAVE / LOAD */}
            <div className="bg-gray-900/90 border border-gray-700/50 rounded-xl p-4 shadow-2xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-display text-sm font-semibold text-amber-100">Sauvegarde du projet</span>
                {savedDate && <span className="text-xs text-gray-500">Dernière : {savedDate}</span>}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={handleSave}
                  className="flex items-center justify-center gap-2 bg-green-600/20 border border-green-600/50 rounded-lg px-3 py-2 text-sm text-green-300 hover:bg-green-600/30 transition-colors"
                >
                  <Save size={15} />
                  Sauvegarder
                </button>
                <button
                  onClick={handleLoad}
                  className="flex items-center justify-center gap-2 bg-blue-600/20 border border-blue-600/50 rounded-lg px-3 py-2 text-sm text-blue-300 hover:bg-blue-600/30 transition-colors"
                >
                  <Download size={15} />
                  Restaurer
                </button>
                <button
                  onClick={handleExportJSON}
                  className="flex items-center justify-center gap-2 bg-amber-600/20 border border-amber-600/50 rounded-lg px-3 py-2 text-sm text-amber-300 hover:bg-amber-600/30 transition-colors"
                >
                  <Upload size={15} />
                  Exporter JSON
                </button>
                <button
                  onClick={handleImportJSON}
                  className="flex items-center justify-center gap-2 bg-purple-600/20 border border-purple-600/50 rounded-lg px-3 py-2 text-sm text-purple-300 hover:bg-purple-600/30 transition-colors"
                >
                  <Download size={15} />
                  Importer JSON
                </button>
              </div>
              {saveMsg && (
                <div className="flex items-center justify-center gap-2 bg-gray-800 rounded py-1.5 text-sm text-amber-300 fade-in">
                  <CheckCircle size={14} />
                  {saveMsg}
                </div>
              )}
            </div>

            {/* OTHER BUTTONS */}
            <div className="flex gap-3">
              <button
                onClick={handleCopy}
                className="flex-1 flex items-center justify-center gap-2 bg-amber-600/20 border border-amber-600/50 rounded-lg px-4 py-2.5 text-sm text-amber-300 hover:bg-amber-600/30 hover:text-amber-200 transition-colors"
              >
                <Copy size={16} />
                Copier le récapitulatif
              </button>
              <button
                onClick={handleReset}
                className="flex items-center justify-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-400 hover:bg-red-900/30 hover:border-red-500/50 hover:text-red-300 transition-colors"
              >
                <Trash2 size={16} />
                Réinitialiser
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
