import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/stock'
import { useAppStore } from '../store'
import type { WatchlistItem } from '../types'

export function useWatchlist() {
  const queryClient = useQueryClient()
  const userId = useAppStore(s => s.userId)

  const { data: watchlist = [] } = useQuery({
    queryKey: ['watchlist', userId],
    queryFn: () => api.watchlist(userId!),
    staleTime: 5 * 60 * 1000,
    enabled: !!userId,
  })

  const addMutation = useMutation({
    mutationFn: (item: { symbol: string; name: string }) =>
      api.addWatchlist({
        stock_code: item.symbol,
        stock_name: item.name,
        market_type: /^\d+$/.test(item.symbol) ? 'KR' : 'US',
      }, userId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist', userId] }),
  })

  const removeMutation = useMutation({
    mutationFn: (symbol: string) => api.removeWatchlist(symbol, userId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist', userId] }),
  })

  const reorderMutation = useMutation({
    mutationFn: (items: WatchlistItem[]) =>
      api.reorderWatchlist(
        items.map((item, idx) => ({ stock_code: item.symbol, sort_order: idx + 1 })),
        userId!,
      ),
    onMutate: async (newOrder: WatchlistItem[]) => {
      await queryClient.cancelQueries({ queryKey: ['watchlist', userId] })
      const prev = queryClient.getQueryData<WatchlistItem[]>(['watchlist', userId])
      queryClient.setQueryData(['watchlist', userId], newOrder)
      return { prev }
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(['watchlist', userId], ctx.prev)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['watchlist', userId] }),
  })

  const isInWatchlist = (symbol: string) =>
    watchlist.some(w => w.symbol === symbol)

  return {
    watchlist,
    isInWatchlist,
    add: (item: { symbol: string; name: string }) => addMutation.mutate(item),
    remove: (symbol: string) => removeMutation.mutate(symbol),
    reorder: (items: WatchlistItem[]) => reorderMutation.mutate(items),
    toggle: (symbol: string, name: string) => {
      if (isInWatchlist(symbol)) removeMutation.mutate(symbol)
      else addMutation.mutate({ symbol, name })
    },
  }
}
