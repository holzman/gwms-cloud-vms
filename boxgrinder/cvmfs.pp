class cvmfs
{
    package
    {
        "cvmfs":
            name => "cvmfs",
            ensure => latest,
            require => User["cvmfs"],
            notify => Service["autofs"],
    }

    package
    {
        "cvmfs-keys":
            name => "cvmfs-keys",
            ensure => present,
            require => Package["cvmfs"],
    }

    package
    {   "fuse":
            name => "fuse.x86_64",
            ensure => present,
    }

    # we run cvmfs as a dedicated user
    group
    {
        "cvmfs":
            name => "cvmfs",
            ensure => present,
            system => true,
    }

    user
    {
        "cvmfs":
        name => "cvmfs",
        ensure => present,
        system => true,
        gid => "cvmfs",
        groups => ["cvmfs", "fuse"],
        require => [Group["cvmfs"], Package["fuse"]],
        managehome => false,
        shell => '/sbin/nologin',
    }

    ## Files for talking to UW's CVMFS.
    file
    {
        "wisc_pubkey":
            path => "/etc/cvmfs/keys/cms.hep.wisc.edu.pub",
            mode => "0644",
            owner => "root",
            group => "root",
            source => "file:///root/cms.hep.wisc.edu.pub",
            ensure => present,
            require => Package["cvmfs"],
    }

    file
    {
        "wisc_conf":
            path => "/etc/cvmfs/config.d/cms.hep.wisc.edu.conf",
            mode => "0644",
            owner => "root",
            group => "root",
            source => "file:///root/cms.hep.wisc.edu.conf",
            ensure => present,
            require => Package["cvmfs"],
    }

    file
    {
        "default.local":
            path => "/etc/cvmfs/default.local",
            mode => "0644",
            owner => "root",
            group => "root",
            source => "file:///root/default.local",
            require => Package["cvmfs"],
            ensure => present,
    }

    ## Files for making CMS CVMFS work.
    file
    {
        "SITECONF_dir":
            path => "/etc/cvmfs/SITECONF",
            mode => "0644", owner => "root", group => "root",
            recurse => true,
            ensure => directory,
            require => Package["cvmfs"],
    }

    file
    {
        "JobConfig_dir":
            path => "/etc/cvmfs/SITECONF/JobConfig",
            mode => "0644", owner => "root", group => "root",
            recurse => true,
            ensure => directory,
            require => File["SITECONF_dir"],
    }

    file
    {
        "local_dir":
            path => "/etc/cvmfs/SITECONF/local",
            mode => "0644", owner => "root", group => "root",
            recurse => true,
            ensure => directory,
            require => File["SITECONF_dir"],
    }

    file
    {
        "phedex_dir":
            path => "/etc/cvmfs/SITECONF/local/PhEDEx",
            mode => "0644", owner => "root", group => "root",
            recurse => true,
            ensure => directory,
            require => File["local_dir"],
    }

    file
    {
        "site-local-config.xml":
            path => "/etc/cvmfs/SITECONF/JobConfig/site-local-config.xml",
            source => "file:///root/site-local-config.xml",
            mode => "0644", owner => "root", group => "root",
            ensure => present,
            require => File["JobConfig_dir"],
    }

    file
    {
        "storage.xml":
            path => "/etc/cvmfs/SITECONF/local/PhEDEx/storage.xml",
            source => "file:///root/storage.xml",
            mode => "0644", owner => "root", group => "root",
            ensure => present,
            require => File["phedex_dir"],
    }

    ## Use FNAL stratum one
    file
    {
        "FNAL_stratum_one":
            path => "/etc/cvmfs/domain.d/cern.ch.local",
            source => "file:///root/cern.ch.local",
            mode => "0644", owner => "root", group => "root",
            ensure => present,
            require => Package["cvmfs"],
    }

    file
    {
        "fuse.conf":
            path => "/etc/fuse.conf",
            mode => "0644",
            owner => "root",
            group => "root",
            source => "file:///root/fuse.conf",
            ensure => present,
    }

    file
    {
        "cvmfs_cache":
            path => "/var/cache/cvmfs2",
            ensure => directory,
            owner => "cvmfs",
            group => "cvmfs",
            mode => 0700,
            require => [User["cvmfs"], Group["cvmfs"], Package["cvmfs"]],
    }

    service
    {
        "cvmfs":
            name => "cvmfs",
            ensure => running,
            enable => true,
            hasrestart => true,
            hasstatus => true,
            require => [Package["cvmfs"], File["default.local"], File["fuse.conf"], File["cvmfs_cache"]],
            subscribe => File["/etc/cvmfs/default.local"],
    }
}


class autofs
{
    package { autofs: name => "autofs", ensure => present }

    service
    {
        "autofs":
            name => "autofs",
            ensure => running,
            enable => true,
            hasrestart => true,
            hasstatus => true,
            require => Package["autofs"],
            subscribe => File["autofs.master"],
    }

    file
    {
        "autofs.master":
            path => "/etc/auto.master",
            mode => 644,
            owner => "root",
            group => "root",
            content => "/cvmfs /etc/auto.cvmfs",
            require => Package[autofs],
            ensure => present,
    }
}

class osg-ca-certs
{
    package { osg-ca-certs: name => "osg-ca-certs", ensure => latest }
}

class osg-wn-client
{
    package { osg-wn-client: name => "osg-wn-client", ensure => present }
}

class fetch-crl
{
    package { fetch-crl: name => "fetch-crl", ensure => present }

    service
    {
        "fetch-crl":
            name => "fetch-crl-cron",
            ensure => running,
            enable => true,
            hasrestart => true,
            hasstatus => true,
            require => Package["fetch-crl"],
    }
}

class {'cvmfs': }
class {'autofs': }
class {'osg-wn-client': }
class {'osg-ca-certs': }
class {'fetch-crl': }
