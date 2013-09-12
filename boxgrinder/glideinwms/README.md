# Vanilla glideinWMS Example

This example will install a generic no frills VM compatible with glideinWMS.

On Fedora 18:

/usr/lib/python2.7/site-packages/imgcreate/kickstart.py

```python
    """A class to apply a kickstart firewall configuration to a system."""
    def apply(self, ksfirewall):
        #args = ["/usr/bin/firewall-offline-cmd"]
        args = ["/usr/sbin/lokkit"]
```

/usr/share/gems/gems/boxgrinder-build-0.10.4/lib/boxgrinder-build/helpers/guestfs-helper.rb

```ruby
      #@guestfs.aug_rm("/augeas/load//incl[. != '/etc/sysconfig/selinux']")
      @guestfs.aug_rm("/augeas/load//incl[. != '/etc/selinux/config']")
      #selinux = @guestfs.aug_get("/files/etc/sysconfig/selinux/SELINUX")
      selinux = @guestfs.aug_get("/files/etc/selinux/config/SELINUX")
```

https://issues.jboss.org/browse/BGBUILD-380?page=com.atlassian.jira.plugin.system.issuetabpanels:all-tabpanel