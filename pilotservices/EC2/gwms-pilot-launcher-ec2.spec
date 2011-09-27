# Define custom macros
%define is_fedora %(test -e /etc/fedora-release && echo 1 || echo 0)

Name:               gwms-pilot-launcher-ec2
Version:            0.0.1
Release:            3

Summary:            The glideinWMS service that contextualizes an Amazon EC2 AMI
Group:              System Environment/Daemons
License:            Fermitools Software Legal Information (Modified BSD License)
URL:                http://www.uscms.org/SoftwareComputing/Grid/WMS/glideinWMS/doc.v2/manual/
BuildRoot:          %{_builddir}
BuildArchitectures: noarch

#Requires:
#BuildRequires:

Source0:        glideinwms-pilot
Source1:        pilot-launcher

Requires(post): /sbin/service
Requires(post): /usr/sbin/useradd
Requires(post): /sbin/chkconfig
Requires(post): /usr/sbin/groupadd
Requires(post): /usr/sbin/useradd

%description
glideinWMS pilot launcher service

Sets up a service definition in init.d (glideinwms-pilot) that executes
pilot-launcher.  This script contextualizes an Amazon AMI to become a
glideinWMS worker node.  It is responsible for bootstrapping the pilot Condor
StartD and shutting down the AMI once the pilot exits.

%prep
#%setup -q

%build
#make %{?_smp_mflags}

%pre
# Make user glidein_pilot
/usr/sbin/groupadd -g 91234 glidein_pilot
/usr/sbin/useradd -M -g 91234 -u 91234 -d /mnt/glidein_pilot -s /bin/bash glidein_pilot

%install
rm -rf $RPM_BUILD_ROOT

# Install the init.d
install -d  $RPM_BUILD_ROOT/%{_initrddir}
install -m 0755 %{SOURCE0} $RPM_BUILD_ROOT/%{_initrddir}/glideinwms-pilot

# install the executables
install -d $RPM_BUILD_ROOT%{_sbindir}
install -m 0500 %{SOURCE1} $RPM_BUILD_ROOT%{_sbindir}/pilot-launcher

%post
# $1 = 1 - Installation
# $1 = 2 - Upgrade
# Source: http://www.ibm.com/developerworks/library/l-rpm2/

/sbin/chkconfig --add glideinwms-pilot
/sbin/chkconfig glideinwms-pilot on

sed -i "s/SERVICE_VERSION = 0/SERVICE_VERSION = %{version}/" %{_sbindir}/pilot-launcher
sed -i "s/SERVICE_RELEASE = 0/SERVICE_RELEASE = %{release}/" %{_sbindir}/pilot-launcher

%preun
# $1 = 0 - Action is uninstall
# $1 = 1 - Action is upgrade

if [ "$1" = "0" ] ; then
    /sbin/chkconfig --del glideinwms-pilot
    /usr/sbin/userdel -f glidein_pilot

    rm -rf %{_sbindir}/pilot-launcher
    rm -rf %{_initrddir}/glideinwms-pilot
fi

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%attr(755,root,root) %{_sbindir}/pilot-launcher
%attr(755,root,root) %{_initrddir}/glideinwms-pilot


%changelog
* Tue Sep 27 2011 Anthony Tiradani  0.0.1-4
- Changed the names of the source files
* Wed Jun 1 2011 Anthony Tiradani  0.0.1-3
- Changed the name of the rpm package to be consistent across versions
* Mon Oct 18 2010 Anthony Tiradani  0.0.1-1
- Initial Version

