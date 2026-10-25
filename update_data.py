"""Census HS850760: validated monthly replacement, atomic version publishing."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import pandas as pd

BASE = 'https://api.census.gov/data/timeseries/intltrade/imports/'
DATASETS = {'statehs': ('STATE', 'HSSTCY'), 'porths': ('PORT', 'HSPTCY')}
MEASURES = ['GEN_VAL_MO', 'VES_WGT_MO', 'AIR_WGT_MO']


def now():
    return datetime.now(timezone.utc).isoformat()


def months(start, end):
    return [str(p) for p in pd.period_range(start, end, freq='M')]


def atomic_json(path, value):
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with tmp.open('w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


@contextmanager
def lock(root):
    path = root / 'update.lock'
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError('Another update is active. If it crashed, verify it stopped before deleting data/update.lock.') from None
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def fetch(ds, month, key):
    geo, _ = DATASETS[ds]
    fields = MEASURES + ['CTY_NAME', 'SUMMARY_LVL', 'SUMMARY_LVL2', 'COMM_LVL', 'LAST_UPDATE']
    if ds == 'porths':
        fields.append('PORT_NAME')
    params = {'get': ','.join(fields), 'I_COMMODITY': '850760',
              'time': month, 'CTY_CODE': '*', geo: '*', 'key': key}
    url = BASE + ds + '?' + urllib.parse.urlencode(params)
    for attempt in range(4):
        retry = False
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                if response.status == 204:
                    return None
                raw = response.read()
            try:
                arr = json.loads(raw)
            except (ValueError, UnicodeError):
                raise RuntimeError(f'{ds} {month}: non-JSON response') from None
            if not isinstance(arr, list) or not arr or not isinstance(arr[0], list):
                raise RuntimeError(f'{ds} {month}: unexpected response schema')
            required = set(fields + ['CTY_CODE', geo, 'I_COMMODITY', 'time'])
            if not required.issubset(arr[0]):
                raise RuntimeError(f'{ds} {month}: required columns missing')
            if len(arr) <= 1:
                raise RuntimeError(f'{ds} {month}: empty response, not confirmed unavailable')
            if len(arr) - 1 >= 49999:
                raise RuntimeError(f'{ds} {month}: monthly response near row limit; stop, split query before retrying')
            if any(len(row) != len(arr[0]) for row in arr[1:]):
                raise RuntimeError(f'{ds} {month}: malformed rows')
            return pd.DataFrame(arr[1:], columns=arr[0])
        except urllib.error.HTTPError as exc:
            retry = exc.code in (429, 500, 502, 503, 504)
            error = f'HTTP {exc.code}'
        except (urllib.error.URLError, TimeoutError, OSError):
            retry = True
            error = 'network/timeout error'
        if not retry or attempt == 3:
            # Never expose URL or key through exception text.
            raise RuntimeError(f'{ds} {month}: {error}') from None
        time.sleep(2 ** attempt)


def clean(raw, ds, month):
    geo, level = DATASETS[ds]
    raw = raw.copy()
    if not raw['time'].eq(month).all() or not raw['I_COMMODITY'].eq('850760').all():
        raise ValueError(f'{ds}: wrong month/product')
    for c in MEASURES:
        raw[c] = pd.to_numeric(raw[c], errors='raise')
        if raw[c].isna().any() or (raw[c] < 0).any() or (raw[c] % 1 != 0).any():
            raise ValueError(f'{ds}: invalid numeric measure')
        raw[c] = raw[c].astype('int64')
    total = raw[(raw.SUMMARY_LVL == 'DET') & (raw.CTY_CODE == '-') & (raw[geo] == '-')
                & (raw.COMM_LVL == 'HS6')]
    if len(total) != 1:
        raise ValueError(f'{ds}: missing or duplicate national control total')
    detail = raw[(raw.SUMMARY_LVL == 'DET') & (raw.SUMMARY_LVL2 == level)
                 & raw.CTY_CODE.str.fullmatch(r'\d{4}', na=False)
                 & raw[geo].notna() & ~raw[geo].isin(['', '-']) & (raw.COMM_LVL == 'HS6')].copy()
    if detail.empty or detail.duplicated(['time', 'CTY_CODE', geo, 'I_COMMODITY']).any():
        raise ValueError(f'{ds}: empty detail or duplicate keys')
    if int(detail.GEN_VAL_MO.sum()) != int(total.GEN_VAL_MO.iloc[0]):
        raise ValueError(f'{ds}: detail does not reconcile to national amount')
    cols = ['time', 'CTY_CODE', 'CTY_NAME', geo, 'I_COMMODITY'] + MEASURES
    if ds == 'porths':
        cols.append('PORT_NAME')
    return detail[cols].reset_index(drop=True)


def validate_pair(state, port, expected):
    for ds, df in [('statehs', state), ('porths', port)]:
        geo = DATASETS[ds][0]
        if set(df.time) != set(expected):
            raise ValueError(f'{ds}: missing or unexpected months')
        if df.duplicated(['time', 'CTY_CODE', geo, 'I_COMMODITY']).any():
            raise ValueError(f'{ds}: duplicate keys')
    a = state.groupby(['time', 'CTY_CODE']).GEN_VAL_MO.sum()
    b = port.groupby(['time', 'CTY_CODE']).GEN_VAL_MO.sum()
    # Full-zero country rows may differ across geography endpoints.
    if a.sub(b, fill_value=0).ne(0).any():
        raise ValueError('State/port country-month amounts differ')


def replace_months(old, new):
    if old is None:
        return new.copy()
    return pd.concat([old[~old.time.isin(new.time.unique())], new], ignore_index=True)


def read_current(root):
    pointer = root / 'current.json'
    if not pointer.exists():
        return None, None
    version = json.loads(pointer.read_text(encoding='utf-8'))['version']
    folder = root / 'versions' / version
    return ({ds: pd.read_parquet(folder / f'{ds}.parquet') for ds in DATASETS},
            json.loads((folder / 'metadata.json').read_text(encoding='utf-8')))


def publish(root, frames, source, updated_months):
    version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:8]
    folder = root / 'versions' / version
    folder.mkdir(parents=True)
    # Readers keep using the old pointer until BOTH data files and metadata are ready.
    for ds, df in frames.items():
        geo = DATASETS[ds][0]
        df.sort_values(['time', 'CTY_CODE', geo]).to_parquet(folder / f'{ds}.parquet', index=False)
    metadata = {'version': version, 'last_successful_update': now(),
                'min_month': min(frames['statehs'].time), 'max_month': max(frames['statehs'].time),
                'rows': {ds: len(df) for ds, df in frames.items()},
                'validation': 'passed', 'source': source, 'updated_months': updated_months,
                'hs_code': '850760', 'zero_records': 'preserved when present in source'}
    atomic_json(folder / 'metadata.json', metadata)
    atomic_json(root / 'current.json', {'version': version})
    return metadata


def bootstrap_zip(root, path):
    import zipfile
    if (root / 'current.json').exists():
        raise ValueError('Already initialized; bootstrap cannot overwrite an existing version')
    with zipfile.ZipFile(path) as archive:
        raw = json.loads(archive.read('clean_data.json'))
        audit = json.loads(archive.read('audit.json'))
    frames = {}
    for ds in DATASETS:
        df = pd.DataFrame(raw[ds])
        for c in MEASURES:
            df[c] = pd.to_numeric(df[c], errors='raise').astype('int64')
        if df[MEASURES].isna().any().any() or (df[MEASURES] < 0).any().any():
            raise ValueError('Invalid bootstrap measures')
        if not df.I_COMMODITY.eq('850760').all():
            raise ValueError('Wrong bootstrap product')
        sums = df.groupby('time').GEN_VAL_MO.sum().to_dict()
        if sums != audit[ds]['monthly_totals']:
            raise ValueError('Bootstrap does not match supplied audit totals')
        frames[ds] = df
    expected = months(min(frames['statehs'].time), max(frames['statehs'].time))
    validate_pair(frames['statehs'], frames['porths'], expected)
    return publish(root, frames, 'user-supplied ZIP snapshot, reconciled to bundled audit; not live API validation', expected)


def run(args):
    root = Path(args.data_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with lock(root):
        try:
            if args.bootstrap_zip:
                meta = bootstrap_zip(root, args.bootstrap_zip)
                status = {'last_checked': now(), 'status': 'bootstrap_success', 'data_through': meta['max_month']}
            else:
                key = os.environ.get('CENSUS_API_KEY')
                if not key:
                    raise ValueError('Set CENSUS_API_KEY in the environment first')
                old, meta = read_current(root)
                today = datetime.now(timezone.utc).strftime('%Y-%m')
                start = args.start if old is None or args.full else str(max(
                    pd.Period(args.start, 'M'), pd.Period(meta['max_month'], 'M') - (args.lookback - 1)))
                end = str(pd.Period(today, 'M') - 1)
                staged = {ds: [] for ds in DATASETS}
                unavailable = []
                for month in months(start, end):
                    print('Checking', month, flush=True)
                    pair = {ds: fetch(ds, month, key) for ds in DATASETS}
                    missing = [ds for ds, df in pair.items() if df is None]
                    if missing:
                        if len(missing) != 2 or (meta and month <= meta['max_month']):
                            raise ValueError(f'{month}: one endpoint unavailable or an existing month disappeared')
                        unavailable.append(month)
                        continue
                    if unavailable:
                        raise ValueError('A gap appears before an available month')
                    pair = {ds: clean(df, ds, month) for ds, df in pair.items()}
                    validate_pair(pair['statehs'], pair['porths'], [month])
                    for ds in DATASETS:
                        staged[ds].append(pair[ds])
                if not staged['statehs']:
                    raise ValueError('No valid months downloaded; previous version retained')
                new = {ds: pd.concat(parts, ignore_index=True) for ds, parts in staged.items()}
                frames = {ds: replace_months(None if old is None else old[ds], new[ds]) for ds in DATASETS}
                expected = months(min(frames['statehs'].time), max(frames['statehs'].time))
                validate_pair(frames['statehs'], frames['porths'], expected)
                meta = publish(root, frames, 'Census API statehs/porths; monthly national controls verified', sorted(new['statehs'].time.unique()))
                status = {'last_checked': now(), 'status': 'success', 'data_through': meta['max_month'],
                          'not_yet_available': unavailable}
            atomic_json(root / 'status.json', status)
            print(json.dumps(status, ensure_ascii=False))
        except Exception as exc:
            atomic_json(root / 'status.json', {'last_checked': now(), 'status': 'failed',
                                             'error': str(exc), 'previous_version_retained': True})
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', default=str(Path(__file__).parent / 'data'))
    parser.add_argument('--start', default='2017-01')
    parser.add_argument('--lookback', type=int, default=24)
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--bootstrap-zip', help='Initialize offline from the supplied original code/data ZIP')
    args = parser.parse_args()
    if args.lookback < 1:
        parser.error('--lookback must be at least 1')
    try:
        run(args)
    except Exception as exc:
        print('Update failed:', str(exc))
        raise SystemExit(1)
