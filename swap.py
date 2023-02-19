from __future__ import print_function
from collections import OrderedDict
import os
import sys
pp = lambda *x: print(x, sep="\n")
import traceback

INIT_ERR_MSG = lambda m: "{} not initialized.".format(m)
IS_TTY = len(sys.argv[0]) != 0
_LINEBREAK = "------------------------------------------"
LINEBREAK = (_LINEBREAK, _LINEBREAK)


if not IS_TTY:
    from ladybug_rhino.openstudio import load_osm, dump_osm
else:
    #argv = sys.argv[1:]
    #assert len(argv) == 2, "Expected 2 args, got {}.".format(len(argv))
    # Define load_osm, dump_osm
    import openstudio as ops
    #print(*dir(ops), sep="\n")
    def load_osm(osm_fpath):
        model = ops.model.Model.load(ops.toPath(osm_fpath))
        assert model.is_initialized()
        return model.get()

    def dump_osm(osm_model, osm_fpath):
        osm_model.save(ops.toPath(osm_fpath), True)
        return osm_fpath

    run = True
    args = sys.argv[1:]
    if len(args) == 0:
        _swaps = (0, 0, 1)
    elif args[0] == "-h":
        print("Usage: python swap.py <swap_constr> <swap_sizing> <swap_equip>")
        assert False
    else:
        _swaps = args
    swap_constr_, swap_sizing_, swap_equip_ = [bool(int(i)) for i in _swaps]
    _osm_fpath = os.path.join(os.getcwd(), "act/act.osm")
    _ref_osm_fpath = os.path.join(os.getcwd(), "ref/ref.osm")
    assert os.path.exists(_osm_fpath), os.path.abspath(_osm_fpath)
    assert os.path.exists(_ref_osm_fpath), os.path.abspath(_ref_osm_fpath)


def ppdir(obj, qstr=""):
    """Helper function to pretty print directories."""
    def cond_fn(x):
        return (not x.startswith("__")) and (qstr.lower() in x)
    return [x for x in dir(obj) if cond_fn(x.lower())]


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


def modelobj_set_fn(property_fn, property_set):
    """Predicate fn for ModelObjs from property fn and set.

    Given sets B, M, P, and Q:
        B = {0, 1}
        M = {m | m ∈ ModelObject set}
        P = {p | p ∈ Property set}
        Q ⊆ P, Property subset defined by user
    and a function g:
        g:M -> P | g(m) = p ∈ P

    Function f is returned as subset of M where P(M) ∈ Q.
        f:M -> B | f(m) = g(m) ⊆ Q
    """
    return lambda m: property_fn(m) in property_set


def modelobj_subset(act_osm, ref_osm, swap_srf_types, swap_srf_bcs):
    """Filter subset of modelobs from user predicates.

    Args:
        act_osm: Ma ∈ act ModelObjects
        ref_osm: Ms ∈ ref ModelObjects
        swap_srf_types: Q ∈ Property set
        swap_srf_vc: Q ∈ Property set

    Returns {Sa, Sr}
        where:
            Sa = {sa | g(sa) ∈ Qa ⊆ Pa}
            Sr = {sr | g(sr) ∈ Qr ⊆ Pr}
            g(srf) = type(srf) ⊆ Q & bc(srf) ⊆ Q
    """

    def _is_srf(s):
        _is_type = modelobj_set_fn(
            lambda s_: s_.surfaceType(), swap_srf_types)
        _is_bc = modelobj_set_fn(
            lambda s_: s_.outsideBoundaryCondition(), swap_srf_bcs)
        return _is_bc(s) and _is_type(s)

    act_srfs = list(filter(_is_srf, act_osm.getSurfaces()))
    ref_srfs = list(filter(_is_srf, ref_osm.getSurfaces()))

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

# TODO: cross-entropy of attri
def hist(values):
    """Histogram of attribute values."""
    pass


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


def swap_equip(act_osm, ref_osm, verbose=False):
    """Remove elevator from ref_osm."""

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
    def _match_spc(rspcs, aspcs):
        rspcs = sorted(rspcs, key=lambda x: x.nameString())
        aspcs = sorted(aspcs, key=lambda x: x.nameString())
        for rspc, aspc in zip(rspcs, aspcs):
            assert rspc.nameString() in aspc.nameString(), \
                "Names don't match in spc."
        return rspcs, aspcs

    ref_spcs = ref_osm.getSpaces()
    act_spcs = act_osm.getSpaces()
    ref_spcs, act_spcs = _match_spc(ref_spcs, act_spcs)
    ref_equips = ref_osm.getElectricEquipmentDefinitions()
    for num_def, equip in enumerate(ref_equips):

        if "elevator" in equip.nameString().lower():
            equip.remove()
    meter = ref_osm.getMeterCustomByName("Wired_LTG_Electricity")
    assert_init(meter).get().remove()

    meter = ref_osm.getMeterCustomDecrementByName("Wired_Int_EQUIP")
    assert_init(meter).get().remove()
    #print(ppdir(ref_osm, 'meter'))
    return ref_osm



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
        #print('WIP - disabled.')
        ref_model = swap_equip(act_model, ref_model, verbose=True)

    ## Dump osm model
    act_swap_fpath = dump_osm(act_model, act_swap_fpath)
    ref_swap_fpath = ref_fpath.replace('.osm', '_swap.osm')
    ref_swap_fpath = dump_osm(ref_model, ref_swap_fpath)
    return act_swap_fpath, ref_swap_fpath

if run:

    if IS_TTY:
        act_swap_fpath_ = _osm_fpath.replace('.osm', '_swap.osm')
    else:
        # Create filepath for edited osm
        _osm_dpath = os.path.dirname(_osm_fpath)
        if "hb_model" in _osm_fpath:
            act_swap_dpath = os.path.join(_osm_dpath, '../../..') + "_Swap"
        else:
            act_swap_dpath = os.path.join(_osm_dpath, 'act_swap')
        if not os.path.isdir(act_swap_dpath):
            _ = os.mkdir(act_swap_dpath)

        act_swap_fpath_ = os.path.join(act_swap_dpath, "in.osm")

    # Define defaults
    swap_constr_ = False if swap_constr_ is None else swap_constr_
    swap_sizing_ = False if swap_sizing_ is None else swap_sizing_
    swap_equip_ = False if swap_equip_ is None else swap_equip_
    try:
        osm_fpath_edit, ref_fpath_edit = \
            main(_osm_fpath, _ref_osm_fpath, act_swap_fpath_,
                 swap_constr_, swap_sizing_, swap_equip_)
        print("swap_constr:", swap_constr_,
              "swap_sizing:", swap_sizing_,
              "swap_equip: ", swap_equip_)
        print('Edited file:', osm_fpath_edit)

    except Exception as err:
        print(err)
