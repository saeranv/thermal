#!/bin/bash
# /thermal-mass/thermal.sh

cd "$(dirname "$0")"
THERM_DP=$PWD

# REF VARS
REF_DP="$THERM_DP/ref"
REF_SEED_DP="$REF_DP/ref_seed/run/000_CreateDOEPrototypeBuilding"
REF_SEED_DP="$REF_SEED_DP/output/SR1"
REF_SEED_OSW="$REF_SEED_DP/in.osw" 
REF_SEED_EPW="$REF_SEED_DP/in.epw"
REF_SEED_OSM="$REF_SEED_DP/in.osm"
REF_OSM="$REF_DP/ref.osm"
REF_OSW="$REF_DP/ref/workflow.osw"
REF_EPW="$REF_DP/ref/in.epw"
REF_VARS=( \
    $REF_SEED_DP $REF_DP \ 
    $REF_SEED_OSW $REF_OSW \
    $REF_SEED_OSM $REF_OSM \
    $REF_SEED_EPW $REF_EPW \
    "ref")

# ACT VARS
ACT_DP="$THERM_DP/act"
HB_MODEL_DP=$(python - << EOF
import os; hb_models_dp = "$ACT_DP/hb_models"
is_hb = lambda x: not os.path.isdir(x)
hb_models = list(filter(is_hb, os.listdir(hb_models_dp)))
assert len(hb_models) > 0, f'No HB dirs in act/hb_models/ dir.'
if len(hb_models) > 1:
    print(f'Warning! {len(hb_models)} hb_models found'
           'reverse prefix sorting.')
print(os.path.join(hb_models_dp, sorted(hb_models)[-1]))
EOF
)
HB_MODEL_NAME="${HB_MODEL_DP##*/}"
ACT_SEED_DP="$HB_MODEL_DP/openstudio/run"
ACT_SEED_OSW="$REF_OSW" 
ACT_SEED_EPW="$REF_EPW"
ACT_SEED_OSM="$ACT_SEED_DP/in.osm"
ACT_OSM="$ACT_DP/act.osm"
ACT_OSW="$ACT_DP/act/workflow.osw"
ACT_EPW="$ACT_DP/act/in.epw"
ACT_VARS=( \
    $ACT_SEED_DP $ACT_DP \
    $ACT_SEED_OSW $ACT_OSW \
    $ACT_SEED_OSM $ACT_OSM \
    $ACT_SEED_EPW $ACT_EPW \
    "act")

chk_fp_exist () {
    for i in $@; do
        FP=$i
        if [ ! -f "$FP" ]; then
            echo "Error! $FP does not exist."
            exit 1
        fi
    done
}

modify_osw () {
python - << EOF
# Rewrite .osm seed location in given .osw
import json; from pprint import pprint
osw_fp = '$1'
with open(osw_fp, 'r') as f:
    data = json.load(f)
with open(osw_fp, 'w') as f: 
    if 'hash' in data: data.pop('hash') 
    data['seed_file'] = '../$2.osm'
    json.dump(data, f, indent=4)
pprint(data)
EOF
echo "Finished."
}

rm_mod () {
    # Removes ./ref/ref and ./ref/ref.osm (or act) 
    [ ! "$#" -eq 3 ] && \
        echo "Error, rm_mod requires 3 args." && exit 1
    MOD_DP=$1
    MOD_OSM=$2
    MOD_NAME=$3
    [ -d "$MOD_DP" ] && \
        rm -r "$MOD_DP" 
    echo "Deleted $MOD_NAME/$MOD_NAME/" 
    [ -f $MOD_OSM ] && \ 
        rm -f $MOD_OSM
    echo "Deleted $MOD_NAME/$MOD_NAME.osm" 
}

cp_mod () {
    [ ! "$#" -eq 9 ] && \
        echo "Error, cp_mod requires 9 args, got $#." && exit 1
    MOD_SEED_DP=$1; MOD_DP=$2
    MOD_SEED_OSW=$3; MOD_OSW=$4
    MOD_SEED_OSM=$5; MOD_OSM=$6
    MOD_SEED_EPW=$7; MOD_EPW=$8
    MOD_NAME=$9
    
    if [ ! -d "$MOD_SEED_DP" ]; then
        echo "Error. The $MOD_SEED_DP directory does not exist."
        exit 1
    fi

    # Exit if fp doesn't exist
    echo "Checking if osw, osm and epw files exist for $MOD_NAME/."
    chk_fp_exist $MOD_SEED_OSW $MOD_SEED_OSM $MOD_SEED_EPW

    if [ ! -d "$MOD_DP/$MOD_NAME" ]; then
        mkdir "$MOD_DP/$MOD_NAME"
        echo "Creating ./$MOD_NAME/$MOD_NAME directory."
    fi

    cp "$MOD_SEED_OSW" "$MOD_OSW"
    cp "$MOD_SEED_EPW" "$MOD_EPW"
    cp "$MOD_SEED_OSM" "$MOD_OSM"
    
    echo "Rewriting paths in ./$MOD_NAME/$MOD_NAME/workflow.osm"
    modify_osw $MOD_OSW "$MOD_NAME"
}


helpcmd=$(python -c 'print("""thermal [-h] [-cp] [-rm] [-ls]
Example:
    thermal ref -rm -cp
    thermal act -rm -cp
    thermal ref|act -ls
-cp: copies ref.osm|act.osm and ref/|act/ support folder.
-rm: remove ref.osm|act.osm and ref/|act/ support folder.
-ls: lists files in ref|act dirs
""")')


# Set ACT/REF as MODEL_DP
if [[ "$1" != *"-"* ]]; then
    args=("${@:2}")
    if [[ -d "$THERM_DP/$1" ]]; then 
        ACT_REF_VAR=$1 
    else
        echo "Error, first arg must be 'ref' or 'act', got $1."
        exit 1
    fi
else
    # Note: strings are considered truth
    args=("$@")
fi


if [[ "$#" -eq 0 ]]; then
    echo -e "$helpcmd"
else
    # for arg must be alone on this line
    for i in $@; do
        [[ "$i" == "-h" ]] && \
            echo -e "$helpcmd"
        if [[ "$i" == "-cp" ]]; then
            [[ $ACT_REF_VAR == "ref" ]] && \
                cp_mod ${REF_VARS[@]} || \
                cp_mod ${ACT_VARS[@]}
        fi 
        if [[ "$i" == "-rm" ]]; then 
            [[ $ACT_REF_VAR == "ref" ]] && \
                rm_mod "$REF_DP/ref" "$REF_OSM" 'ref' || \
                rm_mod "$ACT_DP/act" "$ACT_OSM" 'act'
        fi
        if [[ "$i" == "-ls" ]]; then 
            [[ $ACT_REF_VAR == "ref" ]] && \
                ls "$THERM_DP/ref" || \
                ls "$THERM_DP/act"
        fi
    done
fi
