import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_lightweight_charts import renderLightweightCharts

def render_chart(df_ohlcv, mid_term_params, short_term_params, calc_res, rr_targets, st_avg_price, st_hard_sl, c_price, st_partial_sl=None):
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
                "color": 'rgba(38, 166, 154, 0.5)' if row['Close'] >= row['Open'] else 'rgba(239, 83, 80, 0.5)'
            })
        
        series = [
            {
                "type": "Candlestick",
                "data": candles,
                "options": {
                    "upColor": "#26a69a", "downColor": "#ef5350",
                    "borderVisible": False, "wickUpColor": "#26a69a", "wickDownColor": "#ef5350",
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
            add_line(resist_price, "#FFFFFF", 0, "저항")
            add_line(resist_price * 1.10, "#3498DB", 0, "10%")
            add_line(resist_price * 1.02, "#FFFF00", 2, "1차(돌파)")
            add_line(resist_price * 0.98, "#FFFF00", 2, "2차")
            add_line(resist_price * 0.94, "#FFFF00", 2, "3차")
            add_line(resist_price * 0.91, "#FFFF00", 2, "4차")
            
            if st_avg_price > 0:
                add_line(st_avg_price, "#FF9800", 0, "평단", width=2)
                if st_partial_sl:
                    add_line(st_partial_sl, "#FF6B35", 2, "-4%손절")
                add_line(st_hard_sl, "#FF3131", 0, "-10%")
                
                st_risk = st_avg_price - st_hard_sl
                if st_risk > 0:
                    for rr_val in short_term_params["rr_targets"]:
                        rr_price = st_avg_price + (st_risk * rr_val)
                        add_line(rr_price, "#2ECC71", 0, f"{rr_val}배")

        chart_options = {
            "height": 500,
            "layout": {
                "background": {"type": "solid", "color": "#131722"}, 
                "textColor": "#d1d4dc",
                "fontSize": 8
            },
            "grid": {"vertLines": {"color": "rgba(42, 46, 57, 0)"}, "horzLines": {"color": "rgba(42, 46, 57, 0.5)"}},
            "crosshair": {"mode": 0},
            "timeScale": {"borderColor": "rgba(197, 203, 206, 0.8)", "rightOffset": 40}
        }
        
        renderLightweightCharts([{"chart": chart_options, "series": series}], key='chart_v2')
