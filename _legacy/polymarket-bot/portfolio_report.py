#!/usr/bin/env python3
"""
Reporting portefeuille PokyMarket — Génère un rapport HTML complet
pour un portefeuille de 10 000 € basé sur les résultats de backtest.
"""

import csv
import os
import json
from datetime import datetime

# --- Configuration ---
CAPITAL_INITIAL = 10_000.0  # Portefeuille en EUR
BACKTEST_CAPITAL = 5_000.0  # Capital du backtest original (USD)
SCALE_FACTOR = CAPITAL_INITIAL / BACKTEST_CAPITAL  # 2x
TRADES_CSV = "trades_report.csv"
TRAINING_RESULTS = "training_results.json"
OUTPUT_HTML = "portfolio_report_10k.html"


def load_trades(path):
    """Charge les trades depuis le CSV et scale au capital cible."""
    trades = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append({
                "id": int(row["#"]),
                "market": row["market_id"],
                "side": row["side"],
                "entry_price": float(row["entry_price"]),
                "exit_price": float(row["exit_price"]),
                "montant": float(row["montant_engage"]) * SCALE_FACTOR,
                "pnl": float(row["gain_perte"]) * SCALE_FACTOR,
                "entry_time": row["entry_time"],
                "exit_time": row["exit_time"],
                "exit_reason": row["exit_reason"],
                "rendement_pct": float(row["rendement_%"]),
                "pnl_cumule": float(row["pnl_cumule"]) * SCALE_FACTOR,
                "capital_total": float(row["capital_total"]) * SCALE_FACTOR,
            })
    return trades


def load_training(path):
    """Charge les résultats du training."""
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def compute_stats(trades):
    """Calcule les métriques du portefeuille."""
    if not trades:
        return {}

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    total_pnl = sum(pnls)
    total_return = total_pnl / CAPITAL_INITIAL
    n_trades = len(trades)
    n_wins = len(wins)
    n_losses = len(losses)
    win_rate = n_wins / n_trades if n_trades > 0 else 0

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.0001
    profit_factor = gross_profit / gross_loss

    avg_win = sum(wins) / n_wins if wins else 0
    avg_loss = sum(losses) / n_losses if losses else 0
    expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss

    largest_win = max(pnls) if pnls else 0
    largest_loss = min(pnls) if pnls else 0

    # Drawdown
    equity_curve = [CAPITAL_INITIAL]
    for t in trades:
        equity_curve.append(equity_curve[-1] + t["pnl"])
    peak = equity_curve[0]
    max_dd = 0
    max_dd_pct = 0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (val - peak) / peak
        if dd < max_dd_pct:
            max_dd_pct = dd
            max_dd = val - peak

    # Consecutive wins/losses
    max_consec_wins = max_consec_losses = 0
    curr_wins = curr_losses = 0
    for p in pnls:
        if p > 0:
            curr_wins += 1
            curr_losses = 0
            max_consec_wins = max(max_consec_wins, curr_wins)
        else:
            curr_losses += 1
            curr_wins = 0
            max_consec_losses = max(max_consec_losses, curr_losses)

    # Monthly returns
    monthly = {}
    for t in trades:
        try:
            dt = datetime.strptime(t["entry_time"], "%Y-%m-%d %H:%M")
            key = dt.strftime("%Y-%m")
        except Exception:
            continue
        monthly.setdefault(key, 0)
        monthly[key] += t["pnl"]

    # Category breakdown
    categories = {}
    for t in trades:
        cat = t["market"].split("-")[1] if "-" in t["market"] else "OTHER"
        categories.setdefault(cat, {"trades": 0, "pnl": 0, "wins": 0})
        categories[cat]["trades"] += 1
        categories[cat]["pnl"] += t["pnl"]
        if t["pnl"] > 0:
            categories[cat]["wins"] += 1

    # Period
    first_date = trades[0]["entry_time"][:10]
    last_date = trades[-1]["entry_time"][:10]

    return {
        "n_trades": n_trades,
        "n_wins": n_wins,
        "n_losses": n_losses,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "total_return": total_return,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "max_dd_pct": max_dd_pct,
        "max_dd_eur": max_dd,
        "max_consec_wins": max_consec_wins,
        "max_consec_losses": max_consec_losses,
        "final_capital": CAPITAL_INITIAL + total_pnl,
        "equity_curve": equity_curve,
        "monthly": monthly,
        "categories": categories,
        "first_date": first_date,
        "last_date": last_date,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
    }


