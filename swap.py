from __future__ import print_function
from collections import OrderedDict
import os
import json
import shutil
import sys
pp = lambda *x: print(x, sep="\n")

INIT_ERR_MSG = lambda m: "Not initialized error, for {}.".format(m)
IS_TTY = len(sys.argv[0]) > 0
_LINEBREAK = "------------------------------------------"
LINEBREAK = (_LINEBREAK, _LINEBREAK)

try:
    from ladybug.futil import preparedir, nukedir
except ImportError as e:
    raise ImportError('\nFailed to import ladybug:\n\t{}'.format(e))


if not IS_TTY:
    from ladybug_rhino.openstudio import load_osm, dump_osm
else:
    # Define load_osm, dump_osm
    import openstudio as ops
    def load_osm(osm_fpath):
        model = ops.model.Model.load(ops.toPath(osm_fpath))
        assert model.is_initialized()
        return model.get()

    def dump_osm(osm_model, osm_fpath):
        osm_model.save(ops.toPath(osm_fpath), True)
        return osm_fpath

    run, args = True, sys.argv[1:]
    if len(args) == 0:
        _swaps = (1, 1, 1)
    elif args[0] == "-h":
        print("Usage: python swap.py [swap_constr] [swap_sizing] [swap_equip]")
        exit()
    else:
        _swaps = args
    swap_constr_, swap_sizing_, swap_equip_ = [bool(int(i)) for i in _swaps]
    _osw_fpath = os.path.join(os.getcwd(), "act/act/workflow.osw") #act.osm")
    _ref_osm_fpath = os.path.join(os.getcwd(), "ref/ref.osm")
    assert os.path.exists(_osw_fpath), os.path.abspath(_osw_fpath)
    assert os.path.exists(_ref_osm_fpath), os.path.abspath(_ref_osm_fpath)


def ppdir(modelobj, qstr="", *args, **kwargs):
    """Helper function to pretty print directories."""

    def _cond_fn(x):
        x = x.lower()
        return (
            not x.startswith("__") and \
            qstr.lower() in x
        )

    def modelobj_method_strs(obj, cond_fn, result):
        result += [mstr for mstr in dir(obj) if cond_fn(mstr)]
        if not (hasattr(obj, 'parent') and obj.parent().is_initialized()):
            return result
        else:
            parent = obj.parent().get()
            return modelobj_method_strs(parent, cond_fn, result)

    result = modelobj_method_strs(modelobj, _cond_fn, [])
    result += args
    print(*result, **kwargs)


def argmin(arr):
    """argmin: arr[int|float] -> [int|None]"""
    return arr.index(min(arr)) if len(arr) > 0 else None


def assert_init(modelobj):
    """Identity function that validates optional model parameters."""
    assert modelobj.is_initialized(), INIT_ERR_MSG(modelobj)
    return modelobj


def match_srf(act_srf, ref_areas, area_eps):
    """Returns argmin_i{ |area(Sa[i]) - area(Sr)| | 0 <= i < |Sa| }.
    Where Sa, Sr ∈ Surfaces."""

    def _assert_eps(ref_idx, ref_diff, area_eps):
        if ref_diff <= area_eps:
            return ref_idx
        name_, area_ = act_srf.nameString(), act_srf.grossArea()
        ref_areas_ = ", ".join(["{:.2f}" for a in ref_areas])
        raise Exception("The {} act srf not matching with "
                        "with area {:.2f}, ref srf areas: {}, and "
                        "area-epsilon {}."
                        .format(name_, area_, ref_areas_, area_eps))

    def _diff_fn(ref_area, act_srf):
        return abs(act_srf.grossArea() - ref_area)

    diffs = [_diff_fn(ref_area, act_srf)
             for ref_area in ref_areas]
    ri = argmin(diffs)
    ri_diff = _diff_fn(ref_areas[ri], act_srf)
    return _assert_eps(ri, ri_diff, area_eps)


def match_spc(rspcs, aspcs):
    rspcs = sorted(rspcs, key=lambda x: x.nameString())
    aspcs = sorted(aspcs, key=lambda x: x.nameString())
    for rspc, aspc in zip(rspcs, aspcs):
        assert rspc.nameString() in aspc.nameString(), \
            "Names don't match in spc."
    return rspcs, aspcs


