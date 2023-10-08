"""v0.0.1"""
from __future__ import print_function
import os
import typing as ty
from sys import argv
import json
import ntpath
import re
path = os.path
# from ladybug_rhino.openstudio import load_osm, dump_osm, import_openstudio


# TODO: fix the Hardcode edits
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


def match_phrase(query, phrases):
    """Given list of phrases, returns phrase most like query."""

    def _tkize(words):
        """Tokenizes words into tokens via regex.
        # [..] match char inside; [^..] not match char inside
        # \s all whitepace; \W all non-alphanum; x{n,} match >n reps of x
        """
        return re.sub(r'\s{1,}', '_', re.sub(r'[^\s\w]', '', words))

    # joint_len: how many words in overlap btwn query and phrase
    q, ps = query, phrases
    q_set = set(_tkize(q).split('_'))
    p_sets = [set(_tkize(p).split('_'))
              for p in ps]
    joints = [len(q_set.intersection(p_set))
              for p_set in p_sets]

    # Get phrase with highest joint (most matches) with query
    return ps[joints.index(max(joints))]


def edit_spacetype(osm_model, echo=False):
    """Changes the spacetype of spaces in model."""

    for spct in osm_model.getSpaceTypes():
        # Get std that matches spct name
        spct_name = spct.nameString()
        stdtag_key = match_phrase(spct_name, list(STDTAG_DICT.keys()))
        stdtag = STDTAG_DICT[stdtag_key]
        # Set the std from dict.
        spct.setStandardsTemplate(stdtag["standardsTemplate"])
        spct.setStandardsBuildingType(stdtag["standardsBuildingType"])
        spct.setStandardsSpaceType(stdtag["standardsSpaceType"])
        if echo:
            print(f'Defining spacetype `{stdtag_key}` for `{spct_name}`')
    return osm_model


def edit_workflow(ops, model, osw_dict, osw_fpath):
    """Make workflow OSW from osm model from osw_dict."""

    # Set paths
    osm_fpath = osw_dict['seed_file']
    epw_fpath = osw_dict['weather_file']
    mea_dpath = osw_dict['measure_paths'][0]
    mea_dpath = assert_path(mea_dpath)

    # Set seed, epw paths
    workflow = model.workflowJSON()
    workflow.setSeedFile(ops.toPath(osm_fpath))
    workflow.setWeatherFile(ops.toPath(epw_fpath))
    # Set measure path
    meadir_dpath, mea_name = path.split(mea_dpath)
    workflow.addMeasurePath(ops.toPath(meadir_dpath))
    # Check that measure path can be found
    mea_fpath = assert_init(workflow.findMeasure(mea_name)).get()

    # Set measures
    # measure = ops.BCLMeasure(mea_fpath)
    # args = measure.arguments()
    # print(*dir(workflow), sep='\n')
    # arg = args[2]
    # print(arg.name()); print(type(arg))
    # osw_dict['arguments']

    # measure.save()

    return workflow


def run(osw_fpath, osm_fpath, epw_fpath, echo):

    import openstudio as ops
    # Define swap paths
    osm_fpath_swap = osm_fpath.replace(".osm", "_swap.osm")
    osw_fpath_swap = osw_fpath.replace(".osw", "_swap.osw")

    # Load OSM model, modify it
    osm_model_swap = load_osm(ops, osm_fpath)
    osm_model_swap = edit_spacetype(osm_model_swap, echo=echo)

    # Load OSW dict, add the osm, epw file
    osw_dict = load_osw(osw_fpath)
    osw_dict["weather_file"] = epw_fpath
    osw_dict["seed_file"] = osm_fpath_swap

    # Dump rest of measures
    # print(osw_dict.keys())
    # args = osw_dict['args']

    # Modify OSW
    workflow = edit_workflow(ops, osm_model_swap, osw_dict, osw_fpath_swap)

    # del osm_model_swap

    # Dump OSM
    if echo:
        simdir = path.dirname(path.abspath(osm_fpath_swap))
        print(f"Saving modified OSW, OSM to {simdir}")
    osm_fpath_swap = dump_osm(ops, osm_model_swap, osm_fpath_swap)
    workflow.saveAs(ops.toPath(osw_fpath))
    return osm_fpath_swap, osw_fpath_swap

if __name__ == "__main__":

    # Version
    # Define inputs args
    print("Swap v0.0.2")
    paths, echo = argv[1:], True
    is_help = len(paths) < 3 or paths[0] in {'-h', '--help'}
    if is_help:
        print("Usage: python swap.py [osw] [osm] [epw]")
        exit(1)

    # Get paths from args, make swap fpaths
    paths = [assert_path(p) for p in paths]
    _osw_fpath, _osm_fpath, _epw_fpath = paths[:3]

    try:
        osmswap_fpath, oswswap_fpath = \
            run(_osw_fpath, _osm_fpath, _epw_fpath, echo=echo)
    except Exception as err:
        for name in dir():
            if name.startswith("_"):
                continue
            del globals()[name]
        # raise w/o arg means gets last exception and reraise it
        raise

    print(osmswap_fpath, oswswap_fpath, sep="\n")


