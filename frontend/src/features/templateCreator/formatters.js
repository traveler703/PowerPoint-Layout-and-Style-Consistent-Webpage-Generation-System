export function escapeHtml(value) {
  if (!value) return ''
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

export function renderMarkdown(text) {
  if (!text) return ''
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}

export function isColorDark(color) {
  if (!color) return false
  let hex = color.replace('#', '')
  if (hex.length === 3) {
    hex = hex.split('').map(character => character + character).join('')
  }
  if (hex.length !== 6) return false

  const red = Number.parseInt(hex.substring(0, 2), 16)
  const green = Number.parseInt(hex.substring(2, 4), 16)
  const blue = Number.parseInt(hex.substring(4, 6), 16)
  return (red * 299 + green * 587 + blue * 114) / 1000 < 128
}

export function adjustBrightness(color, percent) {
  if (!color) return '#333333'
  let hex = color.replace('#', '')
  if (hex.length === 3) {
    hex = hex.split('').map(character => character + character).join('')
  }
  if (hex.length !== 6) return '#333333'

  const value = Number.parseInt(hex, 16)
  const adjustment = Math.round(2.55 * percent)
  const red = Math.min(255, Math.max(0, (value >> 16) + adjustment))
  const green = Math.min(255, Math.max(0, ((value >> 8) & 0x00FF) + adjustment))
  const blue = Math.min(255, Math.max(0, (value & 0x0000FF) + adjustment))
  return `#${(0x1000000 + red * 0x10000 + green * 0x100 + blue).toString(16).slice(1)}`
}
