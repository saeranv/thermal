import os
from ladybug.epw import EPW

epw_fpath = os.path.join(os.getcwd(), "ref/ref/in.epw")

assert os.path.isfile(epw_fpath)

epw = EPW(epw_fpath)

db = epw.dry_bulb_temperature
print(type(db))

db.convert_to_ip()

print(db.values[:10])
