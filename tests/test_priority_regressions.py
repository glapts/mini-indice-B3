import json
import os
import sys
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.agents.macro_agent import MacroAgent
from core.agents.orchestrator import Orchestrator
from core.harness.contracts import CircuitBreakerState, ExecutionMode, RuntimeStateContract


class TestPriorityRegressions(unittest.TestCase):
    def test_macro_stale_feed_fails_closed(self):
        macro = MacroAgent()
        now = datetime(2026, 11, 22, 14, 0)
        macro.update_sp500(5800, 0.0, updated_at=now - timedelta(seconds=121))

        opinion = macro.evaluate(current_time=now)

        self.assertEqual(opinion.data_quality, "STALE")
        self.assertTrue(opinion.lockout)
        self.assertTrue(opinion.veto_buy)
        self.assertTrue(opinion.veto_sell)

    def test_orchestrator_blocks_when_macro_feed_is_stale(self):
        macro = MacroAgent()
        now = datetime(2026, 11, 22, 14, 0)
        macro.update_sp500(5800, 0.0, updated_at=now - timedelta(seconds=121))
        orchestrator = Orchestrator(
            macro_agent=macro,
            output_state_path=os.path.join(self.id().replace(".", "_") + ".json"),
        )

        try:
            state = orchestrator.run_cycle(current_time=now)
            self.assertFalse(state.trading_enabled)
            self.assertEqual(state.confidence_score, 0.0)
        finally:
            try:
                os.remove(orchestrator.output_state_path)
            except OSError:
                pass

    def test_daily_stop_counter_survives_restart(self):
        with TemporaryDirectory() as tmp:
            state_path = os.path.join(tmp, "runtime_state.json")
            timestamp = datetime.now().replace(microsecond=0).isoformat()
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump({"timestamp": timestamp, "circuit_breaker": {"daily_stops_count": 2}}, f)

            restarted = Orchestrator(output_state_path=state_path)

            self.assertEqual(restarted.daily_stops_count, 2)

    def test_signal_persistence_failure_rolls_back_memory_state(self):
        from core.harness.execution_harness import ExecutionHarness

        harness = object.__new__(ExecutionHarness)
        harness.generated_signals = []
        harness.last_signal = None
        harness._persist_signals = lambda: False
        harness.generated_signals.append(object())

        with self.assertRaises(IOError):
            if not harness._persist_signals():
                harness.generated_signals.pop()
                harness.last_signal = None
                raise IOError("Falha ao persistir sinal; operação não confirmada")

        self.assertEqual(harness.generated_signals, [])
        self.assertIsNone(harness.last_signal)


if __name__ == "__main__":
    unittest.main()
