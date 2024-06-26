# QueryBooster

[https://querybooster.ics.uci.edu/](https://querybooster.ics.uci.edu/)

## News
We gave a talk about this project at Cornell University, here is the [recording](https://drive.google.com/file/d/1JZt94sB2dTzICERljDoxNfcctCD_VBtx/view?usp=sharing). 

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
 - Python 3.9 +
 - NPM

#### Set up Python Virtual Environement
In `QueryBooster` folder,
```bash
python3 -m venv venv
source venv/bin/activate  # Windows, .\venv\Scripts\activate
pip install -r requirements.txt
```

#### Compile and Deploy QueryBooster client
In `QueryBooster` folder,
```bash
cd client/
npm install
npm run build
```

#### Run QueryBooster server
In `QueryBooster` folder,
```bash
cd server

# Dev mode
python wsgi.py

# Server mode (only support Linux, Mac OS X)
gunicorn 'wsgi:app'
```

#### Access QueryBooster web interface
Go to the link http://localhost:8000 to access the web interface.


#### Test
In `QueryBooster` folder,
```bash
python3 -m pytest
```

## Publications
1. [**QueryBooster: Improving SQL Performance Using Middleware Services for Human-Centered Query Rewriting**](https://www.vldb.org/pvldb/vol16/p2911-bai.pdf) (published in VLDB 2023)
2. [**Demo of QueryBooster: Supporting Middleware-Based SQL Query Rewriting as a Service**](https://www.vldb.org/pvldb/vol16/p4038-bai.pdf) (published in VLDB 2023 Demo)
The workloads we experimented on for the paper  are the following:
 - Selected query pairs from WeTune: [Test_wetune.csv](https://github.com/ISG-ICS/QueryBooster/blob/main/experiments/Test_wetune.csv).
 - Query pairs from Calcite test suite: [calcite_tests.csv](https://github.com/ISG-ICS/QueryBooster/blob/main/experiments/calcite_tests.csv).
 - Tableau generated TPC-H queries (and their human-rewritten queries): [tpch_pg.md](https://github.com/ISG-ICS/QueryBooster/blob/main/experiments/tpch_pg.md).
