import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/stock'
import { useAppStore } from '../../store'

export function StockSearch() {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const { setSymbol } = useAppStore()
  const wrapperRef = useRef<HTMLDivElement>(null)

  const { data: results = [] } = useQuery({
    queryKey: ['search', query],
    queryFn: () => api.search(query),
    enabled: query.length >= 1,
    staleTime: 10_000,
  })

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={wrapperRef} className="stock-search">
      <input
        className="search-input"
        placeholder="종목 검색..."
        value={query}
        onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
        onFocus={() => query && setOpen(true)}
      />
      {open && results.length > 0 && (
        <ul className="search-dropdown">
          {results.map((r) => (
            <li
              key={r.symbol}
              className="search-item"
              onMouseDown={() => {
                setSymbol(r.symbol, r.name)
                setQuery('')
                setOpen(false)
              }}
            >
              <span className="search-name">{r.name}</span>
              <span className="search-code">{r.symbol}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
