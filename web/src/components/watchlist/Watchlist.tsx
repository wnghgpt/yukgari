import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '../../store'
import type { SidebarTab } from '../../types'
import { api } from '../../api/stock'
import { WatchlistTab } from './WatchlistTab'
import { RankingTab } from './RankingTab'
import './Watchlist.css'

const TABS: { id: SidebarTab; label: string }[] = [
  { id: 'watchlist', label: '관심' },
  { id: 'marcap',    label: '시총100' },
  { id: 'trading',   label: '거래대금' },
]

export function Watchlist() {
  const [activeTab, setActiveTab] = useState<SidebarTab>('watchlist')
  const { symbol: currentSymbol } = useAppStore()

  const { data: marcapData = [], isFetching: marcapLoading } = useQuery({
    queryKey: ['ranking', 'marcap'],
    queryFn: api.rankingMarcap,
    staleTime: 60 * 60 * 1000,
    enabled: activeTab === 'marcap',
  })

  const { data: tradingData = [], isFetching: tradingLoading } = useQuery({
    queryKey: ['ranking', 'trading'],
    queryFn: api.rankingTrading,
    staleTime: 60 * 60 * 1000,
    enabled: activeTab === 'trading',
  })

  return (
    <div className="watchlist-panel">
      <div className="wl-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`wl-tab ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="wl-content">
        <div style={{ display: activeTab === 'watchlist' ? 'block' : 'none' }}>
          <WatchlistTab currentSymbol={currentSymbol} />
        </div>
        {activeTab === 'marcap' && (
          <RankingTab data={marcapData} loading={marcapLoading} valueHeader="시총" />
        )}
        {activeTab === 'trading' && (
          <RankingTab data={tradingData} loading={tradingLoading} valueHeader="거래대금" />
        )}
      </div>
    </div>
  )
}