def modelobj_subset(act_osm, ref_osm, swap_srf_types, swap_srf_bcs):
    """Filter subset of modelobs from user predicates.

    Args:
        act_osm: Ma ∈ act ModelObjects
        ref_osm: Ms ∈ ref ModelObjects
        swap_srf_types: Q ∈ Property set
        swap_srf_bcs: Q ∈ Property set

    Returns {Sa, Sr}
        where:
            Sa = {sa | g(sa) ∈ Qa ⊆ Pa}
            Sr = {sr | g(sr) ∈ Qr ⊆ Pr}
            g(srf) = type(srf) ⊆ Q & bc(srf) ⊆ Q
    """

    def _is_srf_type(s):
        return s.surfaceType() in swap_srf_types

    def _is_srf_bc(s):
        return s.outsideBoundaryCondition() in swap_srf_bcs

    # Filter out surfaces that don't match bc, and type we are
    # are looking for
    act_srfs = list(
        filter(_is_srf_type, filter(_is_srf_bc, act_osm.getSurfaces())))
    ref_srfs = list(
        filter(_is_srf_type, filter(_is_srf_bc, ref_osm.getSurfaces())))

    # Check consistency of resulting surfaces
    act_len, ref_len = len(act_srfs), len(ref_srfs)
    assert act_len + ref_len > 0, "Zero surfaces lengths.\n" \
        "# act_srfs = {}, # ref_srfs = {}".format(act_len, ref_len)
    assert act_len == ref_len, "Mismatched surface lengths.\n" \
        "# act_srfs = {}, # ref_srfs = {}".format(act_len, ref_len)

    return act_srfs, ref_srfs


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


def swap_design_days(act_osm, ref_osm, verbose=False):
    """Swap sizing period."""

    def diff(dds, mod_name):
        print("{} has {} DesignDay objects:".format(mod_name, len(dds)))
        _ = [print("  " + dd.nameString()) for dd in dds]

    ref_dd = list(ref_osm.getDesignDays())
    act_dd = list(act_osm.getDesignDays())

    if verbose:
        print("Swap DesignDays:")
        diff(ref_dd, 'Ref'); diff(act_dd, 'Act')

    # Remove act_osm design days, add ref_osm design days.
    _ = [dd.remove() for dd in act_dd]
    _ = [swap_modelobj(dd, act_osm) for dd in ref_dd]

    return act_osm


def swap_ground_temp_fcfm(act_osm, ref_osm, verbose=False):
    """Swap ground temperature."""

    def _get_fcfm(mod_osm):
        return mod_osm.getSite().siteGroundTemperatureFCfactorMethod()

    ref_fcfm = assert_init(_get_fcfm(ref_osm)).get()
    act_fcfm = swap_modelobj(ref_fcfm, act_osm)
    if verbose: print(act_fcfm)
    return act_osm


def swap_constr(act_osm, act_srfs, ref_srfs, verbose=False):
    """Swap construction of given srfs.

    Args:
        act_osm: OSM Model
        act_srfs: set of surfaces
        ref_srfs: set of surfaces (reference)

    Returns
        act_osm: OSM Model
    """

    area_eps = 0.5
    if verbose:
        print("Found {} surfaces to swap.".format(len(act_srfs)))
    ref_areas = [r.grossArea() for r in ref_srfs]
    # Core should be: F 126 Perim 0 Area 98354
    for i, act_srf in enumerate(act_srfs):
        old_constr = act_srf.construction().get().nameString() \
            if act_srf.construction().is_initialized() else "None"

        # Get matching ref constr
        ri = match_srf(act_srf, ref_areas, area_eps)
        ref_constr = ref_srfs[ri].construction()

        # Swap
        ref_modelobj = assert_init(ref_constr).get()
        act_modelobj = swap_modelobj(ref_modelobj, act_osm)
        constr = assert_init(act_modelobj.to_ConstructionBase()).get()

        # Construction (shared resource) must be assigned to surface:
        act_srf.setConstruction(constr)

        # Assign scalar bc to surface
        bc = ref_srfs[ri].outsideBoundaryCondition()
        act_srf.setOutsideBoundaryCondition(bc)

        # Check construction assignment
        new_constr = assert_init(act_srf.construction()).get().nameString()
        if verbose:
            print("{}. {}:\n Old: {}\n New: {}".format(
                i, act_srf.nameString(), old_constr, new_constr))
            print(" Area diff: act:{} ref:{}\n".format(
                round(act_srf.grossArea(), 2),
                round(ref_srfs[ri].grossArea(),2))
            )
    return act_osm


