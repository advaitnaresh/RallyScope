"""RallyScope Week 7: interactive badminton dashboard (Plotly Dash).

Three views linked by clickData -> dcc.Store -> shared filter -> all figures.
All figures are calculated from the original, locally downloaded BWF CSV.

Attribution: Dataset by Sahil Motyar, underlying results © BWF.
AI use: ChatGPT assisted with Python/Dash implementation and documentation.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
from dash import Dash, dcc, html, Input, Output, ctx
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go

from data_pipeline import (
    load_matches, select_matches, comeback_summary,
    competitiveness_summary, rivalry_summary, DISCIPLINES,
)

ROOT = Path(__file__).resolve().parent
DATA, QUALITY = load_matches(ROOT / 'data' / 'matches.csv')
YEARS = [int(DATA['year'].min()), int(DATA['year'].max())]
# Levels are grouped by historical competition era; within each era, lower tiers
# appear before higher tiers. Different eras are not treated as interchangeable.
TIER_ORDER = [
    'Grand Prix', 'Grand Prix Gold', 'World Superseries',
    'World Superseries Premier', 'BWF Tour Super 100',
    'HSBC BWF World Tour Super 300', 'HSBC BWF World Tour Super 500',
    'HSBC BWF World Tour Super 750', 'HSBC BWF World Tour Super 1000',
    'HSBC BWF World Tour Finals', 'Grade 1 – Individual Tournaments',
]
TIERS = sorted(DATA['tier'].dropna().unique().tolist(),
               key=lambda t: (TIER_ORDER.index(t) if t in TIER_ORDER else 999, t))
PURPLE = '#57068C'
VIOLET = '#7548B4'
LAVENDER = '#AB88D8'
MUTED = '#697184'
GRID = '#EAE4F1'
PAPER = '#FFFFFF'
DISCIPLINE_NAMES = {'MS': "Men's singles", 'WS': "Women's singles",
                    'MD': "Men's doubles", 'WD': "Women's doubles", 'XD': 'Mixed doubles'}


def base_figure(title: str, subtitle: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title={'text': f'<b>{title}</b><br><span style="font-size:12px;color:#697184">{subtitle}</span>', 'x': 0.02},
        paper_bgcolor=PAPER, plot_bgcolor=PAPER,
        margin={'l': 42, 'r': 16, 't': 82, 'b': 57},
        font={'family': 'Arial, Helvetica, sans-serif', 'color': '#2A2340', 'size': 12},
        showlegend=False, hoverlabel={'bgcolor': '#ffffff', 'font_size': 12},
        clickmode='event+select',
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=GRID)
    return fig


def empty_figure(title: str, subtitle: str, message: str) -> go.Figure:
    fig = base_figure(title, subtitle)
    fig.add_annotation(text=message, x=0.5, y=0.5, xref='paper', yref='paper',
                       showarrow=False, font={'size': 14, 'color': MUTED})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def comeback_fig(df, selection):
    # The proposal's ranking rule is >=10 opportunities. A selected subset may
    # be smaller, so show exploratory contextual values but label them as such.
    contextual = bool(selection)
    required = 1 if contextual else 10
    s = comeback_summary(df, min_opportunities=required).head(12)
    if s.empty:
        return empty_figure('A · Comeback leaders', 'After losing the first game',
                            'No score-valid matches for this filter.')
    s = s.iloc[::-1]
    fig = base_figure('A · Comeback leaders',
                      'Recovery win rate after Game 1 loss' +
                      (' · exploratory small samples' if contextual else ' · minimum 10 opportunities'))
    custom = np.stack([s['competitor'], s['comeback_wins'], s['opportunities']], axis=-1)
    fig.add_trace(go.Bar(
        y=s['competitor'], x=s['rate_pct'], orientation='h',
        marker={'color': [PURPLE if i == len(s)-1 else LAVENDER for i in range(len(s))]},
        customdata=custom, text=[f'{r:.1f}%' for r in s['rate_pct']],
        textposition='outside', cliponaxis=False,
        hovertemplate='<b>%{customdata[0]}</b><br>Comeback rate %{x:.1f}%'
                      '<br>Wins %{customdata[1]} / opportunities %{customdata[2]}<extra></extra>',
    ))
    fig.update_layout(margin={'l': 150, 'r': 42, 't': 84, 'b': 58}, height=460)
    fig.update_xaxes(title='Comeback success rate (%)', range=[0, max(45, min(108, float(s['rate_pct'].max())+12))])
    fig.update_yaxes(title=None, showgrid=False, automargin=True)
    return fig


def competition_fig(df):
    s = competitiveness_summary(df)
    if s.empty:
        return empty_figure('B · Singles vs. doubles', 'Deciding-game frequency',
                            'No score-valid matches for this filter.')
    fig = base_figure('B · Singles vs. doubles', 'Deciding-game frequency across five disciplines')
    colors = [PURPLE if d in ('MS', 'WS') else LAVENDER for d in s['discipline'].astype(str)]
    custom = np.stack([s['discipline'].astype(str), s['matches'],
                       s['deciding'], s['avg_game_margin'].round(2)], axis=-1)
    fig.add_trace(go.Bar(
        x=s['discipline'].astype(str), y=s['rate_pct'],
        marker={'color': colors}, customdata=custom,
        text=[f'{v:.1f}%' for v in s['rate_pct']], textposition='outside', cliponaxis=False,
        hovertemplate='<b>%{customdata[0]}</b><br>Deciding-game rate %{y:.1f}%'
                      '<br>Deciding matches: %{customdata[2]} / %{customdata[1]}'
                      '<br>Avg game-point margin: %{customdata[3]}<extra></extra>',
    ))
    fig.update_layout(height=460, margin={'l': 56, 'r': 30, 't': 84, 'b': 64})
    fig.update_xaxes(title='MS · WS · MD · WD · XD (click to filter)', type='category',
                     categoryorder='array', categoryarray=list(DISCIPLINES))
    fig.update_yaxes(title='Deciding-game rate (%)', range=[0, max(50, min(100, float(s['rate_pct'].max())+12))], ticksuffix='%')
    return fig


def rivalry_fig(df):
    s = rivalry_summary(df, min_meetings=6).head(120)
    if s.empty:
        return empty_figure('C · Competitive rivalries', 'Head-to-head parity and meetings',
                            'No rivalry with at least 6 meetings under these filters.')
    sizes = np.maximum(9.0, 7.0 + 5.6 * np.sqrt(s['deciding_games'].to_numpy(dtype=float)))
    custom = np.stack([s['rivalry_id'], s['side_a'], s['side_b'],
                       s['side_a_wins'], s['meetings'], s['deciding_games']], axis=-1)
    fig = base_figure('C · Competitive rivalries',
                      'Parity 100% means a 50/50 record · circle size = number of deciding games')
    fig.add_trace(go.Scatter(
        x=s['meetings'], y=s['parity_pct'], mode='markers',
        marker={'size': sizes, 'color': VIOLET, 'opacity': .64,
                'line': {'color': PURPLE, 'width': .7}},
        customdata=custom,
        hovertemplate='<b>%{customdata[1]} vs. %{customdata[2]}</b>'
                      '<br>Meetings %{customdata[4]}'
                      '<br>Side A wins %{customdata[3]}'
                      '<br>Head-to-head parity %{y:.1f}%'
                      '<br>Deciding games %{customdata[5]}<extra></extra>',
    ))
    fig.update_layout(height=400, margin={'l': 60, 'r': 36, 't': 85, 'b': 60})
    fig.update_xaxes(title='Head-to-head meetings (min. 6)', rangemode='tozero')
    fig.update_yaxes(title='Rivalry parity (%)', range=[0, 105], ticksuffix='%')
    return fig


app = Dash(__name__, title='RallyScope · Badminton Analytics')
server = app.server
app.layout = html.Div(className='page', children=[
    dcc.Store(id='active-selection', data=None),
    html.Header(className='header', children=[
        html.Div([
            html.Div('RallyScope', className='logo'),
            html.Div('INTERACTIVE BADMINTON PERFORMANCE & RIVALRY ANALYTICS', className='subtitle'),
        ]),
        html.Div('NYU Tandon · Week 7 prototype', className='eyebrow')
    ]),
    html.Section(className='filters', children=[
        html.Div([html.Label('Year range'), dcc.RangeSlider(
            id='year-filter', min=YEARS[0], max=YEARS[1], step=1,
            value=YEARS, marks={x:str(x) for x in range(YEARS[0],YEARS[1]+1,5)}
        )], className='filter years'),
        html.Div([html.Label('Discipline'), dcc.Dropdown(
            id='discipline-filter', options=[{'label': DISCIPLINE_NAMES[d], 'value': d} for d in DISCIPLINES],
            value=list(DISCIPLINES), multi=True, clearable=False)], className='filter'),
        html.Div([html.Label('Tournament tier'), dcc.Dropdown(
            id='tier-filter', options=[{'label': x, 'value': x} for x in TIERS],
            value=TIERS, multi=True, clearable=False)], className='filter'),
        html.Button('Clear chart selection', id='clear-selection', n_clicks=0, className='reset')
    ]),
    html.Div(className='data-strip', children=[
        html.Div([html.Span('Score-valid matches: '), html.B(f"{QUALITY['score_valid_matches']:,}")]),
        html.Div([html.Span('Original source rows: '), html.B(f"{QUALITY['source_rows']:,}")]),
        html.Div([html.Span('Excluded incomplete/ambiguous rows: '), html.B(f"{QUALITY['excluded_rows']:,}")])
    ]),
    html.Div(id='filter-status', className='status'),
    html.Div(className='top-grid', children=[
        html.Section(className='chart-card', children=[dcc.Graph(id='comeback-chart', config={'displaylogo': False})]),
        html.Section(className='chart-card', children=[dcc.Graph(id='competition-chart', config={'displaylogo': False})]),
    ]),
    html.Section(className='chart-card rivalry', children=[dcc.Graph(id='rivalry-chart', config={'displaylogo': False})]),
    html.Footer(className='footer', children=[
        html.Div('Click a bar or rivalry bubble to filter the other charts. Use Clear chart selection to return to the overview.'),
        html.Div('Source: Sahil Motyar / BWF Match Data, underlying results © BWF. Not an official BWF product.'),
    ]),
])


@app.callback(
    Output('active-selection', 'data'),
    Input('comeback-chart', 'clickData'),
    Input('competition-chart', 'clickData'),
    Input('rivalry-chart', 'clickData'),
    Input('clear-selection', 'n_clicks'),
    prevent_initial_call=True,
)
def set_selection(comeback_click, competition_click, rivalry_click, clear):
    """One selected chart datum is stored and applied consistently to all views."""
    source = ctx.triggered_id
    if source == 'clear-selection':
        return None
    lookup = {
        'comeback-chart': (comeback_click, 'player'),
        'competition-chart': (competition_click, 'discipline'),
        'rivalry-chart': (rivalry_click, 'rivalry'),
    }
    if source not in lookup:
        raise PreventUpdate
    point, kind = lookup[source]
    if not point or not point.get('points'):
        raise PreventUpdate
    first = point['points'][0]
    if kind == 'player':
        return {'type': kind, 'value': str(first['customdata'][0])}
    if kind == 'discipline':
        return {'type': kind, 'value': str(first['customdata'][0])}
    return {'type': kind, 'value': str(first['customdata'][0])}


@app.callback(
    Output('comeback-chart', 'figure'),
    Output('competition-chart', 'figure'),
    Output('rivalry-chart', 'figure'),
    Output('filter-status', 'children'),
    Input('year-filter', 'value'),
    Input('discipline-filter', 'value'),
    Input('tier-filter', 'value'),
    Input('active-selection', 'data'),
)
def update_views(years, disciplines, tiers, selection):
    """All three figures depend on the same filtered real match rows."""
    d = select_matches(DATA, years or YEARS, disciplines or [], tiers or [], selection)
    if selection:
        label = f"Selected {selection['type']}: {selection['value'].replace('::',' vs. ')}"
    else:
        label = 'All players and rivalries'
    status = f'{len(d):,} matches in current view · {label}'
    return comeback_fig(d, selection), competition_fig(d), rivalry_fig(d), status


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8050, debug=False)
