"""v0.0.1"""
from __future__ import print_function
import os
import sys
import json
import openstudio as ops
# from ladybug_rhino.openstudio import load_osm, dump_osm, import_openstudio
IS_TTY = sys.stdin.isatty() or len(sys.argv) > 1


if IS_TTY:
    # Define inputs args
    run_, args = True, sys.argv[1:]
    is_help = len(args) == 0 or args[0] in {'-h', '--help'}
    if len(args) != 3 or is_help:
        print("Usage: python swap.py [--osm] <osm_fpath>")
        exit()
    else:
        _osm_fpath, _epw_fpath, _mea_dpath = args[0], args[1], args[2]
else:

    try:
        _osm_fpath, _epw_fpath, _mea_dpath = _osm, _epw, _mea
    except NameError:
        raise Exception("Can't find _osm, or _osw _epw, _mea. Are you in GH?")


def load_osm(osm_fpath):
    model = ops.model.Model.load(ops.toPath(osm_fpath))
    assert model.is_initialized()
    return model.get()


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

def add_measure(osw_dict, osm_fpath, epw_fpath, mea_dpath, mea_name):
    """Adds a measure to the osw file."""

    # Add the seed file
    osw_dict["seed_file"] = osm_fpath

    # Add weather file
    osw_dict["weather_file"] = epw_fpath

    # Add measure path
    osw_dict["measure_paths"] = [mea_dpath]

    # Add measure steps
    osw_dict["steps"] = [
      {
         "arguments" :
         {
            "add_constructions" : False,
            "add_elevators" : False,
            "add_exhaust" : False,
            "add_hvac" : True,
            "add_internal_mass" : True,
            "add_refrigeration" : False,
            "add_space_type_loads" : True,
            "add_swh" : True,
            "add_thermostat" : True,
            "enable_dst" : False,
            "system_type" : "PTAC with gas boiler",
            "template" : "90.1-2016",
            "use_upstream_args" : False
         },
         "description" : "Takes a model with space and stub space types, and assigns constructions, schedules, internal loads, hvac, and other loads such as exterior lights and service water heating.",
         "measure_dir_name" : mea_name,
         "modeler_description" : "It is important that the template argument chosen for this measure is in line with the buding types for the stub space types of the model passed in.",
         "name" : "Create Typical DOE Building from Model"
      }
    ]

    return osw_dict


def main(osm_fpath, epw_fpath, mea_dpath, mea_name):
    """Main function."""

    # Make fpaths
    run_dpath = os.path.dirname(osm_fpath)
    osm_fpath_swap = osm_fpath.replace(".osm", "_swap.osm")
    osw_fpath = os.path.join(run_dpath, "workflow.osw")
    osw_fpath_swap = osw_fpath.replace(".osw", "_swap.osw")

    # Load OSM model, modify it
    osm_model = load_osm(osm_fpath)
    osm_model_swap = edit_spacetype(osm_model, verbose=False)

    # Modify OSW
    osw_dict = load_osw(osw_fpath)
    osw_dict_swap = add_measure(
        osw_dict, osm_fpath, epw_fpath, mea_dpath, mea_name)

    # Dump modified model into swap filepaths
    print(f"Save OSM: {osm_fpath_swap}")
    osm_fpath_swap = dump_osm(osm_model_swap, osm_fpath_swap)
    print("Save OSW: {osw_fpath_swap}")
    _ = dump_osw(osw_dict_swap, osw_fpath_swap)

    return osm_fpath_swap


if run_:
    # "openstudio -w wea_fpath -i eplus.idd -x"
    try:
        # Clean filepath
        _osm_fpath = os.path.realpath(_osm_fpath)
        _epw_fpath = os.path.realpath(_epw_fpath)
        _mea_dpath = os.path.realpath(_mea_dpath)
        _mea_dpath, _mea_name = os.path.split(_mea_dpath)

        assert os.path.exists(_osm_fpath), \
                "Error, OSM file not exist, got {}".format(_osm_fpath)
        assert os.path.exists(_epw_fpath), \
                "Error, EPW file not exist, got {}".format(_epw_fpath)
        assert os.path.exists(_mea_dpath), \
                "Error, Measure dir not exist, got {}".format(_mea_dpath)

        _osm_swap = main(_osm_fpath, _epw_fpath, _mea_dpath, _mea_name)
    except Exception as err:
        print("Error: ", err)
        # for error, tb in zip(log_osw.errors, log_osw.error_tracebacks):
        # print(tb)
        # errors.append(error)
        if IS_TTY:
            import traceback
            traceback.print_tb(err.__traceback__)



