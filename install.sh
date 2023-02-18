#!/bin/bash

install_ops () {
    # DEFINE OPS URL
    OPS_BASE_URL="https://github.com/NREL/OpenStudio/releases/download"
    #OPS_VERSION_URL="v3.4.0/OpenStudio-3.4.0+4bd816f785-Ubuntu-20.04.tar.gz"
    OPS_VERSION="v3.4.0"
    OPS_FILENAME="OpenStudio-3.4.0+4bd816f785-Ubuntu-20.04.deb"
    OPS_URL=$OPS_BASE_URL/$OPS_VERSION/$OPS_FILENAME
    OPS_FILEPATH=$PWD/$OPS_FILENAME

    # DEPENDENCIES 
    # May or not need these. Uncomment if needed.
    sudo apt-get update
    sudo apt-get install dpkg-dev git cmake-curses-gui cmake-gui \
        libssl-dev libxt-dev libncurses5-dev libgl1-mesa-dev \
        autoconf libexpat1-dev libpng12-dev libfreetype6-dev \
        libdbus-glib-1-dev libglib2.0-dev libfontconfig1-dev \
        libxi-dev libxrender-dev libgeographiclib-dev chrpath

    # DOWNLOAD, INSTALL OPS 
    wget $OPS_URL 
    dpkg -i $OPS_FILEPATH
    rm $OPS_FILEPATH
}

install_pylib () {
    # INSTALL PYTHON LIBRARIES
    pip install -r requirements.txt
}

install_ops
install_pylib

