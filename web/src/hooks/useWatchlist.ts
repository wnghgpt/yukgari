import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/stock'

export function useWatchlist() {
  const queryClient = useQueryClient()

  const { data: watchlist = [] } = useQuery({
    queryKey: ['watchlist'],
    queryFn: api.watchlist,
    staleTime: 5 * 60 * 1000,
  })

  const addMutation = useMutation({
    mutationFn: (item: { symbol: string; name: string }) =>
      api.addWatchlist({
        stock_code: item.symbol,
        stock_name: item.name,
        market_type: /^\d+$/.test(item.symbol) ? 'KR' : 'US',
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  })

  const removeMutation = useMutation({
    mutationFn: (symbol: string) => api.removeWatchlist(symbol),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  })

  const isInWatchlist = (symbol: string) =>
    watchlist.some(w => w.symbol === symbol)

  return {
    watchlist,
    isInWatchlist,
    add: (item: { symbol: string; name: string }) => addMutation.mutate(item),
    remove: (symbol: string) => removeMutation.mutate(symbol),
    toggle: (symbol: string, name: string) => {
      if (isInWatchlist(symbol)) removeMutation.mutate(symbol)
      else addMutation.mutate({ symbol, name })
    },
  }
}
