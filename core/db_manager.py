import csv
from mo_sql_parsing import parse
from mo_sql_parsing import format
from pathlib import Path

# load the query costs cache from a file
#
QUEYR_COSTS_CACHE = []
with open(Path(__file__).parent / "../" / 'query_costs_cache.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    # skip head
    next(csv_reader, None)
    for row in csv_reader:
        QUEYR_COSTS_CACHE.append([row[0], float(row[1])])


class DBManager:

    # get the query cost from QUEYR_COSTS_CACHE table
    #   TODO - get the cost from EXPLAIN the query if we have access to the user db
    #
    @staticmethod
    def query_cost(query: str) -> float:
        for qc in QUEYR_COSTS_CACHE:
            q = qc[0]
            c = qc[1]
            if format(parse(q)) == format(parse(query)):
                return c
        return -1.0