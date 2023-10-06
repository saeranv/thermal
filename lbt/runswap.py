"""Run swap.py from subprocess on LBT python."""
from __future__ import print_function
import sys
import os
from subprocess import Popen, PIPE, STDOUT
from honeybee.config import folders as hb_config
from honeybee_energy.config import folders as hbe_config
from ladybug_rhino.download import download_file
path = os.path


# Set ghenv
ghenv.Component.Name = 'Swap OSM'
ghenv.Component.NickName = 'SwapOSM'
# code_lns = ghenv.Component.Code.split('\n')

# Global
SWAP_URL = "https://raw.githubusercontent.com/saeranv/thermal/main/swap.py"
SWAP_NAME = "swap.py"


def update_swap(is_update, swap_fpath, swap_url):
    """Update swap.py from github and confirm in lbt scripts path."""

    if is_update:
        _ = download_file(swap_url, swap_fpath)

    assert path.exists(swap_fpath), \
        "{} not at {}.\n".format(SWAP_NAME, path.dirname(swap_fpath))

    print("Downloaded {} from {}.".format(SWAP_NAME, SWAP_URL))


def run_subproc(cmds):
    """Run subprocess for list of commands (cmds)."""

    p = Popen(cmds, shell=True, stdout=PIPE, stderr=STDOUT)
    _stdout, _ = p.communicate()

    assert p.returncode == 0, \
            "Command failed:\n{}\n".format(" ".join(cmds).strip()) + \
            "stdout|stderr:\n{}\n".format(stdout)

    return _stdout.decode('utf-8')


if run_:

    # Update/confirm swap_fpath exists
    swap_fpath = path.join(hb_config.python_scripts_path, SWAP_NAME)
    _ = update_swap(update_, swap_fpath, SWAP_URL)

    # Run swap
    lbt_pytexe = hb_config.python_exe_path
    swap_cmds = [lbt_pytexe, swap_fpath, _osm, _epw, _mea]
    stdout = run_subproc(swap_cmds)
    osw_fpath = stdout.split('\n')[-1]
    assert path.exists(osw_fpath), \
        "OSW not found at {}".format(osw_fpath)

    # Run workflow.osw
    lbt_opsexe = hbe_config.openstudio_exe
    sim_cmds = [lbt_opsexe, "run", "--no-lifecyclecosts", "-w", osw_fpath]
    stdout = run_subproc(sim_cmds)
    print(stdout)
    print(os.listdir(os.path.join(run_fpath, "run")))

