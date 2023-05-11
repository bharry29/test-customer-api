# Forge Customer API (Orders/Shipments)

This Python/Flask API project is responsible for providing Order and Shipment data to API consumers.


## Testing Code Locally
Because the API is currently read-only, it makes it relatively easy to test code changes locally while connecting to the prod DB, as there is no risk of messing anything up in prod.

1. Create a VirtualEnv environment for your development project. Currently on Python 2.7.
2. Populate environment variables. These can be appended to `bin/activate` for persistence.
    ```bash
    export FLASK_ENV=development
    export DB_USER=forge-api
    export DB_NAME=forge_api_prod
    export DB_PORT=3306
    export DB_PASS=<LOCATE IN ZOHO VAULT>
    export DB_URL=<ENDPOINT FROM RDS PAGE>

    ```
3. Activate your virtualenv.
    ```bash
    cd <VIRTUAL_ENV_FOLDER>
    source bin/activate
    ```
4. Install project requirements:
    ```bash
    pip install -r requirements.txt
    ```
5. Start the API server:
    ```bash
    python app.py
    ```
6. You should be able to access it at `http://127.0.0.1:8090`. You'll need to make a request to a specific endpoint; There is nothing served directly at the docroot.
7. Below are some good sample queries. _You will need to obtain an API_KEY from someone on the Forge team_:
    ```bash
    http://127.0.0.1:8090/orders/03-20-2018:00:00/03-21-2018:23:59/?api_key=<API_KEY>
    http://127.0.0.1:8090/shipments/03-20-2018:00:00/03-21-2018:23:59/?api_key=<API_KEY>
    ```

If you need to test **DB schema** changes along with code changes, you can use the `forge-api-dev` database and connect to that instead. See the RDS console for access info. Make the modifications you need using whatever MySQL tool you prefer, and then change the connection string within `database/db.py` to use `forge-api-dev`. Once you're ready to deploy, make the DB changes to the prod schema, and follow the new code deployment section to deploy the new code to Fargate. Another option is to dump the structure and some sample data from the prod schema into a local MySQL instance and test against that.

## Deploying Changed to Production
1. Submit a Pull Request for your feature branch. Merge info `HEAD/develop` when request has been approved.
    
    __Make sure you increment the `VERSION` variable in `app.py`!__

2. Login to AWS using CLI.
    ```bash
    $(aws ecr get-login --no-include-email --region us-west-2)
    ```
3. Build your Docker image using the following command:
    ```bash
    docker build -t forge-api .
    ```
4. After the build completes, tag your image with a version tag (e.g. v0.0.00) and "latest" so you can push the image to this repository:
    ```bash
    docker tag forge-api:latest 924175341144.dkr.ecr.us-west-2.amazonaws.com/forge-api:<VERSION>
    docker tag forge-api:latest 924175341144.dkr.ecr.us-west-2.amazonaws.com/forge-api:latest
    ```
5. Run the following command to push this image to your newly created AWS repository:
    ```bash
    docker push 924175341144.dkr.ecr.us-west-2.amazonaws.com/forge-api:<VERSION>
    docker push 924175341144.dkr.ecr.us-west-2.amazonaws.com/forge-api:latest
    ```
6. Create a new task revision of the `forge-api` task definition pointing to your new container version tag. Ensure the following environment variable are included in the task definition:
    ```bash
    FLASK_ENV=production
    DB_USER=forge-api
    DB_NAME=forge_api_prod
    DB_PORT=3306
    DB_PASS=<LOCATE IN ZOHO VAULT>
    DB_URL=<ENDPOINT FROM RDS PAGE>
    ```
7. Update the `forge-api` service under the prod-forge-general cluster to use the new task definition revision from previous step.
8. Monitor and ensure service is healthy.


