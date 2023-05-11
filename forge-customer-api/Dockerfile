FROM tiangolo/uwsgi-nginx-flask:python2.7

# Hack for "mysql-python" compilation error.
# https://stackoverflow.com/questions/47688474/unable-to-use-mysqldb-in-python2-virtualenv-on-fedora-27
RUN sed '/st_mysql_options options;/a unsigned int reconnect;' /usr/include/mysql/mysql.h -i.bkp

COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt

COPY ./ /app

EXPOSE 80
EXPOSE 8090
