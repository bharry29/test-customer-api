from sqlalchemy        import create_engine, MetaData, Table, Column, Integer, ForeignKey
from sqlalchemy.sql    import and_
from sqlalchemy.orm    import sessionmaker, load_only

from contextlib import contextmanager

import os

### configs to connect to database
# And we will need to set this up to remove the credentials from the script...
try:
    user    = os.environ['DB_USER']
    pw      = os.environ['DB_PASS']
    url     = os.environ['DB_URL']
    db_name = os.environ['DB_NAME']
    db_port = os.environ['DB_PORT']
except:
    raise Exception("Cannot detect database credentials. Refer to README for details.")

# Ensure $FLASK_ENV is set
try:
    flask_env = os.environ['FLASK_ENV']
except:
    raise Exception("Cannot detect $FLASK_ENV. Try setting to 'development' or 'production'.")

engine = create_engine('mysql://{}:{}@{}:{}/{}?charset=utf8'.format(user, pw, url, db_port, db_name), pool_pre_ping=True)

# Connect to the database depending on $FLASK_ENV
if flask_env == 'production':
    engine.echo = False
elif flask_env == 'development':
    engine.echo = True
else:
    raise Exception("$FLASK_ENV needs to be either 'development' or 'production'.") 

metadata                 = MetaData(engine)

### database tables
customer                 = Table('customer', metadata, autoload=True, autoload_with=engine)
auth_user                = Table('auth_user', metadata, Column('id', Integer, primary_key=True), 
                           Column('customer_id', Integer, ForeignKey("customer.id"), nullable=True), autoload=True)
pdus                     = Table('pdus', metadata, autoload=True)
consoles                 = Table('consoles', metadata, autoload=True)
switches                 = Table('switches', metadata, autoload=True)
servers                  = Table('servers', metadata, autoload=True)
bmc_card                 = Table('bmc_card', metadata, autoload=True)
racks                    = Table('racks', metadata, autoload=True)
storage_devices          = Table('storage_devices', metadata, autoload=True)
server_network_cards     = Table('network_card', metadata, autoload=True)
pdu_connections          = Table('pdu_connections', metadata, autoload=True)
switch_connections       = Table('switch_connections', metadata, autoload=True)
gp_shipping_data         = Table('gp_shipping_data', metadata, autoload=True)
test_result              = Table('test_result', metadata, autoload=True)
serial_number            = Table('serial_number', metadata, autoload=True)
chassis                  = Table('chassis', metadata, autoload=True)
modules                  = Table('modules', metadata, autoload=True)

### SQL session
Session                  = sessionmaker(bind=engine)

@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        print "session exception: {0}".format(e)
        session.rollback()
        raise
    finally:
        session.close()
