# THERM 

## Installation Bugs 
### Openstudio 3.6.1
- Ensure `openstudiolib.dll` is installed in
  `/c/openstudio-3.6.1/csharp/`. If not, copy it from the
  `/c/openstudio-3.6.1/bin/` folder.
### LBT Python (win32)
- Ensure `clr` module is installed in lbt python by pip installing pythonnet. To
  install, run:
  `/c/users/admin/ladybug_tools/python/python.exe -m pip install pythonnet`.


## IN.BAT
## "C:\openstudio-3.4.0\EnergyPlus\energyplus.exe" -w "C:\Users\admin\masterwin\thermal\epw\USA_HI_Honolulu.Intl.AP.911820_TMY3\USA_HI_Honolulu.Intl.AP.911820_TMY3.epw" -i "C:\openstudio-3.4.0\EnergyPlus\Energy+.idd" -x
