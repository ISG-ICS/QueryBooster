# TPC-H Dataset

Reference: [TPC-H with Postgres](https://ankane.org/tpc-h)

### Get TPC-H kit customized by Andrew Kane

```bash
git clone https://github.com/gregrahn/tpch-kit.git
cd tpch-kit/dbgen
make MACHINE=MACOS DATABASE=POSTGRESQL
```

### Create the database and load the schema

```bash
createdb -U postgres tpch
psql -d tpch -U postgres -f dss.ddl
```

### Generate data

```bash
# help information on dbgen
./dbgen --help

# generate 10G data (scale factor = 10)
./dbgen -vf -s 10
```

### Load the data

```bash
for i in `ls *.tbl`; do
  table=${i/.tbl/}
  echo "Loading $table..."
  sed 's/|$//' $i > /tmp/$i
  psql tpch -U postgres -q -c "TRUNCATE $table"
  psql tpch -U postgres -c "\\copy $table FROM '/tmp/$i' CSV DELIMITER '|'"
done
```

### Generate queries

```bash
mkdir /tmp/queries

for i in `ls queries/*.sql`; do
  tail -r $i | sed '2s/;//' | tail -r > /tmp/$i
done

DSS_QUERY=/tmp/queries ./qgen | sed 's/limit -1//' | sed 's/day (3)/day/' > queries.sql
```

### Run queries

```bash
psql tpch -U postgres -c "ANALYZE VERBOSE"
# The following will run forever ...
# psql tpch -U postgres < queries.sql
```

### Add Indexes using Dexter

#### Install [Dexter](https://github.com/ankane/dexter)

Install [HypoPG](https://github.com/HypoPG/hypopg)

```bash
cd /tmp
curl -L https://github.com/HypoPG/hypopg/archive/1.3.1.tar.gz | tar xz
cd hypopg-1.3.1
make
make install # may need sudo
```

Install Dexter

```bash
brew install ankane/brew/dexter
```

#### Add indexes uding Dexter

```bash
for i in `seq 1 5`; do
  dexter -U postgres tpch queries.sql --input-format sql --create
done
```

### Run queries again

```bash
psql tpch -U postgres -c "ANALYZE VERBOSE"
psql tpch -U postgres < queries.sql
```

### Create indexes manually

```sql
-- lineitem
-- create btree on l_shipdate
create index lineitem_l_shipdate_idx ON lineitem USING BTREE (l_shipdate);

-- create btree on l_discount
create index lineitem_l_discount_idx ON lineitem USING BTREE (l_discount);
-- create btree on l_quantity
create index lineitem_l_quantity_idx ON lineitem USING BTREE (l_quantity);

-- create gin on l_comment
CREATE INDEX lineitem_l_comment_idx ON lineitem USING GIN (l_comment gin_trgm_ops);
```



# TPC-H Queries

## Q1

### Tableau Q (5.089 s)

```sql
SELECT SUM(1) AS "cnt:lineitem_5514867AA7E644B18921DC52BAC9DD54:ok",
  AVG("lineitem"."l_extendedprice") AS "avg:l_extendedprice:ok",
  AVG("lineitem"."l_quantity") AS "avg:l_quantity:ok",
  "lineitem"."l_linestatus" AS "l_linestatus",
  "lineitem"."l_returnflag" AS "l_returnflag",
  AVG("lineitem"."l_discount") AS "sum:l_discount:ok",
  SUM("lineitem"."l_extendedprice") AS "sum:l_extendedprice:ok",
  SUM("lineitem"."l_quantity") AS "sum:l_quantity:ok:1",
  SUM(("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount"))) AS "usr:Calculation_238972316117872643:ok",
  SUM((("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount")) * (1 + "lineitem"."l_tax"))) AS "usr:Calculation_238972316118650884:ok"
FROM "public"."lineitem" "lineitem"
WHERE ("lineitem"."l_shipdate" <= (CAST('1998-12-01' AS DATE) + -90 * INTERVAL '1 DAY'))
GROUP BY 4,
  5;
```

### WeTune Rewritten (No more optimization)



## Q2 √

### Create indexes

```sql
CREATE EXTENSION pg_trgm;
CREATE INDEX part_p_type_idx ON part USING GIN (p_type gin_trgm_ops);
```

### Tableau Q (1555.358 ms)

```sql
SELECT MAX("supplier"."s_acctbal") AS "max:s_acctbal:ok",
  "part"."p_name" AS "p_name",
  "supplier"."s_name" AS "s_name"
FROM "public"."supplier" "supplier"
  INNER JOIN "public"."nation" "nation1" ON ("supplier"."s_nationkey" = "nation1"."n_nationkey")
  INNER JOIN "public"."region" "region1" ON ("nation1"."n_regionkey" = "region1"."r_regionkey")
  INNER JOIN "public"."partsupp" "partsupp" ON ("supplier"."s_suppkey" = "partsupp"."ps_suppkey")
  INNER JOIN (
  SELECT r_name as r_name,
         ps_partkey as ps_partkey,
         min(ps_supplycost) as min_supplycost
    FROM partsupp, supplier, nation, region
   WHERE s_suppkey = ps_suppkey 
     AND s_nationkey = n_nationkey
     AND n_regionkey = r_regionkey 
   GROUP BY r_name, ps_partkey
) "Custom SQL Query3" ON (("partsupp"."ps_partkey" = "Custom SQL Query3"."ps_partkey") AND ("partsupp"."ps_supplycost" = "Custom SQL Query3"."min_supplycost"))
  INNER JOIN "public"."part" "part" ON ("partsupp"."ps_partkey" = "part"."p_partkey")
WHERE (("part"."p_size" = 15) AND (SUBSTR(RTRIM(CAST(LOWER(CAST("part"."p_type" AS TEXT)) AS TEXT), ' '), (CASE WHEN (LENGTH(RTRIM(CAST(LOWER(CAST("part"."p_type" AS TEXT)) AS TEXT), ' ')) - LENGTH(CAST('brass' AS TEXT))) < 0 THEN 1 ELSE LENGTH(RTRIM(CAST(LOWER(CAST("part"."p_type" AS TEXT)) AS TEXT), ' ')) - LENGTH(CAST('brass' AS TEXT)) + 1 END), LENGTH(CAST('brass' AS TEXT))) = CAST('brass' AS TEXT)) AND ("Custom SQL Query3"."r_name" = 'EUROPE') AND ("region1"."r_name" = 'EUROPE'))
GROUP BY 2,
  3;
```

### Rewritten Q' (Push join into subquery & Substr to LIKE, 207ms)

```sql
SELECT MAX("supplier"."s_acctbal") AS "max:s_acctbal:ok",
  "part"."p_name" AS "p_name",
  "supplier"."s_name" AS "s_name"
FROM "public"."supplier" "supplier"
  INNER JOIN "public"."nation" "nation1" ON ("supplier"."s_nationkey" = "nation1"."n_nationkey")
  INNER JOIN "public"."region" "region1" ON ("nation1"."n_regionkey" = "region1"."r_regionkey")
  INNER JOIN "public"."partsupp" "partsupp" ON ("supplier"."s_suppkey" = "partsupp"."ps_suppkey")
  INNER JOIN (
  SELECT r_name as r_name,
         ps_partkey as ps_partkey,
         min(ps_supplycost) as min_supplycost
    FROM partsupp, supplier, nation, region, part
   WHERE s_suppkey = ps_suppkey 
     AND s_nationkey = n_nationkey
     AND n_regionkey = r_regionkey 
     AND r_name = 'EUROPE'
     AND ps_partkey = p_partkey
     AND ("part"."p_size" = 15) AND ("part"."p_type" LIKE '%BRASS')
   GROUP BY r_name, ps_partkey
) "Custom SQL Query3" ON (("partsupp"."ps_partkey" = "Custom SQL Query3"."ps_partkey") AND ("partsupp"."ps_supplycost" = "Custom SQL Query3"."min_supplycost"))
  INNER JOIN "public"."part" "part" ON ("partsupp"."ps_partkey" = "part"."p_partkey")
WHERE (("part"."p_size" = 15) AND ("part"."p_type" LIKE '%BRASS') AND ("region1"."r_name" = 'EUROPE'))
GROUP BY 2,
  3;
```

### WeTune Rewriten (1059.081 ms)

```sql
SELECT "partsupp"."ps_supplycost" AS "min_supplycost",
       "partsupp"."ps_partkey"    AS "p_partkey"
FROM   "partsupp" AS "partsupp"
       INNER JOIN (SELECT "region"."r_name"                AS "r_name",
                          "partsupp0"."ps_partkey"         AS "ps_partkey",
                          Min("partsupp0"."ps_supplycost") AS "min_supplycost"
                   FROM   "partsupp" AS "partsupp0"
                          INNER JOIN "supplier" AS "supplier"
                                  ON "supplier"."s_suppkey" =
                                     "partsupp0"."ps_suppkey"
                          INNER JOIN "nation" AS "nation"
                                  ON "supplier"."s_nationkey" =
                                     "nation"."n_nationkey"
                          INNER JOIN "region" AS "region"
                                  ON "nation"."n_regionkey" =
                                     "region"."r_regionkey"
                   GROUP  BY "ps_partkey",
                             "r_name"
                  ) AS "Custom SQL Query3"
               ON "partsupp"."ps_partkey" = "Custom SQL Query3"."ps_partkey"
                  AND "partsupp"."ps_supplycost" =
                      "Custom SQL Query3"."min_supplycost"
       INNER JOIN "part" AS "part"
               ON "partsupp"."ps_partkey" = "part"."p_partkey"
       INNER JOIN "supplier" AS "supplier0"
               ON "partsupp"."ps_suppkey" = "supplier0"."s_suppkey"
       INNER JOIN "nation" AS "nation1"
               ON "supplier0"."s_nationkey" = "nation1"."n_nationkey"
       INNER JOIN "region" AS "region1"
               ON "nation1"."n_regionkey" = "region1"."r_regionkey"
WHERE  "part"."p_size" = 15
       AND "Custom SQL Query3"."r_name" = 'EUROPE';
```

### ChatGPT Rewriten ()

```sql
SELECT MAX("supplier"."s_acctbal") AS "max:s_acctbal:ok",
       "part"."p_name" AS "p_name",
       "supplier"."s_name" AS "s_name"
FROM "public"."supplier" "supplier"
INNER JOIN "public"."partsupp" "partsupp" ON ("supplier"."s_suppkey" = "partsupp"."ps_suppkey")
INNER JOIN (
  SELECT ps_partkey AS ps_partkey,
         MIN(ps_supplycost) AS min_supplycost
  FROM "public"."partsupp"
  INNER JOIN "public"."supplier" ON ("supplier"."s_suppkey" = "partsupp"."ps_suppkey")
  INNER JOIN "public"."nation" ON ("supplier"."s_nationkey" = "nation"."n_nationkey")
  INNER JOIN "public"."region" ON ("nation"."n_regionkey" = "region"."r_regionkey")
  WHERE "region"."r_name" = 'EUROPE'
  GROUP BY ps_partkey
) "Custom SQL Query3" ON (("partsupp"."ps_partkey" = "Custom SQL Query3"."ps_partkey") AND ("partsupp"."ps_supplycost" = "Custom SQL Query3"."min_supplycost"))
INNER JOIN "public"."part" "part" ON ("partsupp"."ps_partkey" = "part"."p_partkey")
WHERE ("part"."p_size" = 15) AND (LOWER("part"."p_type") LIKE '%brass%') AND ("supplier"."s_acctbal" = (
  SELECT MAX("supplier2"."s_acctbal")
  FROM "public"."supplier" "supplier2"
  INNER JOIN "public"."nation" "nation2" ON ("supplier2"."s_nationkey" = "nation2"."n_nationkey")
  INNER JOIN "public"."region" "region2" ON ("nation2"."n_regionkey" = "region2"."r_regionkey")
  WHERE "region2"."r_name" = 'EUROPE'
))
GROUP BY "part"."p_name", "supplier"."s_name";

-- Explanation of the optimizations:
/**
Simplified the subquery to get the minimum supply cost for each part key in Europe.
Moved the join with nation and region tables to the subquery to reduce the number of joins in the main query.
Replaced CAST(LOWER(CAST("part"."p_type" AS TEXT)) AS TEXT) with LOWER("part"."p_type") to simplify the query.
Replaced SUBSTR(RTRIM(CAST(LOWER(CAST("part"."p_type" AS TEXT)) AS TEXT), ' '), (CASE WHEN (LENGTH(RTRIM(CAST(LOWER(CAST("part"."p_type" AS TEXT)) AS TEXT), ' ')) - LENGTH(CAST('brass' AS TEXT))) < 0 THEN 1 ELSE LENGTH(RTRIM(CAST(LOWER(CAST("part"."p_type" AS TEXT)) AS TEXT), ' ')) - LENGTH(CAST('brass' AS TEXT)) + 1 END), LENGTH(CAST('brass' AS TEXT))) = CAST('brass' AS TEXT) with LOWER("part"."p_type") LIKE '%brass%' to simplify the query and make it more readable.
Replaced GROUP BY 2, 3 with GROUP BY "part"."p_name", "supplier"."s_name" to make the query more readable and easier to maintain.
Replaced the subquery for MAX("supplier"."s_acctbal") with a (Somehow ChatGPT didn't finish the sentence)
*/
```



## Q3

### Create indexes

```sql
-- create btree on c_mktsegment
CREATE INDEX customer_c_mktsegment_idx ON customer USING BTREE (c_mktsegment);
-- create btree on o_orderdate
CREATE INDEX orders_o_orderdate_idx ON orders USING BTREE (o_orderdate);
```

### Tableau Q (4s 93ms)

```sql
SELECT "orders"."o_orderkey" AS "o_orderkey",
  SUM(("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount"))) AS "sum:Calculation_2185231042902667264:ok"
