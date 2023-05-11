from database.db import session_scope, customer, pdus, consoles, switches, servers, racks, chassis
from database.db import storage_devices, gp_shipping_data

from sqlalchemy.sql    import and_

from sqlalchemy import update

import helpers

import datetime
import pendulum

from flask import Blueprint, request, jsonify



shippingapi = Blueprint('shippingapi', __name__)

@shippingapi.route("/shipments/<string:start_date>/<string:end_date>/", methods=['GET', 'POST'])
def shipmentsByStartDateEndDate(start_date, end_date):
    ### get api key
    api_key = request.args.get('api_key')

    ###check date format
    start_date_utc = helpers.parse_date(start_date)
    end_date_utc = helpers.parse_date(end_date)

    data    = getShippingPayload(api_key, None, start_date_utc, end_date_utc)

    ### return filtered payload
    return jsonify(data)


@shippingapi.route("/shipments/<string:start_date>/", methods=['GET', 'POST'])
def shipmentsByStartDate(start_date):
    ### get api key
    api_key = request.args.get('api_key')

    ### check date format
    start_date_utc = helpers.parse_date(start_date)

    data    = getShippingPayload(api_key, None, start_date_utc)

    ### return filtered payload
    return jsonify(data)


@shippingapi.route("/shipments_by_po/<string:order_number>/", methods=['GET', 'POST'])
def shipmentsByOrder(order_number):
    api_key = request.args.get('api_key')

    ## make sure you send something meaningful to caller.
    data    = getShippingPayload(api_key, order_number)

    return jsonify(data)

# adding this api for returning shipments based on redapt order number
@shippingapi.route("/shipments_by_redapt_order/<string:redapt_order_number>/", methods=['GET', 'POST'])
def shipmentsByRedaptOrder(redapt_order_number):
    api_key = request.args.get('api_key')
    data    = getShippingPayload(api_key, None, None,None,redapt_order_number)

    return jsonify(data)

# adding this api for updating shipments timestamp based on redapt invoice number
@shippingapi.route("/update_timestamp_shipments_by_invoice_number/<string:invoice_number>/", methods=['PUT'])
def updateTimestampOfShipmentsByInvoiceNumber(invoice_number):
    with session_scope() as session:
        api_key = request.args.get('api_key')
        # yyyy-mm-dd hh:mm:ss = %Y-%m-%d %H:%M:%S in python strftime
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        #getting the data and updating it directly.
        #synchronize_session - chooses the strategy to update the attributes on objects in the session and "False" syncs the session after a COMMIT for future sessions.
        gp_shipping_data_items = session.query(gp_shipping_data).filter(gp_shipping_data.c.sopnumbe == invoice_number).update({gp_shipping_data.c.updated:current_time}, synchronize_session=False)

        return jsonify({"current_time": current_time}), 200

def getShippingPayload(api_key, order_number = None, start_date = None, end_date = None,redapt_order_number = None):
    with session_scope() as session:
        customer_orgs = helpers.get_customer_allowed_orgs(session, api_key)
        shipping_records = getShippingData(session, customer_orgs, order_number, start_date, end_date, redapt_order_number)
        return shipping_records


def getShippingData(session, customer_orgs, order_number, start_date, end_date, redapt_order_number):
    table_obj = gp_shipping_data
    service_now = 'SERV-08' in customer_orgs
    # base query. add a 2 hour delay from current time before exposing data and always filter by cust org
    # and always filter out CustPOs that are 'DO NOT SEND'
    # and only get invoices that have a tracking number applied
    q = session.query(table_obj)\
        .filter(table_obj.c.CustomerNum.in_(customer_orgs))\
        .filter(pendulum.now(tz='UTC').subtract(hours=3).to_datetime_string() >= table_obj.c.updated)\
        .filter(table_obj.c.TrackingNum != '')\
        .filter(table_obj.c.DcCode != '')\
        .filter(table_obj.c.orignumb.notlike('MPO%'))\
        .filter(table_obj.c.CustPO.notlike('%DO NOT SEND%'))

    # start date and end date filters provided
    if start_date and end_date:
        q = q.filter(and_(table_obj.c.updated >= start_date, table_obj.c.updated <= end_date))
    # just start date filter provided
    elif start_date:
        q = q.filter(table_obj.c.updated >= start_date)

    if order_number is not None:
        q = q.filter(table_obj.c.CustPO == order_number)

    # adding this filter for returning shipments based on redapt order number
    if redapt_order_number is not None:
        print(redapt_order_number)
        q = q.filter(table_obj.c.orignumb == redapt_order_number)
    
    # adding this filter for SNow orders such that DcCode is mandatory
    if service_now:
        q = q.filter(table_obj.c.DcCode != '' and table_obj.c.DcCode is not None)

    return format_shipping_data(session, q)

