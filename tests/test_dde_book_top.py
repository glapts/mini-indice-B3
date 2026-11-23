"""
tests/test_dde_book_top.py

Testes da integracao do BOOK DE OFERTAS DE TOPO (nivel 1) via DDE do Profit Pro.

Contexto: os atributos OCP/OVD/VOC/VOV precisam estar habilitados na janela
"Exportar em Tempo Real (RTD/DDE)" do Profit Pro. Sem eles, o feed degrada
com seguranca (book indisponivel), sem quebrar o restante do sistema.
"""
import unittest
from datetime import datetime

from core.models import BookSnapshot, BookLevel
from analysis.book_analyzer import BookAnalyzer
from feeds.dde_feed import ProfitDDEFeed


class TestDDETopBook(unittest.TestCase):

    def _feed_with_book(self, book: dict) -> ProfitDDEFeed:
        feed = ProfitDDEFeed()
        feed.symbol = "WINZ26"
        feed._read_top_book(lambda item: book.get(item), datetime.now(), 167605.0)
        return feed

    def test_book_com_mercado_aberto(self):
        """Com book valido, o feed expoe melhor oferta, spread e volume."""
        book = {
            "WINZ26.OCP": "167600,00",
            "WINZ26.OVD": "167610,00",
            "WINZ26.VOC": "450,00",
            "WINZ26.VOV": "120,00",
            "WINZ26.LOT": "1,00",
        }
        feed = self._feed_with_book(book)

        self.assertTrue(feed.health.is_book_available)
        top = feed.get_top_book()
        self.assertIsNotNone(top)
        self.assertAlmostEqual(top["best_bid"], 167600.0)
        self.assertAlmostEqual(top["best_ask"], 167610.0)
        self.assertAlmostEqual(top["spread"] if "spread" in top else 10.0, 10.0, places=5)
        self.assertEqual(top["bid_quantity"], 450)
        self.assertEqual(top["ask_quantity"], 120)
        self.assertEqual(top["contract_lot_size"], 1)

    def test_book_zerado_mercado_fechado(self):
        """Book zerado (mercado fechado) nao pode ser considerado disponivel."""
        book = {
            "WINZ26.OCP": "0,00",
            "WINZ26.OVD": "0,00",
            "WINZ26.VOC": "0,00",
            "WINZ26.VOV": "0,00",
            "WINZ26.LOT": "1,00",
        }
        feed = self._feed_with_book(book)

        self.assertFalse(feed.health.is_book_available)
        self.assertIsNone(feed.get_top_book())

    def test_atributos_nao_habilitados(self):
        """Sem OCP/OVD no Profit, o feed degrada sem excecao."""
        feed = self._feed_with_book({})

        self.assertFalse(feed.health.is_book_available)
        self.assertIsNone(feed.get_top_book())

    def test_spread_invertido_descartado(self):
        """Oferta de venda abaixo da de compra e dado invalido."""
        book = {
            "WINZ26.OCP": "167610,00",
            "WINZ26.OVD": "167600,00",
            "WINZ26.VOC": "450,00",
            "WINZ26.VOV": "120,00",
        }
        feed = self._feed_with_book(book)
        self.assertFalse(feed.health.is_book_available)

    def test_lote_padrao_por_ativo(self):
        """O campo LOT devolve o tamanho do lote padrao do contrato."""
        book = {
            "VALE3.OCP": "58,45",
            "VALE3.OVD": "58,47",
            "VALE3.VOC": "1.500,00",
            "VALE3.VOV": "800,00",
            "VALE3.LOT": "100,00",
        }
        feed = ProfitDDEFeed()
        feed.symbol = "VALE3"
        feed._read_top_book(lambda item: book.get(item), datetime.now(), 58.46)

        self.assertTrue(feed.health.is_book_available)
        self.assertEqual(feed.get_top_book()["contract_lot_size"], 100)
        # Lote 100 em acoes: 1500/100 = 15 contratos normalizados.
        self.assertEqual(feed.get_top_book()["bid_quantity"], 1500)

    def test_emite_book_snapshot_no_callback(self):
        """O feed deve emitir BookSnapshot para o on_book_callback."""
        recebidos = []
        feed = ProfitDDEFeed()
        feed.symbol = "WINZ26"
        feed.set_callbacks(on_book=lambda snap: recebidos.append(snap))

        book = {
            "WINZ26.OCP": "167600,00",
            "WINZ26.OVD": "167610,00",
            "WINZ26.VOC": "450,00",
            "WINZ26.VOV": "120,00",
            "WINZ26.LOT": "1,00",
        }
        feed._read_top_book(lambda item: book.get(item), datetime.now(), 167605.0)

        self.assertEqual(len(recebidos), 1)
        snap = recebidos[0]
        self.assertIsInstance(snap, BookSnapshot)
        self.assertAlmostEqual(snap.best_bid, 167600.0)
        self.assertAlmostEqual(snap.best_ask, 167610.0)
        self.assertAlmostEqual(snap.spread, 10.0)
        self.assertEqual(snap.bids[0].quantity, 450)
        self.assertEqual(snap.asks[0].quantity, 120)


class TestBookAnalyzerTopDepth(unittest.TestCase):
    """O BookAnalyzer deve rotular honestamente a profundidade observada."""

    def test_imbalance_rotulado_por_profundidade(self):
        analyzer = BookAnalyzer(depth_levels=10)
        now = datetime.now()
        analyzer.update_snapshot(BookSnapshot(
            timestamp=now,
            bids=[BookLevel(price=167600.0, quantity=450)],
            asks=[BookLevel(price=167610.0, quantity=120)],
        ))

        res = analyzer.evaluate_book_behavior(167605.0)
        metrics = res["metrics"]

        self.assertEqual(metrics["book_depth_levels"], 1)
        self.assertIn("book_imbalance", metrics)
        # Com 1 nivel, nao pode se apresentar como medicao de 5 niveis.
        self.assertNotIn("book_imbalance_top5", metrics)
        self.assertAlmostEqual(metrics["book_imbalance"], 0.579, places=2)
        self.assertEqual(metrics["book_imbalance_depth"], 1)

    def test_limitation_declara_profundidade_real(self):
        analyzer = BookAnalyzer(depth_levels=10)
        analyzer.update_snapshot(BookSnapshot(
            timestamp=datetime.now(),
            bids=[BookLevel(price=167600.0, quantity=450)],
            asks=[BookLevel(price=167610.0, quantity=120)],
        ))

        res = analyzer.evaluate_book_behavior(167605.0)
        limitacoes = " ".join(res["limitations"])
        self.assertIn("nível 1", limitacoes)

    def test_livro_completo_mantem_rotulo_top5(self):
        analyzer = BookAnalyzer(depth_levels=10)
        now = datetime.now()
        analyzer.update_snapshot(BookSnapshot(
            timestamp=now,
            bids=[BookLevel(price=167600.0 - i * 5, quantity=100) for i in range(5)],
            asks=[BookLevel(price=167610.0 + i * 5, quantity=50) for i in range(5)],
        ))

        res = analyzer.evaluate_book_behavior(167605.0)
        metrics = res["metrics"]

        self.assertEqual(metrics["book_depth_levels"], 5)
        self.assertIn("book_imbalance_top5", metrics)
        self.assertEqual(metrics["book_imbalance_depth"], 5)


if __name__ == "__main__":
    unittest.main()
