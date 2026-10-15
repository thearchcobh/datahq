"""Five-minute launchd entry point. All dates use the Irish trading calendar."""
import argparse
from datetime import datetime, timedelta
import fcntl
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Validate credentials/calendar without syncing')
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    for name in ('SUPABASE_URL', 'SUPABASE_SECRET_KEY', 'SQUARE_ACCESS_TOKEN'):
        if not os.environ.get(name):
            raise RuntimeError(f'{name} is missing from .env')
    state = Path.home() / 'Library/Application Support/DataHQ'
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    logs = Path.home() / 'Library/Logs/DataHQ'
    logs.mkdir(parents=True, exist_ok=True, mode=0o700)
    logger = logging.getLogger('datahq.local')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(logs / 'square.log', maxBytes=2_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    with (state / 'square.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.info('Skipped: another local scheduled Square run is active')
            return
        if (state / 'PAUSED').exists() and not args.check:
            logger.info('Skipped: local scheduler is paused')
            return
        try:
            from datahq.database import get_client
            from datahq.sync_window import DUBLIN, in_window
            now = datetime.now(DUBLIN)
            rows = (get_client().table('analytics_opening_hours_daily')
                    .select('trading_date,is_scheduled_open,open_time,close_time,close_next_day')
                    .gte('trading_date', (now.date() - timedelta(days=1)).isoformat())
                    .lte('trading_date', now.date().isoformat()).execute().data)
            allowed = in_window(rows, now)
            logger.info('Irish time %s; trading window open=%s', now.isoformat(), allowed)
            if args.check:
                logger.info('Preflight passed: database/calendar accessible; no sync performed')
                return
            if not allowed:
                return
            env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONUNBUFFERED='1')
            result = subprocess.run([sys.executable, '-m', 'datahq.main', 'square'],
                                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
            if result.stdout:
                logger.info('%s', result.stdout[-16000:])
            if result.stderr:
                logger.warning('%s', result.stderr[-16000:])
            if result.returncode:
                raise RuntimeError(f'Square exited with code {result.returncode}; next attempt in five minutes')
            logger.info('Square sync completed successfully')
        except Exception:
            logger.exception('Square scheduler failed; next scheduled invocation will retry')
            raise


if __name__ == '__main__':
    main()