## How to Provision a new API Key for a Customer
- Log into the Legacy Portal (From INSIDE Redapt: https://portal.redaptcloud.com, from OUTSIDE Redapt, https://portal.redapt.com)
- Click on menu and choose Customers.
- Click Create Customer button at bottom (if customer not already there)
- Fill out the stuff, but most important here is the `Mcap api customer` field. This is a drop-down list of all customers with the Name and Org Name displayed. These are the same customers as from Forge. This list includes parent and sub-accounts. You need to choose the correct Org Name for the data you want this customer to be scoped to. For example, you could choose ServiceNow parent account (SERV-08) which would allow access to all data from all ServiceNow parent and child accounts. Or, you could choose SERV-14, which is just ServiceNow Canada, and then this would only provide access to ServiceNow Canada data.
- Then, you need to create a User and associate them with the Customer you created in the previous step. Click on the menu and choose Users.
- Click on Create User at the bottom. 
- You will see that there is a field called `MCAP API key:` but there is no drop down at this point.
- In the `Employer` box, choose the customer that you created a few steps ago. Fill in the rest of the fields for the user and click Create User.
- Go back and find the new user in the list. Click on Edit towards the right.
- Now, there is a drop-down menu for the `MCAP API key` field.
- Click the drop-down and choose 'New API Key'.
- Click Submit. 
- Now you should be able to give this new generated API key to the customer.
- It would be a good idea to test this first, e.g. look for the test queries below in this document, change the URL to point at the production API instance, and swap out the API key for the one you just generated. You also may need to play with the date ranges to actually see any valid data returned for this new customer. If there is no data returned, it doesn't necessarily mean anything is wrong, it could just mean that there really is no data for that customer account.
- What just happened??: `customer-portal` app has direct access to the forge-api-prod DB. You can see these credentials if you look into the database YAML config file in the `customer-portal` GitHub repo in the Redapt GitHub account. When you generate and save a new API key here in the Legacy Portal UI, it writes that key into the `auth_user` table in the forge-api-prod DB, along with the Customer ID from the customer that you associated the new user with. You can verify this by logging into the forge-api-prod DB and running `select * from auth_user`.


## Device Data API
This data feed comes from device inventory data gathered during the Forge process. The data is synced from the Forge production database to the Forge API production database using Dell Boomi SaaS.


## Shipping API
This data feed comes from Dynamics GP (Accounting/Invoicing system). The data is synced from the GP production database to the Forge API production database using Dell Boomi SaaS.


## Architecture (Listing Production Endpoints)
- 2 AWS Fargate containers scheduled in the `prod-forge-general` cluster. Service name `forge-api`. Task definition name `forge-api`.
- 1 Application Load Balancer named `forge-api-prod`
- 1 DNS CNAME record from `api.redapt.com` to `forge-api-prod-1664427851.us-west-2.elb.amazonaws.com` (A Record of ALB)
- 1 RDS MySQL instance named `forge-api-prod-2`. URL `forge-api-prod-2.cfmorrjwa4k3.us-west-2.rds.amazonaws.com`. See Zoho for root credentials.
- 1 EC2 instance (id i-0ff36e5c5279f3b81) that hosts the Boomi Atom that moves data from forge-prod to forge-api-prod database.
- There is also a Boomi Atom installation located on the `GP2013.redapt.com` VM that's owned by the IT team that allows the data to flow from the GP database to the forge-api-prod database.

The code is pretty straightforward to understand. Database stuff in `database/db.py`, `app.py` is the main process that includes the two blueprints, one for `shipping_api.py` and one for `device_api.py`.


## How to Update SSL Certificates
The SSL termination for the API is done at the ALB level.
- We use the wildcard redapt.com cert for these (*.redapt.com). (The external DNS name for the api is api.redapt.com) Check Zoho for the latest wildcard cert and if not there, check with IT to coordinate the cert renewal.
- Go to the `forge-api-prod` load balancer in the AWS console. Click on the Listeners tab. Click View/edit certificates under the SSL Certificate header for the HTTPS:443 load balancer rule. Here you can upload the latest certificate and then switch the LB over to use that one.


## Database Integration/ETL process
There are two data sources that feed into the API DB: the Forge prod DB in AWS, and the on-prem Dynamics GP (Accounting/inventory system) prod DB. We currently use a tool called Dell Boomi to orchestrate the data transfer. See the Dell Boomi webui for more (https://platform.boomi.com/). It's kinda hard to explain. Probably will just have to figure it out. Basically, there are different processes that move the data around.
- For all the processes that move data from the forge-prod db, see the `MCAP to API` folder and expand the Processes tab. Each Process basically corresponds to one database table being copied over.
- For the (single) process that moves data from the GP database, see `GP to API` folder and expand the Processes tab. The `Shipping Data` process is basically a big compound query that joins a bunch of tables on the GP source and dumps them into a flat table format in the forge-api database.
- To monitor the status of the processes, go to the Manage tab and choose Process Reporting. Right now, all of these processes run every hour, on the :45 of the hour. You should see all green dots next to the processes.

