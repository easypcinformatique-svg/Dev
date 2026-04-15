import { useState } from 'react'
import { useProjectState, INITIAL_STATE, STORAGE_KEY } from './hooks/useLocalStorage.js'
import Dashboard from './components/Dashboard.jsx'
import Planning from './components/Planning.jsx'
import Finances from './components/Finances.jsx'
import Legal from './components/Legal.jsx'
import ArtisansView from './components/Artisans.jsx'
import Notes from './components/Notes.jsx'
import Documents from './components/Documents.jsx'
import './App.css'

const TABS = [
  { id: 'dashboard', label: 'Tableau de bord', icon: '\u25A3' },
  { id: 'planning', label: 'Planning', icon: '\u2630' },
  { id: 'finances', label: 'Finances', icon: '\u20AC' },
  { id: 'legal', label: 'Legal', icon: '\u2696' },
  { id: 'artisans', label: 'Artisans', icon: '\u2692' },
  { id: 'documents', label: 'Documents', icon: '\u{1F4CE}' },
  { id: 'notes', label: 'Journal', icon: '\u270E' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const {
    state,
    toggleTask,
    toggleLegal,
    updatePayment,
    updateArtisan,
    addNote,
    deleteNote,
    updateFinancement,
    resetState,
  } = useProjectState(INITIAL_STATE)

  function handleReset() {
    if (confirm('Reinitialiser toutes les donnees (taches, paiements, notes) ?\n\nCette action est IRREVERSIBLE.\nLes documents (IndexedDB) ne seront pas supprimes.')) {
      resetState()
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1 className="app-title">11 rue Pierre Loti</h1>
          <div className="app-subtitle">SCI JGR — PC 013 071 23 C0061 — Les Pennes Mirabeau</div>
        </div>
      </header>

      <nav className="tab-nav" role="tablist" aria-label="Navigation principale">
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
          >
            <span className="tab-icon" aria-hidden="true">{tab.icon}</span>
            <span className="tab-label">{tab.label}</span>
          </button>
        ))}
      </nav>

      <main className="app-main" role="tabpanel" id={`panel-${activeTab}`}>
        {activeTab === 'dashboard' && <Dashboard state={state} toggleTask={toggleTask} toggleLegal={toggleLegal} />}
        {activeTab === 'planning' && <Planning state={state} toggleTask={toggleTask} />}
        {activeTab === 'finances' && <Finances state={state} updatePayment={updatePayment} updateFinancement={updateFinancement} />}
        {activeTab === 'legal' && <Legal state={state} toggleLegal={toggleLegal} />}
        {activeTab === 'artisans' && <ArtisansView state={state} updateArtisan={updateArtisan} />}
        {activeTab === 'documents' && <Documents toggleTask={toggleTask} toggleLegal={toggleLegal} completedTasks={state.completedTasks} completedLegal={state.completedLegal} />}
        {activeTab === 'notes' && <Notes state={state} addNote={addNote} deleteNote={deleteNote} />}
      </main>

      <footer className="app-footer">
        <button className="btn-reset" onClick={handleReset}>
          Reinitialiser les donnees
        </button>
      </footer>
    </div>
  )
}
