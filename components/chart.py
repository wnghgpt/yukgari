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
            support_price = short_term_params.get("support_price", 0)
            e1_pct = short_term_params.get("entry1_pct", 2.0)
            e2_pct = short_term_params.get("entry2_pct", 1.0)
            sl_pct = short_term_params.get("hard_sl_pct", 4.0)

            add_line(resist_price, "#FFFFFF", 0, "저항")
            add_line(resist_price * (1 + e1_pct / 100), "#FFFF00", 2, f"1차(+{e1_pct:.1f}%)")
            if support_price > 0:
                add_line(support_price, "#FFFFFF", 0, "지지")
                add_line(support_price * (1 + e2_pct / 100), "#FFFF00", 2, f"2차(+{e2_pct:.1f}%)")
                sl_line = support_price * (1 - sl_pct / 100)
            else:
                sl_line = resist_price * (1 - sl_pct / 100)

            if st_avg_price > 0:
                add_line(st_avg_price, "#FF9800", 0, "평단", width=2)
                add_line(sl_line, "#FF3131", 0, f"-{sl_pct:.0f}%손절")

                st_risk = st_avg_price - sl_line
                if st_risk > 0:
                    for rr_val in short_term_params["rr_targets"]:
                        rr_price = st_avg_price + (st_risk * rr_val)
                        add_line(rr_price, "#2ECC71", 0, f"{rr_val}배")

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
