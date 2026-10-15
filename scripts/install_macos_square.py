"""Install per-user Square sync and AC-powered stay-awake LaunchAgents."""
import os
from pathlib import Path
import plistlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != 'darwin':
        raise SystemExit('Run this installer on the Mac, not Linux or Windows.')
    python = ROOT / '.venv/bin/python'
    runner = ROOT / 'scripts/run_local_square.py'
    subprocess.run([str(python), str(runner), '--check'], check=True, cwd=ROOT)
    agents = Path.home() / 'Library/LaunchAgents'
    agents.mkdir(parents=True, exist_ok=True)
    domain = f'gui/{os.getuid()}'
    jobs = [
        {'Label': 'com.thearch.datahq.square',
         'ProgramArguments': [str(python), str(runner)],
         'WorkingDirectory': str(ROOT), 'StartInterval': 300, 'RunAtLoad': True},
        {'Label': 'com.thearch.datahq.awake',
         'ProgramArguments': ['/usr/bin/caffeinate', '-s'],
         'RunAtLoad': True, 'KeepAlive': True},
    ]
    for job in jobs:
        label = job['Label']
        active = subprocess.run(['/bin/launchctl', 'print', f'{domain}/{label}'], capture_output=True)
        if active.returncode == 0:
            print(f'Already loaded: {label}; leaving it running')
            continue
        path = agents / f'{label}.plist'
        path.write_bytes(plistlib.dumps(job))
        path.chmod(0o600)
        subprocess.run(['/usr/bin/plutil', '-lint', str(path)], check=True)
        subprocess.run(['/bin/launchctl', 'bootstrap', domain, str(path)], check=True)
        print(f'Installed: {label}')
    print('Square scheduler installed: every 5 minutes within Irish trading hours + 90 minutes.')
    print('Logs: ~/Library/Logs/DataHQ/square.log')
    print('Keep plugged in with lid open. Agents resume at login, not before login after reboot.')


if __name__ == '__main__':
    main()
