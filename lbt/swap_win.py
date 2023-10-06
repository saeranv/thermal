"""v0.0.1"""
from __future__ import print_function
import os
from sys import argv
import json
import openstudio as ops
# from ladybug_rhino.openstudio import load_osm, dump_osm, import_openstudio


def clean_path(path):
    """Converts to realpath, checks existence."""
    path_ = os.path.realpath(path)
    assert os.path.exists(path_), \
        f"Path does not exist: {path_}"
    return path_


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


def main(osw_fpath, osm_fpath, epw_fpath):
    """Main function."""

    # Make fpaths
    osm_fpath_swap = osm_fpath.replace(".osm", "_swap.osm")
    osw_fpath_swap = osw_fpath.replace(".osw", "_swap.osw")

    # Load OSM model, modify it
    osm_model = load_osm(osm_fpath)
    osm_model_swap = edit_spacetype(osm_model, verbose=False)

    # Modify OSW
    # Add the osm, epw file
    osw_dict_swap = load_osw(osw_fpath)
    osw_dict_swap["seed_file"] = osm_fpath_swap
    osw_dict_swap["weather_file"] = epw_fpath

    # Dump modified model into swap filepaths
    print("Dumping modified OSM to:", osm_fpath_swap)
    osm_fpath_swap = dump_osm(osm_model_swap, osm_fpath_swap)
    print("Dumping modified OSW to:", osw_fpath_swap)
    osw_fpath_swap = dump_osw(osw_dict_swap, osw_fpath_swap)

    return osm_fpath_swap, osw_fpath_swap


if __name__ == "__main__":

    # Version
    print("Swap v0.0.1")
    # Define inputs args
    paths = argv[1:]
    is_help = len(paths) == 0 or paths[0] in {'-h', '--help'}
    if len(paths) != 3 or is_help:

        print("Usage: python swap.py [osm] [epw] [mea]")

    else:

        # Get paths from args
        paths = [clean_path(p) for p in paths]
        _osw_fpath, _osm_fpath, _epw_fpath = paths

        _osm_swap, _osw_swap = \
            main(_osw_fpath, _osm_fpath, _epw_fpath)
        print(f"\n{_osm_swap}\n{_osw_swap}")

