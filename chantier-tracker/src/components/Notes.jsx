import { useState } from 'react'
import { formatDateTime } from '../utils/dateUtils.js'

export default function Notes({ state, addNote, deleteNote }) {
  const [newNote, setNewNote] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (newNote.trim()) {
      addNote(newNote.trim())
      setNewNote('')
    }
  }

  return (
    <div className="notes">
      <form className="note-form" onSubmit={handleSubmit}>
        <textarea
          value={newNote}
          onChange={e => setNewNote(e.target.value)}
          placeholder="Ajouter une note, observation, ou evenement du chantier..."
          rows={3}
        />
        <button type="submit" className="btn-primary" disabled={!newNote.trim()}>
          Ajouter
        </button>
      </form>

      <div className="notes-list">
        {state.notes.length === 0 ? (
          <div className="empty-state">
            Aucune note pour le moment. Utilisez ce journal pour documenter l'avancement du chantier, les problemes rencontres, les decisions prises.
          </div>
        ) : (
          state.notes.map(note => (
            <div key={note.id} className="note-card">
              <div className="note-header">
                <span className="note-date">{formatDateTime(note.date)}</span>
                <button
                  className="note-delete"
                  onClick={() => { if (confirm('Supprimer cette note ?')) deleteNote(note.id) }}
                  title="Supprimer"
                >
                  &#10005;
                </button>
              </div>
              <div className="note-text">{note.text}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