def generate_html(trades, stats, training):
    """Génère le rapport HTML complet."""

    # --- Equity curve data ---
    eq_labels = list(range(len(stats["equity_curve"])))
    eq_values = [round(v, 2) for v in stats["equity_curve"]]

    # Peak for drawdown
    peaks = []
    peak = eq_values[0]
    dd_values = []
    for v in eq_values:
        if v > peak:
            peak = v
        peaks.append(peak)
        dd_values.append(round((v - peak) / peak * 100, 2))

    # Monthly returns for bar chart
    months_sorted = sorted(stats["monthly"].keys())
    monthly_labels = months_sorted
    monthly_values = [round(stats["monthly"][m], 2) for m in months_sorted]
    monthly_colors = ["#00d4aa" if v >= 0 else "#ff4757" for v in monthly_values]

    # Category data
    cat_labels = list(stats["categories"].keys())
    cat_pnls = [round(stats["categories"][c]["pnl"], 2) for c in cat_labels]
    cat_trades = [stats["categories"][c]["trades"] for c in cat_labels]
    cat_winrates = [round(stats["categories"][c]["wins"] / stats["categories"][c]["trades"] * 100, 1) for c in cat_labels]

    # Category full names
    cat_names = {
        "POL": "Politique", "CRY": "Crypto", "SPO": "Sport",
        "GEO": "Géopolitique", "ECO": "Économie", "TEC": "Tech",
    }

    # Trades table rows
    trade_rows = ""
    for t in trades:
        color = "#00d4aa" if t["pnl"] > 0 else "#ff4757"
        cat = t["market"].split("-")[1] if "-" in t["market"] else "?"
        trade_rows += f"""
        <tr>
            <td>{t['id']}</td>
            <td><span class="badge badge-{cat.lower()}">{cat_names.get(cat, cat)}</span></td>
            <td>{t['side']}</td>
            <td>{t['entry_price']:.4f}</td>
            <td>{t['exit_price']:.4f}</td>
            <td>{t['montant']:,.0f} €</td>
            <td style="color:{color};font-weight:700">{t['pnl']:+,.2f} €</td>
            <td style="color:{color}">{t['rendement_pct']:+.1f}%</td>
            <td><span class="reason reason-{t['exit_reason']}">{t['exit_reason']}</span></td>
            <td>{t['entry_time'][:10]}</td>
        </tr>"""

    # Training params
    training_section = ""
    if training:
        bp = training["best_params"]
        training_section = f"""
        <div class="section">
            <h2>Paramètres Optimisés (Bayesian Training - {training['n_iterations']} itérations)</h2>
            <div class="params-grid">
                <div class="param-item">
                    <span class="param-label">Consensus min</span>
                    <span class="param-value">{bp['min_consensus']:.3f}</span>
                </div>
                <div class="param-item">
                    <span class="param-label">Stratégies min</span>
                    <span class="param-value">{bp['min_agreeing_strategies']}</span>
                </div>
                <div class="param-item">
                    <span class="param-label">Spread filter</span>
                    <span class="param-value">{bp['spread_filter']:.3f}</span>
                </div>
                <div class="param-item">
                    <span class="param-label">Vol. percentile</span>
                    <span class="param-value">{bp['volume_percentile_filter']:.1f}</span>
                </div>
                <div class="param-item">
                    <span class="param-label">Stop Loss</span>
                    <span class="param-value">{bp['stop_loss']:.1%}</span>
                </div>
                <div class="param-item">
                    <span class="param-label">Take Profit</span>
                    <span class="param-value">{bp['take_profit']:.1%}</span>
                </div>
                <div class="param-item">
                    <span class="param-label">Trailing Stop</span>
                    <span class="param-value">{bp['trailing_stop']:.1%}</span>
                </div>
                <div class="param-item">
                    <span class="param-label">Max Position</span>
                    <span class="param-value">{bp['max_position_pct']:.0%}</span>
                </div>
                <div class="param-item">
                    <span class="param-label">Max Positions</span>
                    <span class="param-value">{bp['max_positions']}</span>
                </div>
                <div class="param-item">
                    <span class="param-label">Prix max extrême</span>
                    <span class="param-value">{bp['max_price_extreme']:.3f}</span>
                </div>
                <div class="param-item">
                    <span class="param-label">Prix min extrême</span>
                    <span class="param-value">{bp['min_price_extreme']:.3f}</span>
                </div>
                <div class="param-item">
                    <span class="param-label">Best Fitness</span>
                    <span class="param-value">{training['best_fitness']:.3f}</span>
                </div>
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PokyMarket - Reporting Portefeuille 10 000 €</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0a0a1a;
            color: #e0e0e0;
            line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}

        /* Header */
        .header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, #12122a 0%, #1a1a3a 100%);
            border-radius: 16px;
            margin-bottom: 30px;
            border: 1px solid #2a2a4a;
        }}
        .header h1 {{
            font-size: 2.2rem;
            background: linear-gradient(135deg, #00d4aa, #4a90d9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }}
        .header .subtitle {{ color: #8888aa; font-size: 1.1rem; }}
        .header .date {{ color: #6666aa; font-size: 0.9rem; margin-top: 5px; }}

        /* Metric Cards */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #12122a;
            border: 1px solid #2a2a4a;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            transition: transform 0.2s;
        }}
        .metric-card:hover {{ transform: translateY(-2px); border-color: #00d4aa44; }}
        .metric-value {{
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .metric-label {{ color: #8888aa; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; }}
        .green {{ color: #00d4aa; }}
        .red {{ color: #ff4757; }}
        .blue {{ color: #4a90d9; }}
        .yellow {{ color: #ffa502; }}
        .white {{ color: #e0e0e0; }}

        /* Sections */
        .section {{
            background: #12122a;
            border: 1px solid #2a2a4a;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        .section h2 {{
            font-size: 1.3rem;
            color: #4a90d9;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #2a2a4a;
        }}
        .chart {{ width: 100%; height: 400px; }}
        .chart-half {{ width: 100%; height: 350px; }}

        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        @media (max-width: 900px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}

        /* Table */
        .trades-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }}
        .trades-table th {{
            background: #1a1a3a;
            color: #4a90d9;
            padding: 10px 8px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        .trades-table td {{
            padding: 8px;
            border-bottom: 1px solid #1a1a3a;
        }}
        .trades-table tr:hover {{ background: #1a1a3a44; }}
        .table-wrap {{
            max-height: 500px;
            overflow-y: auto;
            border-radius: 8px;
        }}

        /* Badges */
        .badge {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-pol {{ background: #4a90d922; color: #4a90d9; }}
        .badge-cry {{ background: #ffa50222; color: #ffa502; }}
        .badge-spo {{ background: #00d4aa22; color: #00d4aa; }}
        .badge-geo {{ background: #ff475722; color: #ff4757; }}
        .badge-eco {{ background: #9b59b622; color: #9b59b6; }}
        .badge-tec {{ background: #3498db22; color: #3498db; }}

        .reason {{
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.75rem;
        }}
        .reason-take_profit {{ background: #00d4aa22; color: #00d4aa; }}
        .reason-stop_loss {{ background: #ff475722; color: #ff4757; }}
        .reason-resolution {{ background: #ffa50222; color: #ffa502; }}

        /* Params grid */
        .params-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
        }}
        .param-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 12px;
            background: #1a1a3a;
            border-radius: 6px;
        }}
        .param-label {{ color: #8888aa; font-size: 0.85rem; }}
        .param-value {{ color: #00d4aa; font-weight: 600; }}

        /* Risk gauge */
        .risk-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
        }}
        .risk-item {{
            background: #1a1a3a;
            border-radius: 8px;
            padding: 16px;
        }}
        .risk-item .label {{ color: #8888aa; font-size: 0.85rem; margin-bottom: 4px; }}
        .risk-item .value {{ font-size: 1.3rem; font-weight: 700; }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 20px;
            color: #555;
            font-size: 0.8rem;
        }}
    </style>
</head>
<body>
<div class="container">

    <!-- Header -->
    <div class="header">
        <h1>PokyMarket Portfolio Report</h1>
        <div class="subtitle">Portefeuille de {CAPITAL_INITIAL:,.0f} € — Stratégie AlphaComposite</div>
        <div class="date">Période : {stats['first_date']} au {stats['last_date']} | Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
    </div>

    <!-- KPI Cards -->
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-value {'green' if stats['total_return'] >= 0 else 'red'}">{stats['total_return']:+.1%}</div>
            <div class="metric-label">Return Total</div>
        </div>
        <div class="metric-card">
            <div class="metric-value {'green' if stats['total_pnl'] >= 0 else 'red'}">{stats['total_pnl']:+,.0f} €</div>
            <div class="metric-label">PnL Total</div>
        </div>
        <div class="metric-card">
            <div class="metric-value green">{stats['final_capital']:,.0f} €</div>
            <div class="metric-label">Capital Final</div>
        </div>
        <div class="metric-card">
            <div class="metric-value blue">{stats['n_trades']}</div>
            <div class="metric-label">Trades Total</div>
        </div>
        <div class="metric-card">
            <div class="metric-value {'green' if stats['win_rate'] >= 0.5 else 'yellow'}">{stats['win_rate']:.1%}</div>
            <div class="metric-label">Win Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value green">{stats['profit_factor']:.2f}x</div>
            <div class="metric-label">Profit Factor</div>
        </div>
        <div class="metric-card">
            <div class="metric-value red">{stats['max_dd_pct']:.1%}</div>
            <div class="metric-label">Max Drawdown</div>
        </div>
        <div class="metric-card">
            <div class="metric-value yellow">{stats['expectancy']:+.0f} €</div>
            <div class="metric-label">Espérance / Trade</div>
        </div>
    </div>

    <!-- Equity Curve -->
    <div class="section">
        <h2>Courbe d'Equity & Drawdown</h2>
        <div id="equity-chart" class="chart"></div>
    </div>

    <!-- Monthly + Categories -->
    <div class="grid-2">
        <div class="section">
            <h2>PnL Mensuel</h2>
            <div id="monthly-chart" class="chart-half"></div>
        </div>
        <div class="section">
            <h2>Performance par Catégorie</h2>
            <div id="category-chart" class="chart-half"></div>
        </div>
    </div>

    <!-- Risk Metrics -->
    <div class="section">
        <h2>Analyse des Risques</h2>
        <div class="risk-grid">
            <div class="risk-item">
                <div class="label">Capital Initial</div>
                <div class="value white">{CAPITAL_INITIAL:,.0f} €</div>
            </div>
            <div class="risk-item">
                <div class="label">Capital Final</div>
                <div class="value green">{stats['final_capital']:,.0f} €</div>
            </div>
            <div class="risk-item">
                <div class="label">Capital Peak</div>
                <div class="value blue">{max(stats['equity_curve']):,.0f} €</div>
            </div>
            <div class="risk-item">
                <div class="label">Max Drawdown</div>
                <div class="value red">{stats['max_dd_pct']:.2%} ({stats['max_dd_eur']:+,.0f} €)</div>
            </div>
            <div class="risk-item">
                <div class="label">Plus Gros Gain</div>
                <div class="value green">{stats['largest_win']:+,.0f} €</div>
            </div>
            <div class="risk-item">
                <div class="label">Plus Grosse Perte</div>
                <div class="value red">{stats['largest_loss']:+,.0f} €</div>
            </div>
            <div class="risk-item">
                <div class="label">Gain Moyen</div>
                <div class="value green">{stats['avg_win']:+,.0f} €</div>
            </div>
            <div class="risk-item">
                <div class="label">Perte Moyenne</div>
                <div class="value red">{stats['avg_loss']:+,.0f} €</div>
            </div>
            <div class="risk-item">
                <div class="label">Profit Brut</div>
                <div class="value green">{stats['gross_profit']:+,.0f} €</div>
            </div>
            <div class="risk-item">
                <div class="label">Perte Brute</div>
                <div class="value red">-{stats['gross_loss']:,.0f} €</div>
            </div>
            <div class="risk-item">
                <div class="label">Consécutifs Gagnants</div>
                <div class="value green">{stats['max_consec_wins']}</div>
            </div>
            <div class="risk-item">
                <div class="label">Consécutifs Perdants</div>
                <div class="value red">{stats['max_consec_losses']}</div>
            </div>
        </div>
    </div>

    <!-- Category breakdown table -->
    <div class="section">
        <h2>Détail par Catégorie</h2>
        <table class="trades-table">
            <thead>
                <tr>
                    <th>Catégorie</th>
                    <th>Trades</th>
                    <th>Win Rate</th>
                    <th>PnL</th>
                    <th>% du PnL Total</th>
                </tr>
            </thead>
            <tbody>
                {"".join(f'''<tr>
                    <td><span class="badge badge-{c.lower()}">{cat_names.get(c, c)}</span></td>
                    <td>{stats["categories"][c]["trades"]}</td>
                    <td>{stats["categories"][c]["wins"]/stats["categories"][c]["trades"]:.0%}</td>
                    <td style="color:{'#00d4aa' if stats['categories'][c]['pnl']>=0 else '#ff4757'};font-weight:700">{stats["categories"][c]["pnl"]:+,.0f} €</td>
                    <td>{stats["categories"][c]["pnl"]/stats["total_pnl"]*100:.1f}%</td>
                </tr>''' for c in sorted(stats["categories"].keys(), key=lambda x: stats["categories"][x]["pnl"], reverse=True))}
            </tbody>
        </table>
    </div>

    {training_section}

    <!-- Trade History -->
    <div class="section">
        <h2>Historique des Trades ({stats['n_trades']} trades)</h2>
        <div class="table-wrap">
            <table class="trades-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Catégorie</th>
                        <th>Side</th>
                        <th>Entrée</th>
                        <th>Sortie</th>
                        <th>Montant</th>
                        <th>PnL</th>
                        <th>Rend.</th>
                        <th>Raison</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    {trade_rows}
                </tbody>
            </table>
        </div>
    </div>

    <div class="footer">
        PokyMarket — Reporting automatisé | Stratégie AlphaComposite optimisée par Bayesian Training<br>
        Les performances passées ne préjugent pas des performances futures.
    </div>
</div>

<script>
    const plotConfig = {{responsive: true, displayModeBar: false}};
    const layoutBase = {{
        paper_bgcolor: '#12122a',
        plot_bgcolor: '#12122a',
        font: {{color: '#e0e0e0', family: 'Segoe UI, system-ui, sans-serif'}},
        margin: {{l: 50, r: 30, t: 30, b: 40}},
        xaxis: {{gridcolor: '#1a1a3a', zerolinecolor: '#2a2a4a'}},
        yaxis: {{gridcolor: '#1a1a3a', zerolinecolor: '#2a2a4a'}},
    }};

    // Equity Curve
    Plotly.newPlot('equity-chart', [
        {{
            y: {eq_values},
            type: 'scatter',
            mode: 'lines',
            name: 'Capital (€)',
            line: {{color: '#00d4aa', width: 2}},
            fill: 'tozeroy',
            fillcolor: 'rgba(0,212,170,0.05)',
        }},
        {{
            y: {dd_values},
            type: 'scatter',
            mode: 'lines',
            name: 'Drawdown (%)',
            yaxis: 'y2',
            line: {{color: '#ff4757', width: 1}},
            fill: 'tozeroy',
            fillcolor: 'rgba(255,71,87,0.1)',
        }}
    ], {{
        ...layoutBase,
        yaxis: {{...layoutBase.yaxis, title: 'Capital (€)', tickformat: ',.0f'}},
        yaxis2: {{
            title: 'Drawdown (%)',
            overlaying: 'y',
            side: 'right',
            gridcolor: '#1a1a3a',
            tickformat: '.1f',
            range: [{min(dd_values) * 1.5}, 0],
        }},
        legend: {{x: 0.01, y: 0.99, bgcolor: 'rgba(0,0,0,0.5)'}},
        hovermode: 'x unified',
    }}, plotConfig);

    // Monthly PnL
    Plotly.newPlot('monthly-chart', [{{
        x: {monthly_labels},
        y: {monthly_values},
        type: 'bar',
        marker: {{color: {monthly_colors}}},
        hovertemplate: '%{{x}}<br>PnL: %{{y:+,.0f}} €<extra></extra>',
    }}], {{
        ...layoutBase,
        yaxis: {{...layoutBase.yaxis, title: 'PnL (€)', tickformat: '+,.0f'}},
        xaxis: {{...layoutBase.xaxis, tickangle: -45}},
    }}, plotConfig);

    // Category
    Plotly.newPlot('category-chart', [
        {{
            x: {[cat_names.get(c, c) for c in cat_labels]},
            y: {cat_pnls},
            type: 'bar',
            name: 'PnL (€)',
            marker: {{color: {["#00d4aa" if p >= 0 else "#ff4757" for p in cat_pnls]}}},
            hovertemplate: '%{{x}}<br>PnL: %{{y:+,.0f}} €<extra></extra>',
        }},
    ], {{
        ...layoutBase,
        yaxis: {{...layoutBase.yaxis, title: 'PnL (€)', tickformat: '+,.0f'}},
    }}, plotConfig);
</script>

</body>
</html>"""
    return html