FROM "public"."customer" "customer"
  INNER JOIN "public"."orders" "orders" ON ("customer"."c_custkey" = "orders"."o_custkey")
  INNER JOIN "public"."lineitem" "lineitem" ON ("orders"."o_orderkey" = "lineitem"."l_orderkey")
WHERE (("customer"."c_mktsegment" = 'BUILDING') AND ("orders"."o_orderdate" <= (DATE '1995-03-15')) AND ("lineitem"."l_shipdate" >= (DATE '1995-03-15')))
GROUP BY 1;
```

### WeTune Rewritten (No more optimization)



## Q4 √

### Create indexes

```sql
-- create btree on l_commitdate
create index lineitem_l_commitdate_idx ON lineitem USING BTREE (l_commitdate);
-- create btree on l_receiptdate
create index lineitem_l_receiptdate_idx ON lineitem USING BTREE (l_receiptdate);
```

### Tableau Q (3s 694ms)

```sql
SELECT SUM(1) AS "cnt:orders_DB274988E7334A27A5D51FB3B459984C:ok",
  "orders"."o_orderpriority" AS "o_orderpriority"
FROM "public"."orders" "orders"
  LEFT JOIN (
  select distinct l_orderkey as lo_orderkey
    from lineitem
   where l_commitdate < l_receiptdate
) "Custom SQL Query14" ON ("orders"."o_orderkey" = "Custom SQL Query14"."lo_orderkey")
WHERE ((CASE WHEN ("orders"."o_orderkey" = "Custom SQL Query14"."lo_orderkey") THEN TRUE ELSE FALSE END) AND ("orders"."o_orderdate" >= (DATE '1993-07-01')) AND ("orders"."o_orderdate" < (TIMESTAMP '1993-10-01 00:00:00.000')))
GROUP BY 2;
```

### Rewritten Q' (Join to exists,  2s 332ms)

```sql
SELECT SUM(1) AS "cnt:orders_DB274988E7334A27A5D51FB3B459984C:ok",
  "orders"."o_orderpriority" AS "o_orderpriority"
