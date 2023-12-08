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

#### Compile and Deploy QueryBooster client
```bash
cd client/
npm i
npm run build
```

#### Run QueryBooster server
go back to the project directory and type the following command
```bash
gunicorn -w 4 -b 127.0.0.1:8000 'server.server:app'
```

#### Access QueryBooster web interface
Go to the link http://localhost:8000 to access the web interface.


#### Test
```bash
python3 -m pytest
```

## VLDB 2023 Experiment
The workloads we experimented on for the paper "**QueryBooster: Improving SQL Performance Using Middleware Services for Human-Centered Query Rewriting**" (published in VLDB 2023) are the following:
 - Selected query pairs from WeTune: [Test_wetune.csv](https://github.com/ISG-ICS/QueryBooster/blob/main/experiments/Test_wetune.csv).
 - Query pairs from Calcite test suite: [calcite_tests.csv](https://github.com/ISG-ICS/QueryBooster/blob/main/experiments/calcite_tests.csv).
 - Tableau generated TPC-H queries (and their human-rewritten queries): [tpch_pg.md](https://github.com/ISG-ICS/QueryBooster/blob/main/experiments/tpch_pg.md).
