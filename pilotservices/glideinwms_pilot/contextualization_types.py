"""
Valid Contextualization Types

    EC2 - encompasses all cloud implementations that use a meta-data server that
          responds to http://169.254.169.254/latest/user-data to serve the user-
          data to the VM

    NIMBUS - Nimbus is similar to EC2 in that they use a meta-data server to 
          serve the user-data, but they require an extra step.  You must look in
          the /var/nimbus-metadata-server-url file to determine the address of 
          the meta-data server.
          NOT SUPPORTED ANY MORE

    GCE

    OPENNEBULA
""" 


# Code for Nimbus is experimental and was written several years back
# It is most likely broken now so disable it until more testing is done
CONTEXTS = {
    'EC2': 'EC2',
    #'NIMBUS': 'Nimbus',
    'OPENNEBULA': 'One',
    'GCE': 'GCE'
}

def is_context_valid(context):
    return (context.upper() in CONTEXT_TYPES)


def valid_contexts():
    return CONTEXTS.keys()