FROM "public"."orders" "orders"
WHERE (("orders"."o_orderdate" >= (DATE '1993-07-01')) AND ("orders"."o_orderdate" < (TIMESTAMP '1993-10-01 00:00:00.000')))
AND EXISTS (
  select 1
    from lineitem
   where l_commitdate < l_receiptdate
     and "orders"."o_orderkey" = l_orderkey
)
GROUP BY 2;
```

### WeTune Rewritten (Error in parsing SQL query)



## Q5 √

### Tableau Q (2047.747 ms)

```sql
SELECT "nation"."n_name" AS "n_name",
  SUM(("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount"))) AS "sum:Calculation_2185231042902667264:ok"
FROM "public"."customer" "customer"
  INNER JOIN "public"."nation" "nation" ON ("customer"."c_nationkey" = "nation"."n_nationkey")
  INNER JOIN "public"."region" "region" ON ("nation"."n_regionkey" = "region"."r_regionkey")
  INNER JOIN "public"."orders" "orders" ON ("customer"."c_custkey" = "orders"."o_custkey")
  INNER JOIN "public"."lineitem" "lineitem" ON ("orders"."o_orderkey" = "lineitem"."l_orderkey")
  INNER JOIN "public"."supplier" "supplier" ON ("lineitem"."l_suppkey" = "supplier"."s_suppkey")
  INNER JOIN "public"."nation" "nation1" ON ("supplier"."s_nationkey" = "nation1"."n_nationkey")
  INNER JOIN "public"."region" "region1" ON ("nation1"."n_regionkey" = "region1"."r_regionkey")
WHERE (("region"."r_name" = 'ASIA') AND ("customer"."c_nationkey" = "supplier"."s_nationkey") AND ("orders"."o_orderdate" >= (DATE '1994-01-01')) AND ("orders"."o_orderdate" < (TIMESTAMP '1995-01-01 00:00:00.000')) AND ("region1"."r_name" = 'ASIA'))
GROUP BY 1;
```

### Rewritten Q' (Merge region and nation tables, 1910.301 ms)

```sql
SELECT "nation"."n_name" AS "n_name",
   SUM(("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount"))) AS "sum:Calculation_2185231042902667264:ok"
 FROM "public"."customer" "customer", 
      "public"."nation" "nation", 
      "public"."region" "region",
      "public"."orders" "orders",
      "public"."lineitem" "lineitem",
      "public"."supplier" "supplier"
WHERE (("region"."r_name" = 'ASIA') 
  AND ("nation"."n_regionkey" = "region"."r_regionkey")
  AND ("customer"."c_nationkey" = "nation"."n_nationkey")
  AND ("customer"."c_custkey" = "orders"."o_custkey")
  AND ("orders"."o_orderkey" = "lineitem"."l_orderkey")
  AND ("lineitem"."l_suppkey" = "supplier"."s_suppkey")
  AND ("supplier"."s_nationkey" = "nation"."n_nationkey")
  AND ("orders"."o_orderdate" >= (DATE '1994-01-01')) 
  AND ("orders"."o_orderdate" < (TIMESTAMP '1995-01-01 00:00:00.000')))
GROUP BY 1;
```

### WeTune Rewrittern (2069.392 ms)

```sql
SELECT     "nation"."n_name"                                                 AS "n_name",
           Sum("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount")) AS "sum:Calculation_2185231042902667264:ok"
FROM       "customer"                                                        AS "customer"
INNER JOIN "nation"                                                          AS "nation"
ON         "customer"."c_nationkey" = "nation"."n_nationkey"
INNER JOIN "orders" AS "orders"
ON         "customer"."c_custkey" = "orders"."o_custkey"
INNER JOIN "lineitem" AS "lineitem"
ON         "orders"."o_orderkey" = "lineitem"."l_orderkey"
INNER JOIN "supplier" AS "supplier"
ON         "lineitem"."l_suppkey" = "supplier"."s_suppkey"
AND        "customer"."c_nationkey" = "supplier"."s_nationkey"
INNER JOIN "nation" AS "nation1"
ON         "supplier"."s_nationkey" = "nation1"."n_nationkey"
INNER JOIN "region" AS "region"
ON         "nation"."n_regionkey" = "region"."r_regionkey"
INNER JOIN "region" AS "region1"
ON         "nation"."n_regionkey" = "region1"."r_regionkey"
WHERE      "orders"."o_orderdate" >= (DATE '1994-01-01')
and        "orders"."o_orderdate" < (TIMESTAMP '1995-01-01 00:00:00.000')
AND        "region"."r_name" = 'ASIA'
GROUP BY 1;
```



## Q6

### Tableau Q (1s 877ms)

```sql
SELECT SUM(("lineitem"."l_extendedprice" * "lineitem"."l_discount")) AS "sum:Calculation_2185231042940301313:ok"
FROM "public"."lineitem" "lineitem"
WHERE (("lineitem"."l_discount" >= 0.049999999999999996) AND ("lineitem"."l_discount" <= 0.069999999999999993) AND ("lineitem"."l_quantity" < 24) AND ("lineitem"."l_shipdate" >= (DATE '1994-01-01')) AND ("lineitem"."l_shipdate" < (TIMESTAMP '1995-01-01 00:00:00.000')))
HAVING (COUNT(1) > 0);
```

### WeTune Rewritten (No more optimization)



## Q7 √

### Tableau Q (13s 21.2ms)

```sql
SELECT "Custom SQL Query5"."cust_nation" AS "cust_nation",
  "Custom SQL Query5"."l_year" AS "l_year",
  SUM("Custom SQL Query5"."volume") AS "sum:volume:ok",
  "Custom SQL Query5"."supp_nation" AS "supp_nation"
