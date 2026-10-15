# Square on the Mac

Install Python 3.12, clone DataHQ into ~/datahq, create .venv, install
requirements.txt and configure the git-ignored .env. Verify one manual sync first.
Then run `.venv/bin/python scripts/install_macos_square.py` from the repository.

The installer checks database credentials and the opening-hours calendar without
syncing, then installs LaunchAgents for the logged-in user. Square is checked
every 300 seconds and runs only from opening through 90 minutes after closing,
using Europe/Dublin time and today's/yesterday's database calendar. Missing
calendar data fails visibly in the log rather than running at arbitrary times.
Closed periods still perform a small calendar lookup. Scheduled invocations
cannot overlap on this Mac; a ten-minute timeout stops a stuck sync. Failed
invocations retry on the next scheduled tick. This does not lock direct manual
commands or jobs on other computers.

The companion caffeinate agent prevents sleep while on AC power. Keep the lid
open and power/internet connected. The screen may turn off and the account may
be locked. After a restart, log in again to load the agents. No updates run while
the Mac is shut down, asleep or logged out. No automatic git pulls are performed.

Logs: `~/Library/Logs/DataHQ/square.log` (rotated at 2 MB, three backups).
Inspect with `tail -n 20 ~/Library/Logs/DataHQ/square.log`.

Pause: `touch "$HOME/Library/Application Support/DataHQ/PAUSED"`.
This prevents new runs but lets a running sync finish. Wait for its completion
before using GitHub's manual backup or a direct manual sync. GitHub's operational
sync workflow is manual-only; Revolut/weather/cruise/opening-hours schedules stay
on GitHub until separately migrated. Resume by removing only the PAUSED file.

To remove the agents, first pause and wait for any sync to finish; then use
`launchctl bootout gui/$(id -u)/com.thearch.datahq.square` and the equivalent for
`com.thearch.datahq.awake`, and remove their two plist files from ~/Library/LaunchAgents.
