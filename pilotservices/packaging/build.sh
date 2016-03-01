#!/bin/bash

fullpath=`readlink -e $0`
mydir=`dirname $fullpath`
build_home=`readlink -e $mydir/..`

export BUILD_HOME=$build_home

function setup_rpmbuild
{
    # setup the rpmbuild area
    mkdir -p $BUILD_HOME/rpmbuild/BUILD \
             $BUILD_HOME/rpmbuild/RPMS \
             $BUILD_HOME/rpmbuild/RPMS \
             $BUILD_HOME/rpmbuild/SOURCES \
             $BUILD_HOME/rpmbuild/SPECS \
             $BUILD_HOME/rpmbuild/SRPMS

    export RPM_TOPDIR=$BUILD_HOME/rpmbuild
}

function setup_rmpmmacros
{
    # setup rmpmmacros
    export RPMMACROS_EXISTS=0
    if [ -f ~/.rpmmacros ]
    then
        export RPMMACROS_EXISTS=1
        mv ~/.rpmmacros ~/rpmmacros_save
    fi
    cp rpmmacros ~/.rpmmacros
}

function build_source_tarball
{
    # Build the source tar for rpm_build
    tar --create --gzip --verbose --files-from=$BUILD_HOME/source_list.txt --file=$BUILD_HOME/glideinwms_pilot.tar.gz
    mv $BUILD_HOME/glideinwms_pilot.tar.gz $RPM_TOPDIR/SOURCES
}

function setup_spec_files
{
    cp $BUILD_HOME/rpm_specs/glideinwms-vm.spec $RPM_TOPDIR/SPECS/
}

function build_rpms
{
    # build the srpm
    rpmbuild --define "_source_filedigest_algorithm md5" --define "_binary_filedigest_algorithm md5" -bs $RPM_TOPDIR/SPECS/glideinwms-vm.spec

    mkdir -p $BUILD_HOME/srpms
    cp -r $RPM_TOPDIR/SRPMS/* $BUILD_HOME/srpms
    cd $BUILD_HOME/srpms
    srpm_to_build=$(ls -pt $BUILD_HOME/srpms | grep -v '/$' | head -1)
    #mock -r epel-6-x86_64 --no-clean rebuild $srpm_to_build
    #mock -r epel-5-x86_64 --no-clean rebuild $srpm_to_build
    mock -r epel-6-x86_64 --rebuild $srpm_to_build
    #mock -r epel-5-x86_64 --rebuild $srpm_to_build
}

function cleanup
{
    # Remove custom .rpmmacros and restore original .rpmmacros if necessary
    rm -rf ~/.rpmmacros
    if [[ $RPMMACROS_EXISTS -eq 1 ]]; then
        mv ~/rpmmacros_save ~/.rpmmacros
    fi

    # remove the rpmbuild directory
    rm -rf $RPM_TOPDIR
}

function main
{
    # setup rpmbuild environment
    echo "setup rpmbuild environment"
    setup_rpmbuild
    setup_rmpmmacros

    # prepare the source and put it in the proper location
    echo "prepare the source and put it in the proper location"
    build_source_tarball
    setup_spec_files

    # actually build the rpm 
    echo "build rpms"
    build_rpms

    # cleanup after ourselves
    echo "clean up"
    #cleanup
}

main


