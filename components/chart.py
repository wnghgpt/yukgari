import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_lightweight_charts import renderLightweightCharts

def _calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

MA_COLORS = {5: "#FF1744", 20: "#FF9800", 60: "#2ECC71", 120: "#9B59B6", 240: "#808080"}

def render_chart(df_ohlcv, mid_term_params, short_term_params, calc_res, rr_targets, st_avg_price, st_hard_sl, c_price, st_partial_sl=None, show_rsi=False, ma_options=None):
    if df_ohlcv is not None and not df_ohlcv.empty:
        plot_df = df_ohlcv.sort_values('Date', ascending=True)
        candles = []
        volume_data = []
        
        for _, row in plot_df.iterrows():
            time_val = row['Date'].strftime('%Y-%m-%d') if isinstance(row['Date'], (pd.Timestamp, datetime)) else str(row['Date'])[:10]
            candles.append({
                "time": time_val,
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close'])
            })
            volume_data.append({
                "time": time_val,
                "value": float(row['Volume']),
                "color": 'rgba(239, 83, 80, 0.5)' if row['Close'] >= row['Open'] else 'rgba(33, 150, 243, 0.5)'
            })
        
        series = [
            {
                "type": "Candlestick",
                "data": candles,
                "options": {
                    "upColor": "rgba(0,0,0,0)", "downColor": "rgba(0,0,0,0)",
                    "borderVisible": True,
                    "borderUpColor": "#ef5350", "borderDownColor": "#2196F3",
                    "wickUpColor": "#ef5350", "wickDownColor": "#2196F3",
                    "priceLineColor": "#7FFF00"
                }
            },
            {
                "type": "Histogram",
                "data": volume_data,
                "options": {
                    "color": "#26a69a",
                    "priceFormat": {"type": "volume"},
                    "priceScaleId": "", # Overlay mode
                },
                "priceScale": {
                    "scaleMargins": {"top": 0.8, "bottom": 0}
                }
            }
        ]
        
        def add_line(price, color, style, title, width=1):
            line_data = [{"time": c["time"], "value": price} for c in candles]
            series.append({
                "type": "Line",
                "data": line_data,
                "options": {
                    "color": color, "lineWidth": width, "lineStyle": style,
                    "title": title, "crosshairMarkerVisible": False,
                    "priceLineVisible": False, "lastValueVisible": True
                }
            })

        if ma_options:
            for period, enabled in ma_options.items():
                if not enabled:
                    continue
                ma_vals = plot_df["Close"].rolling(period).mean()
                ma_data = [
                    {"time": c["time"], "value": round(float(v), 4)}
                    for c, v in zip(candles, ma_vals)
                    if not pd.isna(v)
                ]
                series.append({
                    "type": "Line",
                    "data": ma_data,
                    "options": {
                        "color": MA_COLORS.get(period, "#ffffff"),
                        "lineWidth": 1,
                        "lineStyle": 0,
                        "title": "",
                        "crosshairMarkerVisible": False,
                        "priceLineVisible": False,
                        "lastValueVisible": False
                    }
                })

        show_lines_user = mid_term_params["show_lines"]
        if show_lines_user:
            for i, zone in enumerate(calc_res['zones']):
                lbl = f"{i+1}차"
                add_line(zone['price'], "#FFFF00", 2, lbl)
            
            add_line(calc_res['avg_price'], "#FF9800", 0, "평단", width=2)
            add_line(calc_res['hard_stop_loss'], "#E74C3C", 0, "손절")
            add_line(mid_term_params["channel_top"], "#FFFFFF", 0, "상단")
            add_line(mid_term_params["channel_bot"], "#FFFFFF", 0, "하단")
            
            for label, price in rr_targets.items():
                simple_lbl = label.replace("RR_", "").replace("x", "배")
                add_line(price, "#2ECC71", 0, simple_lbl)
                
        show_lines_short = short_term_params["show_lines"]
        if show_lines_short:
            resist_price = short_term_params["resist_price"]
            sl_pct = short_term_params.get("hard_sl_pct", 4.0)
            missed = short_term_params.get("missed", False)
            support_price = short_term_params.get("support_price", 0.0)

            if not missed:
                sl_line = resist_price * (1 - sl_pct / 100)
                add_line(resist_price, "#FFFFFF", 0, "저항")
                add_line(resist_price * 1.02, "#FFFF00", 2, "1차(+2%)")
                add_line(resist_price * 0.98, "#FFFF00", 2, "2차(-2%)")

                if st_avg_price > 0:
                    add_line(st_avg_price, "#FF9800", 0, "평단", width=2)
                    add_line(sl_line, "#FF3131", 0, f"-{sl_pct:.0f}%손절")
                    target = short_term_params.get("target_price", 0.0)
                    if target > 0:
                        add_line(target, "#2ECC71", 0, "목표가")
            else:
                if support_price > 0 and resist_price > support_price:
                    # zone 모드: 저항선~지지선 구간 3등분
                    rng = resist_price - support_price
                    add_line(resist_price, "#FFFFFF", 0, "저항")
                    add_line(support_price, "#808080", 0, "지지")
                    add_line(resist_price - rng / 3,     "#FFFF00", 2, "1차(1/3)")
                    add_line(resist_price - rng * 2 / 3, "#FFFF00", 2, "2차(2/3)")
                    add_line(support_price,               "#FFFF00", 2, "3차(지지)")
                else:
                    # pullback 모드: 저항선 기준 +4/+1/-2%
                    add_line(resist_price, "#FFFFFF", 0, "저항")
                    add_line(resist_price * 1.04, "#FFFF00", 2, "1차(+4%)")
                    add_line(resist_price * 1.01, "#FFFF00", 2, "2차(+1%)")
                    add_line(resist_price * 0.98, "#FFFF00", 2, "3차(-2%)")

                if st_avg_price > 0 and st_hard_sl > 0:
                    add_line(st_avg_price, "#FF9800", 0, "평단", width=2)
                    add_line(st_hard_sl, "#FF3131", 0, "손절")
                    target = short_term_params.get("target_price", 0.0)
                    if target > 0:
                        add_line(target, "#2ECC71", 0, "목표가")

        base_layout = {
            "background": {"type": "solid", "color": "#131722"},
            "textColor": "#d1d4dc",
            "fontSize": 8
        }
        base_grid = {"vertLines": {"color": "rgba(42, 46, 57, 0)"}, "horzLines": {"color": "rgba(42, 46, 57, 0.5)"}}
        base_timescale = {"borderColor": "rgba(197, 203, 206, 0.8)", "rightOffset": 40}

        chart_options = {
            "height": 500,
            "layout": base_layout,
            "grid": base_grid,
            "crosshair": {"mode": 0},
            "timeScale": base_timescale
        }

        charts = [{"chart": chart_options, "series": series}]

        if show_rsi:
            rsi_vals = _calc_rsi(plot_df["Close"])
            times = [c["time"] for c in candles]
            rsi_data = [
                {"time": t, "value": round(float(v), 2)}
                for t, v in zip(times, rsi_vals)
                if not pd.isna(v)
            ]
            lvl30 = [{"time": t, "value": 30} for t in times]
            lvl70 = [{"time": t, "value": 70} for t in times]

            rsi_series = [
                {
                    "type": "Line",
                    "data": rsi_data,
                    "options": {
                        "color": "#9B59B6", "lineWidth": 1, "title": "RSI(14)",
                        "priceLineVisible": False, "lastValueVisible": True,
                        "crosshairMarkerVisible": False
                    }
                },
                {
                    "type": "Line",
                    "data": lvl70,
                    "options": {
                        "color": "#ef5350", "lineWidth": 1, "lineStyle": 2,
                        "title": "70", "priceLineVisible": False,
                        "lastValueVisible": False, "crosshairMarkerVisible": False
                    }
                },
                {
                    "type": "Line",
                    "data": lvl30,
                    "options": {
                        "color": "#3498DB", "lineWidth": 1, "lineStyle": 2,
                        "title": "30", "priceLineVisible": False,
                        "lastValueVisible": False, "crosshairMarkerVisible": False
                    }
                }
            ]
            rsi_chart_options = {
                "height": 70,
                "layout": base_layout,
                "grid": base_grid,
                "crosshair": {"mode": 0},
                "timeScale": base_timescale
            }
            charts.append({"chart": rsi_chart_options, "series": rsi_series})

        renderLightweightCharts(charts, key='chart_v2')
