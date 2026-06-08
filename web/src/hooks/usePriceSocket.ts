import { useEffect, useRef, useCallback } from 'react'

type PriceCallback = (symbol: string, price: number) => void

export function usePriceSocket(onPrice: PriceCallback) {
  const wsRef = useRef<WebSocket | null>(null)
  const onPriceRef = useRef(onPrice)
  onPriceRef.current = onPrice

  const subscribe = useCallback((symbol: string) => {
    wsRef.current?.send(JSON.stringify({ action: 'subscribe', symbol }))
  }, [])

  const unsubscribe = useCallback((symbol: string) => {
    wsRef.current?.send(JSON.stringify({ action: 'unsubscribe', symbol }))
  }, [])

  useEffect(() => {
    const ws = new WebSocket(`ws://${location.host}/ws/price`)
    wsRef.current = ws

    ws.onmessage = (e) => {
      try {
        const { symbol, price } = JSON.parse(e.data)
        onPriceRef.current(symbol, price)
      } catch {}
    }

    ws.onclose = () => {
      wsRef.current = null
    }

    return () => {
      ws.close()
    }
  }, [])

  return { subscribe, unsubscribe }
}
