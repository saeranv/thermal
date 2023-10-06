"""Run swap.py from subprocess on LBT python."""
from __future__ import print_function
import sys
import os
import json
from pprint import pprint
from subprocess import Popen, PIPE, STDOUT
from honeybee.config import folders as hb_config
from honeybee_energy.config import folders as hbe_config
from honeybee_energy.measure import Measure
from ladybug_rhino.download import download_file


# Global
path = os.path
SWAP_URL = "https://raw.githubusercontent.com/saeranv/thermal/main/lbt/swap_win.py"
SWAP_NAME = "swap_win.py"
IS_TTY = sys.stdin.isatty() or len(sys.argv) > 1


def run_subproc(cmds):
    """Run subprocess for list of commands (cmds)."""

    # print("Running command:\n", " ".join(cmds))
    p = Popen(cmds, shell=True, stdout=PIPE, stderr=PIPE)
    _stdout, _stderr = p.communicate()

    assert p.returncode == 0, \
            "Command failed:\n{}\n".format(" ".join(cmds).strip()) + \
        "stdout:\n{}\nstderr:\n{}".format(_stdout, _stderr)
    return _stdout, _stderr


def update_swap(swap_fpath):
    """Update swap.py from github and confirm in lbt scripts path."""

    _ = download_file(SWAP_URL, swap_fpath)
    print("## Downloaded {} from {}.".format(SWAP_NAME, SWAP_URL))

    assert path.exists(swap_fpath), \
        "Path {} not exist.\n".format(swap_fpath)


def update_pip(lbt_pytexe, ops_version):
    """Update openstudio SDK via pip."""

    # Check if pip opesntudio is updated
    cmds = [lbt_pytexe, "-m", "pip", "list"]
    stdout = run_subproc(cmds)[0]
    pkgs = stdout.decode("utf-8").strip().split("\n")
    is_pip_match = False
    for pkg in pkgs:
        if "openstudio" in pkg:
            ops_version_ = pkg.split("openstudio")[1].strip()
            print("## Found openstudio {} in pip.".format(ops_version_))
            is_pip_match = ops_version_ == ops_version
            break

    if not is_pip_match:
        # Pip install openstudio if not in pip or version wrong
        _ops_pkg = "openstudio=={}".format(ops_version)
        cmds = [lbt_pytexe, "-m", "pip", "install", _ops_pkg]

        stdout, stderr = run_subproc(cmds)
        if stdout: print(stdout.decode("utf-8").strip())
        if stderr: print(stderr.decode("utf-8").strip())


if IS_TTY:
    # Label bool, fpath inputs
    run_swap_, run_sim_, update_ = True, True, True
    _osm, _epw, _mea_dpath = sys.argv[-3:]
    mea = Measure(_mea_dpath)

if run_swap_ or run_sim_ or update_:

    # Overwrite
    # update_ = False
    # run_swap_ = False
    # run_sim_ = False

    osw_swap, osm_swap = None, None
    swap_fpath = path.join(hb_config.python_scripts_path, SWAP_NAME)
    lbt_pytexe = hb_config.python_exe_path
    lbt_opsexe = hbe_config.openstudio_exe
    opsv_ = hbe_config.openstudio_version
    ops_version = "{}.{}.{}".format(opsv_[0], opsv_[1], opsv_[2])
    runsim_dpath = path.join(path.dirname(_osm), "run") # sim dpath is child

    # # TODO: only for debugging
    swap_fpath = path.abspath(path.join(_epw, "../../../lbt", SWAP_NAME))
    print(swap_fpath)
    # Update/confirm swap_fpath exists
    if update_ or (not path.exists(swap_fpath)):
        # _ = update_swap(swap_fpath)
        _ = update_pip(lbt_pytexe, ops_version)

    if run_swap_:
        # Run swap
        print("\n## Running swap.py on lbtpyt.exe")

        # Update measure
        _osw = path.join(path.dirname(_osm), "workflow.osw")
        with open(_osw, "w") as fp:
            osw_dict = _mea[0].to_osw_dict()
            json.dump(osw_dict, fp, indent=4)

        # Run swap
        swap_cmds = [lbt_pytexe, swap_fpath, _osw, _osm, _epw]
        stdout, stderr = run_subproc(swap_cmds)
        _osm_swap, _osw_swap = \
            stdout.decode('utf-8').strip().split("\n")[-2:]
        if stdout: print(stdout.decode('utf-8'))
        if stderr: print(stderr.decode('utf-8'))

    if run_sim_:
        # Run workflow.osw
        print("\n## Running workflow.osw on openstudio.exe")

        if not _osw_swap:
            _osw_swap = path.join(runsim_dpath, "workflow_swap.osw")

        assert path.exists(_osw_swap), \
            "OSW not found at {}".format(_osw_swap)

        sim_cmds = [lbt_opsexe, "run", "-w", _osw_swap]
        stdout, stderr = run_subproc(sim_cmds)
        if stdout: print(stdout)
        if stderr: print(stderr)

        # Get outputs
        # print(runsim_dpath, ":\n", os.listdir(runsim_dpath))
        osm = path.join(runsim_dpath, "in.osm")
        idf = path.join(runsim_dpath, "in.idf")
        zsz = path.join(runsim_dpath, "epluszsz.csv")
        rdd = path.join(runsim_dpath, "eplus.rdd")
        html = path.join(runsim_dpath, "eplustbl.htm")
        err = path.join(runsim_dpath, "eplusout.err")
        sql = path.join(runsim_dpath, "eplusout.sql")
        print(osm, idf, zsz, rdd, html, err, sql, sep="\n")

