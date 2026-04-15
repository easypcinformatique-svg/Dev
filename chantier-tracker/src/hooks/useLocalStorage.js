import { useState, useEffect, useCallback } from 'react'

export const STORAGE_KEY = 'chantier_11_pierre_loti'

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveState(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // localStorage full or unavailable
  }
}

export function useProjectState(initialData) {
  const [state, setState] = useState(() => {
    const saved = loadState()
    return saved || initialData
  })

  useEffect(() => {
    saveState(state)
  }, [state])

  const toggleTask = useCallback((taskId) => {
    setState(prev => {
      const completed = { ...prev.completedTasks }
      if (completed[taskId]) {
        delete completed[taskId]
      } else {
        completed[taskId] = new Date().toISOString()
      }
      return { ...prev, completedTasks: completed }
    })
  }, [])

  const toggleLegal = useCallback((legalId) => {
    setState(prev => {
      const completed = { ...prev.completedLegal }
      if (completed[legalId]) {
        delete completed[legalId]
      } else {
        completed[legalId] = new Date().toISOString()
      }
      return { ...prev, completedLegal: completed }
    })
  }, [])

  const updatePayment = useCallback((lotId, field, value) => {
    setState(prev => {
      const payments = { ...prev.payments }
      if (!payments[lotId]) payments[lotId] = {}
      payments[lotId] = { ...payments[lotId], [field]: value }
      return { ...prev, payments }
    })
  }, [])

  const updateArtisan = useCallback((artisanId, field, value) => {
    setState(prev => {
      const artisans = { ...prev.artisanUpdates }
      if (!artisans[artisanId]) artisans[artisanId] = {}
      artisans[artisanId] = { ...artisans[artisanId], [field]: value }
      return { ...prev, artisanUpdates: artisans }
    })
  }, [])

  const addNote = useCallback((note) => {
    setState(prev => ({
      ...prev,
      notes: [
        { id: Date.now(), date: new Date().toISOString(), text: note },
        ...prev.notes
      ]
    }))
  }, [])

  const deleteNote = useCallback((noteId) => {
    setState(prev => ({
      ...prev,
      notes: prev.notes.filter(n => n.id !== noteId)
    }))
  }, [])

  const updateFinancement = useCallback((key, value) => {
    setState(prev => ({
      ...prev,
      financement: { ...prev.financement, [key]: value }
    }))
  }, [])

  const resetState = useCallback(() => {
    setState(initialData)
  }, [initialData])

  return {
    state,
    toggleTask,
    toggleLegal,
    updatePayment,
    updateArtisan,
    addNote,
    deleteNote,
    updateFinancement,
    resetState,
  }
}

export const INITIAL_STATE = {
  completedTasks: {},
  completedLegal: {},
  payments: {},
  artisanUpdates: {},
  notes: [],
  financement: { pret: 0, apport: 0 },
}
