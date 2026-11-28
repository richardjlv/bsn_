#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
workspace_dir=${1:-$repo_dir}
python_bin=${BSN_TEST_PYTHON:-python2.7}
ros_pytest_revision=201c4adb8dcf89ff76215fd9b6bf8ccd91d418f3
"$python_bin" -c 'import sys; assert sys.version_info[:2] == (2, 7), "ROS Melodic tests require Python 2.7"'
"$python_bin" -m pip install --user 'pip==20.3.4' 'setuptools==44.1.1' 'wheel==0.37.1'
"$python_bin" -m pip install --user -r "$repo_dir/requirements/test-melodic.txt"
checkout="$workspace_dir/src/ros_pytest"
if [[ -e "$checkout" ]]; then
    test "$(git -C "$checkout" rev-parse HEAD)" = "$ros_pytest_revision" || {
        echo "Existing ros_pytest has a different revision; preserve it and choose a separate workspace." >&2
        exit 1
    }
    test -z "$(git -C "$checkout" status --porcelain)" || {
        echo "Existing ros_pytest has local changes; leaving it untouched." >&2
        exit 1
    }
else
    mkdir -p "$workspace_dir/src"
    git clone https://github.com/machinekoder/ros_pytest.git "$checkout"
    git -C "$checkout" checkout --detach "$ros_pytest_revision"
fi

PYTHONPATH="$checkout/src${PYTHONPATH:+:$PYTHONPATH}" "$python_bin" -c \
    'from ros_pytest import run_pytest; import pytest_bdd; print("Test dependencies import successfully")'
echo "Next: catkin_make, then source devel/setup.bash before running tests."