def main():
    print(f"Génération du reporting portefeuille {CAPITAL_INITIAL:,.0f} €...")

    trades = load_trades(TRADES_CSV)
    training = load_training(TRAINING_RESULTS)
    stats = compute_stats(trades)

    html = generate_html(trades, stats, training)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nRapport généré : {OUTPUT_HTML}")
    print(f"{'='*55}")
    print(f"  RÉSUMÉ PORTEFEUILLE {CAPITAL_INITIAL:,.0f} €")
    print(f"{'='*55}")
    print(f"  Période         : {stats['first_date']} → {stats['last_date']}")
    print(f"  Capital initial  : {CAPITAL_INITIAL:>10,.0f} €")
    print(f"  Capital final    : {stats['final_capital']:>10,.0f} €")
    print(f"  PnL total        : {stats['total_pnl']:>+10,.0f} €")
    print(f"  Return           : {stats['total_return']:>+10.1%}")
    print(f"  Trades           : {stats['n_trades']:>10d}")
    print(f"  Win Rate         : {stats['win_rate']:>10.1%}")
    print(f"  Profit Factor    : {stats['profit_factor']:>10.2f}x")
    print(f"  Max Drawdown     : {stats['max_dd_pct']:>10.2%}")
    print(f"  Espérance/trade  : {stats['expectancy']:>+10.0f} €")
    print(f"{'='*55}")

    # Category breakdown
    print(f"\n  PERFORMANCE PAR CATÉGORIE")
    print(f"  {'Catégorie':<12} {'Trades':>7} {'Win%':>7} {'PnL':>12}")
    print(f"  {'-'*40}")
    cat_names = {"POL": "Politique", "CRY": "Crypto", "SPO": "Sport",
                 "GEO": "Géopolitiq", "ECO": "Économie", "TEC": "Tech"}
    for cat in sorted(stats["categories"].keys(), key=lambda x: stats["categories"][x]["pnl"], reverse=True):
        c = stats["categories"][cat]
        wr = c["wins"] / c["trades"] * 100
        print(f"  {cat_names.get(cat, cat):<12} {c['trades']:>7d} {wr:>6.0f}% {c['pnl']:>+10,.0f} €")


if __name__ == "__main__":
    main()
