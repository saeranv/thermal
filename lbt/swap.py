from __future__ import annotations  # so we can use list, dict for typing
import typing as typ
from collections.abc import Sequence  # typ.Sequence deprecated
import os
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


def tokenize(words: str) -> str:
    r"""Tokenizes phrases into tokens w/ sep='_' via regex.

    _tkize("Office Medium - building") ->"office_medium_building"

    Regex:
        \s{1,}: match >1 white spaces, replace w/ '_'
           \s: all whitepace;
           x{n,}: match >n reps of x
        [^\s\w]: match chars not white space | non-alphanum
            [..] match char inside; [^..] not match char inside
            \w all non-alphanum;
    """
    return (
        re.sub(r'\s{1,}', '_',
               re.sub(r'[^\s\w]', '', words))
    ).lower()


def match_phrase(query: str, phrases: Sequence[str]) -> str:
    """Given query, list of phrases, returns phrase most like query."""

    # joints: how many words in overlap btwn query and phrase
    q, ps = query, phrases
    q_set = set(tokenize(q).split('_'))
    p_sets = [set(tokenize(p).split('_'))
              for p in ps]
    joints = [len(q_set.intersection(p_set))
              for p_set in p_sets]

    # Get phrase with highest joint (most matches) with query
    return ps[joints.index(max(joints))]


def add_spacetype_std(osm_model, echo=True):
    """Changes the spacetype of spaces in model."""

    print("## Add std tags")
    dictkeys = list(STDTAG_DICT.keys())
    spcts = osm_model.getSpaceTypes()
    spcts_id = [spct.nameString() for spct in spcts]
    
    print(" - Matching: ", spcts_id, ' to ', dictkeys)
    spcts_std = [match_phrase(x, dictkeys) for x in spcts_id]
    zipped = zip(spcts, spcts_id, spcts_std)

    for spct, spct_id, spct_std in zipped:
        # Get std that matches spct name
        stdtag = STDTAG_DICT[spct_std]
        # Set the std from dict.
        spct.setStandardsTemplate(stdtag["standardsTemplate"])
        spct.setStandardsBuildingType(stdtag["standardsBuildingType"])
        spct.setStandardsSpaceType(stdtag["standardsSpaceType"])

    if echo:
        print(f"Found {len(spcts)} spacetypes.")
        _ = [print(f'Assigned {spct_id} -> `{spct_std}`')
             for spct_id, spct_std in zipped]
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

    # Set measures
    workflow.saveAs(ops.toPath(osw_fpath))

    # Now edit the json
    osw_dict_swap = load_osw(osw_fpath)
    _mea_step = {
        "measure_dir_name": mea_name,
        "arguments": osw_dict["arguments"]
    }
    osw_dict_swap["steps"] = [_mea_step]
    osw_fpath = dump_osw(osw_dict_swap, osw_fpath)

    return osw_fpath


def swap_modelobj(ref_modelobj, act_osm):
    """Insert ref_modelobj into act_osm, return relevant act_modelobj.

    Note: ref_modelobj must be initialized.
    """
    # Create ref-component from ref-modelobj
    ref_comp = ref_modelobj.createComponent()
    # Insert ref-component into act-model
    act_comp_data = act_osm.insertComponent(ref_comp)
    # Get act-modelobj from act-component
    act_modelobj = assert_init(act_comp_data).get().primaryComponentObject()

    return act_modelobj


def swap_design_days(act_osm, ref_osm):
    """Swap sizing period."""

    def diff(dds, mod_name):
        print(" - {} has {} DesignDay objects.".format(mod_name, len(dds)))
        #_ = [print("  " + dd.nameString()) for dd in dds]

    ref_dd = list(ref_osm.getDesignDays())
    act_dd = list(act_osm.getDesignDays())

    print("## Swap DesignDays:")
    diff(ref_dd, 'Ref'); diff(act_dd, 'Act')

    # Remove act_osm design days, add ref_osm design days.
    _ = [dd.remove() for dd in act_dd]
    _ = [swap_modelobj(dd, act_osm) for dd in ref_dd]

    return act_osm


def swap_spc_equip(act_osm, ref_osm, verbose=False):
    """Remove spc equip from ref_osm."""

    print("## Swap Elevator")
    # Get all spaces, and sort them
    ref_spcs, act_spcs = ref_osm.getSpaces(), act_osm.getSpaces()
    ref_spcs = [x for x in ref_spcs if "Core_bottom" in x.nameString()]
    act_spcs = [x for x in act_spcs if "Core_bottom" in x.nameString()]

    ## Loop through spaces and remove/then assign eqiuip_defn to space
    for ref_spc, act_spc in zip(ref_spcs, act_spcs):
        # TODO: check if parent spacetype or space and check accordingly
        #for act_equip in act_spc.electricEquipment():
        #    parent = assert_init(act_equip.parent()).get()
        #    print(type(parent.iddObjectType()))
        for ref_equip in ref_spc.electricEquipment():
            # TODO: add the diff-check which adds unique_ref_equip
            # i.e. unique_ref_equip = ref_equip not in (act_equip AND ref_equip)
            if "elevator" not in ref_equip.nameString().lower():
                continue
            act_equip = swap_modelobj(ref_equip, act_osm)
            is_parent_set = act_equip.setParent(act_spc)
            assert is_parent_set, \
                "Error! setParent fail for {}".format(act_equip)
            print(' - Added equip: {} to space: {}'.format(
                act_equip.nameString(), act_spc.nameString()))

    return act_osm

