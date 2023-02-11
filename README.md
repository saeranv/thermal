## thermal-mass

Repo for DOE ARPA-E model creation.

The directory is structured around two OSMs: a DOE Prototype OSM (`ref`), and a reconstruction of it in GH, that permits flexible changes to the model construction and geometry logic (`act`).

Broadly, the resources to generate both OSMs are in the following highlevel directories:

## Structure

```
./   
    thermal.sh
    ref/ 
        ref_seed.osm 
        ref_seed/ 
    act/
        act_seed.osm
        act_seed/
        gh/
            ..
    resources/
       .. 
```

```bash
. ./thermal.sh -rm -cp ref    # creates ref/ref.osm, ref/ref/
                              # from ref_seed.osm 

. ./thermal.sh -rm -cp act    # creates act/act.osm, act/act/
                              # from act_seed/*/openstudio/in.osm model
```

```
./   
    thermal.sh
    ref/ 
        ref_seed.osm 
        ref.osm
        ref_ideal.osm
        ref_seed/ 
        ref/
        ref_ideal/
    # resources for creation of "act" GH BEM 
    act/
        act.osm
        act_seed.osm
        act/
        act_seed/
        gh/
    resources/
       .. 

```

## REF MODEL

The reference file is created by running the `create_ref.osm` file in the `./ref` directory. This is an empty seed  with only the `CreateDOEPrototypeBuilding` measure with the following arguments:

```
building_type: "MediumOffice"
climate_zone: "ASHRAE 169-2013-2B"
template: "90.1-2016"
```

Note that the 90.1-2016 standard was used here because the 90.1-2019 template is not available in the `CreateDOEPrototypeBuilding` measure. 

Since the `create_ref.osm` is an empty seed, it provides, a self-contained `ref.osm` and supporting directory is generated from the `create_ref` directory which should be used for actual referencing opertions. This can be generated with the following bash command in the ref directory:
```bash
. ./ref.sh -rm -cp
```

## ACTIVE MODEL


### SIZINGPERIOD 

The `.ddy` files in the `create_ref/run/000_Create_DOEPrototypeBuilding/extracted_files/weather` should not be used to generate the `SizingPeriod:DesignDays` object, since there are more design days there then is used in the actual model. Instead the design days can just be copied directly from the reference `.idf` and added to the active model directly. 



