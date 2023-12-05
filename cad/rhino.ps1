rhino="C:/Program Files/Rhino 7/System/Rhino.exe"
rhf="/mnt/c/users/admin/masterwin/thermal/cad/baseline_01C.3dm" 
_rhf=$(wslpath -w $1 | sed 's;\\;\\\\\\\\;g' )
# /runscript='Grasshopper'
# NOTE: Ridiculous sed to get double \\ for windows path;
#       ref ~ C:\\Users\\..\\cad\\baseline_01C.3dm" 
# TODO: for some reason can't get GH to also run 
# NOTE: this writes Grasshopper in cmdline,but doesn't work
#       so must be GH command itself wrong?
& '$rhino' '/nosplash' '/runscript=\"_-Grasshoper 'D' 'O' 'swap_osm.gh'\"'" 
# pwsh "& '$rhino' '/nosplash' '/runscript=\"-_Open '$_rhf'\"'" 

