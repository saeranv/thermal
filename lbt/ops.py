import sys
import os


LBTDIR = os.path.dirname(__file__)
THERMDIR = os.path.join(LBTDIR, "..")

# lr_ops_fpath = os.path.realpath(os.path.join(CWD, "lbt_ops.py"))
osm_fpath = os.path.join(THERMDIR, "simops_", "run", "in.osm")
assert os.path.exists(osm_fpath), \
    f"OSM file not found at {osm_fpath}"



from ladybug_rhino.openstudio import _copy_openstudio_lib

