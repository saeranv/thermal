import os
from invoke import task
# from io import StringIO
from shlex import quote, split
path = os.path

MASTERD = "/mnt/c/users/admin/masterwin"
LBTD = "/mnt/c/users/admin/ladybug_tools"
THERMD = f"{MASTERD}/thermal"
# Usage: inv -c=TMUXM -l
TMUXM = f"{MASTERD}/orgmode/auto/tmux/tasks"

@task
def echo_test(ctx, dry=False, echo=False):
    """Echo test"""
    _ = ctx.run('echo "hello"', dry=dry, echo=echo)


@task
def reset_simops(ctx, dry=False, echo=False):
    """Copy new sim_ops_ dir from linked sim_ops_ln_ dir."""

    # Absolute paths
    simops_ln_dpath = os.path.relpath(
        os.path.realpath(os.path.join(THERMD, "simops_ln")))
    simops_dpath = os.path.relpath(
        os.path.join(THERMD, "simops"))

    if os.path.exists(simops_dpath):
        cmd = f"rm -rf {simops_dpath}"
        _ = ctx.run(cmd, dry=dry, echo=echo)

    cmd = f"cp -r {simops_ln_dpath} {simops_dpath}"
    _ = ctx.run(cmd, dry=dry, echo=echo)


@task
def unix2dos(ctx):
    """Make dos version of swap file for GH."""

    # Paths
    swap_fpath = os.path.join(THERMD, "lbt", "swap_gh.py")
    swap_fpath_dos = os.path.join(THERMD, "lbt", "swap_gh_win.py")

    # cd to thermd
    with ctx.cd(THERMD):
        # Make sure we use absolute path here since not in ctx
        if os.path.exists(swap_fpath_dos):
            cmd = f"rm -f {swap_fpath_dos}"
            _ = ctx.run(cmd, hide=True)
        # Convert to dos
        cmd = f"unix2dos -n {swap_fpath} {swap_fpath_dos}"
        _ = ctx.run(cmd, hide=True)


@task
def swap_tmux(ctx, t="x:1.2", dry=False, echo=False):
    """Send-keys swap.py to x:1.2 tmux session."""

    osm = "./simops_/run/in.osm"
    epw = "./epw/a1.epw"
    mea = "./mea"
    swapf = "./lbt/swap.py"
    cmd = f'''tmux send-keys -t {t} '''
    cmd += f'''"cd {THERMD} && python {swapf} {osm} {epw} {mea}" ENTER'''

    # Run
    res = ctx.run(cmd, dry=dry, echo=echo)
    # print(res.stdout.strip())

    # popd
    cmd = f'''tmux send-keys -t {t} '''
    cmd += f'''"popd > /dev/null" ENTER'''
    _ = ctx.run(cmd, dry=dry, echo=echo)

@task
def eval_env(ctx, win=False, epw=None, osm=None, mea_d=None,
             mea_n=None):
    """Sets env variables for easy cli usage.

    Usage:
        $ eval (inv eval-env)
        $ lbtpyt swap.py osm epw mea_d mea_n

    Default values:
        osm = ./simops/run/in.osm
        osw = ./simops/run/workflow.osw
        epw = ./epw/a1.epw
        mea_d = ./mea
        mea_n = CreateTypicalDOEBuildingFromModel
        lbtpyt = /mnt/c/users/admin/ladybug_tools/python/python.exe
    """
    # Get own docstring  for help message
    # To many bugs, don't do this.
    # docstr = repr(eval_env.__doc__)

    # Get python path
    lbtpyt = path.join(LBTD, "python/python.exe")
    # Get default file paths
    epw1a = "USA_HI_Honolulu.Intl.AP.911820_TMY3"
    epw_fpath = f"{THERMD}/epw/{epw1a}/{epw1a}.epw"
    osm_fpath = f"{THERMD}/simops/run/in.osm"
    osw_fpath = f"{THERMD}/simops/run/workflow.osw"
    mea_dpath = f"{THERMD}/mea/CreateTypicalDOEBuildingFromModel"
    if win:
        paths = [lbtpyt, epw_fpath, osm_fpath, mea_dpath]
        paths = [ctx.run(f"wslpath -m {x}", hide=True) for x in paths]
        paths = [x.stdout.strip() for x in paths]
        lbtpyt, epw_fpath, osm_fpath, mea_dpath = paths

    # Make command to eval
    env_cmd = (
        f'epw="{epw_fpath}"\n'
        f'osm="{osm_fpath}"\n'
        f'osw="{osw_fpath}"\n'
        f'mea="{mea_dpath}"\n'
        f'lbtpyt="{lbtpyt}"\n'
    )

    # Print to stdout
    print(env_cmd)