FROM (
  SELECT n1.n_name as supp_nation,
         n2.n_name as cust_nation,
         extract(year from l_shipdate) as l_year, 
         l_extendedprice * (1 - l_discount) as volume
    FROM supplier, lineitem, orders, customer, nation n1, nation n2
   WHERE s_suppkey = l_suppkey
     AND o_orderkey = l_orderkey
     AND c_custkey = o_custkey
     AND s_nationkey = n1.n_nationkey 
     AND c_nationkey = n2.n_nationkey 
     AND (
            (n1.n_name = 'FRANCE' and n2.n_name = 'GERMANY')
         OR (n1.n_name = 'GERMANY' and n2.n_name = 'FRANCE')
         )
     AND l_shipdate between date '1995-01-01' and date '1996-12-31'
) "Custom SQL Query5"
GROUP BY 1,
  2,
  4;
```

### Rewritten Q' (Hint BitmapScan, 4s 877ms)

```sql
/*+ BitmapScan(lineitem lineitem_l_shipdate_idx) */
SELECT "Custom SQL Query5"."cust_nation" AS "cust_nation",
  "Custom SQL Query5"."l_year" AS "l_year",
  SUM("Custom SQL Query5"."volume") AS "sum:volume:ok",
  "Custom SQL Query5"."supp_nation" AS "supp_nation"
FROM (
  SELECT n1.n_name as supp_nation,
         n2.n_name as cust_nation,
         extract(year from l_shipdate) as l_year, 
         l_extendedprice * (1 - l_discount) as volume
    FROM supplier, lineitem, orders, customer, nation n1, nation n2
   WHERE s_suppkey = l_suppkey
     AND o_orderkey = l_orderkey
     AND c_custkey = o_custkey
     AND s_nationkey = n1.n_nationkey 
     AND c_nationkey = n2.n_nationkey 
     AND (
            (n1.n_name = 'FRANCE' and n2.n_name = 'GERMANY')
         OR (n1.n_name = 'GERMANY' and n2.n_name = 'FRANCE')
         )
     AND l_shipdate between date '1995-01-01' and date '1996-12-31'
) "Custom SQL Query5"
GROUP BY 1,
  2,
  4;
```

### Rewritten Q' (Push filter before join, same plan)

```sql
SELECT "Custom SQL Query5"."cust_nation" AS "cust_nation",
  "Custom SQL Query5"."l_year" AS "l_year",
  SUM("Custom SQL Query5"."volume") AS "sum:volume:ok",
  "Custom SQL Query5"."supp_nation" AS "supp_nation"
FROM (
  SELECT n1.n_name as supp_nation,
         n2.n_name as cust_nation,
         extract(year from l_shipdate) as l_year, 
         l_extendedprice * (1 - l_discount) as volume
    FROM supplier, (
      SELECT l_suppkey,
             l_orderkey,
             l_shipdate,
             l_extendedprice,
             l_discount
        FROM lineitem lineitem1
       WHERE l_shipdate between date '1995-01-01' and date '1996-12-31'
    ) lineitem, orders, customer, nation n1, nation n2
   WHERE s_suppkey = l_suppkey
     AND o_orderkey = l_orderkey
     AND c_custkey = o_custkey
     AND s_nationkey = n1.n_nationkey 
     AND c_nationkey = n2.n_nationkey 
     AND (
            (n1.n_name = 'FRANCE' and n2.n_name = 'GERMANY')
         OR (n1.n_name = 'GERMANY' and n2.n_name = 'FRANCE')
         )
) "Custom SQL Query5"
GROUP BY 1,
  2,
  4;
```

### WeTune Rewritten (No more optimization)



## Q8 √

### Create indexes

```sql
-- create btree on p_type
create index part_p_type_idx2 ON part USING BTREE (p_type);
```

### Tableau Q (2s 182ms)

```sql
SELECT "nation1"."n_name" AS "n_name (nation1)",
  SUM(("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount"))) AS "sum:Calculation_238972315715985410:ok",
  CAST(TRUNC(EXTRACT(YEAR FROM "orders"."o_orderdate")) AS INTEGER) AS "yr:o_orderdate:ok"
FROM "public"."customer" "customer"
  INNER JOIN "public"."nation" "nation" ON ("customer"."c_nationkey" = "nation"."n_nationkey")
  INNER JOIN "public"."region" "region" ON ("nation"."n_regionkey" = "region"."r_regionkey")
  INNER JOIN "public"."orders" "orders" ON ("customer"."c_custkey" = "orders"."o_custkey")
  INNER JOIN "public"."lineitem" "lineitem" ON ("orders"."o_orderkey" = "lineitem"."l_orderkey")
  INNER JOIN "public"."part" "part" ON ("lineitem"."l_partkey" = "part"."p_partkey")
  INNER JOIN "public"."supplier" "supplier" ON ("lineitem"."l_suppkey" = "supplier"."s_suppkey")
  INNER JOIN "public"."nation" "nation1" ON ("supplier"."s_nationkey" = "nation1"."n_nationkey")
WHERE (("orders"."o_orderdate" >= (DATE '1995-01-01')) AND ("orders"."o_orderdate" <= (DATE '1996-12-31')) AND ("part"."p_type" = 'ECONOMY ANODIZED STEEL') AND ("region"."r_name" = 'AMERICA'))
GROUP BY 1,
  3;
```

### Rewritten Q' (Hint join order, 1s 50ms)

```sql
/*+ Leading(part lineitem orders customer nation region supplier nation1) */
SELECT "nation1"."n_name" AS "n_name (nation1)",
  SUM(("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount"))) AS "sum:Calculation_238972315715985410:ok",
  CAST(TRUNC(EXTRACT(YEAR FROM "orders"."o_orderdate")) AS INTEGER) AS "yr:o_orderdate:ok"
FROM "public"."customer" "customer"
  INNER JOIN "public"."nation" "nation" ON ("customer"."c_nationkey" = "nation"."n_nationkey")
  INNER JOIN "public"."region" "region" ON ("nation"."n_regionkey" = "region"."r_regionkey")
  INNER JOIN "public"."orders" "orders" ON ("customer"."c_custkey" = "orders"."o_custkey")
  INNER JOIN "public"."lineitem" "lineitem" ON ("orders"."o_orderkey" = "lineitem"."l_orderkey")
  INNER JOIN "public"."part" "part" ON ("lineitem"."l_partkey" = "part"."p_partkey")
  INNER JOIN "public"."supplier" "supplier" ON ("lineitem"."l_suppkey" = "supplier"."s_suppkey")
  INNER JOIN "public"."nation" "nation1" ON ("supplier"."s_nationkey" = "nation1"."n_nationkey")
WHERE (("orders"."o_orderdate" >= (DATE '1995-01-01')) AND ("orders"."o_orderdate" <= (DATE '1996-12-31')) AND ("part"."p_type" = 'ECONOMY ANODIZED STEEL') AND ("region"."r_name" = 'AMERICA'))
GROUP BY 1,
  3;
```

### Rewritten Q' (Force join order by extracting subquery, same plan)

```sql
SELECT "nation1"."n_name" AS "n_name (nation1)",
  SUM(("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount"))) AS "sum:Calculation_238972315715985410:ok",
  CAST(TRUNC(EXTRACT(YEAR FROM "orders"."o_orderdate")) AS INTEGER) AS "yr:o_orderdate:ok"
