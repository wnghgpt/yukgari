import { useState, useEffect } from 'react'
import './JournalAddModal.css'

const PATTERNS = [
  '손잡이컵', '손잡이컵 (놓침)',
  '역추세', '우량주',
  '횡보돌파', '횡보돌파 (놓침)',
]

interface Props {
  open: boolean
  defaultPattern: string
  onConfirm: (pattern: string) => void
  onCancel: () => void
}

export function JournalAddModal({ open, defaultPattern, onConfirm, onCancel }: Props) {
  const [pattern, setPattern] = useState(defaultPattern)

  useEffect(() => { setPattern(defaultPattern) }, [defaultPattern])

  if (!open) return null

  const handleConfirm = () => onConfirm(pattern)

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <p className="modal-title">패턴 선택</p>
        <select
          className="modal-select"
          value={pattern}
          onChange={e => setPattern(e.target.value)}
        >
          {PATTERNS.map(p => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <div className="modal-actions">
          <button className="modal-btn modal-btn-cancel" onClick={onCancel}>취소</button>
          <button className="modal-btn modal-btn-confirm" onClick={handleConfirm}>추가</button>
        </div>
      </div>
    </div>
  )
}
