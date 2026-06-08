export interface CalcResult {
  entryPrices: number[]
  weights: number[]
  quantities: number[]
  amounts: number[]
  avgPrice: number
  stopLoss: number
  targetPrice: number
  budget: number
  lossPct: number
  rrMultiple: number
  isZone: boolean
}

interface BreakoutParams {
  resistPrice: number
  missed: boolean
  slPct: number        // not-missed 손절%
  missedSlPct: number  // missed 손절%
  rrMultiple: number
  allowedLoss: number
  isOverseas: boolean
}

interface ZoneParams {
  resistPrice: number
  supportPrice: number
  missedSlPct: number
  rrMultiple: number
  allowedLoss: number
  isOverseas: boolean
}

function snap(v: number, isOverseas: boolean) {
  return isOverseas ? Math.round(v * 100) / 100 : Math.round(v)
}

export function calcBreakout(p: BreakoutParams): CalcResult | null {
  if (p.resistPrice <= 0) return null

  let entryPrices: number[]
  let weights: number[]
  const isZone = false

  if (!p.missed) {
    entryPrices = [p.resistPrice * 1.02, p.resistPrice * 0.98]
    weights = [70, 30]
  } else {
    entryPrices = [p.resistPrice * 1.04, p.resistPrice * 1.01, p.resistPrice * 0.98]
    weights = [30, 40, 30]
  }

  const dummyTotal = weights.reduce((a, b) => a + b, 0)
  const dummyAmounts = weights.map(w => (w / dummyTotal) * 1_000_000)
  const totalDummy = dummyAmounts.reduce((a, b) => a + b, 0)
  const totalQtyDummy = dummyAmounts.reduce((sum, a, i) => sum + a / entryPrices[i], 0)
  const avgPrice = totalDummy / totalQtyDummy

  const stopLoss = snap(p.missed
    ? avgPrice * (1 - p.missedSlPct / 100)
    : p.resistPrice * (1 - p.slPct / 100), p.isOverseas)

  const lossPct = avgPrice > 0 ? (avgPrice - stopLoss) / avgPrice * 100 : 0
  const budget = lossPct > 0 ? p.allowedLoss / (lossPct / 100) : 0

  const wTotal = weights.reduce((a, b) => a + b, 0)
  const amounts = weights.map(w => (w / wTotal) * budget)
  const quantities = amounts.map((a, i) => a / entryPrices[i])
  const targetPrice = snap(avgPrice + p.rrMultiple * (avgPrice - stopLoss), p.isOverseas)

  return {
    entryPrices: entryPrices.map(v => snap(v, p.isOverseas)),
    weights, quantities, amounts,
    avgPrice: snap(avgPrice, p.isOverseas),
    stopLoss, targetPrice, budget, lossPct,
    rrMultiple: p.rrMultiple, isZone,
  }
}

export function calcZone(p: ZoneParams): CalcResult | null {
  if (p.resistPrice <= 0 || p.supportPrice <= 0 || p.resistPrice <= p.supportPrice) return null

  const rng = p.resistPrice - p.supportPrice
  const entryPrices = [
    p.resistPrice - rng / 3,
    p.resistPrice - rng * 2 / 3,
    p.supportPrice,
  ]
  const weights = [20, 30, 50]

  const wTotal = weights.reduce((a, b) => a + b, 0)
  const dummyAmounts = weights.map(w => (w / wTotal) * 1_000_000)
  const totalDummy = dummyAmounts.reduce((a, b) => a + b, 0)
  const totalQtyDummy = dummyAmounts.reduce((sum, a, i) => sum + a / entryPrices[i], 0)
  const avgPrice = totalDummy / totalQtyDummy

  const stopLoss = snap(avgPrice * (1 - p.missedSlPct / 100), p.isOverseas)
  const lossPct = avgPrice > 0 ? (avgPrice - stopLoss) / avgPrice * 100 : 0
  const budget = lossPct > 0 ? p.allowedLoss / (lossPct / 100) : 0

  const amounts = weights.map(w => (w / wTotal) * budget)
  const quantities = amounts.map((a, i) => a / entryPrices[i])
  const targetPrice = snap(avgPrice + p.rrMultiple * (avgPrice - stopLoss), p.isOverseas)

  return {
    entryPrices: entryPrices.map(v => snap(v, p.isOverseas)),
    weights, quantities, amounts,
    avgPrice: snap(avgPrice, p.isOverseas),
    stopLoss, targetPrice, budget, lossPct,
    rrMultiple: p.rrMultiple, isZone: true,
  }
}

export function fmtPrice(v: number, isOverseas: boolean): string {
  if (isOverseas) return `$${v.toFixed(2)}`
  return `${Math.round(v).toLocaleString()}원`
}

export function fmtAmount(v: number, isOverseas: boolean): string {
  if (isOverseas) return `$${v.toFixed(0)}`
  return `${(v / 10000).toFixed(0)}만원`
}