FROM "public"."customer" "customer"
  INNER JOIN "public"."nation" "nation" ON ("customer"."c_nationkey" = "nation"."n_nationkey")
  INNER JOIN "public"."region" "region" ON ("nation"."n_regionkey" = "region"."r_regionkey")
  INNER JOIN "public"."orders" "orders" ON ("customer"."c_custkey" = "orders"."o_custkey")
  INNER JOIN ( SELECT "lineitem1"."l_orderkey",
                      "lineitem1"."l_suppkey",
                      "lineitem1"."l_extendedprice",
                      "lineitem1"."l_discount"
                 FROM "public"."lineitem" "lineitem1"
                   INNER JOIN "public"."part" "part" ON ("lineitem1"."l_partkey" = "part"."p_partkey")
                WHERE ("part"."p_type" = 'ECONOMY ANODIZED STEEL')
  ) "lineitem" ON ("orders"."o_orderkey" = "lineitem"."l_orderkey")
  INNER JOIN "public"."supplier" "supplier" ON ("lineitem"."l_suppkey" = "supplier"."s_suppkey")
  INNER JOIN "public"."nation" "nation1" ON ("supplier"."s_nationkey" = "nation1"."n_nationkey")
WHERE (("orders"."o_orderdate" >= (DATE '1995-01-01')) AND ("orders"."o_orderdate" <= (DATE '1996-12-31')) AND ("region"."r_name" = 'AMERICA'))
GROUP BY 1,
  3;
```

### WeTune Rewritten (No more optimization)



## Q9 √

### Create indexes

```sql
CREATE EXTENSION pg_trgm;
CREATE INDEX part_p_name_idx ON part USING GIN (p_name gin_trgm_ops);
```

### Tableau Q (8s 108ms)

```sql
SELECT "Custom SQL Query6"."nation" AS "nation",
  "Custom SQL Query6"."o_year" AS "o_year",
  SUM("Custom SQL Query6"."amount") AS "sum:amount:ok"
FROM (
  select n_name as nation,
         extract(year from o_orderdate) as o_year,
         l_extendedprice * (1 - l_discount) - ps_supplycost * l_quantity as amount 
    from part, supplier, lineitem, partsupp, orders, nation
   where s_suppkey = l_suppkey
     and ps_suppkey = l_suppkey 
     and ps_partkey = l_partkey
     and p_partkey = l_partkey
     and o_orderkey = l_orderkey 
     and s_nationkey = n_nationkey 
     and p_name like '%' || 'green' || '%'
) "Custom SQL Query6"
GROUP BY 1,
  2;
```

### Rewritten Q' (Hint SeqScan, 5s 815ms)

```sql
/*+ SeqScan(lineitem) */
SELECT "Custom SQL Query6"."nation" AS "nation",
  "Custom SQL Query6"."o_year" AS "o_year",
  SUM("Custom SQL Query6"."amount") AS "sum:amount:ok"
FROM (
  select n_name as nation,
         extract(year from o_orderdate) as o_year,
         l_extendedprice * (1 - l_discount) - ps_supplycost * l_quantity as amount 
    from part, supplier, lineitem, partsupp, orders, nation
   where s_suppkey = l_suppkey
     and ps_suppkey = l_suppkey 
     and ps_partkey = l_partkey
     and p_partkey = l_partkey
     and o_orderkey = l_orderkey 
     and s_nationkey = n_nationkey 
     and p_name like '%' || 'green' || '%'
) "Custom SQL Query6"
GROUP BY 1,
  2;
```

### WeTune Rewritten (No more optimization)



## Q10

### Create indexes

```sql
-- create btree on l_returnflag
create index lineitem_l_returnflag_idx ON lineitem USING BTREE (l_returnflag);
```

### Tableau Q (3s 761ms)

```sql
SELECT "customer"."c_name" AS "c_name",
  SUM(("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount"))) AS "sum:Calculation_2185231042902667264:ok"
FROM "public"."customer" "customer"
  INNER JOIN "public"."orders" "orders" ON ("customer"."c_custkey" = "orders"."o_custkey")
  INNER JOIN "public"."lineitem" "lineitem" ON ("orders"."o_orderkey" = "lineitem"."l_orderkey")
WHERE (("lineitem"."l_returnflag" = 'R') AND ("orders"."o_orderdate" >= (DATE '1993-10-01')) AND ("orders"."o_orderdate" < (TIMESTAMP '1994-01-01 00:00:00.000')))
GROUP BY 1;
```

### WeTune Rewritten (No more optimization)



## Q11 √

### Tableau Q (217ms)

```sql
SELECT "t0"."n_name (nation1)" AS "n_name (nation1)",
  "t0"."p_name" AS "p_name",
  "t0"."sum:Calculation_2714122524503875585:ok" AS "sum:Calculation_2714122524503875585:ok"
FROM (
  SELECT "nation1"."n_name" AS "n_name (nation1)",
    "part"."p_name" AS "p_name",
    SUM(("partsupp"."ps_supplycost" * "partsupp"."ps_availqty")) AS "sum:Calculation_2714122524503875585:ok"
  FROM "public"."supplier" "supplier"
    INNER JOIN "public"."partsupp" "partsupp" ON ("supplier"."s_suppkey" = "partsupp"."ps_suppkey")
    INNER JOIN "public"."part" "part" ON ("partsupp"."ps_partkey" = "part"."p_partkey")
    INNER JOIN "public"."nation" "nation1" ON ("supplier"."s_nationkey" = "nation1"."n_nationkey")
  WHERE ("nation1"."n_name" = 'GERMANY')
  GROUP BY 1,
    2
) "t0"
  LEFT JOIN (
  SELECT "nation1"."n_name" AS "n_name (nation1)",
    SUM(("partsupp"."ps_supplycost" * "partsupp"."ps_availqty")) AS "__measure__0"
  FROM "public"."partsupp" "partsupp"
    INNER JOIN "public"."supplier" "supplier" ON ("partsupp"."ps_suppkey" = "supplier"."s_suppkey")
    INNER JOIN "public"."nation" "nation1" ON ("supplier"."s_nationkey" = "nation1"."n_nationkey")
  WHERE ("nation1"."n_name" = 'GERMANY')
  GROUP BY 1
) "t1" ON ("t0"."n_name (nation1)" = "t1"."n_name (nation1)")
WHERE ((CASE WHEN "t1"."__measure__0" = 0 THEN NULL ELSE CAST("t0"."sum:Calculation_2714122524503875585:ok" AS DOUBLE PRECISION) / "t1"."__measure__0" END) >= 9.9999999999999002E-05);
```

### Rewritten Q' (Join to Subquery, 186ms)

```sql
SELECT "nation1"."n_name" AS "n_name (nation1)",
       "part"."p_name" AS "p_name",
       SUM(("partsupp"."ps_supplycost" * "partsupp"."ps_availqty")) AS "sum:Calculation_2714122524503875585:ok"
 FROM "public"."supplier" "supplier"
   INNER JOIN "public"."partsupp" "partsupp" ON ("supplier"."s_suppkey" = "partsupp"."ps_suppkey")
   INNER JOIN "public"."part" "part" ON ("partsupp"."ps_partkey" = "part"."p_partkey")
   INNER JOIN "public"."nation" "nation1" ON ("supplier"."s_nationkey" = "nation1"."n_nationkey")
  WHERE ("nation1"."n_name" = 'GERMANY')
  GROUP BY 1, 2 
  HAVING SUM(("partsupp"."ps_supplycost" * "partsupp"."ps_availqty")) >= (
      SELECT SUM(("partsupp"."ps_supplycost" * "partsupp"."ps_availqty")) * 9.9999999999999002E-05
        FROM "public"."partsupp" "partsupp"
          INNER JOIN "public"."supplier" "supplier" ON ("partsupp"."ps_suppkey" = "supplier"."s_suppkey")
          INNER JOIN "public"."nation" "nation1" ON ("supplier"."s_nationkey" = "nation1"."n_nationkey")
       WHERE ("nation1"."n_name" = 'GERMANY')
  );
