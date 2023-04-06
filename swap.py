from __future__ import print_function
from collections import OrderedDict
import os
import sys
pp = lambda *x: print(x, sep="\n")

INIT_ERR_MSG = lambda m: "Not initialized error, for {}.".format(m)
IS_TTY = len(sys.argv[0]) > 0
_LINEBREAK = "------------------------------------------"
LINEBREAK = (_LINEBREAK, _LINEBREAK)


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
        _swaps = (0, 0, 0, 1)
    elif args[0] == "-h":
        print("Usage: python swap.py [swap_constr] [swap_sizing] [swap_equip]"
              " [swap_light]")
        exit()
    else:
        _swaps = args
    swap_constr_, swap_sizing_, swap_equip_, swap_light_ = \
        [bool(int(i)) for i in _swaps]
    _osm_fpath = os.path.join(os.getcwd(), "act/act.osm")
    _ref_osm_fpath = os.path.join(os.getcwd(), "ref/ref.osm")
    assert os.path.exists(_osm_fpath), os.path.abspath(_osm_fpath)
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
    print(*result, *args, **kwargs)


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


def swap_hvac(act_osm, ref_osm):
    """Swap hvac."""

    def _diff_hvac(act_osm, ref_osm):
        """Compare hvac."""
        pass

    # TODO: check if hvac objects exist using lib from idf


def swap_spc_light(act_osm, ref_osm):
    """Swap space lighting."""

    ## Get resources
    light_sched_name = "OfficeMedium BLDG_LIGHT_SCH_2013"
    #ref_sched_opt = ref_osm.getScheduleByName(light_sched_name)
    #ref_sched = assert_init(ref_sched_opt).get()
    #act_sched = swap_modelobj(ref_sched, act_osm)

    # Get all spaces, and sort them
    ref_spcs, act_spcs = ref_osm.getSpaces(), act_osm.getSpaces()
    ref_spcs, act_spcs = match_spc(ref_spcs, act_spcs)

    ## Loop through spaces and remove/then assign light_defn to space
    for ref_spc, act_spc in zip(ref_spcs, act_spcs):
        ref_name, act_name = ref_spc.nameString(), act_spc.displayName()
        ref_spc_type = assert_init(ref_spc.spaceType()).get()
        act_spc_type = assert_init(act_spc.spaceType()).get()

        # DaylightSensors
        ref_controls = ref_spc.daylightingControls()
        if len(ref_controls) == len(act_spc.daylightingControls()):
            continue

        # Space lights
        for act_spc_light in act_spc.lights():
            act_spc_light.remove()
        for ref_type_light in ref_spc_type.lights():
            # Get sched
            ref_light = assert_init(ref_type_light.to_Lights()).get()
            act_light_opt = swap_modelobj(ref_light, act_osm)
            act_light = assert_init(act_light_opt.to_Lights()).get()
            is_parent_set = act_light.setParent(act_spc)
            assert is_parent_set, "setParent fail for {}".format(act_light)
            # Swap schedule
            act_sched_opt = act_osm.getScheduleByName(light_sched_name)
            act_sched = assert_init(act_sched_opt).get()
            is_sched = act_light.setSchedule(act_sched)
            print('Added {} to space: {}'.format(act_light.nameString(), act_name))

        for ref_control in ref_controls:
            act_control = swap_modelobj(ref_control, act_osm)
            is_parent_set = act_control.setParent(act_spc)
            assert is_parent_set, "setParent fail for {}".format(act_control)
            print('Added {} to space: {}'.format(
                  act_control.nameString(), act_name))
    ems_data = {
        'sensor_name': [],
        'actuated_comp': []
    }

    for ems_sensor in ref_osm.getEnergyManagementSystemSensors():
        ems_sensor_var = ems_sensor.outputVariableOrMeterName()
        if "Lights" not in ems_sensor_var:
            continue
        act_ems_sensor = swap_modelobj(ems_sensor, act_osm)
        ems_data['sensor_name'] += [act_ems_sensor.nameString()]
    for ems_actuator in ref_osm.getEnergyManagementSystemActuators():
        if "Lights" not in ems_actuator.actuatedComponentType():
            continue
        act_ems_actuator = swap_modelobj(ems_actuator, act_osm)
        act_ems_actuator = act_ems_actuator.to_EnergyManagementSystemActuator()
        act_ems_actuator = assert_init(act_ems_actuator).get()
        #comp = assert_init(act_ems_actuator.actuatedComponent()).get()
        #ems_data['actuated_comp'] += [comp.nameString()]
    for ems_glob_var in ref_osm.getEnergyManagementSystemGlobalVariables():
        swap_modelobj(ems_glob_var, act_osm)
    #for ems_out_var in ref_osm.getEnergyManagementSystemOutputVariables():
    #    swap_modelobj(ems_out_var, act_osm)
    for ems_int_var in ref_osm.getEnergyManagementSystemInternalVariables():
        swap_modelobj(ems_int_var, act_osm)
    # Programs
    for ems_prog_call in ref_osm.getEnergyManagementSystemProgramCallingManagers():
        ems_prog_call_name = ems_prog_call.nameString()
        if "Light" not in ems_prog_call_name:
            continue
        act_prog_call = swap_modelobj(ems_prog_call, act_osm)
        act_prog_call = act_prog_call.to_EnergyManagementSystemProgramCallingManager()
        act_prog_call = assert_init(act_prog_call).get()
        # Swap program
        ems_prog = assert_init(ems_prog_call.getProgram(0)).get()
        act_prog = swap_modelobj(ems_prog, act_osm)
        act_prog = assert_init(act_prog.to_EnergyManagementSystemProgram()).get()
        act_prog_call.eraseProgram(0)
        act_prog_call.addProgram(act_prog)

    #for ems_prog in ref_osm.getEnergyManagementSystemPrograms():
    #    swap_modelobj(ems_prog, act_osm)
    #ems_progs = act_osm.getEnergyManagementSystemPrograms()
    #ems_prog_calls = act_osm.getEnergyManagementSystemProgramCallingManagers()
    #for ems_prog, ems_prog_call in zip(ems_progs, ems_prog_calls):
    #    ems_prog_call.eraseProgram(0)
    #    ems_prog_call.addProgram(ems_prog)

    return act_osm


