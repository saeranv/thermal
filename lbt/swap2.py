"""v0.0.1"""
from __future__ import print_function
import os
import typing as ty
from sys import argv
import json
import openstudio as ops
path = os.path
# from ladybug_rhino.openstudio import load_osm, dump_osm, import_openstudio


class InitError(Exception):
    """OpenStudio initialization errors."""
    def __init__(self, mobj):
        self.msg = f"Init error for {mobj}:\n"


def assert_init(mobj):
    """Identity fn that validates optional model parameters."""
    if not mobj.is_initialized():
        raise InitError(mobj)
    return mobj


def assert_path(path_str):
    """Identity fn converts path to realpath, assert existence."""
    pth = path.realpath(path_str)
    if not path.exists(pth):
        raise FileExistsError(pth)
    return pth


def load_osm(_osm_fpath):
    model = ops.model.Model.load(ops.toPath(_osm_fpath))
    return assert_init(model).get()


def dump_osm(osm_model, osm_fpath):
    osm_model.save(ops.toPath(osm_fpath), True)
    return osm_fpath


def load_osw(osw_fpath):
    """Load an OpenStudio Workflow file."""
    with open(osw_fpath, 'r') as f:
        osw_dict = json.load(f)
    return osw_dict


def dump_osw(osw_dict, osw_fpath):
    """Dump an OpenStudio Workflow file."""
    with open(osw_fpath, 'w') as f:
        _ = json.dump(osw_dict, f, indent=4)

    return osw_fpath


def edit_spacetype(osm_model, verbose=False):
    """Changes the spacetype of spaces in model."""

    # Hardcode edits
    STDTAG_DICT = {
        "Office WholeBuilding - Md Office": {
            "standardsTemplate": "90.1-2016",
            "standardsBuildingType": "Office",
            "standardsSpaceType": "WholeBuilding - Md Office"
        },
        "Plenum": {
            "standardsTemplate": "90.1-2016",
            "standardsBuildingType": "MediumOffice",
            "standardsSpaceType": "Plenum"
        }
    }

    # Get all spacetypes in model
    spacetypes = list(osm_model.getSpaceTypes())
    for i, spct in enumerate(spacetypes):
        stdtag = STDTAG_DICT[spct.nameString()]
        spct.setStandardsTemplate(
            stdtag["standardsTemplate"])
        spct.setStandardsBuildingType(
            stdtag["standardsBuildingType"])
        spct.setStandardsSpaceType(
            stdtag["standardsSpaceType"])
        if verbose:
            print()
            print(i, spct.nameString())
            print(i, spct.standardsTemplate())
            print(i, spct.standardsBuildingType())
            print(i, spct.standardsSpaceType())

    return osm_model

def ppdir(mobj, qstr="", *args, **kwargs):
    """Print model objects mobj methods given query qstr.

    This will recursively search parent of mobj for query.
    """

    def _cond_fn(qstr:str)->ty.Callable:
        """Bool indicating does target x str matche query q."""
        q = qstr.lower()
        return lambda x: (q in x.lower()) and (x.lower()[:2] != "__")

    def _ppdir(mobj, cond_fn, str_arr):
        """Recursively get method str from model object mobj."""
        mo, fn, sa = mobj, cond_fn, str_arr
        sa += [s for s in dir(mo) if fn(s)]

        # Check parent, and recurse if possible
        if hasattr(mo, 'parent') and mo.parent().is_initialized():
            mop = mo.parent().get()
            return _ppdir(mop, fn, sa)
        # Else, return string array
        return sa

    result = _ppdir(mobj, _cond_fn(qstr), [])
    print(*result, *args, **kwargs)


def make_workflow(model, osw_dict):
    """Make workflow OSW from osm model from osw_dict."""

    osm_fpath = osw_dict['seed_file']
    epw_fpath = osw_dict['weather_file']
    _mea_dpath = osw_dict['measure_paths'][0]

    workflow = model.workflowJSON()
    # ppdir(workflow, '', sep='\n')

    # Set paths
    workflow.setSeedFile(ops.toPath(osm_fpath))
    workflow.setWeatherFile(ops.toPath(epw_fpath))

    # Set directory ops will search for measures
    # TODO: fix this in swapgh?
    # mea_parent_dpath = path.dirname(_mea_dpath)
    from pathlib import PureWindowsPath, PurePosixPath
    import ntpath
    # print(_mea_dpath)
    mea_dpath = PureWindowsPath(_mea_dpath).as_posix()
    mea_dpath_ = _mea_dpath.replace(os.sep, ntpath.sep)
    print(os.sep, ntpath.sep)
    print(mea_dpath_)
    mea_parent_dpath = path.dirname(mea_dpath)
    mea_parent_dpath_ = path.dirname(mea_dpath_)
    # workflow.addMeasurePath(ops.toPath(mea_dpath))
    print('parent', mea_parent_dpath)
    print('parent', mea_parent_dpath_)

    # print('name', mea_name)
    # Set measures


if __name__ == "__main__":

    # Version
    print("Swap v0.0.1")
    # Define inputs args
    paths = argv[1:]
    is_help = len(paths) == 0 or paths[0] in {'-h', '--help'}
    if len(paths) != 3 or is_help:

        print("Usage: python swap.py [osw] [osm] [epw]")
        exit(1)

    # Get paths from args, make swap fpaths
    paths = [assert_path(p) for p in paths]
    osw_fpath, osm_fpath, epw_fpath = paths
    osm_fpath_swap = osm_fpath.replace(".osm", "_swap.osm")
    osw_fpath_swap = osw_fpath.replace(".osw", "_swap.osw")

    try:
        # Load OSM model, modify it
        __osm_model = load_osm(osm_fpath)
        # osm_model_swap = edit_spacetype(osm_model, verbose=False)
        # print("Dumping modified OSM to:", osm_fpath_swap)
        # osm_fpath_swap = dump_osm(osm_model_swap, osm_fpath_swap)
        # Modify OSW
        # Add the osm, epw file
        # osw_dict = load_osw(osw_fpath)
        # osw_dict["weather_file"] = epw_fpath
        # osw_dict["seed_file"] = osm_fpath_swap
        #osw_dict_swap = make_workflow(osm_model_swap, osw_dict)
        # print("Dumping modified OSW to:", osw_fpath_swap)
        # osw_fpath_swap = dump_osw(osw_dict_swap, osw_fpath_swap)
    except Exception as err:
        # raise w/o arg means gets last exception and reraise it
        raise

    # print(osm_fpath_swap, osw_fpath_swap, sep="\n")