```

### WeTune Rewritten (202.120ms)

```sql
SELECT     "t0"."n_name (nation1)"                       AS "n_name (nation1)",
           "t0"."p_name"                                 AS "p_name",
           "t0"."sum:Calculation_2714122524503875585:ok" AS "sum:Calculation_2714122524503875585:ok"
FROM       (
                      SELECT     "nation1"."n_name"                                         AS "n_name (nation1)",
                                 "part"."p_name"                                            AS "p_name",
                                 Sum("partsupp"."ps_supplycost" * "partsupp"."ps_availqty") AS "sum:Calculation_2714122524503875585:ok"
                      FROM       "supplier"                                                 AS "supplier"
                      INNER JOIN "partsupp"                                                 AS "partsupp"
                      ON         "supplier"."s_suppkey" = "partsupp"."ps_suppkey"
                      INNER JOIN "part" AS "part"
                      ON         "partsupp"."ps_partkey" = "part"."p_partkey"
                      INNER JOIN "nation" AS "nation1"
                      ON         "supplier"."s_nationkey" = "nation1"."n_nationkey"
                      WHERE      "nation1"."n_name" = 'GERMANY' 
                      GROUP BY 1, 2) AS "t0"
INNER JOIN
           (
                      SELECT     "nation10"."n_name"                                          AS "n_name (nation1)",
                                 Sum("partsupp0"."ps_supplycost" * "partsupp0"."ps_availqty") AS "__measure__0"
                      FROM       "partsupp"                                                   AS "partsupp0"
                      INNER JOIN "supplier"                                                   AS "supplier0"
                      ON         "partsupp0"."ps_suppkey" = "supplier0"."s_suppkey"
                      INNER JOIN "nation" AS "nation10"
                      ON         "supplier0"."s_nationkey" = "nation10"."n_nationkey"
                      WHERE      "nation10"."n_name" = 'GERMANY' 
                      GROUP BY 1) AS "t1"
ON         "t0"."n_name (nation1)" = "t1"."n_name (nation1)"
WHERE      (
                      CASE
                                 WHEN "t1"."__measure__0" = 0 THEN NULL
                                 ELSE cast("t0"."sum:Calculation_2714122524503875585:ok" as double precision) / "t1"."__measure__0"
                      END) >= 9.9999999999999E-5;
```



## Q12 √

### Create indexes

```sql
-- create btree on l_shipmode
create index lineitem_l_shipmode_idx ON lineitem USING BTREE (l_shipmode);
```

### Tableau Q (5s 555ms)

```sql
SELECT "t0"."l_shipmode" AS "l_shipmode",
  SUM((CASE WHEN ("t0"."o_orderpriority" IN ('1-URGENT', '2-HIGH')) THEN 1 ELSE 0 END)) AS "sum:Calculation_3040633497533177856:ok",
  SUM((CASE WHEN (("t0"."o_orderpriority" <> '1-URGENT') AND ("t0"."o_orderpriority" <> '2-HIGH')) THEN 1 ELSE 0 END)) AS "sum:O High Line Priority (copy)_3040633497533612033:ok"
FROM (
  SELECT "lineitem"."l_shipmode" AS "l_shipmode",
    MIN("orders"."o_orderpriority") AS "o_orderpriority"
  FROM "public"."orders" "orders"
    INNER JOIN "public"."lineitem" "lineitem" ON ("orders"."o_orderkey" = "lineitem"."l_orderkey")
  WHERE (COALESCE(("lineitem"."l_shipmode" IN ('MAIL', 'SHIP')), FALSE) AND ((EXTRACT(EPOCH FROM (CAST("lineitem"."l_commitdate" AS TIMESTAMP) - "lineitem"."l_receiptdate")) / (60.0 * 60 * 24)) < 0) AND ((EXTRACT(EPOCH FROM (CAST("lineitem"."l_shipdate" AS TIMESTAMP) - "lineitem"."l_commitdate")) / (60.0 * 60 * 24)) < 0) AND ("lineitem"."l_receiptdate" >= (DATE '1994-01-01')) AND ("lineitem"."l_receiptdate" < (TIMESTAMP '1995-01-01 00:00:00.000')))
  GROUP BY 1,
    "orders"."o_orderkey"
) "t0"
GROUP BY 1;
```

### Rewritten Q' (Remove unecessary extract & Subquery, 5s 377ms)

```sql
SELECT "lineitem"."l_shipmode" AS "l_shipmode",
  SUM((CASE WHEN ("orders"."o_orderpriority" IN ('1-URGENT', '2-HIGH')) THEN 1 ELSE 0 END)) AS "sum:Calculation_3040633497533177856:ok",
  SUM((CASE WHEN (("orders"."o_orderpriority" <> '1-URGENT') AND ("orders"."o_orderpriority" <> '2-HIGH')) THEN 1 ELSE 0 END)) AS "sum:O High Line Priority (copy)_3040633497533612033:ok"
 FROM "public"."orders" "orders"
   INNER JOIN "public"."lineitem" "lineitem" ON ("orders"."o_orderkey" = "lineitem"."l_orderkey")
WHERE (COALESCE(("lineitem"."l_shipmode" IN ('MAIL', 'SHIP')), FALSE) AND ("lineitem"."l_commitdate" < "lineitem"."l_receiptdate") AND ("lineitem"."l_shipdate" < "lineitem"."l_commitdate") AND ("lineitem"."l_receiptdate" >= (DATE '1994-01-01')) AND ("lineitem"."l_receiptdate" < (TIMESTAMP '1995-01-01 00:00:00.000')))
GROUP BY 1;
```

### WeTune Rewritten (No more optimization)



## Q13

### Create indexes

```sql
CREATE EXTENSION pg_trgm;
CREATE INDEX orders_o_comment_idx ON orders USING GIN (o_comment gin_trgm_ops);
```

### Tableau Q (1s 86.8ms)

```sql
SELECT SUM(1) AS "cnt:_9D331941E6F749BE8A66EABA753CE0D0:ok",
  "Custom SQL Query9"."count" AS "count"
FROM (
  select c_custkey,
         count(o_orderkey) 
    from customer left outer join orders on c_custkey = o_custkey
                   and o_comment not like '%' || 'special' || '%' || 'requests' || '%'
  group by c_custkey
) "Custom SQL Query9"
GROUP BY 2;
```

### WeTune Rewritten (Error in Parsing SQL Query)



## Q14

### Tableau Q (2s 705ms)

```sql
SELECT SUM((CASE (SUBSTR(LTRIM(CAST("part"."p_type" AS TEXT), ' '), 1, LENGTH(CAST('PROMO' AS TEXT))) = CAST('PROMO' AS TEXT)) WHEN TRUE THEN ("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount")) ELSE 0 END)) AS "TEMP(Calculation_3040633497544941574)(1680315266)(0)",
  SUM(("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount"))) AS "TEMP(Calculation_3040633497544941574)(3636122938)(0)"
