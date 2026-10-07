from __future__ import annotations

import math
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from simulation import (
    SimulationConfig,
    simulate,
    SHIFT_HOURS,
    TOTAL_SHIFT_HOURS,
    CONFIRMED_EFFECTIVE_RATE_PIECES_PER_HOUR,
    PRODUCTIVE_DAYS_PER_WEEK,
    CONFIRMED_WEEKLY_DEMAND_PIECES,
    NOMINAL_DAILY_CAPACITY_PIECES,
    NOMINAL_WEEKLY_CAPACITY_PIECES,
    WEEKLY_CAPACITY_VS_DEMAND_GAP_PIECES,
    CYCLE_TIME_SECONDS,
    YIELD_RATE,
    IMPLIED_RATE_FROM_CYCLE_PIECES_PER_HOUR,
    production_rate_from_efficiency,
)

st.set_page_config(
    page_title="Simulador Kanban | Stateo 3/8",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)


def fmt_br(value: float, decimals: int = 0) -> str:
    """Formata número no padrão BR (milhar com ponto, decimal com vírgula)."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "§").replace(".", ",").replace("§", ".")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2.5rem; max-width: 1450px;}
.hero {padding: 1.2rem 1.5rem; border-radius: 16px; background: linear-gradient(120deg,#102b46,#1d5b77); color:white; margin-bottom:1rem;}
.hero h1 {margin:0 0 .35rem 0; font-size:2rem;}
.hero p {margin:0; color:#d8e9f2;}
.note {padding:.8rem 1rem; border-radius:10px; background:#fff8e6; border:1px solid #f4d58a; color:#604d1d;}
.rail {display:flex; flex-direction:column; gap:4px; width:min(100%,520px); margin:0 auto;}
.rail-slot {height:22px; position:relative; border-radius:5px; overflow:hidden; border:1px solid rgba(0,0,0,.15); background:#edf0f2;}
.rail-fill {height:100%; transition:width .25s ease; border-radius:4px;}
.rail-label {position:absolute; right:8px; top:1px; font-size:12px; font-weight:700; color:#143044;}
.small-caption {font-size:.85rem;color:#617381;text-align:center;margin-top:.45rem;}
section[data-testid="stSidebar"] {background:#132a3c;}
section[data-testid="stSidebar"] label p,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {color:#f1f5f9 !important;}
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {color:#cbd8e3 !important;}
.param-hint {font-size:.8rem; color:#9fb4c4; margin:.1rem 0 .2rem 0;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>Simulador de Kanban de Produção</h1>
  <p>Stateo 3/8 · consumo de rollers, sinal de reposição e produção ao longo dos dias</p>
</div>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="note"><b>Protótipo baseado principalmente no arquivo de especificação funcional enviado.</b> '
    'Os valores que ainda não foram confirmados estão identificados como premissas ajustáveis; '
    'os resultados são uma simulação, não dados medidos da fábrica.</div>',
    unsafe_allow_html=True,
)

with st.expander("Capacidade teórica vs. demanda informada (dados confirmados)", expanded=True):
    st.caption("Fonte: dados_confirmados.md — turnos, taxa efetiva e demanda semanal informados pela empresa.")
    shift_cols = st.columns(len(SHIFT_HOURS) + 1)
    for col, (name, hours) in zip(shift_cols, SHIFT_HOURS.items()):
        col.metric(name, f"{hours:.2f} h")
    shift_cols[-1].metric("Total por dia", f"{TOTAL_SHIFT_HOURS:.2f} h")

    cap_cols = st.columns(4)
    cap_cols[0].metric("Taxa efetiva (já c/ 76% rendimento)", f"{CONFIRMED_EFFECTIVE_RATE_PIECES_PER_HOUR:.0f} peças/h")
    cap_cols[1].metric("Capacidade nominal/dia", f"{fmt_br(NOMINAL_DAILY_CAPACITY_PIECES, 2)} peças")
    cap_cols[2].metric(f"Capacidade nominal/semana ({PRODUCTIVE_DAYS_PER_WEEK} dias produtivos)",
                       f"{fmt_br(NOMINAL_WEEKLY_CAPACITY_PIECES, 1)} peças")
    cap_cols[3].metric("Demanda média informada/semana", f"{fmt_br(CONFIRMED_WEEKLY_DEMAND_PIECES)} peças")

    st.warning(
        f"**Alerta teórico (não confirmado):** a capacidade nominal calculada fica "
        f"{fmt_br(WEEKLY_CAPACITY_VS_DEMAND_GAP_PIECES, 1)} peças/semana abaixo da demanda média informada. "
        "Esta é apenas uma comparação matemática entre os dados reportados; não representa um déficit "
        "operacional confirmado. Valide com o responsável pelo processo antes de usar como diagnóstico."
    )
    st.caption(
        f"Divergência a confirmar: um ciclo de {CYCLE_TIME_SECONDS:.2f} s com {YIELD_RATE*100:.0f}% de rendimento "
        f"implica cerca de {IMPLIED_RATE_FROM_CYCLE_PIECES_PER_HOUR:.1f} peças/h, diferente das "
        f"{CONFIRMED_EFFECTIVE_RATE_PIECES_PER_HOUR:.0f} peças/h informadas como taxa efetiva. O simulador usa 75 "
        "peças/h (dado reportado) e não aplica o rendimento de 76% uma segunda vez."
    )
    st.caption(
        "Quantidade de operadores por operação/turno ainda não foi informada; o protótipo não limita a produção "
        "por esse fator e nenhum número foi presumido."
    )

with st.sidebar:
    st.header("Parâmetros do cenário")
    st.caption("Altere os campos e clique em **Simular cenário**.")
    with st.form("scenario"):
        st.markdown('<p class="param-hint">Horizonte de dias que a simulação vai cobrir; mais dias revelam tendências de estoque e rupturas.</p>', unsafe_allow_html=True)
        days = st.number_input("Dias a simular", min_value=1, max_value=30, value=7, step=1)

        st.markdown('<p class="param-hint">Posições do trilho com estoque saudável, sem necessidade de reposição imediata.</p>', unsafe_allow_html=True)
        green = st.number_input("Posições verdes", min_value=0, max_value=50, value=13, step=1)

        st.markdown('<p class="param-hint">Posições de alerta: sinalizam que o estoque está se aproximando do nível crítico.</p>', unsafe_allow_html=True)
        yellow = st.number_input("Posições amarelas", min_value=0, max_value=20, value=1, step=1)

        st.markdown('<p class="param-hint">Posições de risco: estoque baixo indicando situação crítica, mas a reposição já ocorre todo dia em que há consumo.</p>', unsafe_allow_html=True)
        red = st.number_input("Posições vermelhas", min_value=0, max_value=50, value=5, step=1)

        st.markdown('<p class="param-hint">Quantidade de peças que cabem em um roller; usado para converter peças em rollers no cálculo do kanban.</p>', unsafe_allow_html=True)
        pieces_per_roller = st.number_input("Peças por roller", min_value=1, max_value=10000, value=144, step=1)

        capacity_slots = int(green + yellow + red)
        if capacity_slots < 1:
            st.error("Defina pelo menos uma posição no trilho.")

        st.markdown('<p class="param-hint">Quantidade de rollers já disponíveis no trilho no início da simulação.</p>', unsafe_allow_html=True)
        initial_stock = st.number_input(
            "Estoque inicial (rollers)", min_value=0, max_value=max(1, capacity_slots),
            value=min(20, capacity_slots), step=1,
        )
        mean_demand = st.number_input(
            "Demanda média diária (peças)", min_value=0, max_value=1000000,
            value=1845, step=100,
            help="1.845 peças/dia é a demanda informada (11.069 peças/semana ÷ 6 dias produtivos, com 1 peça de diferença por arredondamento).",
        )
        variability_pct = st.number_input(
            "Variação da demanda (%)", min_value=0, max_value=60, value=15, step=1,
            help="Gera dias acima/abaixo da média. É apenas uma oscilação demonstrativa.",
        )
        machine_efficiency_pct = st.number_input(
            "Eficiência da máquina (%)", min_value=0.0, max_value=100.0, value=YIELD_RATE * 100, step=0.5,
            help="76% é o rendimento informado, calibrado para resultar nas 75 peças/h reportadas. Ajuste para ver o efeito na produção efetiva abaixo.",
        )
        production_rate = production_rate_from_efficiency(machine_efficiency_pct / 100)
        st.markdown(
            f'<p class="param-hint">Produção efetiva da máquina (calculada): <b>{production_rate:.1f} peças/h</b> '
            f'(100% de rendimento = {production_rate_from_efficiency(1):.1f} peças/h; 76% = 75 peças/h).</p>',
            unsafe_allow_html=True,
        )
        operating_hours = st.number_input(
            "Horas de operação por dia", min_value=1.0, max_value=24.0, value=TOTAL_SHIFT_HOURS, step=0.01,
            help="20,17 h/dia é a soma dos 3 turnos informados (7,42 + 7,42 + 5,33 h). Ajuste se outra jornada se aplicar.",
        )
        manual_text = st.text_area(
            "Demandas reais por dia (opcional)", placeholder="Ex.: 1800, 2050, 1730",
            help="Se preencher, esses valores substituem os primeiros dias; dias restantes usam a demanda variável.",
        )
        run_button = st.form_submit_button("Simular cenário", type="primary", width="stretch")

    if capacity_slots != 19:
        st.warning(f"Com as zonas atuais, a capacidade física passa a {capacity_slots} rollers.")
    if green + yellow + red != 19 and capacity_slots == 19:
        st.info("As posições verdes/amarelas/vermelhas diferem da divisão indicada na especificação.")

if "scenario_values" not in st.session_state:
    st.session_state.scenario_values = {
        "days": 7, "green": 13, "yellow": 1, "red": 5,
        "pieces_per_roller": 144, "initial_stock": 19,
        "mean_demand": 1845, "variability_pct": 15,
        "production_rate": CONFIRMED_EFFECTIVE_RATE_PIECES_PER_HOUR, "operating_hours": TOTAL_SHIFT_HOURS, "seed": 42,
        "machine_efficiency_pct": YIELD_RATE * 100,
        "manual_text": "",
    }
if run_button:
    st.session_state.scenario_values = {
        "days": int(days), "green": int(green), "yellow": int(yellow), "red": int(red),
        "pieces_per_roller": int(pieces_per_roller), "initial_stock": int(initial_stock),
        "mean_demand": float(mean_demand), "variability_pct": int(variability_pct),
        "production_rate": float(production_rate), "operating_hours": float(operating_hours),
        "machine_efficiency_pct": float(machine_efficiency_pct),
        "seed": 42, "manual_text": manual_text,
    }

v = st.session_state.scenario_values
manual_demands = [float(x) for x in re.findall(r"\d+(?:[.,]\d+)?", v["manual_text"])
                  for x in [x.replace(",", ".")]] if v["manual_text"].strip() else None
config = SimulationConfig(
    days=v["days"], green_slots=v["green"], yellow_slots=v["yellow"], red_slots=v["red"],
    pieces_per_roller=v["pieces_per_roller"], initial_stock_slots=min(v["initial_stock"], v["green"] + v["yellow"] + v["red"]),
    average_daily_demand=v["mean_demand"], demand_variability=v["variability_pct"] / 100,
    production_rate_pieces_per_hour=v["production_rate"], operating_hours_per_day=v["operating_hours"],
    machine_efficiency=v["machine_efficiency_pct"] / 100,
    seed=v["seed"],
)

if config.capacity_slots < 1:
    st.error("A simulação precisa de pelo menos uma posição no trilho.")
    st.stop()
if config.initial_stock_slots != v["initial_stock"]:
    st.warning("O estoque inicial foi limitado à capacidade atual do trilho.")

try:
    daily_rows, timeline_rows = simulate(config, manual_demands)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

daily = pd.DataFrame(daily_rows)
timeline = pd.DataFrame(timeline_rows)
total_demand = float(daily["demanda_pecas"].sum())
total_shortage = float(daily["falta_pecas"].sum())
total_production = float(daily["producao_pecas"].sum())

st.subheader("Visão geral")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Capacidade do trilho", f"{config.capacity_slots} rollers", f"{config.capacity_pieces:,} peças".replace(",", "."))
col2.metric("Demanda no cenário", f"{total_demand:,.0f} peças".replace(",", "."), f"{config.days} dias")
col3.metric("Produção simulada", f"{total_production:,.0f} peças".replace(",", "."))
col4.metric("Demanda não atendida", f"{total_shortage:,.0f} peças".replace(",", "."), delta="ruptura" if total_shortage > 0 else "sem ruptura", delta_color="inverse")

selected_day = st.number_input("Inspecionar o dia", min_value=1, max_value=config.days, value=1, step=1, key="inspect_day")
row = daily.iloc[selected_day - 1]
left, right = st.columns([1, 1.1], gap="large")
with left:
    st.markdown(f"### Trilho Kanban — fim do dia {selected_day}")
    zone_colors = (["#2e9d63"] * config.green_slots
                   + ["#f2b632"] * config.yellow_slots
                   + ["#d94a4a"] * config.red_slots)
    filled_slots = float(row["estoque_final_rollers"])
    slots_html = []
    for i, color in enumerate(zone_colors):
        # O trilho é mostrado de cima para baixo; o nível de estoque cai primeiro na zona verde.
        fraction = max(0.0, min(1.0, filled_slots - (config.capacity_slots - i - 1)))
        width = fraction * 100
        slots_html.append(
            f'<div class="rail-slot"><div class="rail-fill" style="width:{width:.1f}%;background:{color};"></div>'
            f'<span class="rail-label">{i + 1:02d} · {"cheio" if fraction >= .999 else ("vazio" if fraction <= .001 else f"{fraction*100:.0f}%")}</span></div>'
        )
    st.markdown('<div class="rail">' + "".join(slots_html) + "</div>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="small-caption">Verde: {config.green_slots} · Amarelo: {config.yellow_slots} '
        f'· Vermelho: {config.red_slots} | Zona de alerta: ≤ {config.trigger_slots} rollers</div>',
        unsafe_allow_html=True,
    )
    state_color = "#d94a4a" if row["maquina_ao_final"] == "Produzindo" else "#2478a5"
    st.markdown(
        f'<div style="margin-top:1rem;padding:1rem;border-radius:12px;background:{state_color};color:white;'
        f'text-align:center;font-weight:700;font-size:1.1rem">Máquina: {row["maquina_ao_final"]}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"Demanda: {row['demanda_pecas']:,.0f} peças · cartões pedidos: {int(row['cartoes_solicitados'])} · "
        f"retirados: {int(row['cartoes_retirados'])} · produzidos: {int(row['rollers_produzidos'])} rollers"
        .replace(",", ".")
    )
with right:
    st.markdown(f"### Resumo do dia {selected_day}")
    m1, m2 = st.columns(2)
    m1.metric("Estoque inicial", f"{int(row['estoque_inicial_rollers'])} rollers")
    m2.metric("Estoque final", f"{int(row['estoque_final_rollers'])} rollers")
    m3, m4 = st.columns(2)
    m3.metric("Tempo produzindo", f"{row['horas_maquina_ligada']:.2f} h")
    m4.metric("Acionamentos", f"{int(row['acionamentos_maquina'])}")
    progress_fraction = min(1.0, row["progresso_proximo_roller_pecas"] / config.pieces_per_roller)
    st.progress(progress_fraction, text=(
        f"Próximo roller: {row['progresso_proximo_roller_pecas']:.1f} / "
        f"{config.pieces_per_roller} peças"
    ))
    if row["falta_pecas"] > 0:
        st.error(f"Ruptura estimada neste dia: {row['falta_pecas']:,.0f} peças não atendidas.".replace(",", "."))
    if row["excesso_por_arredondamento_pecas"] > 0:
        st.info(
            f"Pelo arredondamento para roller inteiro, foram retiradas "
            f"{row['excesso_por_arredondamento_pecas']:,.0f} peças equivalentes além da demanda exata."
            .replace(",", ".")
        )

st.subheader("Comportamento do estoque")
st.caption(
    "A cada dia, o consumo esvazia o trilho e a máquina repõe o que a capacidade diária permitir — "
    "sem esperar o estoque cair na faixa amarela/vermelha. Por isso o nível sobe e desce dia a dia, "
    "podendo terminar no verde, no limiar ou na faixa amarela/vermelha, conforme o saldo entre demanda e produção."
)
fig = go.Figure()
fig.add_hrect(y0=0, y1=config.red_slots, fillcolor="rgba(217,74,74,.10)", line_width=0, layer="below")
fig.add_hrect(y0=config.red_slots, y1=config.trigger_slots, fillcolor="rgba(242,182,50,.16)", line_width=0, layer="below")
fig.add_hrect(y0=config.trigger_slots, y1=config.capacity_slots, fillcolor="rgba(46,157,99,.08)", line_width=0, layer="below")
fig.add_trace(go.Scatter(
    x=timeline["hora_total"], y=timeline["estoque_rollers"], mode="lines",
    name="Estoque disponível", line=dict(color="#155e83", width=3),
    hovertemplate="Hora %{x:.1f}<br>Estoque %{y:.2f} rollers<extra></extra>",
))
fig.add_hline(y=config.trigger_slots, line_dash="dash", line_color="#ce9412",
              annotation_text="Limite da zona amarela/vermelha", annotation_position="top left")
fig.update_layout(
    height=390, margin=dict(l=10, r=10, t=30, b=10),
    xaxis_title="Horas acumuladas de simulação", yaxis_title="Estoque (rollers)",
    yaxis=dict(range=[0, config.capacity_slots + 1], dtick=max(1, math.ceil(config.capacity_slots / 10))),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    hovermode="x unified",
)
st.plotly_chart(fig, width="stretch")

st.subheader("Demanda e reposição por dia")
st.caption(
    "A demanda diária exibida é **simulada** (gerada aleatoriamente a partir da média e variação configuradas, "
    "ou substituída pelos valores manuais informados) — não é uma série histórica real de produção."
)
bar = go.Figure()
bar.add_trace(go.Bar(x=daily["dia"], y=daily["demanda_pecas"], name="Demanda informada/simulada", marker_color="#8096a8"))
bar.add_trace(go.Bar(x=daily["dia"], y=daily["producao_pecas"], name="Produção concluída", marker_color="#2e9d63"))
bar.update_layout(barmode="group", height=340, margin=dict(l=10, r=10, t=20, b=10),
                  xaxis_title="Dia", yaxis_title="Peças", legend=dict(orientation="h", y=1.08, x=0))
st.plotly_chart(bar, width="stretch")

with st.expander("Tabela detalhada da simulação"):
    display_cols = [
        "dia", "estoque_inicial_rollers", "demanda_pecas", "cartoes_solicitados",
        "cartoes_retirados", "pecas_retiradas_do_estoque", "excesso_por_arredondamento_pecas",
        "falta_pecas", "rollers_produzidos", "producao_pecas", "estoque_final_rollers",
        "progresso_proximo_roller_pecas", "horas_maquina_ligada", "acionamentos_maquina", "maquina_ao_final",
    ]
    st.dataframe(daily[display_cols], width="stretch", hide_index=True)
    st.download_button(
        "Baixar resumo em CSV", data=daily.to_csv(index=False).encode("utf-8-sig"),
        file_name="resumo_simulacao_kanban.csv", mime="text/csv",
    )

with st.expander("Regras e premissas desta versão"):
    st.markdown(f"""