def attr_dict(modelobj, attrs):
    """Get ordered dictionary given attributes from modelobj."""
    return OrderedDict([(attr, getattr(modelobj, attr)()) for attr in attrs])


def is_modelobj_approx_equal(attrs, refobj, actobj, eps=1e-6):
    """True if distance between attributes less than eps, else False."""
    ref_vec = attr_dict(refobj, attrs).values()
    act_vec = attr_dict(actobj, attrs).values()

    return all(abs(float(r) - float(a)) <= eps
               for r, a in zip(ref_vec, act_vec))


def swap_sizing_params(act_osm, ref_osm, verbose=False):
    """Swap sizing parameters."""
    def _diff_sizing_params(act_osm, ref_osm, verbose=False):
        """Compare required sizing parameters."""
        return is_modelobj_approx_equal(
            'heatingSizingFactor coolingSizingFactor'.split(' '),
            ref_osm.getSizingParameters(),
            act_osm.getSizingParameters())

    def _swap_sizing_params(act_osm, ref_osm, verbose=False):
        """Swap required sizing parameters."""
        refparam = ref_osm.getSizingParameters()
        actparam = act_osm.getSizingParameters()
        heatsize = refparam.heatingSizingFactor()
        coolsize = refparam.coolingSizingFactor()
        actparam.setHeatingSizingFactor(heatsize)
        actparam.setCoolingSizingFactor(coolsize)

        return act_osm

    if _diff_sizing_params(act_osm, ref_osm, verbose):
        return act_osm

    if verbose: print("Sizing params not equal. Swapping.")
    act_osm = _swap_sizing_params(act_osm, ref_osm, verbose)

    return act_osm


def swap_spc_equip(act_osm, ref_osm, verbose=False):
    """Remove spc equip from ref_osm."""

    def _diff_equip(act_osm, ref_osm):
        """Compare required sizing parameters."""
        # TODO: add rest of the fields
        # designLevelCalculationMethod
        attrs = 'designLevel'.split(' ')
        ref_equips = ref_osm.getElectricEquipmentDefinitions()
        act_equips = act_osm.getElectricEquipmentDefinitions()
        return all(is_modelobj_approx_equal(attrs, ref, act)
                   for ref, act in zip(ref_equips, act_equips))

    #is_diff = _diff_equip(act_osm, ref_osm)
    #if is_diff:
    #    print("Equipments are equal. No swapping.")
    #    return act_osm
    print("Equipments not equal. Swapping.")

    # Get all spaces, and sort them
    ref_spcs, act_spcs = ref_osm.getSpaces(), act_osm.getSpaces()
    ref_spcs, act_spcs = match_spc(ref_spcs, act_spcs)

    ## Loop through spaces and remove/then assign eqiuip_defn to space
    for ref_spc, act_spc in zip(ref_spcs, act_spcs):
        # TODO: check if parent spacetype or space and check accordingly
        #for act_equip in act_spc.electricEquipment():
        #    parent = assert_init(act_equip.parent()).get()
        #    print(type(parent.iddObjectType()))
        for ref_equip in ref_spc.electricEquipment():
            ## TODO: add the diff-check which adds unique_ref_equip
            ## i.e. unique_ref_equip = ref_equip not in (act_equip AND ref_equip)
            if "elevator" not in ref_equip.nameString().lower():
                continue
            act_equip = swap_modelobj(ref_equip, act_osm)
            is_parent_set = act_equip.setParent(act_spc)
            assert is_parent_set, \
                "Error! setParent fail for {}".format(act_equip)
            print('Added equip: {} to space: {}'.format(
                act_equip.nameString(), act_spc.nameString()))

    return act_osm


