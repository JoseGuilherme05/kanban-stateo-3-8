"""Motor da simulação Kanban Stateo 3/8.

A lógica prioriza a especificação funcional Pasted_content.txt, ajustada pela
clarificação do responsável pelo processo sobre o funcionamento diário real:
- cartões/rollers indivisíveis para representar consumo;
- demanda diária convertida em cartões por arredondamento para cima;
- a cada dia, após o consumo, a máquina repõe o que a capacidade diária permitir,
  sem esperar o estoque atingir a faixa amarela/vermelha (ver dados_confirmados.md);
- produção de um roller por vez até o supermercado ficar cheio.

Este é um modelo demonstrativo. As hipóteses configuráveis estão descritas no README
e em dados_confirmados.md.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Optional, Sequence

# Dados de processo confirmados (ver dados_confirmados.md).
SHIFT_HOURS = {"Turno 1": 7.42, "Turno 2": 7.42, "Turno 3": 5.33}
TOTAL_SHIFT_HOURS = round(sum(SHIFT_HOURS.values()), 2)  # 20,17 h/dia
CONFIRMED_EFFECTIVE_RATE_PIECES_PER_HOUR = 75.0  # já considera o rendimento de 76%; não multiplicar de novo
PRODUCTIVE_DAYS_PER_WEEK = 6
CONFIRMED_DAILY_DEMAND_PIECES = 1845.0
CONFIRMED_WEEKLY_DEMAND_PIECES = 11069.0
NOMINAL_DAILY_CAPACITY_PIECES = round(CONFIRMED_EFFECTIVE_RATE_PIECES_PER_HOUR * TOTAL_SHIFT_HOURS, 2)  # 1.512,75
NOMINAL_WEEKLY_CAPACITY_PIECES = round(NOMINAL_DAILY_CAPACITY_PIECES * PRODUCTIVE_DAYS_PER_WEEK, 2)  # 9.076,5
# Diferença teórica entre a demanda semanal informada e a capacidade nominal calculada;
# é um alerta para validação, não um déficit operacional confirmado.
WEEKLY_CAPACITY_VS_DEMAND_GAP_PIECES = round(CONFIRMED_WEEKLY_DEMAND_PIECES - NOMINAL_WEEKLY_CAPACITY_PIECES, 2)
CYCLE_TIME_SECONDS = 37.97
YIELD_RATE = 0.76  # valor padrão; ajustável no simulador como "eficiência da máquina"
# Taxa implícita pelo ciclo informado, divergente dos 75 peças/h reportados; registrada para confirmação.
IMPLIED_RATE_FROM_CYCLE_PIECES_PER_HOUR = round((3600 / CYCLE_TIME_SECONDS) * YIELD_RATE, 1)  # ~72,1
# Taxa a 100% de rendimento, calibrada para que 76% de eficiência resulte nas 75 peças/h informadas.
BASE_MACHINE_RATE_AT_FULL_EFFICIENCY_PIECES_PER_HOUR = round(CONFIRMED_EFFECTIVE_RATE_PIECES_PER_HOUR / YIELD_RATE, 2)  # ~98,68


def production_rate_from_efficiency(efficiency: float) -> float:
    """Escala a taxa de produção (peças/h) proporcionalmente à eficiência (fração 0-1)."""
    return round(BASE_MACHINE_RATE_AT_FULL_EFFICIENCY_PIECES_PER_HOUR * efficiency, 2)


@dataclass(frozen=True)
class SimulationConfig:
    days: int = 7
    green_slots: int = 12
    yellow_slots: int = 1
    red_slots: int = 7
    pieces_per_roller: int = 144
    initial_stock_slots: int = 20
    average_daily_demand: float = 1845.0
    demand_variability: float = 0.15  # coeficiente de variação usado no cenário ilustrativo
    production_rate_pieces_per_hour: float = 75.0
    operating_hours_per_day: float = TOTAL_SHIFT_HOURS  # soma dos 3 turnos informados (7,42+7,42+5,33 h)
    machine_efficiency: float = YIELD_RATE  # rendimento da máquina (0-1); hoje é só informativo, não altera production_rate_pieces_per_hour
    steps_per_hour: int = 12  # resolução interna de 5 minutos
    seed: int = 42

    @property
    def implied_rate_from_cycle_pieces_per_hour(self) -> float:
        return round((3600 / CYCLE_TIME_SECONDS) * self.machine_efficiency, 1)

    @property
    def capacity_slots(self) -> int:
        return self.green_slots + self.yellow_slots + self.red_slots

    @property
    def capacity_pieces(self) -> int:
        return self.capacity_slots * self.pieces_per_roller

    @property
    def trigger_slots(self) -> int:
        # Limite da faixa amarela+vermelha: usado como classificação visual de alerta,
        # não como gatilho exclusivo de produção (a máquina repõe a cada dia com consumo).
        return self.yellow_slots + self.red_slots

    @property
    def trigger_pieces(self) -> int:
        return self.trigger_slots * self.pieces_per_roller


def _distribute_preserving_total(raw_values: Sequence[float], target_total: float) -> list[float]:
    """Reescala valores aleatórios para que a soma bata com o total-alvo (arredondado).

    Mantém o formato da variação gerada (dias acima/abaixo da média) enquanto ancora
    o total do período na média informada, usando o método dos maiores restos para
    distribuir a diferença de arredondamento entre os dias.
    """
    total = sum(raw_values)
    rounded_target = round(target_total)
    if total <= 0 or rounded_target <= 0:
        return [0.0] * len(raw_values)
    scale = target_total / total
    scaled = [v * scale for v in raw_values]
    floored = [math.floor(v) for v in scaled]
    remainder = rounded_target - int(sum(floored))
    order = sorted(range(len(scaled)), key=lambda i: scaled[i] - floored[i], reverse=True)
    result = list(floored)
    for i in range(max(0, remainder)):
        result[order[i % len(order)]] += 1
    return [float(v) for v in result]


def make_daily_demands(config: SimulationConfig,
                       manual_demands: Optional[Sequence[float]] = None) -> list[float]:
    """Gera demanda reprodutível ou usa os valores manuais fornecidos.

    A demanda sintética serve apenas para exercitar o simulador; não representa
    dados reais da fábrica. A variação diária é demonstrativa, mas o total do
    período é ancorado na média informada (ex.: uma semana de 6 dias preserva a
    demanda semanal de 11.069 peças). Valores manuais informados substituem os
    primeiros dias e podem alterar o total.
    """
    rng = random.Random(config.seed)
    raw = [
        max(0.0, rng.gauss(
            config.average_daily_demand,
            config.average_daily_demand * config.demand_variability,
        ))
        for _ in range(config.days)
    ]
    generated = _distribute_preserving_total(raw, config.average_daily_demand * config.days)
    if manual_demands:
        for i, value in enumerate(manual_demands[:config.days]):
            generated[i] = max(0.0, float(value))
    return generated


def simulate(config: SimulationConfig,
             manual_demands: Optional[Sequence[float]] = None) -> tuple[list[dict], list[dict]]:
    """Executa uma simulação e devolve (resumo_diário, série_temporal).

    A demanda de cada dia é distribuída uniformemente pelas horas configuradas.
    Quando uma demanda pede um roller, um cartão/roller inteiro é retirado (144
    peças por padrão), conforme a regra de arredondamento para cima do documento.
    Assim que há espaço (estoque abaixo da capacidade cheia), a máquina liga e
    produz à taxa efetiva configurada, liberando um novo roller a cada 144 peças
    produzidas, até preencher o trilho ou esgotar a capacidade de produção do dia.
    """
    if config.days < 1:
        raise ValueError("A duração precisa ser de pelo menos 1 dia.")
    if min(config.green_slots, config.yellow_slots, config.red_slots) < 0:
        raise ValueError("As quantidades de posições por zona não podem ser negativas.")
    if config.capacity_slots < 1:
        raise ValueError("A capacidade do Kanban precisa ser de pelo menos 1 posição.")
    if config.pieces_per_roller <= 0:
        raise ValueError("A quantidade de peças por roller precisa ser positiva.")
    if not 0 <= config.initial_stock_slots <= config.capacity_slots:
        raise ValueError("O estoque inicial precisa estar entre zero e a capacidade.")
    if config.operating_hours_per_day <= 0:
        raise ValueError("As horas de operação por dia precisam ser positivas.")
    if config.production_rate_pieces_per_hour < 0:
        raise ValueError("A taxa de produção não pode ser negativa.")
    if config.steps_per_hour < 1:
        raise ValueError("A resolução da simulação precisa ser pelo menos 1 passo por hora.")

    demands = make_daily_demands(config, manual_demands)
    stock_slots = config.initial_stock_slots
    production_progress = 0.0  # peças do próximo roller ainda em produção
    machine_on = False
    dt = 1.0 / config.steps_per_hour
    step_count = max(1, int(round(config.operating_hours_per_day * config.steps_per_hour)))
    daily_rows: list[dict] = []
    timeline: list[dict] = []
    elapsed_hours = 0.0

    for day_index, daily_demand in enumerate(demands, start=1):
        opening_slots = stock_slots
        opening_progress = production_progress
        requested_cards = math.ceil(daily_demand / config.pieces_per_roller) if daily_demand > 0 else 0
        cards_removed = 0
        requested_pieces = 0.0
        pieces_withdrawn = 0.0
        rounding_extra = 0.0
        unmet_pieces = 0.0
        produced_cards = 0
        machine_starts = 0
        machine_hours = 0.0

        for step in range(step_count):
            # Distribui os cartões de demanda de forma uniforme ao longo do dia.
            cards_due_total = math.floor((step + 1) * requested_cards / step_count)
            cards_due_before = math.floor(step * requested_cards / step_count)
            cards_due = cards_due_total - cards_due_before

            for card_number in range(cards_due):
                demand_piece_index = (cards_due_before + card_number) * config.pieces_per_roller
                pieces_for_this_card = min(
                    float(config.pieces_per_roller),
                    max(0.0, daily_demand - demand_piece_index),
                )
                requested_pieces += pieces_for_this_card
                if stock_slots > 0:
                    stock_slots -= 1
                    cards_removed += 1
                    pieces_withdrawn += config.pieces_per_roller
                    rounding_extra += config.pieces_per_roller - pieces_for_this_card
                else:
                    unmet_pieces += pieces_for_this_card

            # Sinal de produção: qualquer consumo que abra espaço aciona a reposição no mesmo
            # dia (não é preciso esperar a faixa amarela/vermelha); a máquina repõe o que a
            # capacidade diária permitir, podendo terminar o dia no verde, no limiar ou no
            # amarelo/vermelho, dependendo do saldo entre demanda e produção.
            if not machine_on and stock_slots < config.capacity_slots:
                machine_on = True
                machine_starts += 1

            # Produção durante o passo, liberando rollers completos de 144 peças.
            if machine_on and stock_slots < config.capacity_slots and config.production_rate_pieces_per_hour > 0:
                capacity_to_fill = (
                    (config.capacity_slots - stock_slots) * config.pieces_per_roller
                    - production_progress
                )
                available_output = config.production_rate_pieces_per_hour * dt
                actual_output = min(available_output, max(0.0, capacity_to_fill))
                production_progress += actual_output
                machine_hours += actual_output / config.production_rate_pieces_per_hour
                while (production_progress + 1e-9 >= config.pieces_per_roller
                       and stock_slots < config.capacity_slots):
                    production_progress -= config.pieces_per_roller
                    stock_slots += 1
                    produced_cards += 1
                if stock_slots >= config.capacity_slots:
                    # Não há autorização/espaço para produzir além da capacidade física.
                    stock_slots = config.capacity_slots
                    production_progress = 0.0
                    machine_on = False

            elapsed_hours += dt
            timeline.append({
                "dia": day_index,
                "hora_no_dia": (step + 1) * dt,
                "hora_total": elapsed_hours,
                "estoque_rollers": stock_slots + production_progress / config.pieces_per_roller,
                "estoque_pecas": stock_slots * config.pieces_per_roller + production_progress,
                "maquina_ligada": machine_on,
                "progresso_proximo_roller": production_progress,
            })

        daily_rows.append({
            "dia": day_index,
            "estoque_inicial_rollers": opening_slots,
            "demanda_pecas": round(daily_demand, 1),
            "cartoes_solicitados": requested_cards,
            "cartoes_retirados": cards_removed,
            "pecas_retiradas_do_estoque": round(pieces_withdrawn, 1),
            "excesso_por_arredondamento_pecas": round(rounding_extra, 1),
            "falta_pecas": round(unmet_pieces, 1),
            "rollers_produzidos": produced_cards,
            "producao_pecas": produced_cards * config.pieces_per_roller,
            "estoque_final_rollers": stock_slots,
            "estoque_final_pecas": stock_slots * config.pieces_per_roller,
            "progresso_proximo_roller_pecas": round(production_progress, 1),
            "horas_maquina_ligada": round(machine_hours, 2),
            "acionamentos_maquina": machine_starts,
            "maquina_ao_final": "Produzindo" if machine_on else "Standby",
            "estoque_inicial_progresso_pecas": round(opening_progress, 1),
        })

    return daily_rows, timeline
