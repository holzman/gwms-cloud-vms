#!/bin/sh

usage="USAGE: $0 <path to rpm file> [prod]"
remote_cmd() {
    cmd=$1
    ssh $repologin "$cmd"
}

#rpmfile=$1
repo=$1

#if [ "$rpmfile" = "" ]; then
#    echo "Specify rpm file"
#    echo $usage
#    exit 1
#fi

# Check with Parag or Tony to get access to the repo
repologin="fnalu.fnal.gov"
repodir='/web/sites/glideinwms.fnal.gov/htdocs/rpms/'

# Root directory where mock puts the files
mockdir="/var/lib/mock"

#For now only EL6 support
versionlist='6'

#For now only 64bit support
archlist='x86_64'

# Create repo for dev (developers) and one for production (operations)
#flavors='release development'
flavors='development'

#make changes where appropiate (eg: scp new rpms)
for flavor in $flavors; do
    for version in $versionlist; do
        for arch in $archlist; do
            workdir="$repodir/$flavor/el$version/$arch"
            sourcedir="$mockdir/epel-$version-$arch/result"
            remote_cmd "mkdir -p $workdir"
            scp $sourcedir/*rpm "$repologin:$workdir"
            remote_cmd "createrepo $workdir"
            #remote_cmd "chmod -R g+w $workdir"
         done
    done
done
