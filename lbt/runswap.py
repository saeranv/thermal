"""Run swap.py from subprocess on LBT python."""
from __future__ import print_function
import sys
import os
from subprocess import Popen, PIPE, STDOUT
from honeybee.config import folders as hbconfig
path = os.path

IS_TTY = sys.stdin.isatty() or len(sys.argv) > 1

if IS_TTY:
    _osm, _epw, _mea = sys.argv[1:]
    code_lns = []
else:
    ghenv.Component.Name = 'Swap OSM'
    ghenv.Component.NickName = 'SwapOSM'
    code_lns = ghenv.Component.Code.split('\n')


pytexe = hbconfig.python_exe_path
# PYTLIB = hbconfig.python_package_path
lbt_script_path = hbconfig.python_scripts_path
swap_path = path.join(lbt_script_path, "swap.py")

lbt_scripts = os.listdir(lbt_script_path)


if not path.exists(swap_path):
    idx = 0
    for i, ln in enumerate(code_lns):
        if not ln.startswith('# SWAP.PY'):
            continue
        idx = i + 1
        break

    code_lns = code_lns[:idx]
    with open(swap_path, 'w') as f:
        f.writelines(code_lns)

if not path.exists(swap_path):
    raise ValueError("Can't find swap.py in {}".format(lbt_script_path))


run_ = False


