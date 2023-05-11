import pendulum

from database.db import customer, auth_user
from flask import abort
from sqlalchemy import or_

def get_customer_allowed_orgs(session, api_key):
    if api_key:
        q = session.query(auth_user).filter(auth_user.c.api_key == api_key).all()
        if q:
            cust_q = session.query(customer).filter(customer.c.id == q[0].customer_id).all()
            if cust_q:
                if is_parent(cust_q[0]):
                    cust_suborgs_and_self = get_customer_suborgs_and_parent(session, cust_q[0])
                    # print "RETURNING ORGS: {}".format(cust_suborgs_and_self)
                    return cust_suborgs_and_self
                else:
                    # print "RETURNING SINGLE ORG NAME: {}".format(cust_q[0].org_name)
                    return [ cust_q[0].org_name ]
    abort(403)

# we are now doing customer-org based filtering by API key instead of just Forge customer string matching.
# there are parent and child customer orgs. if the org associated with an API key is a parent org,
# it needs to retrieve records associated with the parent org and all children orgs
def is_parent(cust):
    return cust.parent_org_name is None or cust.parent_org_name == '' or cust.org_name == cust.parent_org_name

def get_customer_suborgs_and_parent(session, cust):
    q = session.query(customer).filter(or_(customer.c.org_name == cust.org_name, customer.c.parent_org_name == cust.org_name))
    return [ x.org_name for x in q ]

# the main customer using this API inputs the params assuming the dates are PST.
# so, parse them as PST. this really should be fixed and timestamps all standardized on UTC
# as well as the date input format being ISO standard or something like that
def parse_date(date_text, utc=True):
    try:
        datetime_input = pendulum.from_format(date_text, 'MM-DD-YYYY:HH:mm', tz='America/Los_Angeles')
    except ValueError:
        abort(412)
    if utc:
        datetime_input = pendulum.timezone('UTC').convert(datetime_input)
    return datetime_input.to_datetime_string()
