import sys
# append the path of the parent directory
sys.path.append("..")
from core.data_manager import DataManager
import json


class QueryLogger:

    def __init__(self, dm: DataManager) -> None:
        self.dm = dm
    
    def __del__(self):
        del self.dm
    
    def log_query(self, original_query: str, rewritten_query: str, rewriting_path: list) -> None:
        self.dm.log_query(original_query, rewritten_query, rewriting_path)

    def list_queries(self) -> list:
        queries = self.dm.list_queries()
        res = []
        for query in queries:
            res.append({
                'id': query[0],
                'timestamp': query[1],
                'latency': query[2],
                'original_sql': query[3],
                'rewritten_sql': query[4]
            })
        return res
    
    def rewriting_path(self, query_id: str) -> dict:
        original_sql = self.dm.get_original_sql(query_id)
        res = {
            "original_sql": original_sql,
            "rewritings":[]
        }
        rewritings = self.dm.list_rewritings(query_id)
        for rewriting in rewritings:
            res["rewritings"].append({
                "seq": rewriting[0],
                "rule": rewriting[1],
                "rewritten_sql": rewriting[2]
            })
        return res