- **Fonte principal das regras:** `Pasted_content.txt` — demanda diária variável, 20 posições por padrão, 144 peças por roller, consumo convertido em cartões arredondando para cima.
- **Reposição diária (clarificação do responsável pelo processo):** a cada dia, após o consumo, a máquina repõe o que a capacidade diária de produção permitir — não é preciso o estoque cair na faixa amarela/vermelha para a produção começar. O trilho pode terminar o dia no verde, no limiar ou na faixa amarela/vermelha, dependendo do saldo entre demanda e produção daquele dia.
- **Interpretação configurada:** as 20 posições são a capacidade total (12 verdes + 1 amarela + 7 vermelhas). Assim, “12 verdes” é tratado como tamanho da zona verde, não como o estoque total inicial. O estoque inicial começa cheio por padrão.
- **Demanda:** {fmt_br(v['mean_demand'])} peças/dia é o valor informado (11.069 peças/semana ÷ 6 dias produtivos). A série diária exibida no gráfico é **gerada por simulação** (variação demonstrativa reproduzível pela semente), não é um histórico real de produção; o total de uma semana de 6 dias é ancorado na demanda semanal informada.
- **Produção:** {fmt_br(v['production_rate'], 1)} peças/h é a taxa efetiva calculada a partir da eficiência configurada (não é um valor independente). A produção libera um roller quando acumula {v['pieces_per_roller']} peças.
- **Eficiência da máquina:** {fmt_br(v['machine_efficiency_pct'], 1)}% é o rendimento configurado no cenário; a taxa efetiva escala proporcionalmente a partir dele (100% de rendimento = {fmt_br(production_rate_from_efficiency(1), 1)} peças/h, calibrado para que 76% resulte nas 75 peças/h informadas). Com {fmt_br(CYCLE_TIME_SECONDS, 2)} s/ciclo, o rendimento também implica cerca de {fmt_br(config.implied_rate_from_cycle_pieces_per_hour, 1)} peças/h pela via do tempo de ciclo — valor teórico divergente, mantido apenas para comparação.
- **Janela de operação:** {fmt_br(v['operating_hours'], 2)} h/dia é a soma dos 3 turnos informados (7,42 + 7,42 + 5,33 h). É editável; neste protótipo, consumo e produção acontecem durante a mesma janela e a demanda é distribuída uniformemente nela.
- **Capacidade vs. demanda:** a capacidade nominal calculada (75 × {fmt_br(v['operating_hours'], 2)} h × 6 dias = {fmt_br(NOMINAL_WEEKLY_CAPACITY_PIECES, 1)} peças/semana) fica {fmt_br(WEEKLY_CAPACITY_VS_DEMAND_GAP_PIECES, 1)} peças/semana abaixo da demanda informada ({fmt_br(CONFIRMED_WEEKLY_DEMAND_PIECES)} peças/semana). Trata-se de um alerta teórico para validação, não um déficit operacional confirmado.
- **Zona amarela/vermelha:** com {config.trigger_slots} rollers ou menos, o trilho fica na faixa de alerta/crítica — é uma classificação visual de risco, não o gatilho exclusivo da produção.
- **Arredondamento:** cada demanda que requer parte de um roller retira um roller inteiro, conforme a especificação. O excedente é apresentado na tabela.
- **Operadores:** a quantidade de operadores por operação/turno ainda não foi informada; a produção não é limitada por esse fator neste protótipo.
- **Fora do escopo atual:** falhas, manutenção, setups, transporte entre máquinas, regra de 48 horas e interação de várias referências. Podem ser incluídos quando os dados forem conhecidos.
""")

st.caption("Protótipo acadêmico/industrial em evolução · valide as premissas com o responsável pelo processo antes de apresentar resultados como dados reais.")
