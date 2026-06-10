import { useEffect, useRef, useCallback } from 'react'

type PriceCallback = (symbol: string, price: number) => void

export function usePriceSocket(onPrice: PriceCallback) {
  const wsRef    = useRef<WebSocket | null>(null)
  const pendingRef = useRef<Set<string>>(new Set())
  const onPriceRef = useRef(onPrice)
  onPriceRef.current = onPrice

  const subscribe = useCallback((symbol: string) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'subscribe', symbol }))
    } else {
      pendingRef.current.add(symbol)
    }
  }, [])

  const unsubscribe = useCallback((symbol: string) => {
    pendingRef.current.delete(symbol)
    wsRef.current?.send(JSON.stringify({ action: 'unsubscribe', symbol }))
  }, [])

  useEffect(() => {
    const ws = new WebSocket(`ws://${location.host}/ws/price`)
    wsRef.current = ws

    ws.onopen = () => {
      pendingRef.current.forEach(sym => {
        ws.send(JSON.stringify({ action: 'subscribe', symbol: sym }))
      })
      pendingRef.current.clear()
    }

    ws.onmessage = (e) => {
      try {
        const { symbol, price } = JSON.parse(e.data)
        onPriceRef.current(symbol, price)
      } catch {}
    }

    ws.onclose = () => {
      wsRef.current = null
    }

    return () => { ws.close() }
  }, [])

  return { subscribe, unsubscribe }
}
