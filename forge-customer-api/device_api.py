from database.db import session_scope, pdus, consoles, switches, servers, racks, test_result, serial_number, bmc_card
from database.db import storage_devices, server_network_cards, pdu_connections, switch_connections, chassis, modules

from sqlalchemy.sql    import and_

import helpers
import datetime
import pendulum

from flask import Blueprint, request, jsonify


deviceapi = Blueprint('deviceapi', __name__)

@deviceapi.route("/orders/", methods=['GET', 'POST'])
def orders():
    api_key = request.args.get('api_key')

    ## make sure you send something meaningful to caller.
    data    = getPayload(api_key) # 2724dbfcdec0557512cd283f3acfa0cbdad6c584
    
    return jsonify(data)


@deviceapi.route("/orders/<string:start_date>/", methods=['GET', 'POST'])
def ordersByStartDate(start_date):
    ### get api key
    api_key = request.args.get('api_key')

    ### check date format
    start_date_pst = helpers.parse_date(start_date, utc=False)
    
    data    = getPayload(api_key, None, start_date_pst) 

    ### return filtered payload
    return jsonify(data)


@deviceapi.route("/orders/<string:start_date>/<string:end_date>/", methods=['GET', 'POST'])
def ordersByStartDateEndDate(start_date, end_date):
    ### get api key
    api_key = request.args.get('api_key')
    
    ###check date format
    start_date_pst = helpers.parse_date(start_date, utc=False)
    end_date_pst = helpers.parse_date(end_date, utc=False)
    
    data    = getPayload(api_key, None, start_date_pst, end_date_pst)

    ### return filtered payload
    return jsonify(data)

@deviceapi.route("/order/<string:order_number>/", methods=['GET', 'POST'])
def order(order_number):
    api_key = request.args.get('api_key')

    ## make sure you send something meaningful to caller.
    data    = getPayload(api_key, order_number)
    
    return jsonify(data)

# adding this api for returning orders based on redapt order number
@deviceapi.route("/order_by_redapt_order/<string:redapt_order_number>/", methods=['GET', 'POST'])
def redaptOrder(redapt_order_number):
    api_key = request.args.get('api_key')

    data    = getPayload(api_key, None, None, None, redapt_order_number)
    
    return jsonify(data)


### Function that makes the SQL call to get rack components
def getPayload(api_key, order_number = None, start_date = None, end_date = None, redapt_order_number = None):
    with session_scope() as session:
        customer_orgs = helpers.get_customer_allowed_orgs(session, api_key)
        rack_components = getRackComponents(session, customer_orgs, order_number, start_date, end_date, redapt_order_number)
        return rack_components

def componentData(session, customer_orgs, order_number, table_obj, start_date = None, end_date = None, redapt_order_number = None):
    # base query. filter by customer org, only devices marked 'released to ship', and
    # add a 2 hour delay from current time before exposing data
    q = session.query(table_obj)\
        .filter(table_obj.c.customer.in_(customer_orgs))\
        .filter(pendulum.now(tz='UTC').subtract(hours=2).to_datetime_string() >= table_obj.c.update_date)\
        .filter(table_obj.c.released_to_ship.isnot(None))

    if start_date and end_date:
        q = q.filter(and_(table_obj.c.update_date >= start_date, table_obj.c.update_date <= end_date))
    elif start_date:
        q = q.filter(table_obj.c.update_date >= start_date)        

    if order_number is not None:
        q = q.filter(table_obj.c.purchase_order == order_number)
    # adding this filter for returning orders based on redapt order number
    if redapt_order_number is not None:
        q = q.filter(table_obj.c.build == redapt_order_number)       
    
    return q.all()

