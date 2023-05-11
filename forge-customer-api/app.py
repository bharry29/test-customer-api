from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException, PreconditionFailed, Forbidden

from device_api import deviceapi
from shipping_api import shippingapi

import sys
import os

VERSION = "1.5.20"

app = Flask(__name__)

# Ensure $FLASK_ENV is set
try:
    flask_env = os.environ['FLASK_ENV']
except:
    raise Exception("Cannot detect $FLASK_ENV. Try setting to 'development' or 'production'.")

# Connect to the database depending on $FLASK_ENV
if flask_env == 'production':
    import logging
    # from logging.handlers import RotatingFileHandler
    from slack_log_handler import SlackLogHandler

    # file_handler = RotatingFileHandler('mcap/mcap_api/error.log', maxBytes=1024 * 1024 * 100, backupCount=5)
    # file_handler.setLevel(logging.WARNING)
    # app.logger.addHandler(file_handler)

    webhook_url = "https://hooks.slack.com/services/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"
    slack_handler = SlackLogHandler(webhook_url, channel="#customer-apps", username="device_and_shipping_API")
    slack_handler.setLevel(logging.ERROR)
    app.logger.addHandler(slack_handler)

# for now, warn on usage errors, so we can proactively reach out to customers if they're using improperly
# we may need/want to turn down the verbosity here in the future as the usage grows
# handling the base HTTPException DOES NOT work. Very annoying. So you need to explicitly add a handler
# for every different HTTP error code you may want a notification for.
@app.errorhandler(PreconditionFailed)
@app.errorhandler(Forbidden)
def handle_invalid_usage(error):
    app.logger.error("HTTP exception", exc_info=sys.exc_info())    
    return error

# healthcheck endpoint for ALB
@app.route("/healthcheck/", methods=['GET'])
def healthcheck():
    return "healthy"

app.register_blueprint(deviceapi)
app.register_blueprint(shippingapi)


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8090)
