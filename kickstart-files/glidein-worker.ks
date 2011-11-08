# bg_os_name: centos
# bg_os_version: 5

# Use network installation
url --url="http://newman.ultralight.org/os/centos/5/x86_64"
repo --name="Updates" --baseurl=http://newman.ultralight.org/mirror/centos/5/updates/x86_64 --cost=99
repo --name="CernVM" --baseurl=http://cvmrepo.web.cern.ch/cvmrepo/yum/cvmfs/x86_64/ --cost=99
repo --name="EPEL" --baseurl=http://download.fedora.redhat.com/pub/epel/5/x86_64/ --cost=99
repo --name="OSG" --baseurl=http://repo.grid.iu.edu/osg-testing/x86_64/ --cost=98

# System keyboard
keyboard us

# System language
lang C

#--- skip X-Windows configuration
skipx

# System authorization information
auth --useshadow --enablemd5

# Firewall configuration
firewall --disabled

# SELinux configuration
selinux --disabled

# Network information
network  --bootproto=dhcp --device=eth0 --onboot=on

# Installation logging level
logging --level=info

# Reboot after installation
reboot

# System services
services --enabled="network"

# System timezone
timezone  US/Central

# System bootloader configuration
zerombr
#bootloader --append="acpi=force" --location=mbr --timeout=1
bootloader --location=mbr

# Disk partitioning information
#part /boot  --fstype="ext2" --ondisk=hda --size=200
part /  --fstype="ext2" --ondisk=hda --size=10240

%packages --nobase
# According to http://lists.centos.org/pipermail/centos/2009-April/075627.html
# these are the bare minimum rpms for a functional install
audit-libs
basesystem
bash
beecrypt
bzip2-libs
centos-release
centos-release-notes
chkconfig
coreutils
cpio
cracklib
cracklib-dicts
db4
device-mapper
device-mapper-event
device-mapper-multipath
dhclient
diffutils
dmraid
e2fsprogs
e2fsprogs-libs
elfutils-libelf
ethtool
expat
filesystem
findutils
gawk
gdbm
glib2
glibc
glibc-common
grep
grub
gzip
info
initscripts
iproute
iputils
keyutils-libs
kpartx
krb5-libs
less
libacl
libattr
libcap
libgcc
libselinux
libsepol
libstdc++
libsysfs
libtermcap
lvm2
m2crypto
MAKEDEV
mcstrans
#mingett
-mkinitrd
mktemp
module-init-tools
nash
ncurses
net-tools
openssl
pam
passwd
pcre
popt
procps
psmisc
python
readline
redhat-logos
rootfiles
rpm
rpm-libs
sed
setarch
setup
shadow-utils
sqlite
sysklogd
SysVinit
tar
termcap
tzdata
udev
util-linux
vim-minimal
which
yum
zlib

# additional packages beyond the bare minimum
openssh
openssh-clients
openssh-server

# CERN VM FS
cvmfs
cvmfs-init-scripts

# Grid "stuff"
osg-ca-certs
osg-wn-client
fetch-crl

# Packages in the Core group tagged as 'default' can be configured to not
# be installed by subtracting them in the %packages section.
-audit-libs-python
-checkpolicy
-dhcpv6-client
-ecryptfs-utils
-ed
-file
-gnu-efi
-gpm
-hdparm
-kbd
-libhugetlbfs
-libselinux-python
-libsemanage
-nspr
-nss
-perl
-policycoreutils
-prelink
-selinux-policy
-selinux-policy-targeted
-setools
-setserial
-sysfsutils
-tcl
-udftools
-vim-enhanced

%post --logfile /root/anaconda-post.log
# Have the VM report to the console so we can debug with virsh
echo "starting serial port configuration"
sed -i /boot/grub/grub.conf -e '/kernel/s|$| console=ttyS0|'
sed -i /boot/grub/grub.conf -e '/hiddenmenu/s|$|\nserial –speed=115200 –unit=0 –word=8 –parity=no –stop=1\nterminal –timeout=10 serial|'
echo "S0:12345:respawn:/sbin/agetty ttyS0 115200" >> /etc/inittab
echo "ttyS0" >> /etc/securetty
echo "finished serial port configuration"

# Nimbus needs to have /root/.ssh created so that the create-keypair call will succeed - shouldn't hurt on an Amazon EC2 image
mkdir -p /root/.ssh

# Configure CernVM FS
cat > /etc/cvmfs/default.local << EOF
CVMFS_REPOSITORIES=cms.cern.ch
CVMFS_HTTP_PROXY="http://red-squid1.unl.edu:3128|http://red-squid2.unl.edu:3128;DIRECT"
#CVMFS_CACHE_BASE=/var/cache/cvmfs2
#CVMFS_CACHE_DIR=/var/cache/cvmfs2/cms.cern.ch
EOF
echo "user_allow_other" > /etc/fuse.conf
echo "/cvmfs /etc/auto.cvmfs" > /etc/auto.master
sed -i '/automount/s|nisplus||' /etc/nsswitch.conf
chown root:fuse /bin/fusermount
chmod 4750 /bin/fusermount

# Services we want at boot
/sbin/chkconfig fetch-crl-boot on
/sbin/chkconfig fetch-crl-cron on
/sbin/chkconfig --level 345 cvmfs on
/sbin/chkconfig --level 345 autofs on

# CD-ROM for contextualization
mkdir -p /mnt/cdrom
echo "/dev/hdb /mnt/cdrom iso9660 ro 0 0" >> /etc/fstab

# CMS configuration files
mkdir -p /etc/cms/SITECONF/local/{JobConfig,PhEDEx}
cat > /etc/cms/SITECONF/local/JobConfig/site-local-config.xml << EOF
 <site-local-config>
 <site name="T2_US_Nebraska">
    <event-data>
      <catalog url="trivialcatalog_file://etc/cms/SITECONF/local/PhEDEx/storage.xml?protocol=xrootd"/>
    </event-data>

    <local-stage-out>
      <command value="srm-lcg" />
      <catalog url="trivialcatalog_file://etc/cms/SITECONF/local/PhEDEx/storage.xml?protocol=srm"/>
      <se-name value="srm.unl.edu" />
    </local-stage-out>
    <calib-data>
        <frontier-connect>
        <load balance="proxies"/>
        <proxy url="http://red-squid1.unl.edu:3128"/>
        <proxy url="http://red-squid2.unl.edu:3128"/>
        <server url="http://cmsfrontier.cern.ch:8000/FrontierInt"/>
        <server url="http://cmsfrontier1.cern.ch:8000/FrontierInt"/>
        <server url="http://cmsfrontier2.cern.ch:8000/FrontierInt"/>
        <server url="http://cmsfrontier3.cern.ch:8000/FrontierInt"/>
      </frontier-connect>
    </calib-data>
 </site>
 </site-local-config>
EOF
cat > /etc/cms/SITECONF/local/PhEDEx/storage.xml << EOF
<storage-mapping>
  <lfn-to-pfn protocol="xrootd" destination-match=".*" path-match="/+store/(.*)" result="root://xrootd.unl.edu//store/\$1"/>
  <lfn-to-pfn protocol="srmv2"  destination-match=".*" chain="direct" path-match="/+store/(.*)" result="srm://srm.unl.edu:8443/srm/v2/server?SFN=/mnt/hadoop/user/uscms01/pnfs/unl.edu/data4/cms/store/\$1"/>
</storage-mapping>
EOF

%end

