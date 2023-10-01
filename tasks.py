
import os
# from io import StringIO
from invoke import task

THERMD = os.path.realpath(os.path.dirname(__file__))
if os.path.basename(THERMD) != 'thermal':
    raise Exception('tasks.py not in thermal/ dir.')


@task
def echo_test(ctx, dry=False, echo=True):
    """Echo test"""
    _ = ctx.run('echo "hello"', dry=dry, echo=echo)


@task
def reset_simops(ctx, dry=False, echo=True):
    """Copy new sim_ops_ dir from linked sim_ops_ln_ dir."""

    # Absolute paths
    simops_ln_dpath = os.path.relpath(
        os.path.realpath(os.path.join(THERMD, "simops_ln_")))
    simops_dpath = os.path.relpath(
        os.path.join(THERMD, "simops_"))

    if os.path.exists(simops_dpath):
        cmd = f"rm -rf {simops_dpath}"
        _ = ctx.run(cmd, dry=dry, echo=echo)

    cmd = f"cp -r {simops_ln_dpath} {simops_dpath}"
    _ = ctx.run(cmd, dry=dry, echo=echo)


@task
def swap2dos(ctx, dry=False, echo=True):
    """Make dos version of swap file for GH."""

    # Paths
    swap_fname = "swap.py"
    swap_dos_fname = "swap_win.py"
    swap_dos_fpath = os.path.join(THERMD, swap_dos_fname)
    rel_thermd = os.path.relpath(THERMD)

    # cd to thermd
    with ctx.cd(rel_thermd):
        # Make sure we use absolute path here since not in ctx
        if os.path.exists(swap_dos_fpath):
            cmd = f"rm -f ./{swap_dos_fname}"
            _ = ctx.run(cmd, dry=dry, echo=echo)
        # Convert to dos
        cmd = f"dos2unix -n ./{swap_fname} ./{swap_dos_fname}"
        _ = ctx.run(cmd, dry=dry, echo=echo)

@task
def swap(ctx, osm_fpath=None, epw_fpath=None, mea_dpath=None,
         dry=False, echo=True):
    """Run swap.py"""

    if osm_fpath is None:
        osm_fpath = os.path.join(THERMD, "simops_/run/in.osm")
    if epw_fpath is None:
        epw_fpath = os.path.join(THERMD, "epw/a1.epw")
    if mea_dpath is None:
        mea_dpath = os.path.join(THERMD, "mea")

    cmd = f"python swap.py {osm_fpath} {epw_fpath} {mea_dpath}"
    _ = ctx.run(cmd, dry=dry, echo=echo)


@task
def swap_tmux(ctx, t="x:1.2", dry=False, echo=True):
    """Send-keys swap.py to x:1.2 tmux session."""

    osm = "./simops_/run/in.osm"
    epw = "./epw/a1.epw"
    mea = "./mea"
    swapf = "swap.py"
    cmd = f'''tmux send-keys -t {t} '''
    cmd += f'''"cd {THERMD} && python {swapf} {osm} {epw} {mea}" ENTER'''

    # Run
    res = ctx.run(cmd, dry=dry, echo=echo)
    # print(res.stdout.strip())

    # popd
    cmd = f'''tmux send-keys -t {t} '''
    cmd += f'''"popd > /dev/null" ENTER'''
    _ = ctx.run(cmd, dry=dry, echo=echo)


## IN.BAT
## "C:\openstudio-3.4.0\EnergyPlus\energyplus.exe" -w "C:\Users\admin\masterwin\thermal\epw\USA_HI_Honolulu.Intl.AP.911820_TMY3\USA_HI_Honolulu.Intl.AP.911820_TMY3.epw" -i "C:\openstudio-3.4.0\EnergyPlus\Energy+.idd" -x
