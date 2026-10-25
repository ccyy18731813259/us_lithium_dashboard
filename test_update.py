"""Offline regression tests; no Census key needed."""
import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
import update_data as u


def raw(ds, month='2026-01', value=10):
    geo, level = u.DATASETS[ds]
    base = {'time': month, 'I_COMMODITY': '850760', 'COMM_LVL': 'HS6',
            'SUMMARY_LVL': 'DET', 'CTY_NAME': 'CHINA', 'GEN_VAL_MO': str(value),
            'VES_WGT_MO': '1', 'AIR_WGT_MO': '0'}
    detail = dict(base, CTY_CODE='5700', SUMMARY_LVL2=level)
    detail[geo] = 'CA' if ds == 'statehs' else '0901'
    if ds == 'porths':
        detail['PORT_NAME'] = 'Example'
    total = dict(base, CTY_CODE='-', SUMMARY_LVL2='TOTAL')
    total[geo] = '-'
    return pd.DataFrame([detail, total])


class UpdateTests(unittest.TestCase):
    def test_clean_reconcile_and_duplicate(self):
        r = raw('statehs')
        self.assertEqual(int(u.clean(r, 'statehs', '2026-01').GEN_VAL_MO.sum()), 10)
        with self.assertRaises(ValueError):
            u.clean(pd.concat([r, r.iloc[[0]]]), 'statehs', '2026-01')
        r.loc[1, 'GEN_VAL_MO'] = '11'
        with self.assertRaises(ValueError):
            u.clean(r, 'statehs', '2026-01')

    def test_country_mismatch(self):
        a = u.clean(raw('statehs'), 'statehs', '2026-01')
        b = u.clean(raw('porths', value=11), 'porths', '2026-01')
        with self.assertRaises(ValueError):
            u.validate_pair(a, b, ['2026-01'])

    def test_whole_month_removes_disappeared_rows(self):
        old = pd.DataFrame({'time': ['2025-12', '2026-01', '2026-01'], 'x': [1, 2, 3]})
        new = pd.DataFrame({'time': ['2026-01'], 'x': [4]})
        self.assertEqual(u.replace_months(old, new).x.tolist(), [1, 4])

    def test_atomic_publish_and_failure_retains_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frames = {ds: u.clean(raw(ds), ds, '2026-01') for ds in u.DATASETS}
            u.publish(root, frames, 'test', ['2026-01'])
            before = (root / 'current.json').read_bytes()
            loaded, _ = u.read_current(root)
            self.assertEqual(int(loaded['statehs'].GEN_VAL_MO.sum()), 10)
            args = argparse.Namespace(data_dir=tmp, bootstrap_zip=None, full=False, start='2017-01', lookback=1)
            with patch.dict('os.environ', {'CENSUS_API_KEY': 'test'}), patch.object(u, 'fetch', side_effect=RuntimeError('simulated failure')):
                with self.assertRaises(RuntimeError):
                    u.run(args)
            self.assertEqual(before, (root / 'current.json').read_bytes())
            self.assertEqual(json.loads((root / 'status.json').read_text())['status'], 'failed')
            self.assertFalse((root / 'update.lock').exists())

    def test_partial_file_write_never_switches_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frames = {ds: u.clean(raw(ds), ds, '2026-01') for ds in u.DATASETS}
            u.publish(root, frames, 'test', ['2026-01'])
            before = (root / 'current.json').read_bytes()
            with patch.object(pd.DataFrame, 'to_parquet', side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):
                    u.publish(root, frames, 'test', ['2026-01'])
            self.assertEqual(before, (root / 'current.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