def main(act_fpath, ref_fpath, act_swap_fpath,
         is_swap_constr, is_swap_sizing, is_swap_equip):
    """Main function."""

    swap_srf_types = {"Floor"}
    swap_srf_bcs = {"GroundFCfactorMethod", "Ground"}
    swap_sets = (swap_srf_types, swap_srf_bcs)

    # Load osm models
    act_model, ref_model = load_osm(act_fpath), load_osm(ref_fpath)

    # SWAP CONSTRUCTIONS
    if is_swap_constr:
        print("{}\nSWAP CONSTRUCTION & GROUND TEMPS\n{}".format(*LINEBREAK))
        act_srfs, ref_srfs = modelobj_subset(act_model, ref_model, *swap_sets)
        act_model = swap_constr(act_model, act_srfs, ref_srfs, verbose=True)
        ## SWAP GROUND_TEMP
        #act_model = swap_ground_temp_fcfm(act_model, ref_model, verbose=True)
    ## SWAP SIZING
    if is_swap_sizing:
        print("{}\nSWAP SIZING PARAMS\n{}".format(*LINEBREAK))
        act_model = swap_design_days(act_model, ref_model, verbose=True)
        act_model = swap_sizing_params(act_model, ref_model, verbose=True)
    ## SWAP LOADS
    if is_swap_equip:
        print("{}\nSWAP EQUIP\n{}".format(*LINEBREAK))
        act_model = swap_spc_equip(act_model, ref_model, verbose=True)
    # SWAP LIGHT
    # if is_swap_light:
        # print("{}\nSWAP INTERIOR-LIGHT\n{}".format(*LINEBREAK))
        # act_model = swap_spc_light(act_model, ref_model)

    ## Dump osm model
    act_swap_fpath = dump_osm(act_model, act_swap_fpath)
    return act_swap_fpath


if run:
    if IS_TTY:
        #act_swap_fpath_ = _osw_fpath.replace('.osw', '_swap.osw')
        _dpath, _fname = os.path.split(_osw_fpath)
        # act_swap_dpath = os.path.abspath(os.path.join(_dpath, '../act_swap'))
        # TODO: redo
        act_swap_dpath = _dpath
        act_swap_fpath_ = os.path.abspath(os.path.join(act_swap_dpath, '../act.osm'))
        _osm_fpath = os.path.abspath(os.path.join(_dpath, '../in.osm'))
        osw_swap_fpath_ = os.path.join(act_swap_dpath, _fname)
    else:
        # Create filepath for edited osm
        _dpath, _fname = os.path.split(_osw_fpath)
        _dpath = os.path.abspath(os.path.join(_dpath, '..'))
        _osm_fpath = os.path.abspath(os.path.join(_dpath, 'openstudio', 'run', 'in.osm'))
        _swap_dpath = _dpath + "_Swap"
        osm_swap_fpath_ = os.path.join(_swap_dpath, 'openstudio', 'run', 'in.osm')
        osw_swap_fpath_ = os.path.join(_swap_dpath, _fname)

    nukedir(_swap_dpath, True)
    #preparedir(_swap_dpath)
    print(_dpath)
    print(_swap_dpath)
    print(os.path.exists(_dpath))
    _ = shutil.copytree(_dpath, _swap_dpath)
    print('asfad')
    # if not os.path.isdir(act_swap_dpath):
        # _ = os.mkdir(act_swap_dpath)
    # Copy osw file
    # shutil.copy(_osw_fpath, osw_swap_fpath_)
    # shutil.copy(_osm_fpath, act_swap_fpath_)

    # with open(_osw_fpath, 'r') as f:
        # osw_data = json.load(f)
#
#
    # osw_data['seed_file'] = act_swap_fpath_
    # with open(osw_swap_fpath_, 'w') as f:
        # json.dump(osw_data, f, indent=4)


    # Define defaults
    swap_constr_ = False if swap_constr_ is None else swap_constr_
    swap_sizing_ = False if swap_sizing_ is None else swap_sizing_
    swap_equip_ = False if swap_equip_ is None else swap_equip_
    try:
        component_args = (_osm_fpath, _ref_osm_fpath, act_swap_fpath_,
                          swap_constr_, swap_sizing_, swap_equip_)
        osm_fpath_edit = main(*component_args)
        print("swap_constr:", swap_constr_,
              "swap_sizing:", swap_sizing_,
              "swap_equip: ", swap_equip_)
        print('Edited file:', osm_fpath_edit)
        print('OSW file:', osw_swap_fpath_)
    except Exception as err:
        print(err)
