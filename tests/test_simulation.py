import unittest

from simulation import (
    SimulationConfig,
    simulate,
    make_daily_demands,
    TOTAL_SHIFT_HOURS,
    NOMINAL_DAILY_CAPACITY_PIECES,
    NOMINAL_WEEKLY_CAPACITY_PIECES,
    CONFIRMED_WEEKLY_DEMAND_PIECES,
    WEEKLY_CAPACITY_VS_DEMAND_GAP_PIECES,
    IMPLIED_RATE_FROM_CYCLE_PIECES_PER_HOUR,
)


class SimulationTests(unittest.TestCase):
    def test_no_demand_does_not_start_machine_when_full(self):
        cfg = SimulationConfig(days=2, average_daily_demand=0, initial_stock_slots=19)
        daily, _ = simulate(cfg, [0, 0])
        self.assertEqual(sum(row["acionamentos_maquina"] for row in daily), 0)
        self.assertEqual(sum(row["producao_pecas"] for row in daily), 0)
        self.assertEqual(daily[-1]["estoque_final_rollers"], 19)

    def test_demand_is_rounded_up_to_whole_roller(self):
        cfg = SimulationConfig(days=1, average_daily_demand=145, operating_hours_per_day=1,
                               production_rate_pieces_per_hour=0)
        daily, _ = simulate(cfg, [145])
        self.assertEqual(daily[0]["cartoes_solicitados"], 2)
        self.assertEqual(daily[0]["cartoes_retirados"], 2)
        self.assertEqual(daily[0]["pecas_retiradas_do_estoque"], 288)
        self.assertEqual(daily[0]["excesso_por_arredondamento_pecas"], 143)

    def test_machine_replenishes_without_exceeding_capacity(self):
        cfg = SimulationConfig(days=1, average_daily_demand=12 * 144,
                               operating_hours_per_day=24, production_rate_pieces_per_hour=75)
        daily, timeline = simulate(cfg, [12 * 144])
        self.assertGreaterEqual(daily[0]["acionamentos_maquina"], 1)
        self.assertLessEqual(max(row["estoque_rollers"] for row in timeline), cfg.capacity_slots + 1e-9)
        self.assertLessEqual(daily[0]["estoque_final_rollers"], cfg.capacity_slots)

    def test_production_replenishes_same_day_without_reaching_yellow_red(self):
        # Consumo de 4 rollers (500 peças) deixa o estoque em 16, ainda na zona verde (gatilho em 8).
        # A reposição deve ocorrer no mesmo dia mesmo sem cruzar a faixa amarela/vermelha; a capacidade
        # diária é suficiente para repor quase tudo (o último cartão consumido perto do fim do dia pode
        # não dar tempo de ser totalmente reposto, terminando bem perto do topo, ainda na zona verde).
        cfg = SimulationConfig(days=1, initial_stock_slots=19, average_daily_demand=500)
        daily, _ = simulate(cfg, [500])
        row = daily[0]
        self.assertEqual(row["cartoes_retirados"], 4)
        self.assertGreaterEqual(row["acionamentos_maquina"], 1)
        self.assertGreaterEqual(row["rollers_produzidos"], 3)
        self.assertGreaterEqual(row["estoque_final_rollers"], cfg.trigger_slots)  # permanece na zona verde

    def test_shortage_is_recorded_when_demand_exceeds_inventory(self):
        cfg = SimulationConfig(days=1, initial_stock_slots=1, average_daily_demand=500,
                               operating_hours_per_day=1, production_rate_pieces_per_hour=0)
        daily, _ = simulate(cfg, [500])
        self.assertEqual(daily[0]["cartoes_solicitados"], 4)
        self.assertEqual(daily[0]["cartoes_retirados"], 1)
        self.assertGreater(daily[0]["falta_pecas"], 0)

    def test_random_scenario_is_reproducible(self):
        cfg = SimulationConfig(days=5, seed=19)
        first, _ = simulate(cfg)
        second, _ = simulate(cfg)
        self.assertEqual([r["demanda_pecas"] for r in first], [r["demanda_pecas"] for r in second])

    def test_inventory_balance_for_each_day(self):
        cfg = SimulationConfig(days=4, operating_hours_per_day=24)
        daily, _ = simulate(cfg)
        for row in daily:
            expected = (
                row["estoque_inicial_rollers"] * cfg.pieces_per_roller
                - row["pecas_retiradas_do_estoque"]
                + row["producao_pecas"]
            )
            self.assertAlmostEqual(row["estoque_final_pecas"], expected, delta=1e-9)

    def test_weekly_demand_total_preserves_confirmed_average(self):
        cfg = SimulationConfig(days=6, average_daily_demand=1845, demand_variability=0.15, seed=7)
        demands = make_daily_demands(cfg)
        self.assertEqual(len(demands), 6)
        self.assertEqual(sum(demands), round(1845 * 6))  # 11.070 (1 peça de diferença dos 11.069 por arredondamento)

    def test_wip_in_progress_is_not_counted_as_available_stock(self):
        cfg = SimulationConfig(days=1, initial_stock_slots=0, average_daily_demand=100,
                               operating_hours_per_day=1, production_rate_pieces_per_hour=50)
        daily, _ = simulate(cfg, [100])
        row = daily[0]
        self.assertEqual(row["cartoes_retirados"], 0)
        self.assertEqual(row["falta_pecas"], 100)
        self.assertEqual(row["rollers_produzidos"], 0)
        self.assertEqual(row["estoque_final_rollers"], 0)
        self.assertGreater(row["progresso_proximo_roller_pecas"], 0)  # WIP acumulado, mas indisponível para consumo

    def test_confirmed_capacity_constants_match_process_data(self):
        self.assertAlmostEqual(TOTAL_SHIFT_HOURS, 20.17, places=2)
        self.assertAlmostEqual(NOMINAL_DAILY_CAPACITY_PIECES, 1512.75, places=2)
        self.assertAlmostEqual(NOMINAL_WEEKLY_CAPACITY_PIECES, 9076.5, places=1)
        self.assertAlmostEqual(
            WEEKLY_CAPACITY_VS_DEMAND_GAP_PIECES,
            CONFIRMED_WEEKLY_DEMAND_PIECES - NOMINAL_WEEKLY_CAPACITY_PIECES,
            places=1,
        )
        self.assertAlmostEqual(WEEKLY_CAPACITY_VS_DEMAND_GAP_PIECES, 1992.5, places=1)
        self.assertAlmostEqual(IMPLIED_RATE_FROM_CYCLE_PIECES_PER_HOUR, 72.1, delta=0.1)


if __name__ == "__main__":
    unittest.main()