def run_subproc(cmds):
    """Run subprocess for list of commands (cmds).

    Returns combined stdout, stderr str, and process exit code.
    """

    p = Popen(cmds, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    _stdout, _ = p.communicate()
    return _stdout.decode('utf-8'), p.returncode


if run_:

    # Get swap fpath
    epw_dir = path.dirname(_epw)
    swap_fpath = path.realpath(
        path.join(epw_dir, "..", "..", "lbt", "swap_win.py")
    )

    # Run swap
    swap_cmds = [pytexe, swap_fpath, _osm, _epw, _mea]
    stdout, exitcode = run_subproc(swap_cmds)

    if exitcode != 0:
        msg = ("Swap failed with exit code: {}\n".format(exitcode) + \
               "Command:\n{}\n".format(' '.join(swap_cmds).strip()) + \
               "Stdout|Stderr:\n{}\n".format(stdout))
        raise ValueError(msg)

    print(stdout)
    _osm_swap = _osm


    # cmds = [folders.openstudio_exe, '-I', folders.honeybee_openstudio_gem_path,
    #         'run', '-w', osw_json]
    # if measures_only:
    #     cmds.append('-m')


# SWAP.PY
# from __future__ import print_function
# import os
# import sys
# import json
# pp = lambda *x: print(x, sep="\n")
# IS_TTY = sys.stdin.isatty() or len(sys.argv) > 1


# import openstudio as ops
# def load_osm(osm_fpath):
#     model = ops.model.Model.load(ops.toPath(osm_fpath))
#     assert model.is_initialized()
#     return model.get()

# def dump_osm(osm_model, osm_fpath):
#     osm_model.save(ops.toPath(osm_fpath), True)
#     return osm_fpath

# # from ladybug_rhino.openstudio import load_osm, dump_osm, import_openstudio

# if IS_TTY:
#     # Define inputs args
#     run_, args = True, sys.argv[1:]
#     is_help = len(args) == 0 or args[0] in {'-h', '--help'}
#     if len(args) != 3 or is_help:
#         print("Usage: python swap.py [--osm] <osm_fpath>")
#         exit()
#     else:
#         _osm_fpath, _epw_fpath, _mea_dpath = args[0], args[1], args[2]
# else:

#     try:
#         _osm_fpath, _epw_fpath, _mea_dpath = _osm, _epw, _mea
#     except NameError:
#         raise Exception("Can't find _osm, or _osw _epw, _mea. Are you in GH?")


# def load_osw(osw_fpath):
#     """Load an OpenStudio Workflow file."""
#     with open(osw_fpath, 'r') as f:
#         osw_dict = json.load(f)
#     return osw_dict


# def dump_osw(osw_dict, osw_fpath):
#     """Dump an OpenStudio Workflow file."""
#     with open(osw_fpath, 'w') as f:
#         _ = json.dump(osw_dict, f, indent=4)

#     return osw_fpath


# def edit_spacetype(osm_model, verbose=False):
#     """Changes the spacetype of spaces in model."""

#     # Hardcode edits
#     STDTAG_DICT = {
#         "Office WholeBuilding - Md Office": {
#             "standardsTemplate": "90.1-2016",
#             "standardsBuildingType": "Office",
#             "standardsSpaceType": "WholeBuilding - Md Office"
#         },
#         "Plenum": {
#             "standardsTemplate": "90.1-2016",
#             "standardsBuildingType": "MediumOffice",
#             "standardsSpaceType": "Plenum"
#         }
#     }

#     # Get all spacetypes in model
#     spacetypes = list(osm_model.getSpaceTypes())
#     for i, spct in enumerate(spacetypes):
#         stdtag = STDTAG_DICT[spct.nameString()]
#         spct.setStandardsTemplate(
#             stdtag["standardsTemplate"])
#         spct.setStandardsBuildingType(
#             stdtag["standardsBuildingType"])
#         spct.setStandardsSpaceType(
#             stdtag["standardsSpaceType"])
#         if verbose:
#             print()
#             print(i, spct.nameString())
#             print(i, spct.standardsTemplate())
#             print(i, spct.standardsBuildingType())
#             print(i, spct.standardsSpaceType())

#     return osm_model

# def add_mea(epw_fpath, mea_dpath, mea_name):
#     """Adds a measure to the osw file."""

#     osw_dict = {}

#     # Add the seed file
#     osw_dict["seed_file"] = "./in.osm"

#     # Add weather file
#     osw_dict["weather_file"] = epw_fpath

#     # Add measure path
#     osw_dict["measure_paths"] = [mea_dpath]

#     # Add measure steps
#     osw_dict["steps"] = [
#       {
#          "arguments" :
#          {
#             "add_constructions" : False,
#             "add_elevators" : False,
#             "add_exhaust" : False,
#             "add_hvac" : True,
#             "add_internal_mass" : True,
#             "add_refrigeration" : False,
#             "add_space_type_loads" : True,
#             "add_swh" : True,
#             "add_thermostat" : True,
#             "enable_dst" : False,
#             "system_type" : "PTAC with gas boiler",
#             "template" : "90.1-2016",
#             "use_upstream_args" : False
#          },
#          "description" : "Takes a model with space and stub space types, and assigns constructions, schedules, internal loads, hvac, and other loads such as exterior lights and service water heating.",
#          "measure_dir_name" : mea_name,
#          "modeler_description" : "It is important that the template argument chosen for this measure is in line with the buding types for the stub space types of the model passed in.",
#          "name" : "Create Typical DOE Building from Model"
#       }
#     ]

#     return osw_dict


# def main(osm_fpath, epw_fpath, mea_dpath, mea_name):
#     """Main function."""

#     # Load OSM model
#     osm_model = load_osm(osm_fpath)

#     # Create copy of original OSM
#     osm_fpath_cp = osm_fpath.replace(".osm", "_cp.osm")
#     osm_fpath_cp = dump_osm(osm_model, osm_fpath_cp)

#     # Modify OSM
#     osm_model = edit_spacetype(osm_model, verbose=False)

#     # Load OSW dict
#     # osw_dict = load_osw(osw_fpath)
#     osw_fpath = os.path.join(
#         os.path.dirname(osm_fpath), "workflow.osw")

#     # Modify OSW
#     osw_dict = add_mea(epw_fpath, mea_dpath, mea_name)

#     # Dump modified model into original filepath
#     print("Save OSM: {}".format(os.path.relpath(osm_fpath)))
#     osm_fpath_swap = dump_osm(osm_model, osm_fpath)
#     print("Save OSW: {}".format(os.path.relpath(osw_fpath)))
#     _ = dump_osw(osw_dict, osw_fpath)

#     # # For testing in gitbash
#     # osw_fpath_dos = osw_fpath.replace(".osw", "_dos.osw")
#     # osw_dict_dos = add_mea(
#     #     "C:/users/admin/masterwin/thermal/epw/" + epw_fpath.split("/epw/")[-1],
#     #     "C:/users/admin/masterwin/thermal/mea")
#     # print(f"Save OSW dos: {os.path.relpath(osw_fpath_dos)}")
#     # _ = dump_osw(osw_dict_dos, osw_fpath_dos)

#     return osm_fpath_swap


# if run_:
#     # "openstudio -w wea_fpath -i eplus.idd -x"
#     try:
#         # Clean filepath
#         _osm_fpath = os.path.realpath(_osm_fpath)
#         _epw_fpath = os.path.realpath(_epw_fpath)
#         _mea_dpath = os.path.realpath(_mea_dpath)
#         _mea_dpath, _mea_name = os.path.split(_mea_dpath)

#         assert os.path.exists(_osm_fpath), \
#                 "Error, OSM file not exist, got {}".format(_osm_fpath)
#         assert os.path.exists(_epw_fpath), \
#                 "Error, EPW file not exist, got {}".format(_epw_fpath)
#         assert os.path.exists(_mea_dpath), \
#                 "Error, Measure dir not exist, got {}".format(_mea_dpath)

#         _osm_swap = main(_osm_fpath, _epw_fpath, _mea_dpath, _mea_name)
#     except Exception as err:
#         print("Error: ", err)
#         # for error, tb in zip(log_osw.errors, log_osw.error_tracebacks):
#         # print(tb)
#         # errors.append(error)
#         if IS_TTY:
#             import traceback
#             traceback.print_tb(err.__traceback__)
