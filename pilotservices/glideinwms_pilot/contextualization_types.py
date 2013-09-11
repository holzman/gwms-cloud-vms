"""
Valid Contextualization Types

    EC2 - encompasses all cloud implementations that use a meta-data server that
          responds to http://169.254.169.254/latest/user-data to serve the user-
          data to the VM

    NIMBUS - Nimbus is similar to EC2 in that they use a meta-data server to 
          serve the user-data, but they require an extra step.  You must look in
          the /var/nimbus-metadata-server-url file to determine the address of 
          the meta-data server.

""" 
CONTEXT_TYPE_EC2 = "EC2"
CONTEXT_TYPE_NIMBUS = "NIMBUS"
CONTEXT_TYPE_OPENNEBULA = "OPENNEBULA"
