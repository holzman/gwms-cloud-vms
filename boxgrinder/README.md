# Building a glideinWMS Virtual Machine with BoxGrinder

As of version 10.4, BoxGrinder has a couple of fatal bugs in it that will 
prevent you from using the EC2 and S3 plugins to automatically build and push to
Amazon.  The boxgrinder/patches directory contains several patches that fix 
them.  John Hover from BNL kindly supplied these patches.

To use boxginder's plugins you have to configure them in ~/.boxgrinder/config.
The following is an example of the config I use (minus the credential 
information of course).  Fill in the appropriate information for your setup.

```yaml
plugins:
  sl:
    format: raw      # Disk format to use. Default: raw.

  s3:
    access_key: <REDACTED>             # (required)
    secret_access_key: <REDACTED>      # (required)
    bucket: <Bucket Name>              # (required)
    account_number: XXXX-XXXX-XXXX     # (required)
    path: /                            # default: /
    cert_file: /path/to/cert-XXX.pem   # required only for ami type
    key_file: /path/to/pk-XXX.pem      # required only for ami type
    region: us-east-1                  # amazon region to upload and register amis in; default: us-east-1
    snapshot: false                    # default: false
    overwrite: false                   # default: false
    block-device-mapping: /dev/sdb=ephemeral0
```

The actual command to run is:

```bash
boxgrinder-build hcc-template.appl --debug --trace -p ec2 -d ami
```

If you have configured everything correctly and there are no build errors, you 
will have an AMI uploaded, registered and ready to use in EC2.