#technically, SNow asked for distinct *shipments*.
#in our system, the best key we have for this is invoice. it's possible that two invoices
#might share a carrier and tracking num, but this simplifies things enormously for us
#in terms of keeping track of cancelled invoices. otherwise, we'd have to invent the concept
#of a 'shipment' and somehow keep track of it out of band.
#going with invoice num as the primary key for a 'shipment blob' for now.
def format_shipping_data(session, querySet):
    records = []

    # for every x.sopnumbe, we know the other values in the tuple will all match, since these are associated
    # at the invoice level in GP. i.e. every row in gp_shipping_data with the same sopnumbe is
    # guaranteed to have the same shipmethod, trackingnum, shipdate, and deliverydate. I grab all the values in the tuple
    # for convenience in creating the "shipment" json blob before actually getting each individual row from gp_shipping_data
    # to compile the list of items in the shipment.
    distinct_invoices = set([ (x.sopnumbe, x.ShipMethod, x.TrackingNum, x.ShipDate, x.DeliveryDate, x.Voided, x.orignumb, x.FreightCharge, x.DcCode, x.CustPO, x.Palletized, x.BoxCount) for x in querySet.all() ])
    #print "distinct trackingnums: {0}".format(distinct_invoices)
    for tupl in distinct_invoices:
        if tupl[5] == 1:
            void_date = str(tupl[3])
        else:
            void_date = ''

        shipment = { 'VendorShipmentID': tupl[0], 'Carrier': tupl[1], 'TrackingNumber': tupl[2], 'ShipDate': str(tupl[3]), \
                     'ETA': str(tupl[4]), 'CancelledDate': void_date, 'DcCode': str(tupl[8]), 'Palletized': str(tupl[10]), 'BoxCount': str(tupl[11]), 'Items': [] }

        non_po = False

        if "-NP-" in tupl[9] or "NONPO" in tupl[9]:
            non_po = True
            shipment.update({'FreightCharge': str(tupl[7])})

        # when the original queryset is obtained, one or more line items might have a timestamp newer than all the
        # rest of the items on that shipment/invoice. if just the line item(s) with the newer timestamp is displayed
        # to the API consumer, API consumer could think that that shipment includes only those newer line items.
        # we need to go back and query ALL the line items on that shipment to display to consumer, so there's no confusion,
        # instead of just filtering down the existing querySet variable for each distinct_invoice.
        # basically, if ANY line item on an invoice has a timestamp that falls within a consumer's query date range,
        # we need to re-display ALL line items for that invoice
        items = session.query(gp_shipping_data).filter(gp_shipping_data.c.sopnumbe == tupl[0], \
                gp_shipping_data.c.ShipMethod == tupl[1], gp_shipping_data.c.TrackingNum == tupl[2], \
                gp_shipping_data.c.ShipDate == tupl[3], gp_shipping_data.c.DeliveryDate == tupl[4], \
                gp_shipping_data.c.Voided == tupl[5]).all()

        # pull out all serial numbers and generate a serial-to-asset-tag lookup table for better performance
        # this is necessary because the only way to associate Forge data with GP data is thru serials
        # i also tried creating a MySQL view that joins the gp data with the asset tags, but you have to
        # use a subquery to union the serial -> asset tag tuple for servers, switches, storage, rack, pdu
        # and then join that union'd subquery to the gp_shipping_data table. However, you cannot have subqueries
        # in views until after MySQL 5.7.7, which we can't use right now
        item_serials        = [ x.SerialNumber.strip() for x in items if x.SerialNumber.strip() != "" ]
        serial_to_asset_tag = generate_serial_to_asset_tag(session, item_serials)
        for item in items:
            # need to strip here since the boomi integration does not allow blank strings. if the serial number is blank,
            # boomi won't allow a blank value; to get around this i used a single space. so we want to
            # trim from single space to no spaces.
            serial = item.SerialNumber.strip()

            quantity = str(item.Qty)
            # sometimes there are things like "Data Center Ticket" on invoices that are quantity 0.
            # SNow has expressed their desire to never see anything with quantity 0. So we bump to 1.
            if quantity == "0":
                quantity = "1"

            if serial != '':
                if serial.lower() in serial_to_asset_tag:
                    asset_tag = serial_to_asset_tag[serial.lower()]
                else:
                    asset_tag = ''
                #for each line item on a PO, it might become many entries within the items list.
                #for example, customer may order 16 R430 servers. Since they've asked for each item to be broken out by serial,
                #there isn't just one line item for all 16 servers, they each get their own. However, the way the GP integration works
                #each item gets the total quantity from the original PO line item quantity. so for non-serialized items,
                #we just use the quantity from the PO. But if we're breaking a single line item into multiple actual serialized items,
                #we need to change the quantity value in the item block to just 1.
                quantity = "1"
            else:
                asset_tag = ''

            if item.Comment:
                lineId = item.Comment.zfill(5)
            else:
                lineId = ""

            item_blob = {
                'SerialNumber': serial,
                'SAPAssetNumber': asset_tag,
                'PONumber': item.CustPO.zfill(10),
                'QTYShipped': quantity,
                'PartNumber': item.PartNumber,
                # 'Update_Date': item.updated, # Removed as to not expose to the customer.
                'LineID': lineId,
                'RedaptOrderNumber': item.orignumb
            }

            if(non_po):
                item_blob.update({'Price': str(item.UnitPrice),'ExtendedPrice': str(item.ExtendedPrice)})

            shipment['Items'].append(item_blob)

        records.append(shipment)

    return { 'records': records }

def generate_serial_to_asset_tag(session, serial_nums):
    serial_to_asset = {}

    if len(serial_nums) == 0:
        return serial_to_asset

    tables = [ pdus, servers, consoles, switches, racks, storage_devices, chassis ]
    for table in tables:
        q = session.query(table).filter(table.c.serial.in_(serial_nums)).filter(table.c.released_to_ship.isnot(None)).all()
        for item in q:
            serial_to_asset[item.serial.lower()] = item.asset_tag

    return serial_to_asset
