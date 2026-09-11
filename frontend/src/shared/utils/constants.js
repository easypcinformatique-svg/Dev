export const COMPTOIR_CONFIG = {
  accueil: { nom: 'Accueil', couleur: '#3B82F6', badge: 'badge-accueil', icone: '🏪' },
  web: { nom: 'Web', couleur: '#10B981', badge: 'badge-web', icone: '🌐' },
  whatsapp: { nom: 'WhatsApp', couleur: '#8B5CF6', badge: 'badge-whatsapp', icone: '💬' },
  telephone: { nom: 'Telephone', couleur: '#6366F1', badge: 'badge-accueil', icone: '📞' },
  uber_eats: { nom: 'UberEats', couleur: '#22C55E', badge: 'badge-web', icone: '🟢' },
  deliveroo: { nom: 'Deliveroo', couleur: '#00CCBC', badge: 'badge-web', icone: '🔵' },
  just_eat: { nom: 'JustEat', couleur: '#F97316', badge: 'badge-livraison', icone: '🟠' },
}

export const STATUT_CONFIG = {
  nouvelle: { label: 'Nouvelle', couleur: 'bg-blue-500', text: 'text-blue-400' },
  confirmee: { label: 'Confirmee', couleur: 'bg-cyan-500', text: 'text-cyan-400' },
  en_preparation: { label: 'En preparation', couleur: 'bg-yellow-500', text: 'text-yellow-400' },
  prete: { label: 'Prete', couleur: 'bg-green-500', text: 'text-green-400' },
  en_livraison: { label: 'En livraison', couleur: 'bg-purple-500', text: 'text-purple-400' },
  livree: { label: 'Livree', couleur: 'bg-gray-500', text: 'text-gray-400' },
  recuperee: { label: 'Recuperee', couleur: 'bg-gray-500', text: 'text-gray-400' },
  annulee: { label: 'Annulee', couleur: 'bg-red-500', text: 'text-red-400' },
}

export const TAILLE_LABELS = {
  junior: 'Junior',
  medium: 'Medium',
  large: 'Large',
  xxl: 'XXL',
}

export const PATE_LABELS = {
  classique: 'Classique',
  fine: 'Fine',
  epaisse: 'Epaisse',
  sans_gluten: 'Sans gluten (+2€)',
  complete: 'Complete',
}

export const PATE_OPTIONS = [
  { value: 'classique', label: 'Classique' },
  { value: 'fine', label: 'Fine' },
  { value: 'epaisse', label: 'Epaisse' },
  { value: 'sans_gluten', label: 'Sans gluten' },
  { value: 'complete', label: 'Complete' },
]
