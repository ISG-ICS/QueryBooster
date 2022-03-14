import sys
# append the path of the parent directory
sys.path.append("..")
import configparser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import logging
from io import BytesIO
from core.query_rewritter import QueryRewritter

PORT = 8000
DIRECTORY = "static"

class MyHTTPRequestHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format, *args):
        pass

    def post_query(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')
        
        # TODO - Currently, request is the original query itself. 
        #        Use Json for request in the future if we need more information.
        original_query = request
        log_text = ""
        log_text += "\n=================================================="
        log_text += "\n    Original query"
        log_text += "\n--------------------------------------------------"
        log_text += "\n" + QueryRewritter.format(original_query)
        logging.info(log_text)
        rewritten_query = QueryRewritter.rewrite(original_query)
        log_text = ""
        log_text += "\n=================================================="
        log_text += "\n    Rewritten query"
        log_text += "\n--------------------------------------------------"
        log_text += "\n" + QueryRewritter.format(rewritten_query)
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

        # logic
        logging.info(request)
        # TODO - load rules list from database
        rules = [
            {'id': 0, 'key': 'remove_cast', 'name': 'Remove Cast', 'formula': 'CAST(<exp> AS <type>) => <exp>', 'enabled': True},
            {'id': 1, 'key': 'replace_strpos', 'name': 'Replace Strpos', 'formula': 'STRPOS(LOWER(<exp>), \'<literal>\') > 0 => <exp> ILIKE \'%<literal>%\'', 'enabled': True},
            {'id': 2, 'key': 'use_index', 'name': 'Use Index', 'formula': 'BitmapScan(tweets idx_tweets_monthly_created_at)', 'enabled': True}
        ]
        # read config.ini
        config = configparser.ConfigParser()
        config.read('../config.ini')
        # join config rules
        for rule_key, rule_enabled in config['RULES'].items():
            print(rule_key, rule_enabled)
            for rule in rules:
                if rule_key == rule['key']:
                    rule['enabled'] = True if rule_enabled == 'yes' else False

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(json.dumps(rules).encode('utf-8'))
        self.wfile.write(response.getvalue())

    def post_update_rule(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request = body.decode('utf-8')

        # logic
        logging.info(request)
        rule = json.loads(request)
        # read config.ini
        config = configparser.ConfigParser()
        config.read('../config.ini')
        if rule['key'] in config['RULES']:
            config['RULES'][rule['key']] = 'yes' if rule['enabled'] else 'no'
        with open('../config.ini', 'w') as configfile:
            config.write(configfile)

        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write("done".encode('utf-8'))
        self.wfile.write(response.getvalue())

    def do_POST(self):
        if self.path == "/":
            self.post_query()
        elif self.path == "/listRules":
            self.post_list_rules()
        elif self.path == "/updateRule":
            self.post_update_rule()


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