def main(act_fpath, ref_fpath, act_swap_fpath,
         is_swap_constr, is_swap_sizing, is_swap_equip, is_swap_light):
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
    if is_swap_light:
        print("{}\nSWAP INTERIOR-LIGHT\n{}".format(*LINEBREAK))
        act_model = swap_spc_light(act_model, ref_model)

    ## Dump osm model
    act_swap_fpath = dump_osm(act_model, act_swap_fpath)
    return act_swap_fpath


if run:
    if IS_TTY:
        act_swap_fpath_ = _osm_fpath.replace('.osm', '_swap.osm')
    else:
        # Create filepath for edited osm
        _osm_dpath = os.path.dirname(_osm_fpath)
        act_swap_dpath = os.path.join(_osm_dpath, '../../..') + "_Swap"
        if not os.path.isdir(act_swap_dpath):
            _ = os.mkdir(act_swap_dpath)
        act_swap_fpath_ = os.path.join(act_swap_dpath, "in.osm")

    # Define defaults
    swap_constr_ = False if swap_constr_ is None else swap_constr_
    swap_sizing_ = False if swap_sizing_ is None else swap_sizing_
    swap_equip_ = False if swap_equip_ is None else swap_equip_
    swap_light_ = False if swap_light_ is None else swap_light_
    try:
        osm_fpath_edit = \
            main(_osm_fpath, _ref_osm_fpath, act_swap_fpath_,
                 swap_constr_, swap_sizing_, swap_equip_, swap_light_)
        print("swap_constr:", swap_constr_,
              "swap_sizing:", swap_sizing_,
              "swap_equip: ", swap_equip_,
              "swap_light: ", swap_light_)
        print('Edited file:', osm_fpath_edit)

    except Exception as err:
        print(err)
