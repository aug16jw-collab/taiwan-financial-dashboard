import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import THRESHOLDS, COLOR_LISTED, COLOR_OTC, COLOR_GOOD, COLOR_BAD


def stock_chart(df: pd.DataFrame, code: str, name: str,
                show_ma: bool = True, show_bb: bool = True) -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.20, 0.25],
        vertical_spacing=0.03,
        subplot_titles=("K線圖", "RSI (14)", "MACD (12,26,9)"),
    )

    # ── Candlestick ──
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="K線",
        increasing_line_color="#EF553B",
        decreasing_line_color="#00CC96",
    ), row=1, col=1)

    if show_ma and "MA5" in df.columns:
        for col, color, dash in [("MA5", "#FFA500", "solid"),
                                  ("MA20", "#1F77B4", "solid"),
                                  ("MA60", "#9467BD", "dash")]:
            if col in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df[col], name=col,
                    line=dict(color=color, width=1.2, dash=dash), opacity=0.9,
                ), row=1, col=1)

    if show_bb and "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_upper"], name="BB上軌",
            line=dict(color="rgba(100,100,200,0.5)", width=1, dash="dot"),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_lower"], name="BB下軌",
            line=dict(color="rgba(100,100,200,0.5)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(100,100,200,0.05)",
        ), row=1, col=1)

    # ── Volume (mini bar at bottom of main) ──
    colors = ["#EF553B" if c >= o else "#00CC96"
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"], name="成交量",
        marker_color=colors, opacity=0.4, showlegend=False,
        yaxis="y4",
    ), row=1, col=1)

    # ── RSI ──
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"], name="RSI14",
            line=dict(color="#FF7F0E", width=1.5),
        ), row=2, col=1)
        for level, color in [(70, "rgba(200,0,0,0.3)"), (30, "rgba(0,150,0,0.3)")]:
            fig.add_hline(y=level, line_dash="dash", line_color=color,
                          row=2, col=1)
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(200,0,0,0.05)",
                      line_width=0, row=2, col=1)
        fig.add_hrect(y0=0, y1=30, fillcolor="rgba(0,150,0,0.05)",
                      line_width=0, row=2, col=1)

    # ── MACD ──
    if "MACD_line" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD_line"], name="MACD",
            line=dict(color="#1F77B4", width=1.5),
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD_signal"], name="Signal",
            line=dict(color="#FF7F0E", width=1.5),
        ), row=3, col=1)
        hist = df["MACD_hist"]
        bar_colors = ["#EF553B" if v >= 0 else "#00CC96" for v in hist.fillna(0)]
        fig.add_trace(go.Bar(
            x=df.index, y=hist, name="Histogram",
            marker_color=bar_colors, opacity=0.7,
        ), row=3, col=1)

    fig.update_layout(
        title=dict(text=f"{code} {name}", font=dict(size=16)),
        height=700,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
        xaxis_rangeslider_visible=False,
        margin=dict(l=40, r=20, t=60, b=20),
    )
    fig.update_yaxes(title_text="價格 (NTD)", row=1, col=1)
    fig.update_yaxes(title_text="RSI",        row=2, col=1, range=[0, 100])
    fig.update_yaxes(title_text="MACD",       row=3, col=1)
    return fig


def metric_trend_chart(quarterly_data: dict, code: int,
                        field: str, label: str) -> go.Figure:
    quarters, values = [], []
    for qname in sorted(quarterly_data.keys()):
        df = quarterly_data[qname]
        row = df[df["code"] == code]
        if len(row) > 0:
            val = row.iloc[0][field]
            if pd.notna(val):
                quarters.append(qname)
                values.append(float(val))

    fig = go.Figure()
    if not values:
        return fig

    fig.add_trace(go.Scatter(
        x=quarters, y=values, mode="lines+markers+text",
        text=[f"{v:.1f}" for v in values],
        textposition="top center",
        line=dict(color=COLOR_LISTED, width=2),
        marker=dict(size=8),
        name=label,
    ))

    thresh_info = THRESHOLDS.get(field)
    if thresh_info:
        good_t, higher_good, bad_t = thresh_info
        fig.add_hline(y=good_t, line_dash="dash", line_color="green",
                      annotation_text=f"優質門檻 {good_t}", annotation_position="left")
        if bad_t is not None:
            fig.add_hline(y=bad_t, line_dash="dot", line_color="red",
                          annotation_text=f"警戒線 {bad_t}", annotation_position="left")

    fig.update_layout(
        title=f"{label} 季度趨勢",
        template="plotly_white",
        height=280,
        margin=dict(l=40, r=20, t=40, b=20),
        yaxis_title=label,
    )
    return fig


