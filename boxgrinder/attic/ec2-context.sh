#!/bin/bash
########################################
# OLD DO NOT USE - Kept for history sake
########################################

# Since we are putting scripts here, better to make sure the dir exists
mkdir -p /usr/local/bin

################################################################################
#### Nimbus Specific - Image Contextualization
################################################################################

#### Nimbus needs to have /root/.ssh created so that the create-keypair call will succeed - shouldn't hurt on an Amazon EC2 image
mkdir -p /root/.ssh

################################################################################
#### CVMFS Specific - Image Contextualization
################################################################################

#### Configure CernVM FS
mkdir -p /etc/cvmfs/local.d
cat > /etc/cvmfs/default.local << EOF
CVMFS_REPOSITORIES=cms.cern.ch
CVMFS_HTTP_PROXY="http://red-squid1.unl.edu:3128|http://red-squid2.unl.edu:3128;DIRECT"
CVMFS_CACHE_BASE=/var/scratch/cvmfs
EOF

echo "user_allow_other" > /etc/fuse.conf
echo "/cvmfs /etc/auto.cvmfs" > /etc/auto.master
sed -i '/automount/s|nisplus||' /etc/nsswitch.conf
chown root:fuse /bin/fusermount
chmod 4750 /bin/fusermount

#### add to /etc/init.d/cvmfs after the install has been completed
sed -i "s,. /etc/init.d/functions\n\nRETVAL=0\n,. /etc/init.d/functions\n\nRETVAL=0\n\nmkdir -p /mnt/cvmfs2\ncd /var/cache/\nln -s /mnt/cvmfs2 cvmfs2\n\n,g" /etc/init.d/cvmfs

################################################################################
#### CMS Specific - Image Contextualization
################################################################################

#### CMS configuration files
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
        <proxy url="http://cache01.hep.wisc.edu:80"/>
        <proxy url="http://cache02.hep.wisc.edu:80"/>
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

################################################################################
#### General - Image Contextualization
################################################################################

#### Services we want at boot
/sbin/chkconfig fetch-crl-cron on
/sbin/chkconfig --level 345 cvmfs on
/sbin/chkconfig --level 345 autofs on
