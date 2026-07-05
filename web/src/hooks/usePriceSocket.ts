import { useEffect, useCallback, useRef } from 'react'

type PriceCallback = (symbol: string, price: number) => void

// ── 모듈 레벨 싱글톤 WS ─────────────────────────────────────────
const _callbacks  = new Set<PriceCallback>()
const _pending    = new Set<string>()
const _subscribed = new Set<string>()
let   _ws: WebSocket | null = null

function _connect() {
  if (_ws && _ws.readyState !== WebSocket.CLOSED) return
  _ws = new WebSocket(`ws://${location.host}/ws/price`)

  _ws.onopen = () => {
    _subscribed.forEach(sym =>
      _ws!.send(JSON.stringify({ action: 'subscribe', symbol: sym }))
    )
    _pending.forEach(sym =>
      _ws!.send(JSON.stringify({ action: 'subscribe', symbol: sym }))
    )
    _pending.clear()
  }

  _ws.onmessage = (e) => {
    try {
      const { symbol, price } = JSON.parse(e.data)
      _callbacks.forEach(cb => cb(symbol, price))
    } catch {}
  }

  _ws.onclose = () => {
    _ws = null
    setTimeout(_connect, 3000)
  }
}

function _subscribe(symbol: string) {
  if (_subscribed.has(symbol)) return
  _subscribed.add(symbol)
  if (_ws?.readyState === WebSocket.OPEN) {
    _ws.send(JSON.stringify({ action: 'subscribe', symbol }))
  } else {
    _pending.add(symbol)
    _connect()
  }
}

// ── hook ────────────────────────────────────────────────────────
export function usePriceSocket(onPrice: PriceCallback) {
  const onPriceRef = useRef(onPrice)
  onPriceRef.current = onPrice

  useEffect(() => {
    const cb: PriceCallback = (sym, price) => onPriceRef.current(sym, price)
    _callbacks.add(cb)
    _connect()
    return () => { _callbacks.delete(cb) }
  }, [])

  const subscribe = useCallback((symbol: string) => _subscribe(symbol), [])

  return { subscribe }
}
