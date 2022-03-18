import sys
# append the path of the parent directory
sys.path.append("..")
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import logging
from io import BytesIO
from core.query_rewritter import QueryRewritter
from core.data_manager import DataManager

PORT = 8000
DIRECTORY = "static"

class MyHTTPRequestHandler(SimpleHTTPRequestHandler):

    dm = DataManager()

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
        log_text += "\n" + QueryRewritter.format(original_query)
        log_text += "\n--------------------------------------------------"
        logging.info(log_text)
        rewritten_query = QueryRewritter.rewrite(original_query, self.dm, database)
        log_text = ""
        log_text += "\n=================================================="
        log_text += "\n    Rewritten query"
        log_text += "\n--------------------------------------------------"
        log_text += "\n" + QueryRewritter.format(rewritten_query)
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

        # list rules from data manager
        rules = self.dm.list_rules()
        rules_json = []
        for rule in rules:
            rules_json.append({
                'id': rule[0],
                'key': rule[1],
                'name': rule[2],
                'formula': rule[3],
                'enabled': True if rule[4] == 1 else False
            })

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

    def do_POST(self):
        if self.path == "/":
            self.post_query()
        elif self.path == "/listRules":
            self.post_list_rules()
        elif self.path == "/switchRule":
            self.post_switch_rule()


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