### function to get rack components
def getRackComponents(session, customer_orgs, order_number, start_date = None, end_date = None, redapt_order_number = None):
    records     = []
    results     = {}
    component_tables = [ racks, servers, storage_devices, consoles, switches, pdus, chassis ]

    # pull this out of the loop....SN requires blank fields but they are stupid. see below where `service_now` is used
    # and Box wants burn results in the payload
    service_now = 'SERV-08' in customer_orgs
    box         = 'BOXN-01' in customer_orgs

    ### get server components
    for component_type in component_tables:
        q   = componentData(session, customer_orgs, order_number, component_type, start_date, end_date, redapt_order_number)
    
        if q is not None or len(q) > 0:
            for s in q:
                # this is a hack for discrete asset builds (you have to put them in under a rack in MCAP,
                # but since that "rack" isn't real, we need to hide it from the API)
                if s.device_type == 'rack' and s.serial.lower() == 'no_serial':
                    continue

                component                    = {}

                # ServiceNow only fields
                if service_now:
                    component['A_Core/DSR_Port'] = ""
                    component['B_Core/DSR_Port'] = ""
                    component['PDU-B1-PS1']      = ""
                    component['PDU-B2-PS2']      = ""
                    component['PDU-B1-PS3']      = ""
                    component['PDU-B2-PS4']      = ""
                    
                    if 'pir_sku' in s.keys():
                        component['PIR_SKU']         = s.pir_sku

                ### map common components
                component['Device_Type']     = s.device_type
                component['interfaces']      = []

                # Removed as to not expose "Update_Date" to the customer.
                # if  ('update_date') in s.keys() and s.update_date:
                #     component['Update_Date'] = s.update_date.strftime('%Y-%m-%d %H:%M:%S')
                # else:
                #     component['Update_Date'] = ''

                component['PO']              = s.purchase_order
                component['Name']            = s.name
                component['Asset_Tag']       = s.asset_tag
                
                component['SKU']             = ""
                if 'customer_sku' in s.keys():
                    component['SKU']         = s.customer_sku or ""
                component['Model']           = s.model
                component['Serial']          = s.serial
                component['Manufacturer']    = s.vendor
                component['U_Slot']          = "0"
                if 'u_slot' in s.keys():
                    component['U_Slot']          = str(s.u_slot)
                
                # Adding these new columns for SNow as they are requested for new devices
                if 'total_nodes' in s.keys() and s.total_nodes is not None:
                    component['Total_nodes']     = str(s.total_nodes)  
                
                if 'installed_nodes' in s.keys() and s.installed_nodes is not None:
                    component['Installed_nodes'] = str(s.installed_nodes)

                pdu_portmaps = session.query(pdu_connections).filter(pdu_connections.c.source_profile_id == s.profile_id).all()
                for portmap in pdu_portmaps:
                    target = portmap.target_port
                    if target.startswith('P'):
                        target = target[1:]
                    component['{0}-{1}'.format(portmap.target_name, portmap.source_port)] = target
                
                # servers only. grab uuid and put in blob. Per ServiceNow's request 10-13-18
                if s.device_type == 'server':
                    component['uuid'] = s.sys_uuid or ''
                component['RedaptOrderNumber'] = s.build # show redapt order number in the payload output

                # things common to servers and mass_storage
                if s.device_type == 'server' or s.device_type == 'mass_storage' or s.device_type == 'storage_node' or s.device_type == 'server_node':
                    try:
                        bmc_portmap           = session.query(switch_connections) \
                                                   .filter(switch_connections.c.source_profile_id == s.profile_id) \
                                                   .filter(switch_connections.c.source_port == "mgmt") \
                                                   .all()[0]
                        bmc_target            = '{0}-{1}'.format(bmc_portmap.target_name, bmc_portmap.target_port)
                    except:
                        bmc_target = ''

                    try:
                        sys_bmcs = session.query(bmc_card).filter(bmc_card.c.profile_id == s.profile_id).all()
                        for bmc in sys_bmcs:
                            component['interfaces'].append({'Name': 'DRAC',
                                                            'MAC': bmc.hw_address, 
                                                            'RSW_Port': bmc_target,
                                                            'Type': 'PMI',
                                                            'Bus': '',
                                                            'Device': '',
                                                            'Function': ''})
                    except:
                        pass
                        # print '  *** Could not find BMC MAC Address for device w/serial {0}'.format(s.serial)

                    system_network_cards  = session.query(server_network_cards) \
                                                   .filter(s.profile_id == server_network_cards.c.profile_id) \
                                                   .all()
                    network_card_portmaps = session.query(switch_connections) \
                                                   .filter(switch_connections.c.source_profile_id == s.profile_id) \
                                                   .filter(switch_connections.c.source_port != "mgmt") \
                                                   .all()
                    
                    for iface in system_network_cards:
                        portmap = [ x for x in network_card_portmaps if x.source_port == iface.logical_id ]
                        target_port = '{0}-{1}'.format(portmap[0].target_name, portmap[0].target_port) if portmap else ''
                        source_port_name = iface.logical_id or ''
                        # iface_type is a little confusing to me, since all cards of all types use the PCI bus, but here is SN's spec:
                        # Integrated is onboard Ethernet
                        # PCI is a PCI Ethernet card
                        # PMI is the iDrac interface -- this case is handled a few lines above when BMC cards are enumerated
                        iface_type = 'Integrated' if iface.logical_id.startswith('eno') else 'PCI'
                        component['interfaces'].append({'Name':source_port_name,
                                                        'MAC':iface.address,
                                                        'RSW_Port': target_port,
                                                        'Type': iface_type,
                                                        'Bus': "{}".format(iface.pci_bus),
                                                        'Device': "{}".format(iface.pci_device),
                                                        'Function': "{}".format(iface.pci_function)})

                # specific for servers and only for customer Box (right now)
                # key: blank means the test was not run. string "true" means the test was run.
                # string "false" should never be used since we wouldn't ship a customer a box with
                # a failed burn test...lol. whatever format they want they shall get.
                if s.device_type == 'server' and box:
                    component['CPU_BURNIN']     = ""
                    if did_test_succeed(session, s.serial, "cpu"):
                        component['CPU_BURNIN'] = "true"

                    component['MEM_BURNIN']     = ""
                    if did_test_succeed(session, s.serial, "memory"):
                        component['MEM_BURNIN'] = "true"

                    component['DISK_BURNIN']    = ""
                    if did_test_succeed(session, s.serial, "hdd"):
                        component['DISK_BURNIN'] = "true"

                    component['NETWORK_BURNIN'] = ""
                    if did_test_succeed(session, s.serial, "network"): 
                        component['NETWORK_BURNIN'] = "true"

                    component['INTEGRATION']    = "true"

                # specific for PDUs
                if s.device_type == 'pdu': 
                    pdu_switchportmaps = session.query(switch_connections) \
                                                .filter(s.profile_id == switch_connections.c.source_profile_id).all()
                    if pdu_switchportmaps:
                        target_port = '{0}-{1}'.format(pdu_switchportmaps[0].target_name,pdu_switchportmaps[0].target_port)
                        component['interfaces'].append({'Name': 'MGMT_Port', 'MAC': s.mac_address, 
                                                        'RSW_Port': target_port})

                # specific for network stuffs
                if s.device_type == 'switch' or s.device_type == 'console':
                    component['interfaces'].append({'Name': 'MGMT_Port', 'MAC': s.mac_address})

                if service_now:
                    if s.device_type == 'mass_storage':
                            modules_list = session.query(modules).filter(s.storagedevice_id == modules.c.maindevice_id).all()
                            if s.device_subtype == 'flashblade':
                                component['modules'] = []
                                for module in modules_list:
                                    component['modules'].append({'Name': str(module[0]), 'Serial': str(module[1])})
                            if s.device_subtype == 'flasharray':    
                                component['controllers'] = []
                                for controller in modules_list:
                                    component['controllers'].append({'Name': str(controller[0]), 'Serial': str(controller[1])})

                    if s.device_type == 'storage_chassis':
                            modules_list = session.query(modules).filter(s.chassis_id == modules.c.device_module_chassis_id).all()
                            component['modules'] = []
                            component['controllers'] = []

                            for module in modules_list:
                                if module.device_subtype == 'flashblade': 
                                    component['modules'].append({'Name': str(module[0]), 'Serial': str(module[1])})
                                elif module.device_subtype == 'flasharray':
                                    component['controllers'].append({'Name': str(module[0]), 'Serial': str(module[1])})                

                    if s.device_type == 'mass_storage' or s.device_type == 'storage_node':
                        if 'chassis_serial' in s.keys() and s.chassis_serial is not None:
                            component['storage_chassis'] = str(s.chassis_serial)
                        if 'ru_position' in s.keys() and s.ru_position is not None:
                            component['ru_position'] = str(s.ru_position)    

                    if s.device_type == 'server' or s.device_type == 'server_node':
                        if 'chassis_serial' in s.keys() and s.chassis_serial is not None:
                            component['server_chassis'] = str(s.chassis_serial)
                        if 'ru_position' in s.keys() and s.ru_position is not None: 
                            component['ru_position'] = str(s.ru_position)

                records.append(component)

    results['records'] = records    
    return results

def did_test_succeed(session, serial, test_type):
    serial_id = session.query(serial_number).filter(serial_number.c.number == serial).first().id
    test_results = session.query(test_result).filter(test_result.c.serial_number_id == serial_id) \
                                             .filter(test_result.c.test_type == test_type) \
                                             .filter(test_result.c.success == 1).all()
    return len(test_results) > 0    
