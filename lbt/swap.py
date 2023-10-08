"""v0.0.1"""
from __future__ import print_function
import os
import typing as ty
from sys import argv
import json
import ntpath
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


def assert_path(pth):
    """Identity fn converts path to realpath, assert existence."""

    def _convert_os(pth):
        if os.name == 'nt':
            pth = pth.replace(os.sep, ntpath.sep)
            return pth.replace("/mnt/c", "C:")
        # else: # posix
        pth = pth.replace(ntpath.sep, os.sep)
        return pth.lower().replace("c:", "/mnt/c")

    pth = _convert_os(pth)
    if not path.exists(pth):
        raise FileExistsError(pth)
    return pth


def load_osm(_ops, _osm_fpath):
    _model = _ops.model.Model.load(_ops.toPath(_osm_fpath))
    return assert_init(_model).get()


def dump_osm(_ops, osm_model, osm_fpath):
    osm_model.save(_ops.toPath(osm_fpath), True)
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


def make_workflow(ops, model, osw_dict, osw_fpath):
    """Make workflow OSW from osm model from osw_dict."""

    # Set paths
    osm_fpath = osw_dict['seed_file']
    epw_fpath = osw_dict['weather_file']
    _mea_dpath = osw_dict['measure_paths'][0]
    _mea_dpath = assert_path(_mea_dpath)

    # Set paths
    workflow = model.workflowJSON()
    workflow.setSeedFile(ops.toPath(osm_fpath))
    workflow.setWeatherFile(ops.toPath(epw_fpath))
    mea_dpath, mea_name = path.split(_mea_dpath)
    # print(mea_dpath)
    # TODO: redundant?
    workflow.addFilePath(ops.toPath(mea_dpath))
    workflow.addMeasurePath(ops.toPath(mea_dpath))
    _chk_mea_dpath = workflow.findMeasure(mea_name)

    # print(mea_dpath)
    # TODO: set assert check if path exists
    # print(*dir(workflow), sep='\n')
    # Set measures
    workflow.saveAs(ops.toPath(osw_fpath))


def run(osw_fpath, osm_fpath, epw_fpath):

    import openstudio as ops
    # Define swap paths
    osm_fpath_swap = osm_fpath.replace(".osm", "_swap.osm")
    osw_fpath_swap = osw_fpath.replace(".osw", "_swap.osw")

    # Load OSM model, modify it
    osm_model_swap = load_osm(ops, osm_fpath)
    osm_model_swap = edit_spacetype(osm_model_swap, verbose=False)

    # Add the osm, epw file
    osw_dict = load_osw(osw_fpath)
    osw_dict["weather_file"] = epw_fpath
    osw_dict["seed_file"] = osm_fpath_swap

    # Dump rest of measures
    # print(osw_dict.keys())
    # args = osw_dict['args']

    # Modify OSW
    make_workflow(
        ops, osm_model_swap, osw_dict, osw_fpath_swap)
    del osm_model_swap


    # Dump OSM
    # print("Dumping modified OSM to:", osm_fpath_swap)
    # osm_fpath_swap = dump_osm(ops, osm_model_swap, osm_fpath_swap)
    # Dump OSW
    # print("Dumping modified OSW to:", osw_fpath_swap)
    # osw_fpath_swap = dump_osw(osw_dict_swap, osw_fpath_swap)
    return osm_fpath_swap, osw_fpath_swap

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
    _osw_fpath, _osm_fpath, _epw_fpath = paths

    try:
        osmswap_fpath, oswswap_fpath = \
            run(_osw_fpath, _osm_fpath, _epw_fpath)
    except Exception as err:
        for name in dir():
            if not name.startswith("_"):
                del globals()[name]
        # raise w/o arg means gets last exception and reraise it
        raise

    print(osmswap_fpath, oswswap_fpath, sep="\n")




