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
  { id: 'marcap',    label: '시총' },
  { id: 'trading',   label: '거래대금' },
]

type Market = 'KR' | 'US'

export function Watchlist() {
  const [activeTab, setActiveTab] = useState<SidebarTab>('watchlist')
  const [market, setMarket] = useState<Market>('KR')
  const { symbol: currentSymbol } = useAppStore()

  const { data: marcapKrData = [], isFetching: marcapKrLoading } = useQuery({
    queryKey: ['ranking', 'marcap', 'KR'],
    queryFn: api.rankingMarcap,
    staleTime: 60 * 60 * 1000,
    enabled: activeTab === 'marcap' && market === 'KR',
  })

  const { data: marcapUsData = [], isFetching: marcapUsLoading } = useQuery({
    queryKey: ['ranking', 'marcap', 'US'],
    queryFn: api.rankingUsMarcap,
    staleTime: 60 * 60 * 1000,
    enabled: activeTab === 'marcap' && market === 'US',
  })

  const { data: tradingKrData = [], isFetching: tradingKrLoading } = useQuery({
    queryKey: ['ranking', 'trading', 'KR'],
    queryFn: api.rankingTrading,
    staleTime: 60 * 60 * 1000,
    enabled: activeTab === 'trading' && market === 'KR',
  })

  const { data: tradingUsData = [], isFetching: tradingUsLoading } = useQuery({
    queryKey: ['ranking', 'trading', 'US'],
    queryFn: api.rankingUsTrading,
    staleTime: 60 * 60 * 1000,
    enabled: activeTab === 'trading' && market === 'US',
  })

  const rankingData = activeTab === 'marcap'
    ? (market === 'KR' ? marcapKrData : marcapUsData)
    : (market === 'KR' ? tradingKrData : tradingUsData)

  const rankingLoading = activeTab === 'marcap'
    ? (market === 'KR' ? marcapKrLoading : marcapUsLoading)
    : (market === 'KR' ? tradingKrLoading : tradingUsLoading)

  const valueHeader = activeTab === 'marcap' ? '시총' : '거래대금'

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

      {/* 국내/해외 서브탭 */}
      {activeTab !== 'watchlist' && (
        <div className="wl-market-tabs">
          <button
            className={`wl-market-btn ${market === 'KR' ? 'active' : ''}`}
            onClick={() => setMarket('KR')}
          >
            🇰🇷 국내
          </button>
          <button
            className={`wl-market-btn ${market === 'US' ? 'active' : ''}`}
            onClick={() => setMarket('US')}
          >
            🇺🇸 해외
          </button>
        </div>
      )}

      <div className="wl-content">
        <div style={{ display: activeTab === 'watchlist' ? 'block' : 'none' }}>
          <WatchlistTab currentSymbol={currentSymbol} />
        </div>
        {activeTab !== 'watchlist' && (
          <RankingTab
            data={rankingData}
            loading={rankingLoading}
            market={market}
          />
        )}
      </div>
    </div>
  )
}
