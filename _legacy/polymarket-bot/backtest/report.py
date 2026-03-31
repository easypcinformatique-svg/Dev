"""
Générateur de rapport visuel interactif HTML.

Utilise Plotly pour créer un dashboard complet avec :
- Equity curve avec drawdown overlay
- Distribution des rendements
- Heatmap mensuelle des rendements
- Répartition des trades par catégorie
- Métriques clés en cards
- Analyse des positions et du risk management
"""

import numpy as np
import pandas as pd
import json
from datetime import datetime


def _plotly_cdn() -> str:
    return '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'


def _metric_card(label: str, value: str, color: str = "#00d4aa") -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-value" style="color: {color}">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """


def _format_pct(v: float) -> str:
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2%}"


def _format_ratio(v: float) -> str:
    return f"{v:.3f}"


def _format_money(v: float) -> str:
    return f"${v:,.0f}"


def generate_report(result, output_path: str = "backtest_report.html") -> str:
    """
    Génère un rapport HTML interactif complet.

    Args:
        result: BacktestResult du moteur de backtest
        output_path: Chemin du fichier HTML de sortie

    Returns:
        Chemin du fichier généré
    """
    m = result.metrics
    eq = result.equity_curve
    trades = result.trades
    positions = result.positions_over_time

    # --- Couleurs du thème ---
    bg_dark = "#0a0a1a"
    bg_card = "#12122a"
    text_main = "#e0e0e0"
    accent_green = "#00d4aa"
    accent_red = "#ff4757"
    accent_blue = "#4a90d9"
    accent_yellow = "#ffa502"
    grid_color = "#1a1a3a"

    # --- Préparer les données pour les charts ---
    # 1. Equity curve
    eq_daily = eq.resample("D").last().dropna()
    eq_dates = [str(d.date()) for d in eq_daily.index]
    eq_values = eq_daily.values.tolist()

    # Drawdown
    peak = np.maximum.accumulate(eq_daily.values)
    dd = ((eq_daily.values - peak) / peak * 100).tolist()

    # 2. Distribution des rendements quotidiens
    daily_ret = eq_daily.pct_change().dropna()
    ret_values = (daily_ret * 100).tolist()

    # 3. Heatmap mensuelle
    if len(daily_ret) > 0:
        monthly_ret = daily_ret.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        months = monthly_ret.index
        heatmap_data = {}
        for dt, val in zip(months, monthly_ret.values):
            year = str(dt.year)
            month = dt.month
            if year not in heatmap_data:
                heatmap_data[year] = [None] * 12
            heatmap_data[year][month - 1] = round(val * 100, 2)
        years = sorted(heatmap_data.keys())
        heatmap_z = [heatmap_data[y] for y in years]
    else:
        years = []
        heatmap_z = []

    # 4. Trades analysis
    if len(trades) > 0:
        win_pnls = trades[trades["pnl"] > 0]["pnl"].tolist()
        loss_pnls = trades[trades["pnl"] <= 0]["pnl"].tolist()
        trade_dates = [str(t) for t in trades["exit_time"]]
        trade_pnls = trades["pnl"].tolist()
        trade_cumul = trades["pnl"].cumsum().tolist()

        # Par exit_reason
        reason_counts = trades["exit_reason"].value_counts()
        reason_labels = reason_counts.index.tolist()
        reason_values = reason_counts.values.tolist()

        # Par side
        side_counts = trades["side"].value_counts()
        side_labels = side_counts.index.tolist()
        side_values = side_counts.values.tolist()
    else:
        win_pnls = loss_pnls = trade_dates = trade_pnls = trade_cumul = []
        reason_labels = reason_values = side_labels = side_values = []

    # 5. Exposure over time
    if len(positions) > 0:
        exp_dates = [str(d) for d in positions["timestamp"]]
        exp_values = (positions["exposure_pct"] * 100).tolist()
        n_pos = positions["n_positions"].tolist()
    else:
        exp_dates = exp_values = n_pos = []

    # --- Couleur du return ---
    ret_color = accent_green if m.total_return >= 0 else accent_red
    sharpe_color = accent_green if m.sharpe_ratio >= 1 else (accent_yellow if m.sharpe_ratio >= 0.5 else accent_red)
    dd_color = accent_green if abs(m.max_drawdown) < 0.10 else (accent_yellow if abs(m.max_drawdown) < 0.20 else accent_red)

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polymarket Backtest Report - {result.strategy_name}</title>
    {_plotly_cdn()}
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: {bg_dark};
            color: {text_main};
            min-height: 100vh;
        }}
        .header {{
            background: linear-gradient(135deg, #0d0d2b 0%, #1a1a4a 100%);
            padding: 30px 40px;
            border-bottom: 1px solid #2a2a5a;
        }}
        .header h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 5px;
        }}
        .header .subtitle {{
            color: #888;
            font-size: 14px;
        }}
        .header .strategy-badge {{
            display: inline-block;
            background: {accent_blue};
            color: #fff;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 13px;
            margin-top: 8px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px 40px; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: {bg_card};
            border: 1px solid #2a2a5a;
            border-radius: 12px;
            padding: 18px;
            text-align: center;
            transition: transform 0.2s;
        }}
        .metric-card:hover {{ transform: translateY(-2px); border-color: {accent_blue}; }}
        .metric-value {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; }}
        .metric-label {{ font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
        .chart-container {{
            background: {bg_card};
            border: 1px solid #2a2a5a;
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
        }}
        .chart-title {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 10px;
            color: #fff;
        }}
        .chart-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}
        .section-title {{
            font-size: 20px;
            font-weight: 700;
            color: #fff;
            margin: 30px 0 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid {accent_blue};
        }}
        .trades-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        .trades-table th {{
            background: #1a1a3a;
            padding: 10px 12px;
            text-align: left;
            font-weight: 600;
            color: #aaa;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}
        .trades-table td {{
            padding: 8px 12px;
            border-bottom: 1px solid #1a1a3a;
        }}
        .trades-table tr:hover {{ background: #1a1a2a; }}
        .pnl-positive {{ color: {accent_green}; font-weight: 600; }}
        .pnl-negative {{ color: {accent_red}; font-weight: 600; }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #555;
            font-size: 12px;
            border-top: 1px solid #1a1a3a;
            margin-top: 30px;
        }}
        @media (max-width: 768px) {{
            .chart-row {{ grid-template-columns: 1fr; }}
            .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .container {{ padding: 10px 15px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>POLYMARKET BACKTEST REPORT</h1>
        <div class="subtitle">
            Capital: {_format_money(m.initial_capital)} |
            Periode: {eq.index[0].strftime('%Y-%m-%d') if len(eq) > 0 else 'N/A'} →
            {eq.index[-1].strftime('%Y-%m-%d') if len(eq) > 0 else 'N/A'} |
            {m.total_trades} trades
        </div>
        <span class="strategy-badge">{result.strategy_name}</span>
    </div>

    <div class="container">
        <!-- KPI Cards -->
        <div class="metrics-grid">
            {_metric_card("Return Total", _format_pct(m.total_return), ret_color)}
            {_metric_card("Return Annualise", _format_pct(m.annualized_return), ret_color)}
            {_metric_card("Sharpe Ratio", _format_ratio(m.sharpe_ratio), sharpe_color)}
            {_metric_card("Sortino Ratio", _format_ratio(m.sortino_ratio), sharpe_color)}
            {_metric_card("Max Drawdown", _format_pct(m.max_drawdown), dd_color)}
            {_metric_card("Calmar Ratio", _format_ratio(m.calmar_ratio), accent_blue)}
            {_metric_card("Win Rate", _format_pct(m.win_rate), accent_green if m.win_rate > 0.5 else accent_red)}
            {_metric_card("Profit Factor", _format_ratio(m.profit_factor), accent_green if m.profit_factor > 1 else accent_red)}
            {_metric_card("PnL Cumule", _format_money(m.cumulative_pnl), ret_color)}
            {_metric_card("Volatilite Ann.", _format_pct(m.volatility_annualized), accent_yellow)}
            {_metric_card("VaR 95%", _format_pct(m.var_95), accent_red)}
            {_metric_card("Omega Ratio", _format_ratio(m.omega_ratio), accent_blue)}
        </div>

        <!-- Equity Curve + Drawdown -->
        <div class="section-title">Equity Curve & Drawdown</div>
        <div class="chart-container">
            <div id="equityChart" style="height: 400px;"></div>
        </div>

        <!-- Distribution + Heatmap -->
        <div class="section-title">Analyse des Rendements</div>
        <div class="chart-row">
            <div class="chart-container">
                <div id="distChart" style="height: 350px;"></div>
            </div>
            <div class="chart-container">
                <div id="heatmapChart" style="height: 350px;"></div>
            </div>
        </div>

        <!-- Trades Analysis -->
        <div class="section-title">Analyse des Trades</div>
        <div class="chart-row">
            <div class="chart-container">
                <div id="cumulPnlChart" style="height: 350px;"></div>
            </div>
            <div class="chart-container">
                <div id="tradeScatterChart" style="height: 350px;"></div>
            </div>
        </div>

        <div class="chart-row">
            <div class="chart-container">
                <div id="reasonPieChart" style="height: 300px;"></div>
            </div>
            <div class="chart-container">
                <div id="sidePieChart" style="height: 300px;"></div>
            </div>
        </div>

        <!-- Exposure -->
        <div class="section-title">Exposition & Positions</div>
        <div class="chart-container">
            <div id="exposureChart" style="height: 300px;"></div>
        </div>

        <!-- Detailed Metrics Table -->
        <div class="section-title">Metriques Detaillees</div>
        <div class="chart-container">
            <div class="chart-row">
                <div>
                    <table class="trades-table">
                        <tr><th colspan="2">Rendements</th></tr>
                        <tr><td>Meilleur jour</td><td class="pnl-positive">{_format_pct(m.best_day)}</td></tr>
                        <tr><td>Pire jour</td><td class="pnl-negative">{_format_pct(m.worst_day)}</td></tr>
                        <tr><td>Rendement moyen/jour</td><td>{_format_pct(m.avg_daily_return)}</td></tr>
                        <tr><td>Ecart-type</td><td>{_format_pct(m.return_std)}</td></tr>
                        <tr><th colspan="2">Risque</th></tr>
                        <tr><td>Downside Deviation</td><td>{_format_pct(m.downside_deviation)}</td></tr>
                        <tr><td>VaR 99%</td><td class="pnl-negative">{_format_pct(m.var_99)}</td></tr>
                        <tr><td>CVaR 95%</td><td class="pnl-negative">{_format_pct(m.cvar_95)}</td></tr>
                        <tr><td>CVaR 99%</td><td class="pnl-negative">{_format_pct(m.cvar_99)}</td></tr>
                        <tr><td>Skewness</td><td>{_format_ratio(m.skewness)}</td></tr>
                        <tr><td>Kurtosis</td><td>{_format_ratio(m.kurtosis)}</td></tr>
                    </table>
                </div>
                <div>
                    <table class="trades-table">
                        <tr><th colspan="2">Trades</th></tr>
                        <tr><td>Trades gagnants</td><td class="pnl-positive">{m.winning_trades}</td></tr>
                        <tr><td>Trades perdants</td><td class="pnl-negative">{m.losing_trades}</td></tr>
                        <tr><td>Gain moyen</td><td class="pnl-positive">{_format_money(m.avg_win)}</td></tr>
                        <tr><td>Perte moyenne</td><td class="pnl-negative">{_format_money(m.avg_loss)}</td></tr>
                        <tr><td>Plus gros gain</td><td class="pnl-positive">{_format_money(m.largest_win)}</td></tr>
                        <tr><td>Plus grosse perte</td><td class="pnl-negative">{_format_money(m.largest_loss)}</td></tr>
                        <tr><td>Expectancy</td><td>{_format_money(m.expectancy)}</td></tr>
                        <tr><td>Consecutifs gagnants</td><td>{m.max_consecutive_wins}</td></tr>
                        <tr><td>Consecutifs perdants</td><td>{m.max_consecutive_losses}</td></tr>
                        <tr><td>Trades/jour</td><td>{m.avg_trades_per_day:.1f}</td></tr>
                        <tr><td>Duree moy. (h)</td><td>{m.avg_trade_duration_hours:.1f}</td></tr>
                        <tr><td>Tail Ratio</td><td>{_format_ratio(m.tail_ratio)}</td></tr>
                    </table>
                </div>
            </div>
        </div>

        <!-- Last 50 trades -->
        <div class="section-title">Derniers Trades</div>
        <div class="chart-container" style="overflow-x: auto;">
            <table class="trades-table">
                <thead>
                    <tr>
                        <th>Market</th>
                        <th>Side</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Size</th>
                        <th>PnL</th>
                        <th>Return</th>
                        <th>Raison</th>
                        <th>Date sortie</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(_trade_row(t) for _, t in trades.tail(50).iterrows()) if len(trades) > 0 else "<tr><td colspan='9' style='text-align:center;padding:20px;'>Aucun trade</td></tr>"}
                </tbody>
            </table>
        </div>
    </div>

    <div class="footer">
        Polymarket Backtesting Engine | Rapport genere le {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </div>

    <script>
        const layout_base = {{
            paper_bgcolor: '{bg_dark}',
            plot_bgcolor: '{bg_card}',
            font: {{ color: '{text_main}', family: 'Segoe UI, system-ui, sans-serif' }},
            margin: {{ l: 50, r: 20, t: 40, b: 40 }},
            xaxis: {{ gridcolor: '{grid_color}', zerolinecolor: '{grid_color}' }},
            yaxis: {{ gridcolor: '{grid_color}', zerolinecolor: '{grid_color}' }},
        }};

        // 1. Equity Curve + Drawdown
        Plotly.newPlot('equityChart', [
            {{
                x: {json.dumps(eq_dates)},
                y: {json.dumps(eq_values)},
                type: 'scatter',
                mode: 'lines',
                name: 'Equity',
                line: {{ color: '{accent_green}', width: 2 }},
                fill: 'tonexty',
                fillcolor: 'rgba(0, 212, 170, 0.05)',
            }},
            {{
                x: {json.dumps(eq_dates)},
                y: {json.dumps(dd)},
                type: 'scatter',
                mode: 'lines',
                name: 'Drawdown %',
                line: {{ color: '{accent_red}', width: 1 }},
                fill: 'tozeroy',
                fillcolor: 'rgba(255, 71, 87, 0.1)',
                yaxis: 'y2',
            }}
        ], {{
            ...layout_base,
            title: 'Equity Curve & Drawdown',
            yaxis: {{ ...layout_base.yaxis, title: 'Capital ($)', tickformat: '$,.0f' }},
            yaxis2: {{ title: 'Drawdown (%)', overlaying: 'y', side: 'right', ticksuffix: '%', gridcolor: 'transparent', range: [Math.min(...{json.dumps(dd)}) * 1.5, 5] }},
            legend: {{ x: 0.01, y: 0.99, bgcolor: 'rgba(0,0,0,0.5)' }},
            hovermode: 'x unified',
        }});

        // 2. Distribution des rendements
        Plotly.newPlot('distChart', [{{
            x: {json.dumps(ret_values)},
            type: 'histogram',
            nbinsx: 50,
            marker: {{ color: '{accent_blue}', line: {{ color: '#fff', width: 0.5 }} }},
            opacity: 0.8,
        }}], {{
            ...layout_base,
            title: 'Distribution des Rendements Quotidiens',
            xaxis: {{ ...layout_base.xaxis, title: 'Rendement (%)' }},
            yaxis: {{ ...layout_base.yaxis, title: 'Frequence' }},
            shapes: [{{
                type: 'line', x0: 0, x1: 0, y0: 0, y1: 1, yref: 'paper',
                line: {{ color: '#fff', width: 1, dash: 'dash' }}
            }}],
        }});

        // 3. Heatmap mensuelle
        Plotly.newPlot('heatmapChart', [{{
            z: {json.dumps(heatmap_z)},
            y: {json.dumps(years)},
            x: ['Jan','Fev','Mar','Avr','Mai','Jun','Jul','Aou','Sep','Oct','Nov','Dec'],
            type: 'heatmap',
            colorscale: [[0, '{accent_red}'], [0.5, '{bg_dark}'], [1, '{accent_green}']],
            zmid: 0,
            text: {json.dumps(heatmap_z)},
            texttemplate: '%{{text:.1f}}%',
            textfont: {{ size: 10 }},
            hovertemplate: '%{{y}} %{{x}}: %{{z:.2f}}%<extra></extra>',
        }}], {{
            ...layout_base,
            title: 'Rendements Mensuels (%)',
        }});

        // 4. PnL cumulatif des trades
        Plotly.newPlot('cumulPnlChart', [{{
            x: {json.dumps(trade_dates)},
            y: {json.dumps(trade_cumul)},
            type: 'scatter',
            mode: 'lines',
            line: {{ color: '{accent_green}', width: 2 }},
            fill: 'tozeroy',
            fillcolor: 'rgba(0, 212, 170, 0.1)',
        }}], {{
            ...layout_base,
            title: 'PnL Cumule des Trades',
            yaxis: {{ ...layout_base.yaxis, title: 'PnL ($)', tickformat: '$,.0f' }},
        }});

        // 5. Trade scatter
        Plotly.newPlot('tradeScatterChart', [
            {{
                x: {json.dumps(trade_dates)},
                y: {json.dumps(trade_pnls)},
                type: 'bar',
                marker: {{
                    color: {json.dumps(trade_pnls)}.map(v => v >= 0 ? '{accent_green}' : '{accent_red}'),
                }},
            }}
        ], {{
            ...layout_base,
            title: 'PnL par Trade',
            yaxis: {{ ...layout_base.yaxis, title: 'PnL ($)', tickformat: '$,.0f' }},
        }});

        // 6. Exit reason pie
        Plotly.newPlot('reasonPieChart', [{{
            labels: {json.dumps(reason_labels)},
            values: {json.dumps(reason_values)},
            type: 'pie',
            hole: 0.4,
            marker: {{ colors: ['{accent_blue}', '{accent_red}', '{accent_green}', '{accent_yellow}'] }},
            textinfo: 'label+percent',
            textfont: {{ color: '#fff' }},
        }}], {{
            ...layout_base,
            title: 'Raisons de Sortie',
        }});

        // 7. Side pie
        Plotly.newPlot('sidePieChart', [{{
            labels: {json.dumps(side_labels)},
            values: {json.dumps(side_values)},
            type: 'pie',
            hole: 0.4,
            marker: {{ colors: ['{accent_green}', '{accent_red}'] }},
            textinfo: 'label+percent',
            textfont: {{ color: '#fff' }},
        }}], {{
            ...layout_base,
            title: 'Repartition YES / NO',
        }});

        // 8. Exposure
        Plotly.newPlot('exposureChart', [
            {{
                x: {json.dumps(exp_dates)},
                y: {json.dumps(exp_values)},
                type: 'scatter',
                mode: 'lines',
                name: 'Exposition %',
                line: {{ color: '{accent_yellow}', width: 1.5 }},
                fill: 'tozeroy',
                fillcolor: 'rgba(255, 165, 2, 0.1)',
            }},
            {{
                x: {json.dumps(exp_dates)},
                y: {json.dumps(n_pos)},
                type: 'scatter',
                mode: 'lines',
                name: 'Nb positions',
                line: {{ color: '{accent_blue}', width: 1.5 }},
                yaxis: 'y2',
            }}
        ], {{
            ...layout_base,
            title: 'Exposition & Nombre de Positions',
            yaxis: {{ ...layout_base.yaxis, title: 'Exposition (%)', ticksuffix: '%' }},
            yaxis2: {{ title: 'Positions', overlaying: 'y', side: 'right', gridcolor: 'transparent' }},
            legend: {{ x: 0.01, y: 0.99, bgcolor: 'rgba(0,0,0,0.5)' }},
        }});
    </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def _trade_row(trade: pd.Series) -> str:
    pnl_class = "pnl-positive" if trade["pnl"] >= 0 else "pnl-negative"
    ret_pct = trade.get("return_pct", 0)
    return f"""
    <tr>
        <td>{trade['market_id']}</td>
        <td>{trade['side']}</td>
        <td>{trade['entry_price']:.4f}</td>
        <td>{trade['exit_price']:.4f}</td>
        <td>${trade['size']:,.0f}</td>
        <td class="{pnl_class}">${trade['pnl']:,.2f}</td>
        <td class="{pnl_class}">{ret_pct:+.2%}</td>
        <td>{trade['exit_reason']}</td>
        <td>{str(trade['exit_time'])[:16]}</td>
    </tr>
    """
