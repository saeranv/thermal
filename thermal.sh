#!/bin/bash
# /thermal-mass/thermal.sh

cd "$(dirname "$0")"
echo "thermal.sh: $(pwd)"
THERMWIN_DP="/mnt/c/users/admin/master/thermal"
THERM_DP=$PWD

# REF VARS
REF_DP="$THERM_DP/ref"
REF_SEED_DP="$REF_DP/ref_seed/run"
REF_DOE_DP="$REF_SEED_DP/000_CreateDOEPrototypeBuilding/output/SR1"
# NOTE: only use REF_DOE for osw, epw the .osm is empty!
REF_SEED_OSW="$REF_DOE_DP/in.osw"
REF_SEED_EPW="$REF_DOE_DP/in.epw"
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
from sys import stderr
is_hb = lambda x: "Swap" not in x
hb_models = [hb for hb in os.listdir(hb_models_dp)
             if is_hb(hb)]
if len(hb_models) != 1:
    stderr.write('Must be one HB model in act/hb_models/ dir without '
                 f'Swap in name, found:\n\t{os.listdir(hb_models_dp)}.')
print(os.path.join(hb_models_dp, hb_models[0]))
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

# TODO: move to ops.py
modify_osw () {
python - << EOF
# Rewrite .osm seed location in given .osw
import json; from pprint import pprint
osw_fp = '$1'
osm_fp = '$2'
filter_m = lambda m: 'OpenStudio Results' not in m['name'] 
with open(osw_fp, 'r') as f:
    data = json.load(f)
with open(osw_fp, 'w') as f:    
    if 'hash' in data: 
        data.pop('hash') 
    if 'weather_file' in data:
        data.pop('weather_file')
    data['weather_file'] = './in.epw'
    data['steps'] = list(filter(filter_m, data['steps']))
    data['seed_file'] = f'../{osm_fp}.osm'
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

swap_cp () {
    echo "Copy ./act/act_swap, ./ref/ref to windows dir."
    [[ -d "$THERMWIN_DP/ref" ]] && rm -r "$THERMWIN_DP/ref"
    [[ -d "$THERMWIN_DP/act_swap" ]] && rm -r "$THERMWIN_DP/act_swap"
    cp -r "$THERM_DP/act/act_swap" "$THERMWIN_DP/"
    cp -r "$THERM_DP/ref/ref" "$THERMWIN_DP/"
    cp "$THERM_DP/ref/ref.osm" "$THERMWIN_DP/"
    cp "$THERM_DP/act/act_swap.osm" "$THERMWIN_DP/"
}
#mk_hb_model_swap () {
#    # Create HB_MODEL_DIR for future swap model 
#    HB_SWAP_DP="${HB_MODEL_DP}_Swap" 
#    if [ ! -d "$HB_SWAP_DP" ]; then
#        cp -r "$HB_MODEL_DP" "$HB_SWAP_DP"
#    else
#        cp -u "ACT_OSM" "$HB_SWAP_DP/openstudio/run/in.osm"
#    fi
#}

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
        STDIN_VAR=$1 
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
    exit 1
fi

if [[ "$1" == "-swap_sim" ]]; then
    echo "Create ./act/act_swap dir"
    ACT_SWAP_DP="$ACT_DP/act_swap"
    [[ -d "$ACT_SWAP_DP" ]] && \
        rm -rf "$ACT_SWAP_DP"
    mkdir "$ACT_SWAP_DP"
    cp "$ACT_OSW" "$ACT_SWAP_DP/workflow.osw"
    cp "$ACT_EPW" "$ACT_SWAP_DP/in.epw"
    modify_osw "$ACT_SWAP_DP/workflow.osw" "act_swap"
    echo "Simulate ./act/act_swap"
    openstudio run -w "$ACT_SWAP_DP/workflow.osw"
    tail -3 "$ACT_SWAP_DP/run/eplusout.err"
    swap_cp  
    exit 1
elif [[ "$1" == "-swap_cp" ]]; then
    swap_cp
    exit 1
fi

# for arg must be alone on this line
for i in $@; do
    [[ "$i" == "-h" ]] && \
        echo -e "$helpcmd"
    if [[ "$i" == "-cp" ]]; then
        [[ $STDIN_VAR == "ref" ]] && \
            cp_mod ${REF_VARS[@]} || \
            cp_mod ${ACT_VARS[@]}
    fi
    if [[ "$i" == "-sim" ]]; then
        echo "Simulating ref/ref" 
        openstudio run -w "$REF_OSW"
    fi
    if [[ "$i" == "-rm" ]]; then 
        [[ $STDIN_VAR == "ref" ]] && \
            rm_mod "$REF_DP/ref" "$REF_OSM" 'ref' || \
            rm_mod "$ACT_DP/act" "$ACT_OSM" 'act'
    fi
    if [[ "$i" == "-ls" ]]; then 
        [[ $STDIN_VAR == "ref" ]] && \
            ls "$THERM_DP/ref" || \
            ls "$THERM_DP/act"
    fi
done
