#!/usr/bin/env bash
# Run the suite.
#
# PYTEST_DISABLE_PLUGIN_AUTOLOAD is set because this machine has ROS 2 on the
# system path; its pytest plugins load before ours and fail on a missing
# dependency that has nothing to do with this project. Harmless elsewhere.
set -euo pipefail
cd "$(dirname "$0")"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest "$@"
