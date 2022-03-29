# VisBooster
This repository hosts the source code for the VisBooster system published as a Demo paper in BigVis 2022 workshop.

## Introduction
VisBooster is a middleware-based **query rewriting** framework.

<p align="center">
  <img src="https://github.com/ISG-ICS/VisBooster/blob/main/pub/framework.png" width="500">
</p>

VisBooster intercepts SQL queries by customizing JDBC drivers used by Tableau and uses rules to rewrite the queries to semantically equivalent yet more efficient queries. The rewriting rules are designed by data experts who analyze slow queries and apply their domain knowledge and optimization expertise. VisBooster can accelerate visualization queries formulated by Tableau up to 100 times faster.

The following is the demo we showed at BigVis 2022 Workshop (jointly held with EDBT/ICDT 2022).
[![IMAGE ALT TEXT HERE](https://i.ytimg.com/vi/TsO6EaRzrb4/hqdefault.jpg?sqp=-oaymwEcCNACELwBSFXyq4qpAw4IARUAAIhCGAFwAcABBg==&rs=AOn4CLB9RKsckkw7Tgpm8l59eOgFCExekA)](https://youtu.be/TsO6EaRzrb4)

## JDBC Drivers

The VisBooster customized JDBC drivers repository are listed below:

 - [PostgreSQL JDBC Driver](https://github.com/ISG-ICS/smart-pgjdbc)
 - [MySQL JDBC Driver](https://github.com/ISG-ICS/smart-mysql-connector-j)

## Run VisBooster

#### Requirements
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Run VisBooster server
```bash
cd server/
python3 server.py
```

#### Access VisBooster web interface
Go to the link http://localhost:8000 to access the web interface.
