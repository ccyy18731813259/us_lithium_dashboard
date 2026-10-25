import unittest
from streamlit.testing.v1 import AppTest
from model import ROOT, load_version, country_panel, geography_table, comparison, concentration, COUNTRY_ZH
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
            weighted=(table['中国份额相对全国倍数']*table['占全国进口比重（%）']/100).sum()
            self.assertAlmostEqual(weighted,1)

    def test_chinese_source_names(self):
        version=json.loads((ROOT/'data/current.json').read_text())['version']
        state,port,_=load_version(version)
        codes=set(state.CTY_CODE)|set(port.CTY_CODE)
        self.assertFalse(codes-set(COUNTRY_ZH))
        _,_,names=country_panel(state)
        self.assertEqual(names['5830'],'中国台湾')
        self.assertEqual(names['5820'],'中国香港')
        self.assertEqual(names['5660'],'中国澳门')
        self.assertTrue(names.map(lambda n: all(not ('a'<=c.lower()<='z') for c in n)).all())

    def test_app_default_and_rolling(self):
        app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=60).run()
        self.assertEqual(len(app.exception),0, str(app.exception))
        self.assertEqual(len(app.tabs),7)
        app.radio(key='trend_mode').set_value('滚动12个月').run()
        self.assertEqual(len(app.exception),0, str(app.exception))
        app.selectbox(key='state').set_value('中国占当地进口比重（%）').run()
        self.assertEqual(len(app.exception),0, str(app.exception))
        app.selectbox(key='state_drill').set_value('TX').run()
        self.assertEqual(len(app.exception),0, str(app.exception))
        app.selectbox(key='transport_country').set_value('5700').run()
        self.assertEqual(len(app.exception),0, str(app.exception))
        app.selectbox(key='source_comparison').set_value(3).run()
        self.assertEqual(len(app.exception),0, str(app.exception))
        app.radio(key='source_scale').set_value('首月=100').run()
        self.assertEqual(len(app.exception),0, str(app.exception))
        app.select_slider[0].set_value(('2017-01','2017-06')).run()
        self.assertEqual(len(app.exception),0, str(app.exception))
        app.radio(key='trend_mode').set_value('当月').run()
        self.assertEqual(len(app.exception),0, str(app.exception))

    def test_comparison_and_decomposition(self):
        version=json.loads((ROOT/'data/current.json').read_text())['version']
        raw,shares,_=country_panel(load_version(version)[0])
        self.assertIsNone(comparison(raw,'2017-06',12))
        for k in (3,6,12):
            change,old,new=comparison(raw,'2026-08',k)
            self.assertEqual(len(set(old)&set(new)),0)
            self.assertEqual(len(old),k)
            self.assertAlmostEqual(change['份额变化（百分点）'].sum(),0,places=8)
            a=change['基期金额'].sum();b=change['报告期金额'].sum();r=change.loc['5700']
            scale=r['基期金额']/a*(b-a)
            mix=b*(r['报告期金额']/b-r['基期金额']/a)
            self.assertAlmostEqual(scale+mix,r['金额变化'],places=4)
            self.assertAlmostEqual(change['对美国进口增长的贡献（百分点）'].sum(),(b/a-1)*100)
        metrics=concentration(shares)
        self.assertTrue(metrics['HHI'].between(0,1).all())
        self.assertTrue((metrics['有效来源数（1/HHI）']>=1).all())


if __name__ == '__main__':
    unittest.main()
