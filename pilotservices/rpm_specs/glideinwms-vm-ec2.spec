Name:               glideinwms-vm-ec2
Version:            0.0.1
Release:            3

Summary:            The glideinWMS service that contextualizes an EC2 VM
Group:              System Environment/Daemons
License:            Fermitools Software Legal Information (Modified BSD License)
URL:                http://www.uscms.org/SoftwareComputing/Grid/WMS/glideinWMS/doc.v2/manual/
BuildRoot:          %{_tmppath}/%{name}-buildroot
BuildArchitectures: noarch

Source0:        glidein-pilot-ec2.ini

Requires:       glideinwms-vm-core
Conflicts:      glideinwms-vm-nimbus
Conflicts:      glideinwms-vm-one

%description
glideinWMS pilot launcher service for EC2

Sets up a service definition in init.d (glideinwms-pilot) that executes
pilot_launcher.  This script contextualizes an EC2 VM to become a
glideinWMS worker node.  It is responsible for bootstrapping the pilot Condor
StartD and shutting down the VM once the pilot exits.

%build

%install
rm -rf $RPM_BUILD_ROOT

# install the ini
install -d  $RPM_BUILD_ROOT/%{_sysconfdir}/glideinwms
install -m 0755 %{SOURCE0} $RPM_BUILD_ROOT/%{_sysconfdir}/glideinwms/glidein-pilot.ini

%clean
rm -rf $RPM_BUILD_ROOT

%post
# $1 = 1 - Installation
# $1 = 2 - Upgrade
# Source: http://www.ibm.com/developerworks/library/l-rpm2/

%preun
# $1 = 0 - Action is uninstall
# $1 = 1 - Action is upgrade

if [ "$1" = "0" ] ; then
    rm -rf %{_sysconfdir}/glideinwms/glidein-pilot.ini
fi

%files
%defattr(-,root,root,-)
%attr(755,root,root) %config(noreplace) %{_sysconfdir}/glideinwms/glidein-pilot.ini

%changelog
* Mon May 30 2012 Anthony Tiradani  0.0.1-3
- Initial Version

