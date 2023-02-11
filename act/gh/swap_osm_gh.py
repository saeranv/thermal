from __future__ import print_function
import sys
from os import path
from io import StringIO
from ladybug_rhino.openstudio import load_osm, dump_osm


def log_stdout(act_fpath):
    """Write stdout -> buffer."""
    # Swap stdout and string buffer
    sys.stdout = sys.stderr = StringIO()

    # log file path
    _act_dpath = path.dirname(act_fpath)
    _rel_log = "../../../../../gh.log"
    return path.abspath(path.join(_act_dpath, _rel_log))


def dump_stdout(log_fpath):
    """Write buffer -> log & stdout."""
    # Write sys.stdout to log file
    output = sys.stdout.getvalue().strip()
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    # Write to log file, and also print
    with open(log_fpath, "w") as f:
        f.write(output)
    return output


def match_srf(act_srf, ref_areas, area_eps):
    """Returns argmin_i{ |area(Sa[i]) - area(Sr)| | 0 <= i < |Sa| }.

    Where Sa, Sr ∈ Surfaces.

    """

    diffs = [abs(act_srf.grossArea() - ref_area)
             for ref_area in ref_areas]

    min_diff = min(diffs)
    assert min_diff <= area_eps, \
        "No matching surface found, min diff {}.".format(min_diff)

    return diffs.index(min_diff)


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
        _is_bc = modelobj_set_fn(
            lambda s_: s_.surfaceType(), swap_srf_types)
        _is_type = modelobj_set_fn(
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


def swap_constr(act_osm, act_srfs, ref_srfs):
    """Swap construction of given srfs.

    Args:
        act_osm: OSM Model
        act_srfs: set of surfaces
        ref_srfs: set of surfaces (reference)

    Returns
        act_osm: OSM Model

    """
    area_eps = 0.5
    print("Found {} surfaces to swap.\n".format(len(act_srfs)))
    ref_areas = [r.grossArea() for r in ref_srfs]

    for i, act_srf in enumerate(act_srfs):
        old_constr = act_srf.construction().get().nameString() \
            if act_srf.construction().is_initialized() else "None"

        # Get matching ref constr
        ri = match_srf(act_srf, ref_areas, area_eps)
        ref_modelobj = ref_srfs[ri].construction()
        assert ref_modelobj.is_initialized()

        # Create ref-component from ref-modelobj
        ref_comp = ref_modelobj.get().createComponent()
        # ...insert ref-component into act-model
        act_comp_data = act_osm.insertComponent(ref_comp)
        assert act_comp_data.is_initialized()
        # Get act-modelobj from act-component
        act_modelobj = act_comp_data.get().primaryComponentObject()

        # Cast to Construction and set in act-surface
        constr = act_modelobj.to_ConstructionBase()
        assert constr.is_initialized()
        act_srf.setConstruction(constr.get())
        assert act_srf.construction().is_initialized(), \
            "Construction not initialized."

        # Assign scalar bc to surface
        bc = ref_srfs[ri].outsideBoundaryCondition()
        act_srf.setOutsideBoundaryCondition(bc)

        # Check construction assignment
        new_constr = act_srf.construction().get().nameString()
        print("{}. {} Area: {} \n Old: {}\n New: {}\n".format(
            i, act_srf.nameString(), act_srf.grossArea(),
            old_constr, new_constr))

    return act_osm


def main(act_fpath, ref_fpath, debug=False):
    """Main function."""

    swap_srf_types = {"Floor"}
    swap_srf_bcs = {"GroundFCfactorMethod", "Ground", "Outdoors"}
    swap_sets = (swap_srf_types, swap_srf_bcs)

    # Modify sys.stdout to str buffer
    log_fpath = log_stdout(act_fpath) if debug else ''

    # Create filepath for edited osm
    act_fpath_edit = act_fpath.replace(".osm", "_edit.osm")

    # Load osm models
    act_model, ref_model = load_osm(act_fpath), load_osm(ref_fpath)
    # Swap
    act_srfs, ref_srfs = modelobj_subset(act_model, ref_model, *swap_sets)
    act_model_edit = swap_constr(act_model, act_srfs, ref_srfs)

    # Dump/print sys.stdout
    output = dump_stdout(log_fpath) if debug else ''; print(output)

    # Dump osm model
    return dump_osm(act_model_edit, act_fpath_edit)


if run:
    osm_fpath_edit = main(_osm_fpath, _ref_osm_fpath, debug=True)