FROM "public"."lineitem" "lineitem"
  INNER JOIN "public"."part" "part" ON ("lineitem"."l_partkey" = "part"."p_partkey")
WHERE (("lineitem"."l_shipdate" >= (DATE '1995-09-01')) AND ("lineitem"."l_shipdate" < (TIMESTAMP '1995-10-01 00:00:00.000')))
HAVING (COUNT(1) > 0);
```

### WeTune Rewritten (No more optimization)



## Q15

### Tableau Q (3s 273ms)

```sql
SELECT "supplier"."s_name" AS "s_name",
  SUM("Custom SQL Query10"."sv_revenue") AS "sum:sv_revenue:ok"
FROM "public"."supplier" "supplier"
  INNER JOIN (
  select l_suppkey as sv_suppkey,
         sum(l_extendedprice * (1 - l_discount)) as sv_revenue 
    from lineitem 
   where l_shipdate >= (DATE '1996-01-01')
     and l_shipdate < (DATE '1996-01-01') + interval '3' month 
   group by 1
) "Custom SQL Query10" ON ("supplier"."s_suppkey" = "Custom SQL Query10"."sv_suppkey")
GROUP BY 1;
```

### WeTune Rewritten (No more optimization)



## Q16

### Create indexes

```sql
CREATE EXTENSION pg_trgm;
CREATE INDEX supplier_s_comment_idx ON supplier USING GIN (s_comment gin_trgm_ops);
```

### Tableau Q (919ms)

```sql
SELECT SUM(1) AS "cnt:partsupp_15DE8B9A059848209E180EDFF7CC796D:ok",
  "part"."p_brand" AS "p_brand"
FROM "public"."partsupp" "partsupp"
  INNER JOIN "public"."part" "part" ON ("partsupp"."ps_partkey" = "part"."p_partkey")
  LEFT JOIN (
  select s_suppkey as cs_suppkey
   from supplier
  where s_comment like '%Customer%Complaints%'
) "Custom SQL Query13" ON ("partsupp"."ps_suppkey" = "Custom SQL Query13"."cs_suppkey")
WHERE (("part"."p_brand" <> 'Brand#45') AND (CASE WHEN ("partsupp"."ps_suppkey" = "Custom SQL Query13"."cs_suppkey") THEN FALSE ELSE TRUE END) AND ("part"."p_size" IN (3, 9, 14, 19, 23, 36, 45, 49)) AND (CASE WHEN (SUBSTR(LTRIM(CAST("part"."p_type" AS TEXT), ' '), 1, LENGTH(CAST('MEDIUM POLISHED' AS TEXT))) = CAST('MEDIUM POLISHED' AS TEXT)) THEN FALSE ELSE TRUE END))
GROUP BY 2;
```

### WeTune Rewritten (Error in parsing SQL query)



## Q17 √

### Create indexes

```sql
-- create btree on p_brand
CREATE INDEX part_p_brand_idx ON part USING BTREE (p_brand);
-- create btree on p_container
CREATE INDEX part_p_container_idx ON part USING BTREE (p_container);
```

### Tableau Q (47s 46ms)

```sql
SELECT AVG("Custom SQL Query11"."avg_yearly") AS "avg:avg_yearly:ok",
  "part"."p_container" AS "p_container (Custom SQL Query11)"
FROM "public"."part" "part"
  INNER JOIN (
  select p_brand,
         p_container,
         sum(l_extendedprice) / 7.0 as avg_yearly
    from lineitem, part 
   where p_partkey = l_partkey
     and l_quantity < (
           select 0.2 * avg(l_quantity)
             from lineitem
            where l_partkey = p_partkey
         )
   group by 1, 2
) "Custom SQL Query11" ON (("part"."p_brand" = "Custom SQL Query11"."p_brand") AND ("part"."p_container" = "Custom SQL Query11"."p_container"))
WHERE ((SUBSTR(LTRIM(CAST(LOWER(CAST("part"."p_container" AS TEXT)) AS TEXT), ' '), 1, LENGTH(CAST('med' AS TEXT))) = CAST('med' AS TEXT)) AND ("part"."p_brand" = 'Brand#23'))
GROUP BY 2;
```

### Rewritten Q' (Remove unnecessary subquery & Substr to LIKE, 17s 802ms)

```sql
select p_container,
       sum(l_extendedprice) / 7.0 as avg_yearly
  from lineitem, part 
 where p_partkey = l_partkey
   and l_quantity < (
         select 0.2 * avg(l_quantity)
           from lineitem
          where l_partkey = p_partkey
       )
   and part.p_brand = 'Brand#23'
   and part.p_container LIKE 'MED%'
 group by 1;
```

### WeTune Rewritten (No more optimization)



## Q18 √

### Tableau Q (10.104 s)

```sql
SELECT "t0"."c_name" AS "c_name",
  SUM("lineitem"."l_quantity") AS "sum:l_quantity:ok:1"
FROM "public"."lineitem" "lineitem"
  INNER JOIN (
  SELECT "orders"."o_orderkey" AS "l_orderkey (lineitem)",
    MIN("customer"."c_name") AS "c_name"
  FROM "public"."customer" "customer"
    INNER JOIN "public"."orders" "orders" ON ("customer"."c_custkey" = "orders"."o_custkey")
    INNER JOIN "public"."lineitem" "lineitem" ON ("orders"."o_orderkey" = "lineitem"."l_orderkey")
    INNER JOIN (
    select l_orderkey, sum(l_quantity) as o_quantity
    from lineitem
    group by l_orderkey
  ) "Custom SQL Query" ON ("orders"."o_orderkey" = "Custom SQL Query"."l_orderkey")
  WHERE ("Custom SQL Query"."o_quantity" > 300)
  GROUP BY 1
) "t0" ON ("lineitem"."l_orderkey" = "t0"."l_orderkey (lineitem)")
GROUP BY 1;
```

### Rewritten Q' (Remove unnecessary subquery, 4.852 s)

```sql
SELECT "customer"."c_name" AS "c_name",
  SUM("lineitem"."l_quantity") AS "sum:l_quantity:ok"
 FROM "public"."customer" "customer"
   INNER JOIN "public"."orders" "orders" ON ("customer"."c_custkey" = "orders"."o_custkey")
   INNER JOIN "public"."lineitem" "lineitem" ON ("orders"."o_orderkey" = "lineitem"."l_orderkey")
   INNER JOIN (                         
   select l_orderkey, sum(l_quantity) as o_quantity
   from lineitem                                                                            
   group by l_orderkey                                                                            
 ) "Custom SQL Query" ON ("orders"."o_orderkey" = "Custom SQL Query"."l_orderkey")
  WHERE ("Custom SQL Query"."o_quantity" > 300)
GROUP BY 1;
```

### WeTune Rewritten (8701.470 ms)

```sql
SELECT "t0"."c_name"                AS "c_name",
       Sum("lineitem"."l_quantity") AS "sum:l_quantity:ok"
