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
SWAP_URL = "https://raw.githubusercontent.com/saeranv/thermal/main/lbt/swap.py"
SWAP_NAME = "swap.py"
IS_TTY = sys.stdin.isatty() or len(sys.argv) > 1


def run_subproc(cmds):
    """Run subprocess for list of commands (cmds)."""

    print("Running command:\n{}\n".format(" ".join(cmds)))
    p = Popen(cmds, shell=True, stdout=PIPE, stderr=PIPE)
    _stdout, _stderr = p.communicate()

    assert p.returncode == 0, \
        "returncode: {}\nstdout:\n{}\nstderr:\n{}".format(
            p.returncode, _stdout, _stderr)
    return _stdout, _stderr


def update_swap(_swap_fpath):
    """Update swap.py from github and confirm in lbt scripts path."""

    _ = download_file(SWAP_URL, _swap_fpath)
    print("## Downloaded {} from {}.".format(SWAP_NAME, SWAP_URL))

    assert path.exists(_swap_fpath), \
        "Path {} not exist.\n".format(_swap_fpath)


def update_pip(_lbt_pytexe, _ops_version):
    """Update openstudio SDK via pip."""

    # Check if pip opesntudio is updated
    cmds = [_lbt_pytexe, "-m", "pip", "list"]
    _stdout = run_subproc(cmds)[0]
    pkgs = _stdout.decode("utf-8").strip().split("\n")
    is_pip_match = False
    for pkg in pkgs:
        if "openstudio" in pkg:
            _ops_version_ = pkg.split("openstudio")[1].strip()
            print("## Found openstudio {} in pip.".format(_ops_version_))
            is_pip_match = _ops_version_ == _ops_version
            break

    if not is_pip_match:
        # Pip install openstudio if not in pip or version wrong
        _ops_pkg = "openstudio=={}".format(_ops_version)
        cmds = [_lbt_pytexe, "-m", "pip", "install", _ops_pkg]

        _stdout, _stderr = run_subproc(cmds)
        if _stdout: print(_stdout.decode("utf-8").strip())
        if _stderr: print(_stderr.decode("utf-8").strip())


def dump_mea(measure, osw_fpath):
    """Dump measure to osw file."""

    osw_dict = measure.to_osw_dict()
    osw_dict["measure_paths"] = [measure.folder]
    with open(osw_fpath, "w") as fp:
        json.dump(osw_dict, fp, indent=4)
    return osw_fpath

if IS_TTY:
    # Label bool, fpath inputs
    run_swap_, run_sim_, update_ = True, True, True
    _osm, _epw, _mea_dpath = sys.argv[-3:]
    _mea = Measure(_mea_dpath)

if run_swap_ or run_sim_ or update_:

    # # Overwrite
    # update_ = False
    # run_swap_ = False
    # run_sim_ = False

    lbt_pytexe = hb_config.python_exe_path
    lbt_opsexe = hbe_config.openstudio_exe
    opsv_ = hbe_config.openstudio_version
    ops_version = "{}.{}.{}".format(opsv_[0], opsv_[1], opsv_[2])
    swap_fpath = path.join(hb_config.python_scripts_path, SWAP_NAME)
    # # TODO: only for debugging
    # swap_fpath = path.abspath(path.join(_epw, "../../../lbt", SWAP_NAME))

    # Update/confirm swap_fpath exists
    if update_ or (not path.exists(swap_fpath)):
        _ = update_swap(swap_fpath)
        _ = update_pip(lbt_pytexe, ops_version)
        update_cmds = [lbt_pytexe, swap_fpath, "--help"]
        stdout = run_subproc(update_cmds)[0]
        print(stdout.decode("utf-8").strip())

    assert isinstance(_osm, str) and path.exists(_osm), \
        "Error, OSM file does not exist."
    assert isinstance(_epw, str) and path.exists(_epw), \
        "Error, EPW file does not exist."
    assert _mea is not None, \
        "Error, Measure obj does not exist."

    try:
        _osw_swap, _osm_swap = None, None
        runsim_dpath = path.dirname(_osm) # sim dpath is child
        _osw = path.join(runsim_dpath, "workflow.osw")


        if run_swap_:
            # Run swap
            print("\n## Running swap.py on lbtpyt.exe")
            # Update measure, and run swap_win.py
            _osw = dump_mea(_mea[0], _osw)
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

            ransim_dpath = path.join(runsim_dpath, "run")
            _sql = path.join(ransim_dpath, "eplusout.sql")
            if path.exists(_sql):
                osm = path.join(ransim_dpath, "in.osm")
                _osm_swap = _osm_swap
                idf = path.join(ransim_dpath, "in.idf")
                zsz = path.join(ransim_dpath, "epluszsz.csv")
                rdd = path.join(ransim_dpath, "eplus.rdd")
                html = path.join(ransim_dpath, "eplustbl.htm")
                err = path.join(ransim_dpath, "eplusout.err")
                sql = _sql
                print(osm, idf, zsz, rdd, html, err, sql, sep="\n")
    except:
        # clear globals in case error in OSM object.
        for name in dir():
            if name.startswith("_"):
                continue
            del globals()[name]
        # raise w/o arg means gets last exception and reraise it
        raise
