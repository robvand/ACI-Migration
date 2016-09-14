#!/usr/bin/env python
"""
Originally created for x Proof of Concept

This script will extend VLANs entering the ACI fabric over a single vPC pair.
It will create BDs and EPGs under a tenant/context/AP of your chosing to create a 1:1 vlan mapping to the external network
It is also possible to automatically add a (VMM) domain association to each EPG.

//Rob van der Kind - robvand@cisco.com
"""
import acitoolkit.acitoolkit as aci
import csv
import getpass
import sys

def main():
    """
    Main create routine
    :return: None
    """

# Login to the APIC
session = aci.Session(raw_input("APIC URL: "), raw_input("APIC username: "), getpass.getpass())
resp = session.login()
if not resp.ok:
    print('%% Could not login to APIC')

if resp.ok:
    print ("\nApic login successful")

# Selecting Tenant
tenants = aci.Tenant.get(session)
print ('\n')
print ('-------')
print ('Tenants')
print ('-------')
for temp_tenant in tenants:
    print(temp_tenant)
tenant_name = raw_input("\nPlease enter the Tenant name: ")
tenant = aci.Tenant(tenant_name)

# Selecting Application Profile
application_profiles = aci.AppProfile.get(session, tenant)
print ('\n')
print ('--------------------')
print ('Application Profiles')
print ('--------------------')
for temp_app_profile in application_profiles:
    print(temp_app_profile)
app = aci.AppProfile(raw_input("\nPlease enter the AP name: "), tenant)
contexts = aci.Context.get(session, tenant)

# Selecting VRF or Context for BDs to be created
print ('\n')
print ('--------')
print ('Contexts')
print ('--------')
for temp_context in contexts:
    print(temp_context)
context_name = raw_input("\nPlease enter a context for the new BDs: ")

# Select VPC path, defaults to node 101 & 102, edit if required
vpcs = aci.PortChannel.get(session)
print ('\n')
print ('---------')
print ('vPC paths')
print ('---------')
for vpc in vpcs:
    print (vpc)
vpc_name = raw_input("\nEnter the vPC name please: ")
VPC_DN = "topology/pod-1/protpaths-101-102/pathep-[{}]".format(vpc_name)

# Select domain type
print ('\n')
print ('-----------')
print ('Domain Type')
print ('-----------')
print ('VMM Domain')
print ('L2')
print ('L3')
print ('Phys')

domain_type = raw_input("\nEnter the domain type please: ")
if domain_type == str("VMM Domain"):
    domains = aci.VmmDomain.get(session)
    print ("")
    print ('----------')
    print ('VMM Domain')
    print ('----------')

    for domain in domains:
        print domain.name

    vmm_domain_type = raw_input("\nEnter the VMM Domain type (VMware or Microsoft): ")
    if vmm_domain_type == str("VMware"):
        domain_type_prefix = "uni/vmmp-VMware/dom-"

    elif vmm_domain_type == str("Microsoft"):
        domain_type_prefix = "uni/vmmp-Microsoft/dom-"

elif domain_type == str("L2"):
    domain_type_prefix = "uni/l2dom-"
    domains = aci.L2ExtDomain.get(session)
    print ("")
    print ('------------------')
    print ('L2 External Domain')
    print ('------------------')

    for domain in domains:
        print domain.name

elif domain_type == str("L3"):
    domain_type_prefix = "uni/l3dom-"
    domains = aci.L3ExtDomain.get(session)
    print ("")
    print ('------------------')
    print ('L3 External Domain')
    print ('------------------')

    for domain in domains:
        print domain.name

elif domain_type == str("Phys"):
    domain_type_prefix = "uni/phys-"
    domains = aci.PhysDomain.get(session)
    print ("")
    print ('---------------')
    print ('Physical domain')
    print ('---------------')

    for domain in domains:
        print domain.name

domain_name = raw_input("\nEnter the domain name please: ")
domain_DN = domain_type_prefix + domain_name

    # Importing CSV file containing VLAN,VLAN Name
filename = raw_input("\nPlease enter the path to your .CSV: ")
f = open(filename, 'rt')

input_vlan_bd_pairs = []
extended_vlan_count = 0

try:
    reader = csv.reader(f)
    for row in reader:
        input_vlan_bd_pairs.append(row)
finally:
    f.close()

for vlan_bd_pair in input_vlan_bd_pairs:
    vlan_id = vlan_bd_pair[0]
    bd_name = vlan_bd_pair[1]

    # Creating new Bridge domain, change values if required
    new_bridge_domain = aci.BridgeDomain(bd_name, tenant)
    new_bridge_domain.set_arp_flood("yes")
    new_bridge_domain.set_unicast_route("no")
    new_bridge_domain.set_unknown_mac_unicast("flood")
    new_bridge_domain.set_unknown_multicast("flood")
    new_bridge_domain.add_context(aci.Context(context_name, tenant))
    #new_bridge_domain.set  MULTIDEST FLOODING

    # Associate EPG with BD
    epg = aci.EPG(bd_name, app)
    epg.add_bd(new_bridge_domain)

    # Associate path with EPG
    static_binding = {"fvRsPathAtt":{"attributes":{"encap":"vlan-{}".format(vlan_id),
                                                   "tDn": VPC_DN,
                                                   "instrImedcy":"lazy",
                                                   "status":"created"}}}

    domain = {"fvRsDomAtt":{"attributes":{#"encap":"vlan-{}".format(vlan_id),   <- uncomment for static encap. Should be defined in a pool
                                          "tDn": domain_DN,
                                          "instrImedcy":"lazy",
                                          "status":"created"}}}


    # Push the changes to the APIC
    resp = session.push_to_apic(tenant.get_url(),
                                tenant.get_json())
    epgurl = '/api/node/mo/uni/tn-{}/ap-{}/epg-{}.json'.format(tenant.name, app.name, epg.name)

    if not resp.ok:
        print('%% Error: Could not push configuration to APIC')
        print(resp.text)

    domain_server_response = session.push_to_apic(epgurl, domain)

    if not resp.ok:
        print('%% Error: Could not push configuration to APIC')
        print(resp.text)

    static_binding_server_response = session.push_to_apic(epgurl, static_binding)

    if resp.ok:
        extended_vlan_count = extended_vlan_count + 1
        print("{}/{} Succesfully extended VLAN {} to ACI fabric").format(extended_vlan_count, len(input_vlan_bd_pairs),bd_name)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