FROM   "lineitem" AS "lineitem"
       INNER JOIN (SELECT "orders"."o_orderkey"    AS "l_orderkey (lineitem)",
                          Min("customer"."c_name") AS "c_name"
                   FROM   "customer" AS "customer"
                          INNER JOIN "orders" AS "orders"
                                  ON "customer"."c_custkey" =
                                     "orders"."o_custkey"
                          INNER JOIN "lineitem" AS "lineitem0"
                                  ON "orders"."o_orderkey" =
                                     "lineitem0"."l_orderkey"
                          INNER JOIN (SELECT "lineitem1"."l_orderkey"      AS
                                             "l_orderkey",
                                             Sum("lineitem1"."l_quantity") AS
                                             "o_quantity"
                                      FROM   "lineitem" AS "lineitem1"
                                      GROUP  BY "l_orderkey")
                                     AS
                                     "Custom SQL Query"
                                  ON "lineitem0"."l_orderkey" =
                                     "Custom SQL Query"."l_orderkey"
                   WHERE  "Custom SQL Query"."o_quantity" > 300
                   GROUP BY "orders"."o_orderkey") AS "t0"
               ON "lineitem"."l_orderkey" = "t0"."l_orderkey (lineitem)"
GROUP BY 1;
```



## Q19

### Tableau Q (89.1ms)

```sql
SELECT SUM(("lineitem"."l_extendedprice" * (1 - "lineitem"."l_discount"))) AS "sum:Calculation_2185231042902667264:ok"
FROM "public"."lineitem" "lineitem"
  INNER JOIN "public"."part" "part" ON ("lineitem"."l_partkey" = "part"."p_partkey")
WHERE ((("part"."p_brand" = 'Brand#12') AND ("part"."p_container" IN ('SM CASE', 'SM BOX', 'SM PACK', 'SM PKG')) AND ("lineitem"."l_quantity" >= 1) AND ("lineitem"."l_quantity" <= 11) AND ("part"."p_size" >= 1) AND ("part"."p_size" <= 5) AND ("lineitem"."l_shipmode" IN ('AIR', 'AIR REG')) AND ("lineitem"."l_shipinstruct" = 'DELIVER IN PERSON')) OR (("part"."p_brand" = 'Brand#23') AND ("part"."p_container" IN ('MED BAG', 'MED BOX', 'MED PKG', 'MED PACK')) AND ("lineitem"."l_quantity" >= 10) AND ("lineitem"."l_quantity" <= 20) AND ("part"."p_size" >= 1) AND ("part"."p_size" <= 10) AND ("lineitem"."l_shipmode" IN ('AIR', 'AIR REG')) AND ("lineitem"."l_shipinstruct" = 'DELIVER IN PERSON')) OR (("part"."p_brand" = 'Brand#34') AND ("part"."p_container" IN ('LG CASE', 'LG BOX', 'LG PACK', 'LG PKG')) AND ("lineitem"."l_quantity" >= 20) AND ("lineitem"."l_quantity" <= 30) AND ("part"."p_size" >= 1) AND ("part"."p_size" <= 15) AND ("lineitem"."l_shipmode" IN ('AIR', 'AIR REG')) AND ("lineitem"."l_shipinstruct" = 'DELIVER IN PERSON')))
HAVING (COUNT(1) > 0);
```

### WeTune Rewritten (No more optimization)



## Q20_query

### Tableau Q (3s 350ms)

```sql
SELECT SUM(1) AS "cnt:_07E87B97643444148F42037178FC7634:ok",
  "supplier"."s_name" AS "s_name"
FROM "public"."supplier" "supplier"
  INNER JOIN (
  select ps_suppkey 
    from partsupp 
   where ps_partkey in ( 
             select p_partkey 
               from part 
              where p_name like 'forest' || '%'
         )
     and ps_availqty > (
             select 0.5 * sum(l_quantity)
               from lineitem
              where l_partkey = ps_partkey
                and l_suppkey = ps_suppkey
                and l_shipdate >= (DATE '1994-01-01')
                and l_shipdate < (DATE '1994-01-01') + interval '1' year
          )
) "Custom SQL Query12" ON ("supplier"."s_suppkey" = "Custom SQL Query12"."ps_suppkey")
  INNER JOIN "public"."nation" "nation1" ON ("supplier"."s_nationkey" = "nation1"."n_nationkey")
WHERE ("nation1"."n_name" = 'CANADA')
GROUP BY 2;
```

### WeTune Rewritten (No more optimization)





# Deprecated

## Q18 (Old)

### Tableau Q (26.574 s)

```sql
SELECT "t0"."c_name" AS "c_name",
  SUM("Custom SQL Query"."o_quantity") AS "sum:o_quantity:ok"
FROM (
  select l_orderkey, sum(l_quantity) as o_quantity
  from lineitem
  group by l_orderkey
) "Custom SQL Query"
  INNER JOIN (
  SELECT "Custom SQL Query"."l_orderkey" AS "l_orderkey",
    "customer"."c_name" AS "c_name"
  FROM (
    select l_orderkey, sum(l_quantity) as o_quantity
    from lineitem
    group by l_orderkey
  ) "Custom SQL Query"
    LEFT JOIN "public"."orders" "orders" ON ("Custom SQL Query"."l_orderkey" = "orders"."o_orderkey")
    LEFT JOIN "public"."customer" "customer" ON ("orders"."o_custkey" = "customer"."c_custkey")
  GROUP BY 2,
    1
) "t0" ON ("Custom SQL Query"."l_orderkey" IS NOT DISTINCT FROM "t0"."l_orderkey")
WHERE ("Custom SQL Query"."o_quantity" >= 301)
GROUP BY 1;
```

### Rewritten Q' (Push filter into subquery, 6.059 s)

```sql
SELECT "t0"."c_name" AS "c_name",
  SUM("Custom SQL Query"."o_quantity") AS "sum:o_quantity:ok"
FROM (
  select l_orderkey, sum(l_quantity) as o_quantity
  from lineitem
  group by l_orderkey
  having sum(l_quantity) >= 301
) "Custom SQL Query"
  INNER JOIN (
  SELECT "Custom SQL Query"."l_orderkey" AS "l_orderkey",
    "customer"."c_name" AS "c_name"
  FROM (
    select l_orderkey, sum(l_quantity) as o_quantity
    from lineitem
    group by l_orderkey
    having sum(l_quantity) >= 301
  ) "Custom SQL Query"
    LEFT JOIN "public"."orders" "orders" ON ("Custom SQL Query"."l_orderkey" = "orders"."o_orderkey")
    LEFT JOIN "public"."customer" "customer" ON ("orders"."o_custkey" = "customer"."c_custkey")
  GROUP BY 2,
    1
) "t0" ON ("Custom SQL Query"."l_orderkey" IS NOT DISTINCT FROM "t0"."l_orderkey")
GROUP BY 1;
```

### Rewritten Q'' (Remove duplicated subquery, 3.432 s)

```sql
SELECT "customer"."c_name" AS "c_name",
  SUM("Custom SQL Query"."o_quantity") AS "sum:o_quantity:ok"
FROM (
    select l_orderkey, sum(l_quantity) as o_quantity
    from lineitem
    group by l_orderkey
    having sum(l_quantity) >= 301
  ) "Custom SQL Query"
    LEFT JOIN "public"."orders" "orders" ON ("Custom SQL Query"."l_orderkey" = "orders"."o_orderkey")
    LEFT JOIN "public"."customer" "customer" ON ("orders"."o_custkey" = "customer"."c_custkey")
GROUP BY 1;
```









