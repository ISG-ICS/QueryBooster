# QueryBooster

## Introduction
QueryBooster is a middleware-based **query rewriting** framework.

<p align="center">
  <img src="https://github.com/ISG-ICS/QueryBooster/blob/main/pub/framework.png" width="500">
</p>

QueryBooster intercepts SQL queries by customizing JDBC drivers used by applications (e.g., Tableau) and uses rules to rewrite the queries to semantically equivalent yet more efficient queries. The rewriting rules are designed by data experts who analyze slow queries and apply their domain knowledge and optimization expertise. QueryBooster can accelerate queries formulated by Tableau up to 100 times faster.

## JDBC Drivers

The QueryBooster customized JDBC drivers repository are listed below:

 - [PostgreSQL JDBC Driver](https://github.com/ISG-ICS/smart-pgjdbc)
 - [MySQL JDBC Driver](https://github.com/ISG-ICS/smart-mysql-connector-j)

## Run QueryBooster

#### Requirements
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Run QueryBooster server
```bash
cd server/
python3 server.py
```

#### Access QueryBooster web interface
Go to the link http://localhost:8000 to access the web interface.
