"""Unit tests for tasks cli."""

import os
import pytest
import swap.tasks as tasks
Path = tasks.Path


def test_path_init():
    p_str = "/home/thermal"
    p = Path(p_str)

    # Test basics
    assert isinstance(p.path, str)
    assert p.path == p_str, p.path


def test_path_join():

    p_str = "/home/thermal"
    p = Path(p_str)

    # Test basic join
    p = p.join("sim_").join("gh")
    assert p.path == p_str + "/sim_/gh"

    # Test complex join
    p_str = "/home"
    p = Path(p_str).join("thermal", "sim", "gh")
    assert p.path == "/home/thermal/sim/gh"


def test_path_mutation():
    # Test no mutation exists
    p = Path("/thermal")
    p1 = p.join("cad")
    p2 = p.join("epw")

    assert p1.path == "/thermal/cad"
    assert p2.path == "/thermal/epw"


def test_path_exists():

    # Check path that doesn't exists
    p_str = "/home/thermal/fake/path"
    p = Path(p_str)
    assert p.exists() is False, p.exists()
    with pytest.raises(FileNotFoundError) as err:
        p.chk("Custom path")
    err_msg, _err_msg = str(err.value), f"Custom path {p_str} doesn't exist."
    assert err_msg == _err_msg

    # Check path that exists
    p_str = os.path.dirname(__file__)
    p = Path(p_str)
    assert p.exists() is True, p.exists()
    assert p.chk().path == p_str, p.path


def test_path_relpath():

    abspath_str = "/thermal/sim_/gh/null.osm"

    # Test path 1 folder down
    curpath_str = "/thermal/swap"
    relpath_str = "../sim_/gh/null.osm"
    _relpath_str = Path(abspath_str).relpath(curpath_str)
    assert relpath_str == _relpath_str

    # Test path 1 folders up
    curpath_str = "/thermal"
    relpath_str = "sim_/gh/null.osm"
    _relpath_str = Path(abspath_str).relpath(curpath_str)
    assert relpath_str == _relpath_str

    # Test default of '.' folders up
    abspath_str = os.path.join(os.path.dirname(__file__), "../sim_/null.osm")
    # cwd is 'thermal/tests/'
    relpath_str = "sim_/null.osm"
    _relpath_str = Path(abspath_str).relpath()
    assert relpath_str == _relpath_str, abspath_str