def distribution_chart(df: pd.DataFrame, field: str, label: str) -> go.Figure:
    vals = pd.to_numeric(df[field], errors="coerce").dropna()
    vals = vals[(vals >= vals.quantile(0.01)) & (vals <= vals.quantile(0.99))]

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=vals, nbinsx=50, name=label,
        marker_color=COLOR_LISTED, opacity=0.75,
    ))

    thresh_info = THRESHOLDS.get(field)
    if thresh_info:
        good_t, higher_good, bad_t = thresh_info
        fig.add_vline(x=good_t, line_dash="dash", line_color="green",
                      annotation_text=f"優質 {good_t}")
        if bad_t is not None:
            fig.add_vline(x=bad_t, line_dash="dot", line_color="red",
                          annotation_text=f"警戒 {bad_t}")

    fig.update_layout(
        title=f"{label} 分佈",
        template="plotly_white",
        height=260,
        margin=dict(l=40, r=20, t=40, b=20),
        showlegend=False,
    )
    return fig


def top20_chart(df: pd.DataFrame, field: str, label: str,
                ascending: bool = False) -> go.Figure:
    sub = df[["code", "name", "market", field]].copy()
    sub[field] = pd.to_numeric(sub[field], errors="coerce")
    sub = sub.dropna(subset=[field]).sort_values(field, ascending=ascending).head(20)
    sub = sub.iloc[::-1]  # flip for horizontal bar

    colors = [COLOR_LISTED if m == "上市" else COLOR_OTC for m in sub["market"]]
    labels = [f"{int(r.code)} {str(r['name'])}" for _, r in sub.iterrows()]

    fig = go.Figure(go.Bar(
        x=sub[field], y=labels,
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}" for v in sub[field]],
        textposition="outside",
    ))
    fig.update_layout(
        title=f"{label} Top 20",
        template="plotly_white",
        height=520,
        margin=dict(l=160, r=60, t=40, b=20),
        xaxis_title=label,
        yaxis=dict(tickfont=dict(size=11)),
    )
    return fig


def market_pie(df: pd.DataFrame) -> go.Figure:
    counts = df["market"].value_counts()
    fig = go.Figure(go.Pie(
        labels=counts.index,
        values=counts.values,
        marker_colors=[COLOR_LISTED, COLOR_OTC],
        hole=0.4,
    ))
    fig.update_layout(
        title="市場分佈",
        template="plotly_white",
        height=260,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=True,
    )
    return fig


def multi_metric_bar(stats: dict, metrics: list) -> go.Figure:
    labels = [m[0] for m in metrics]
    all_vals    = [stats["全市場"].get(m[1], 0) for m in metrics]
    listed_vals = [stats["上市"].get(m[1], 0)   for m in metrics]
    otc_vals    = [stats["上櫃"].get(m[1], 0)   for m in metrics]

    fig = go.Figure()
    for vals, name, color in [
        (all_vals, "全市場", "#888888"),
        (listed_vals, "上市", COLOR_LISTED),
        (otc_vals, "上櫃", COLOR_OTC),
    ]:
        fig.add_trace(go.Bar(name=name, x=labels, y=vals, marker_color=color))

    fig.update_layout(
        barmode="group",
        template="plotly_white",
        height=320,
        margin=dict(l=40, r=20, t=20, b=60),
        xaxis_tickangle=-30,
    )
    return fig