def swap_airloops(swp_osm, ref_osm):
    """Change OA system properties.
    
    Modifies OS:AirLoopHVAC object, which lists air loop 
    for all zones per storey.

    1. Add availability schedule to OA loop 
    2. Modify 'System Outdoor Air Method' to ZoneSum 
       in OA:Controller.
    3. Enable economizer by defining 
       'Economizer Control Type' as 'DifferentialDryBulb' 
       in OS:Controller:OutdoorAir.
    4. Attach return plenum. 
    """
    
    def _get_oa_ctrl(_airloop):
        """Get OA controller given AirloopHVAC obj."""
        oa_sys = assert_init(
            _airloop.airLoopHVACOutdoorAirSystem()
        ).get()
        return oa_sys.getControllerOutdoorAir()
        
    ref_airloop = ref_osm.getAirLoopHVACs()[0] 
    
    # Add Economizer to mechanical ventilation controller
    print("## Swap airloop economizer") 
    # Airloop -> OASystem -> OA Controller -> Economizer
    # Assume economizer same for all loops
    ref_oa_ctrl = _get_oa_ctrl(ref_airloop)
    ref_econ_type = ref_oa_ctrl.getEconomizerControlType()
    for airloop in swp_osm.getAirLoopHVACs():
        oa_ctrl = _get_oa_ctrl(airloop)
        econ_type = oa_ctrl.getEconomizerControlType()
        oa_ctrl.setEconomizerControlType(ref_econ_type)
        print(f" - {airloop.nameString()}: "
              f"rep econ={econ_type}; ref econ={ref_econ_type}.")
    
    # Swap ScheduleRuleset in 'Availability Schedule'
    print("## Swap airloop HVAC availability schedule")
    ref_sched = ref_airloop.availabilitySchedule()
    ref_sched_clone = assert_init(
        ref_sched.clone(swp_osm).to_ScheduleRuleset()
    ).get()
    for swp_airloop in swp_osm.getAirLoopHVACs():
        swp_sched = swp_airloop.availabilitySchedule()
        print(f" - {swp_airloop.nameString()}: "
              f"rep: {swp_sched.nameString()}; "
              f"ref: {ref_sched.nameString()}")
        swp_airloop.setAvailabilitySchedule(
            ref_sched_clone)
            
    
    # 'System Outdoor Air Method' to ZoneSum 
    # in Controller:MechanicalVentilation
    
    # ppdir(ref_osm, 'mechanicalventilation')
    
    
    return swp_osm


def run(osw_fpath, osm_fpath, ref_osm_fpath, epw_fpath, echo):

    import openstudio as ops
    # Define swap paths
    osm_fpath_swap = osm_fpath.replace(".osm", "_swap.osm")
    osw_fpath_swap = osw_fpath.replace(".osw", "_swap.osw")

    # Load OSM models
    osm_model_swap = load_osm(ops, osm_fpath)
    osm_model_ref = load_osm(ops, ref_osm_fpath)

    # Swap airloop sched
    osm_model_swap = swap_airloops(osm_model_swap, osm_model_ref)
    # Swap DDY
    osm_model_swap = swap_design_days(osm_model_swap, osm_model_ref)
    # Swap equip
    osm_model_swap = swap_spc_equip(osm_model_swap, osm_model_ref)    
    # Load, modify OSW
    osm_model_swap = add_spacetype_std(osm_model_swap, echo=echo)
    osw_dict = load_osw(osw_fpath)
    osw_dict["weather_file"] = epw_fpath
    osw_dict["seed_file"] = osm_fpath_swap
    osw_fpath_swap = edit_workflow(ops, osm_model_swap, osw_dict, osw_fpath_swap)

    # Dump OSM
    if echo:
        simdir = path.dirname(path.abspath(osm_fpath_swap))
        print(f"Saving modified OSW, OSM to {simdir}")
    osm_fpath_swap = dump_osm(ops, osm_model_swap, osm_fpath_swap)
    return osm_fpath_swap, osw_fpath_swap


if __name__ == "__main__":

    # Version
    # Define inputs args
    paths, echo = argv[1:], False
    is_help = len(paths) < 3 or paths[0] in {'-h', '--help'}
    if is_help:
        print("Swap v3.0.0 usage: python swap.py [osw] [osm] [epw]")
        exit(0)

    # Get paths from args, make swap fpaths
    paths = [assert_path(p) for p in paths]
    _osw_fpath, _osm_fpath, _ref_osm_fpath, _epw_fpath = paths[:4]

    try:
        osmswap_fpath, oswswap_fpath = \
            run(_osw_fpath, _osm_fpath, _ref_osm_fpath, _epw_fpath, echo=echo)
    except Exception as err:
        for name in dir():
            if name.startswith("_"):
                continue
            del globals()[name]
        # raise w/o arg means gets last exception and reraise it
        raise

    print(osmswap_fpath, oswswap_fpath, sep="\n")



