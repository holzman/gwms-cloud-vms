# Define custom macros
%define is_fedora %(test -e /etc/fedora-release && echo 1 || echo 0)
# From http://fedoraproject.org/wiki/Packaging:Python
# Define python_sitelib
%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif

Name:               glideinwms-vm-core
Version:            0.1
Release:            1

Summary:            The glideinWMS service that contextualizes a VM
Group:              System Environment/Daemons
License:            Fermitools Software Legal Information (Modified BSD License)
URL:                http://www.uscms.org/SoftwareComputing/Grid/WMS/glideinWMS/doc.v2/manual/
BuildRoot:          %{_tmppath}/%{name}-buildroot
BuildArchitectures: noarch

Source0:        glideinwms_pilot.tar.gz

Requires(post): /sbin/chkconfig
Requires(post): /usr/sbin/groupadd
Requires(post): /usr/sbin/useradd
Requires(post): /bin/chmod

%description
glideinWMS pilot launcher service

Sets up a service definition in init.d (glideinwms-pilot) that executes
pilot_launcher.  This script contextualizes a VM to become a glideinWMS worker 
node.  It is responsible for bootstrapping the pilot Condor StartD and shutting 
down the VM once the pilot exits.

%prep
%setup -q -n glideinwms_pilot

%build
#make %{?_smp_mflags}

%pre
# Make glidein_pilot group
/usr/sbin/groupadd -g 91234 glidein_pilot

# Make glidein_pilot group - Do NOT create the home directory
# On EC2 we are placing the home directory into ephemeral storage.
# The pilot-launcher script will create the directory and set permissions
/usr/sbin/useradd -M -g 91234 -u 91234 -d /mnt/glidein_pilot -s /bin/bash glidein_pilot

# Add glidein_pilot to sudoers so that it can shutdown the VM without a password 
/bin/chmod +w /etc/sudoers
echo glidein_pilot ALL= NOPASSWD: ALL >> /etc/sudoers
/bin/chmod -w /etc/sudoers

%install
rm -rf $RPM_BUILD_ROOT

# For some reason the setup macro cd's into the glideinwms_pilot directory.
# We will move up one directory so that we can access all the source files
# without having to specify relative paths.
cd ..

# "install" the python site-packages directory
install -d $RPM_BUILD_ROOT%{python_sitelib}
# copy the glideinwms_pilot package to the python site-packages directory
cp -arp glideinwms_pilot $RPM_BUILD_ROOT%{python_sitelib}

# install the init.d
install -d  $RPM_BUILD_ROOT/%{_initrddir}
install -m 0755 glideinwms-pilot $RPM_BUILD_ROOT/%{_initrddir}/glideinwms-pilot

# install the "executable"
install -d $RPM_BUILD_ROOT%{_sbindir}
install -m 0500 pilot-launcher $RPM_BUILD_ROOT%{_sbindir}/pilot-launcher

%clean
rm -rf $RPM_BUILD_ROOT

%post
# $1 = 1 - Installation
# $1 = 2 - Upgrade
# Source: http://www.ibm.com/developerworks/library/l-rpm2/

/sbin/chkconfig --add glideinwms-pilot
/sbin/chkconfig glideinwms-pilot on

%preun
# $1 = 0 - Action is uninstall
# $1 = 1 - Action is upgrade

if [ "$1" = "0" ] ; then
    /sbin/chkconfig --del glideinwms-pilot
    /usr/sbin/userdel -f glidein_pilot

    rm -rf %{_sbindir}/pilot-launcher
    rm -rf %{_initrddir}/glideinwms-pilot
    rm -rf %{python_sitelib}/glideinwms-pilot
fi

%files
%defattr(-,root,root,-)
%attr(755,root,root) %{_sbindir}/pilot-launcher
%attr(755,root,root) %{_initrddir}/glideinwms-pilot
%attr(755,root,root) %{python_sitelib}/glideinwms_pilot

%changelog
* Mon Sep 04 2012 Anthony Tiradani  0.0.1-1
- Initial Version

