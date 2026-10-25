import unittest
from streamlit.testing.v1 import AppTest
from model import ROOT, load_version, country_panel, geography_table
import json


class DashboardTests(unittest.TestCase):
    def test_real_data_metrics(self):
        version = json.loads((ROOT/'data/current.json').read_text())['version']
        state, port, _ = load_version(version)
        raw, share, _ = country_panel(state)
        self.assertEqual(int(raw.loc['2026-08'].sum()), 1306251046)
        self.assertEqual(int(raw.loc['2026-08','5700']), 483949127)
        self.assertAlmostEqual(float(share.loc['2026-08'].sum()), 1)
        for df, geo in [(state,'STATE'),(port,'PORT')]:
            table = geography_table(df,geo,'2026-08','2026-08')
            self.assertEqual(int(table['进口金额（美元）'].sum()), 1306251046)
            self.assertAlmostEqual(float(table['占全国自华进口比重（%）'].sum()),100)

    def test_app_default_and_rolling(self):
        app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=60).run()
        self.assertEqual(len(app.exception),0, str(app.exception))
        self.assertEqual(len(app.tabs),6)
        app.radio[0].set_value('滚动12个月').run()
        self.assertEqual(len(app.exception),0, str(app.exception))
        app.selectbox[0].set_value('中国占当地进口比重（%）').run()
        self.assertEqual(len(app.exception),0, str(app.exception))
        app.select_slider[0].set_value(('2017-01','2017-06')).run()
        self.assertEqual(len(app.exception),0, str(app.exception))


if __name__ == '__main__':
    unittest.main()
