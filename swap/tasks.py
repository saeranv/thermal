from __future__ import annotations  # so we can use Path type
import os
from invoke import task
from dataclasses import dataclass
import functools as ft
# from io import StringIO
# from shlex import quote, split
path = os.path

LBT_DPATH = "/mnt/c/Users/admin/ladybug_tools"
THERM_DPATH = "/mnt/c/Users/admin/masterwin/thermal"
SIM_GH_DPATH = path.join(THERM_DPATH, "sim_/gh/rep_doe")
SIM_CLI_DPATH = path.join(THERM_DPATH, "sim_/cli/rep_doe")
lbt_python = path.join(LBT_DPATH, "python/python.exe")
epw_dpath = path.join(THERM_DPATH, "epw")


@dataclass(frozen=True)
class Path:
    """Path class for method chaining.

    We cache a attribute 'path' with functools, to act like a setter to
    avoid conflict between frozen=True and __post_init__ method
    """
    _path: str

    @ft.cached_property
    def path(self) -> str:
        return os.path.abspath(self._path)

    @ft.cache
    def relpath(self, refdir=".") -> str:
        refdir = Path(refdir).path
        return os.path.relpath(self.path, refdir)

    def __repr__(self) -> str:
        return self.path

    @classmethod
    def init_join(cls, *args) -> Path:
        return cls(os.path.join(*args))

    def join(self, *args) -> Path:
        return Path(os.path.join(self.path, *args))

    def parent(self) -> Path:
        """Returns parent dpath. Equivalent to os.path.dirname."""
        return Path(os.path.dirname(self.path))

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def chk(self, path_name="Path") -> Path:
        if not self.exists():
            err_msg = f"{path_name} {self.path} doesn't exist."
            raise FileNotFoundError(err_msg)
        return self


@task
def echo_test(ctx, dry=False, echo=False):
    """Echo test"""
    _ = ctx.run('echo "hello"', dry=dry, echo=echo)


@task
def list(ctx):
    """invoke --collections $thermd/swap/tasks --list."""

    tasks_fpath = Path.init_join(THERM_DPATH, "swap").path
    with ctx.cd(tasks_fpath):
        _ = ctx.run("invoke --list")


@task
def cp_sim(ctx, cz="1a"):
    """Copies simulation dir for in_swap.osm.

    Copies hb osm model from 'sim_/gh/' dir to 'sim_/cli/' dir:
        '/thermal/sim_/gh/rep_doe/rep_doe_{cz}/'
        '/thermal/sim_/cli/rep_doe/rep_doe_{cz}/'
    """
    model_name = "rep_doe_" + cz.lower()
    sim_gh = Path.init_join(SIM_GH_DPATH, model_name).chk()
    sim_cli = Path.init_join(SIM_CLI_DPATH, model_name)

    # If intermediate dir doesn't exist, make it
    if not sim_cli.parent().exists():
        cmd = f"mkdir -p {sim_cli.parent().relpath()}"
        _ = ctx.run(cmd, hide=True)

    # Delete if cli dir exists
    if sim_cli.exists():
        cmd = f"rm -rf {sim_cli.path}"
        _ = ctx.run(cmd, hide=True)

    # Copy from gh dir
    cmd = f"cp -r {sim_gh.relpath()} {sim_cli.relpath()}"
    _ = ctx.run(cmd, hide=True)

    # Clean up old swap files if exists
    rm_paths = ["in_swap.osm", "workflow_swap.osw"]
    for p in rm_paths:
        try:
            fpath = sim_cli.join("openstudio", "run", p).chk()
            _ = ctx.run(f"rm -rf {fpath.path}", hide=True)
        except FileNotFoundError:
            pass


@task
def run_swap(ctx, cz='1a'):
    """Creates in_swap.osm, workflow_swap.osw in sim_cli dir.

    $ lbt_python swap.py run/workflow.osw run/in.osm epw/1a.epw
    """
    model_name = "rep_doe_" + cz.lower()
    sim_cli = Path.init_join(SIM_CLI_DPATH, model_name, "openstudio/run").chk()

    with ctx.cd(os.path.curdir):
        # Get path strings rel to curdir
        lbtpyt = Path(lbt_python).relpath()
        swap = Path.init_join(THERM_DPATH, "swap/swap.py").chk().relpath()
        osm = sim_cli.join("in.osm").chk().path
        osw = sim_cli.join("workflow.osw").chk().path
        epw = Path.init_join(epw_dpath, cz.lower() + ".epw").chk().path
        # Run command
        cmd = f"{lbtpyt} {swap} {osw} {osm} {epw}"
        r = ctx.run(cmd, hide=False)
        # print(r.stdout)


@task
def run_sim(ctx, cz='1a'):
    """openstudio run -w workflow_swap.osw"""
    model_name = "rep_doe_" + cz.lower()
    sim_cli = Path.init_join(SIM_CLI_DPATH, model_name, "openstudio/run").chk()

    with ctx.cd(os.path.curdir):
        osw = sim_cli.join("workflow_swap.osw").chk().relpath()
        print(osw)
        cmd = f"openstudio run -w {osw} &"
        _ = ctx.run(cmd, hide=False)
        # print(r.stdout)


def _null():
    pass
