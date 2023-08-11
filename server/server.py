import sys
# append the path of the parent directory
sys.path.append("..")
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import logging
import threading
from io import BytesIO
from core.profiler import Profiler
from core.query_patcher import QueryPatcher
from core.query_rewriter import QueryRewriter
from core.data_manager import DataManager
from core.rule_generator import RuleGenerator
from core.rule_manager import RuleManager
from core.query_manager import QueryManager
from core.app_manager import AppManager
from core.user_manager import UserManager

PORT = 8000
DIRECTORY = "static"

class MyHTTPRequestHandler(SimpleHTTPRequestHandler):

    dm = DataManager()
    rm = RuleManager(dm)
    qm = QueryManager(dm)
    am = AppManager(dm)
    um = UserManager(dm)

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
        
        request = json.loads(request, strict=False)
        cmd = request['cmd']
        appguid = request['appguid']
        guid = request['guid']
        
        # rewrite
        if cmd == 'rewrite':
            original_query = request['query']
            database = request['db']
            log_text = ""
            log_text += "\n=================================================="
            log_text += "\n    Original query"
            log_text += "\n--------------------------------------------------"
            log_text += "\n appguid: " + appguid
            log_text += "\n guid: " + guid
            log_text += "\n db: " + database
            log_text += "\n" + QueryRewriter.beautify(original_query)
            log_text += "\n--------------------------------------------------"
            logging.info(log_text)
            rules = self.rm.fetch_enabled_rules(appguid)
            rewritten_query, rewriting_path = QueryRewriter.rewrite(original_query, rules)
            rewritten_query = QueryPatcher.patch(rewritten_query, database)
            for rewriting in rewriting_path:
                rewriting[1] = QueryPatcher.patch(rewriting[1], database)
            self.qm.log_query(appguid, guid, QueryPatcher.patch(QueryRewriter.reformat(original_query), database), rewritten_query, rewriting_path)
            log_text = ""
            log_text += "\n=================================================="
            log_text += "\n    Rewritten query"
            log_text += "\n--------------------------------------------------"
            log_text += "\n appguid: " + appguid
            log_text += "\n guid: " + guid
            log_text += "\n db: " + database
            log_text += "\n" + QueryRewriter.beautify(rewritten_query)
            log_text += "\n--------------------------------------------------"
            logging.info(log_text)
            self.send_response(200)
            self.end_headers()
            response = BytesIO()
            response.write(rewritten_query.encode('utf-8'))
            self.wfile.write(response.getvalue())
        # report
        elif cmd == 'report':
            query_time_ms = request['queryTimeMs']
            log_text = ""
            log_text += "\n=================================================="
            log_text += "\n    Report query time ms"
            log_text += "\n--------------------------------------------------"
            log_text += "\n appguid: " + appguid
            log_text += "\n guid: " + guid
            log_text += "\n query_time_ms: " + str(query_time_ms)
            log_text += "\n--------------------------------------------------"
            logging.info(log_text)
            self.qm.report_query(appguid, guid, query_time_ms)
            
            # start a background thread to suggest rewritings for this query
            #
            threading.Thread(target=self.background_suggest_rewritings, name='Background Suggest Rewritings', args=[guid]).start()
            
            self.send_response(200)
            self.end_headers()
            response = BytesIO()
            response.write('true'.encode('utf-8'))
            self.wfile.write(response.getvalue())
    
    def post_list_rules(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/listRules] request:")
        logging.info(request)

        request = json.loads(request, strict=False)
        user_id = request['user_id'] if 'user_id' in request else None
        app_id = request['app_id'] if 'app_id' in request else None

        rules_json = self.rm.list_rules(user_id, app_id)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(rules_json).encode('utf-8'))
        self.wfile.write(response.getvalue())

    def post_enable_rule(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/enableRule] request:")
        logging.info(request)

        # enable rule for the given app to data manager
        request = json.loads(request, strict=False)
        rule = request['rule']
        app = request['app']
        success = self.dm.enable_rule(rule['id'], app['id'], app['name'])

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(str(success).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_disable_rule(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/disableRule] request:")
        logging.info(request)

        # enable rule for the given app to data manager
        request = json.loads(request, strict=False)
        rule = request['rule']
        app = request['app']
        success = self.dm.disable_rule(rule['id'], app['id'], app['name'])

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
        request = json.loads(request, strict=False)
        rule = request['rule']
        user_id = request['user_id']
        success = self.rm.add_rule(rule, user_id)

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

        request = json.loads(request, strict=False)
        user_id = request['user_id'] if 'user_id' in request else None

        queries_json = self.qm.list_queries(user_id)

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

        # fetch rewriting path from query manager
        query_id = json.loads(request)["queryId"]
        rewriting_path_json = self.qm.rewriting_path(query_id)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(rewriting_path_json).encode('utf-8'))
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
    
    def post_list_applications(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/listApplications] request:")
        logging.info(request)

        request = json.loads(request, strict=False)
        user_id =  user_id = request['user_id'] if 'user_id' in request else None

        applications_json = self.am.list_applications(user_id)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(applications_json).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_save_application(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/saveApplication] request:")
        logging.info(request)

        # fetch application information
        app = json.loads(request)
        success = self.am.save_applications(app)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(str(success).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_delete_application(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/deleteApplication] request:")
        logging.info(request)

        # delete rule from rule manager
        request = json.loads(request)
        application = request['app']
        application['user_id'] = request['user_id']
        success = self.am.delete_application(application)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(str(success).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def post_create_user(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/createUser] request:")
        logging.info(request)

        # add rule to rule manager
        request = json.loads(request, strict=False)
        success = self.um.create_user(request)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(str(success).encode('utf-8'))
        self.wfile.write(response.getvalue())

    def post_suggestion_rewriting_path(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logging
        logging.info("\n[/suggestionRewritingPath] request:")
        logging.info(request)

        # fetch suggestion rewriting path from query manager
        query_id = json.loads(request)["queryId"]
        suggestion_rewriting_path_json = self.qm.suggestion_rewriting_path(query_id)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(suggestion_rewriting_path_json).encode('utf-8'))
        self.wfile.write(response.getvalue())
    
    def background_suggest_rewritings(self, guid: str) -> None:

        _dm = DataManager(init=False)
        _qm = QueryManager(_dm)
        _rm = RuleManager(_dm)

        log_text = ""
        log_text += "\n=================================================="
        log_text += "\n   Background suggest rewritings [Started]"
        log_text += "\n--------------------------------------------------"
        log_text += "\n guid: " + guid
        logging.info(log_text)

        # fetch the query with the given guid
        query = _qm.fetch_query(guid)
        if query['rewritten'] == 'NO':
            # suggest rewritings for the query
            original_query = query['sql']
            log_text = ""
            log_text += "\n--------------------------------------------------"
            log_text += "\n    Original query"
            log_text += "\n--------------------------------------------------"
            log_text += "\n" + QueryRewriter.beautify(original_query)
            logging.info(log_text)
            # fetch all rules
            rules = _rm.fetch_all_rules()
            rewritten_query, rewriting_path = QueryRewriter.rewrite(original_query, rules)
            rewritten_query = QueryPatcher.patch(rewritten_query)
            for rewriting in rewriting_path:
                rewriting[1] = QueryPatcher.patch(rewriting[1])
            _qm.log_query_suggestion(query['id'], rewritten_query, rewriting_path)
            log_text = ""
            log_text += "\n--------------------------------------------------"
            log_text += "\n    Rewritten query"
            log_text += "\n--------------------------------------------------"
            log_text += "\n" + QueryRewriter.beautify(rewritten_query)
            log_text += "\n--------------------------------------------------"
            logging.info(log_text)
        
        log_text += "\n--------------------------------------------------"
        log_text += "\n   Background suggest rewritings [Ended]"
        log_text += "\n--------------------------------------------------"

        return None

    def do_POST(self):
        if self.path == "/":
            self.post_query()
        elif self.path == "/listRules":
            self.post_list_rules()
        elif self.path == "/enableRule":
            self.post_enable_rule()
        elif self.path == "/disableRule":
            self.post_disable_rule()
        elif self.path == "/listQueries":
            self.post_list_queries()
        elif self.path == "/rewritingPath":
            self.post_rewriting_path()
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
        elif self.path == "/listApplications":
            self.post_list_applications()
        elif self.path == "/saveApplication":
            self.post_save_application()
        elif self.path == "/deleteApplication":
            self.post_delete_application()
        elif self.path == "/createUser":
            self.post_create_user()
        elif self.path == "/suggestionRewritingPath":
            self.post_suggestion_rewriting_path()


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
