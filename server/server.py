import sys
# append the path of the parent directory
sys.path.append("..")
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import logging
from io import BytesIO
from core.profiler import Profiler
from core.query_patcher import QueryPatcher
from core.query_rewriter import QueryRewriter
from core.data_manager import DataManager
from core.rule_generator import RuleGenerator
from core.rule_manager import RuleManager
from core.query_logger import QueryLogger

PORT = 8000
DIRECTORY = "static"

class MyHTTPRequestHandler(SimpleHTTPRequestHandler):

    dm = DataManager()
    rm = RuleManager(dm)
    ql = QueryLogger(dm)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format, *args):
        pass

    def post_query(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.debug("\n[/] request:")
        logging.debug(request)
        
        # rewrite
        request = json.loads(request, strict=False)
        original_query = request['query']
        database = request['db']
        log_text = ""
        log_text += "\n=================================================="
        log_text += "\n    Original query"
        log_text += "\n--------------------------------------------------"
        log_text += "\n" + QueryRewriter.beautify(original_query)
        log_text += "\n--------------------------------------------------"
        logging.info(log_text)
        rules = self.rm.fetch_enabled_rules(database)
        rewritten_query, rewriting_path = QueryRewriter.rewrite(original_query, rules)
        rewritten_query = QueryPatcher.patch(rewritten_query, database)
        for rewriting in rewriting_path:
            rewriting[1] = QueryPatcher.patch(rewriting[1], database)
        self.ql.log_query(original_query, rewritten_query, rewriting_path)
        log_text = ""
        log_text += "\n=================================================="
        log_text += "\n    Rewritten query"
        log_text += "\n--------------------------------------------------"
        log_text += "\n" + QueryRewriter.beautify(rewritten_query)
        log_text += "\n--------------------------------------------------"
        logging.info(log_text)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(rewritten_query.encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_list_rules(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/listRules] request:")
        logging.info(request)

        rules_json = self.rm.list_rules()

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(rules_json).encode('utf-8'))
        self.wfile.write(response.getvalue())

    def post_switch_rule(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/switcheRule] request:")
        logging.info(request)

        # enable/disable rule to data manager
        rule = json.loads(request)
        success = self.dm.switch_rule(rule['id'], rule['enabled'])

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(str(success).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_add_rule(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/addRule] request:")
        logging.info(request)

        # add rule to rule manager
        rule = json.loads(request)
        success = self.rm.add_rule(rule)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(str(success).encode('utf-8'))
        self.wfile.write(response.getvalue())

    def post_delete_rule(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/deleteRule] request:")
        logging.info(request)

        # delete rule from rule manager
        rule = json.loads(request)
        success = self.rm.delete_rule(rule)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(str(success).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_list_queries(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/listQueries] request:")
        logging.info(request)

        queries_json = self.ql.list_queries()

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(queries_json).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_rewriting_path(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/rewritingPath] request:")
        logging.info(request)

        # fetch rewriting path from query logger
        query_id = json.loads(request)["queryId"]
        rewriting_path_json = self.ql.rewriting_path(query_id)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(rewriting_path_json).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_generate_seed_rule(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/generateSeedRule] request:")
        logging.info(request)

        # generate seed rule from rule generator
        request_json = json.loads(request)
        q0 = request_json["q0"]
        q1 = request_json["q1"]
        seed_rule_json = RuleGenerator.generate_seed_rule(q0, q1)

        # patch pattern and rewrite in seed rule
        # TODO - get database from frontend request
        #
        seed_rule_json['pattern'] = QueryPatcher.patch(seed_rule_json['pattern'], 'postgresql')
        seed_rule_json['rewrite'] = QueryPatcher.patch(seed_rule_json['rewrite'], 'postgresql')

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(seed_rule_json).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_generate_rule_graph(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/generateRuleGraph] request:")
        logging.info(request)

        # generate rule graph from rule generator
        request_json = json.loads(request)
        q0 = request_json["q0"]
        q1 = request_json["q1"]
        root_rule_json = RuleGenerator.generate_rule_graph(q0, q1)

        # transform the rule graph to the UI required format
        rule_graph_json = self.rm.transform_rule_graph(root_rule_json)

        # patch pattern and rewrite in rules of the rule_graph_json
        # TODO - get database from frontend request
        #
        for rule in rule_graph_json['rules']:
            rule['pattern'] = QueryPatcher.patch(rule['pattern'], 'postgresql')
            rule['rewrite'] = QueryPatcher.patch(rule['rewrite'], 'postgresql')

        # logging
        logging.info("\n[/generateRuleGraph] profiles:")
        logging.info(Profiler.show())

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(rule_graph_json).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_generate_rules_graph(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/generateRulesGraph] request:")
        logging.info(request)

        # generate rules graph from rule generator
        request_json = json.loads(request)
        database = request_json['database']
        examples = request_json['examples']
        root_rules_json = RuleGenerator.generate_rules_graph(examples)

        # transform the rules graph to the UI required format
        rule_graph_json = self.rm.transform_rules_graph(root_rules_json)

        # patch pattern and rewrite in rules of the rule_graph_json
        #
        for rule in rule_graph_json['rules']:
            rule['pattern'] = QueryPatcher.patch(rule['pattern'], database)
            rule['rewrite'] = QueryPatcher.patch(rule['rewrite'], database)

        # logging
        logging.info("\n[/generateRulesGraph] profiles:")
        logging.info(Profiler.show())

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(rule_graph_json).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_recommend_rule(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/recommendRule] request:")
        logging.info(request)

        # generate a general rule from rule generator
        request_json = json.loads(request)
        q0 = request_json["q0"]
        q1 = request_json["q1"]
        recommend_rule_json = RuleGenerator.generate_general_rule(q0, q1)

        # patch pattern and rewrite in recommend rule
        # TODO - get database from frontend request
        #
        recommend_rule_json['pattern'] = QueryPatcher.patch(recommend_rule_json['pattern'], 'postgresql')
        recommend_rule_json['rewrite'] = QueryPatcher.patch(recommend_rule_json['rewrite'], 'postgresql')

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(recommend_rule_json).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_recommend_rules(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/recommendRules] request:")
        logging.info(request)

        # generate rules graph from rule generator
        request_json = json.loads(request)
        database = request_json['database']
        examples = request_json['examples']
        root_rules_json = RuleGenerator.generate_rules_graph(examples)
        recommend_rules_json = RuleGenerator.recommend_rules(root_rules_json, len(examples))

        # patch pattern and rewrite in recommend rules
        #
        for rule in recommend_rules_json:
            rule['pattern'] = QueryPatcher.patch(rule['pattern'], database)
            rule['rewrite'] = QueryPatcher.patch(rule['rewrite'], database)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(recommend_rules_json).encode('utf-8'))
        self.wfile.write(response.getvalue())

    def do_POST(self):
        if self.path == "/":
            self.post_query()
        elif self.path == "/listRules":
            self.post_list_rules()
        elif self.path == "/switchRule":
            self.post_switch_rule()
        elif self.path == "/listQueries":
            self.post_list_queries()
        elif self.path == "/rewritingPath":
            self.post_rewriting_path()
        elif self.path == "/generateSeedRule":
            self.post_generate_seed_rule()
        elif self.path == "/generateRuleGraph":
            self.post_generate_rule_graph()
        elif self.path == "/generateRulesGraph":
            self.post_generate_rules_graph()
        elif self.path == "/recommendRule":
            self.post_recommend_rule()
        elif self.path == "/recommendRules":
            self.post_recommend_rules()
        elif self.path == "/addRule":
            self.post_add_rule()
        elif self.path == "/deleteRule":
            self.post_delete_rule()


if __name__ == '__main__':
    # logging.basicConfig(format='%(asctime)s, %(levelname)s, %(message)s', level=logging.INFO)
    logging.basicConfig(format='%(message)s', level=logging.INFO)
    httpd = HTTPServer(('localhost', PORT), MyHTTPRequestHandler)
    print('\n  Server started.')
    print('\n    [Ctrl+C] to stop')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print('\n  Server stopped.')
