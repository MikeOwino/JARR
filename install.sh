#! /usr/bin/env bash

#
# This script install all dependencies and configure JARR
# for Python 3.
#

PYTHON_VERSION="3.4"

sudo apt-get install -y libpq-dev build-essential libxml2-dev libxslt1-dev

sed -i '/psycopg2/d' requirements.txt
sudo pip$PYTHON_VERSION install --upgrade -r requirements.txt

# Initializes the configuration file
cp src/conf/conf.cfg-sample src/conf/conf.cfg

# Delete default database configuration
sed -i '/database/d' src/conf/conf.cfg
sed -i '/database_url/d' src/conf/conf.cfg

if [ "$1" == postgres ]; then
    sudo apt-get install -y postgresql postgresql-server-dev-9.4 postgresql-client
    sudo pip$PYTHON_VERSION install psycopg2
    echo "127.0.0.1:5433:aggregator:pgsqluser:pgsqlpwd" > ~/.pgpass
    chmod 0600 ~/.pgpass
    sudo -u postgres createuser pgsqluser --no-superuser --createdb --no-createrole
    sudo -u postgres createdb aggregator --no-password
    echo "ALTER USER pgsqluser WITH ENCRYPTED PASSWORD 'pgsqlpwd';" | sudo -u postgres psql
    echo "GRANT ALL PRIVILEGES ON DATABASE aggregator TO pgsqluser;" | sudo -u postgres psql

    # Add configuration lines for PostgreSQL
    echo '[database]' >> src/conf/conf.cfg
    echo 'database_url = postgres://pgsqluser:pgsqlpwd@127.0.0.1:5433/aggregator' >> src/conf/conf.cfg
elif [ "$1" == sqlite ]; then
    sudo pip$PYTHON_VERSION install pysqlite # not working with Python 3!
    # Add configuration lines for SQLite
    echo '[database]' >> src/conf/conf.cfg
    echo 'database_url = sqlite+pysqlite:///jarr.db' >> src/conf/conf.cfg
fi

python$PYTHON_VERSION src/manager.py db_empty
python$PYTHON_VERSION src/manager.py db_create

# Bootstrap
git submodule init
git submodule update
