from flask import Flask, send_from_directory, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

import sys
# append the path of the parent directory
sys.path.append("..")
# from http.server import HTTPServer, SimpleHTTPRequestHandler
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

app = Flask(__name__, static_folder="static/static")
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

dm = DataManager()
rm = RuleManager(dm)
qm = QueryManager(dm)
am = AppManager(dm)
um = UserManager(dm)

#Members API Route
@app.route("/", methods=["GET", "POST"])
def post_query():
    try:
        if request.method == "GET":
            return send_from_directory('./static/', 'index.html')

        elif request.method == "POST":
            # request_data
            request_data = json.loads(request.data, strict=False)

            # Logging
            print("\n[/] request:")
            print(request)

            cmd = request_data['cmd']
            appguid = request_data['appguid']
            guid = request_data['guid']

            print("GUID: " + guid)
            # rewrite
            if cmd == 'rewrite':
                original_query = request_data['query']
                database = request_data['db']

                log_text = "\n=================================================="
                log_text += "\n    Original query"
                log_text += "\n--------------------------------------------------"
                log_text += "\n appguid: " + appguid
                log_text += "\n guid: " + guid
                log_text += "\n db: " + database
                log_text += "\n" + QueryRewriter.beautify(original_query)
                log_text += "\n--------------------------------------------------"
                print(log_text)

                # Fetch enabled rules
                # print("ETA1")
                rules = rm.fetch_enabled_rules(appguid)
                # print("ETA2")
                # Rewrite the query
                rewritten_query, rewriting_path = QueryRewriter.rewrite(original_query, rules)
                rewritten_query = QueryPatcher.patch(rewritten_query, database)

                for rewriting in rewriting_path:
                    rewriting[1] = QueryPatcher.patch(rewriting[1], database)

                formatted_original_query = QueryRewriter.reformat(original_query)
                # print("ETA3")
                qm.log_query(
                    appguid, guid, QueryPatcher.patch(formatted_original_query, database),
                    rewritten_query, rewriting_path)
                # print("ETA4")
                log_text = "\n=================================================="
                log_text += "\n    Rewritten query"
                log_text += "\n--------------------------------------------------"
                log_text += "\n appguid: " + appguid
                log_text += "\n guid: " + guid
                log_text += "\n db: " + database
                log_text += "\n" + QueryRewriter.beautify(rewritten_query)
                log_text += "\n--------------------------------------------------"
                print(log_text)

                return rewritten_query

            # report
            elif cmd == 'report':
                query_time_ms = request_data['queryTimeMs']

                log_text = "\n=================================================="
                log_text += "\n    Report query time ms"
                log_text += "\n--------------------------------------------------"
                log_text += "\n appguid: " + appguid
                log_text += "\n guid: " + guid
                log_text += "\n query_time_ms: " + str(query_time_ms)
                log_text += "\n--------------------------------------------------"
                logging.info(log_text)
                # print("ETA5")
                qm.report_query(appguid, guid, query_time_ms)
                # print("ETA6")
                # Start a background thread to suggest rewritings for this query
                threading.Thread(target=background_suggest_rewritings, name='Background Suggest Rewritings', args=[guid]).start()

                return 'true'

    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/createUser', methods=['POST'])
def create_user():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/createUser] request:")
        print(request_data)

        success = um.create_user(request_data)

        return jsonify(success), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/listRules', methods=['POST'])
def list_rules():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/listRules] request:")
        print(request_data)

        user_id = request_data.get('user_id')
        app_id = request_data.get('app_id')
        rules_json = rm.list_rules(user_id, app_id)

        return jsonify(rules_json), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/deleteRule', methods=['POST'])
def delete_rule():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/deleteRule] request:")
        print(request_data)

        success = rm.delete_rule(request_data)

        return jsonify(success), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/saveRule', methods=['POST'])
def save_rule():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/saveRule] request:")
        print(request_data)

        rule = request_data.get('rule')
        user_id = request_data.get('user_id')
        success = rm.save_rule(rule, user_id)

        return jsonify(success), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/recommendRule', methods=['POST'])
def recommend_rule():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/recommendRule] request:")
        print(request_data)

        q0 = request_data.get("q0")
        q1 = request_data.get("q1")
        recommend_rule_json = RuleGenerator.generate_general_rule(q0, q1)

        # Patch pattern and rewrite in recommend rule (TODO: Get database from frontend request)
        recommend_rule_json['pattern'] = QueryPatcher.patch(recommend_rule_json['pattern'], 'postgresql')
        recommend_rule_json['rewrite'] = QueryPatcher.patch(recommend_rule_json['rewrite'], 'postgresql')

        return jsonify(recommend_rule_json), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/recommendRules', methods=['POST'])
def recommend_rules():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/recommendRules] request:")
        print(request_data)

        database = request_data.get('database')
        examples = request_data.get('examples')
        root_rules_json = RuleGenerator.generate_rules_graph(examples)
        recommend_rules_json = RuleGenerator.recommend_rules(root_rules_json, len(examples))

        # Patch pattern and rewrite in recommended rules
        for rule in recommend_rules_json:
            rule['pattern'] = QueryPatcher.patch(rule['pattern'], database)
            rule['rewrite'] = QueryPatcher.patch(rule['rewrite'], database)

        return jsonify(recommend_rules_json), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/generateRuleGraph', methods=['POST'])
def generate_rule_graph():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/generateRuleGraph] request:")
        print(request_data)

        q0 = request_data.get("q0")
        q1 = request_data.get("q1")
        root_rule_json = RuleGenerator.generate_rule_graph(q0, q1)

        # Transform the rule graph to the UI required format
        rule_graph_json = rm.transform_rule_graph(root_rule_json)

        # Patch pattern and rewrite in rules of the rule_graph_json (TODO: Get database from frontend request)
        for rule in rule_graph_json['rules']:
            rule['pattern'] = QueryPatcher.patch(rule['pattern'], 'postgresql')
            rule['rewrite'] = QueryPatcher.patch(rule['rewrite'], 'postgresql')

        # Logging
        print("\n[/generateRuleGraph] profiles:")
        print(Profiler.show())

        return jsonify(rule_graph_json), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/generateRulesGraph', methods=['POST'])
def generate_rules_graph():
    try:
        request_json = request.get_json()

        # Logging
        logging.info("\n[/generateRulesGraph] request:")
        logging.info(request_json)

        # Extract data from the JSON request
        database = request_json['database']
        examples = request_json['examples']
        root_rules_json = RuleGenerator.generate_rules_graph(examples)

        # Transform the rules graph to the UI required format
        rule_graph_json = rm.transform_rules_graph(root_rules_json)

        # Patch pattern and rewrite in rules of the rule_graph_json
        for rule in rule_graph_json['rules']:
            rule['pattern'] = QueryPatcher.patch(rule['pattern'], database)
            rule['rewrite'] = QueryPatcher.patch(rule['rewrite'], database)

        # Logging
        logging.info("\n[/generateRulesGraph] profiles:")
        logging.info(Profiler.show())

        return jsonify(rule_graph_json), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/enableRule', methods=['POST'])
def enable_rule():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/enableRule] request:")
        print(request_data)

        rule = request_data.get('rule')
        app = request_data.get('app')
        success = dm.enable_rule(rule['id'], app['id'], app['name'])

        return jsonify(success), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/disableRule', methods=['POST'])
def disable_rule():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/disableRule] request:")
        print(request_data)

        rule = request_data.get('rule')
        app = request_data.get('app')
        success = dm.disable_rule(rule['id'], app['id'], app['name'])

        return jsonify(success), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/listQueries', methods=['POST'])
def list_queries():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/listQueries] request:")
        print(request_data)

        user_id = request_data.get('user_id')
        queries_json = qm.list_queries(user_id)

        return jsonify(queries_json), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/rewritingPath', methods=['POST'])
def rewriting_path():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/rewritingPath] request:")
        print(request_data)

        query_id = request_data.get('queryId')
        rewriting_path_json = qm.rewriting_path(query_id)

        return jsonify(rewriting_path_json), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/listApplications', methods=['POST'])
def list_applications():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/listApplications] request:")
        print(request_data)

        user_id = request_data.get('user_id') if 'user_id' in request_data else None
        applications_json = am.list_applications(user_id)

        return jsonify(applications_json), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/saveApplication', methods=['POST'])
def save_application():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/saveApplication] request:")
        print(request_data)

        success = am.save_application(request_data)

        return jsonify(success), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/deleteApplication', methods=['POST'])
def delete_application():
    try:
        request_data = request.get_json()

        # Logging
        logging.info("\n[/deleteApplication] request:")
        logging.info(request_data)

        # Extract data from the JSON request
        application = request_data['app']
        application['user_id'] = request_data['user_id']
        success = am.delete_application(application)

        return jsonify(success), 200
    except Exception as e:
        return jsonify(str(e)), 400

@app.route('/suggestionRewritingPath', methods=['POST'])
def suggestion_rewriting_path():
    try:
        request_data = request.get_json()

        # Logging
        print("\n[/suggestionRewritingPath] request:")
        print(request_data)

        query_id = request_data.get('queryId')
        suggestion_rewriting_path_json = qm.suggestion_rewriting_path(query_id)

        return jsonify(suggestion_rewriting_path_json), 200
    except Exception as e:
        return jsonify(str(e)), 400

def background_suggest_rewritings(guid):
    print("DAVID start background")
    _dm = DataManager(init=False)
    _qm = QueryManager(_dm)
    _rm = RuleManager(_dm)

    print("DAVID 1")

    log_text = ""
    log_text += "\n=================================================="
    log_text += "\n   Background suggest rewritings [Started]"
    log_text += "\n--------------------------------------------------"
    log_text += "\n guid: " + guid
    print(log_text)

    print("DAVID 2")
    # Fetch the query with the given guid
    print("guid: " + guid)
    query = _qm.fetch_query(guid)
    print("DAVID 3")
    if query['rewritten'] == 'NO':
        print("DAVID if statement")
        # Suggest rewritings for the query
        original_query = query['sql']
        log_text = ""
        log_text += "\n--------------------------------------------------"
        log_text += "\n    Original query"
        log_text += "\n--------------------------------------------------"
        log_text += "\n" + QueryRewriter.beautify(original_query)
        print(log_text)
        # Fetch all rules
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
        print(log_text)

    log_text += "\n--------------------------------------------------"
    log_text += "\n   Background suggest rewritings [Ended]"
    log_text += "\n--------------------------------------------------"

    print("DAVID -- end background")
    return None

# testing
#@app.route can take path parameters such as
#1.
# @app.route("/members")
# def members():
#     return {"members" : ["A", "B", "C"]}
#2.
# @app.route("/<filename>")
# def serve_static(filename):
#     return send_from_directory('./static/', filename)
#3.
# @app.route("/static/js/<path:filename>")
# def serve_static2(filename):
#     return send_from_directory('./static/static/js', filename)
# @app.route("/static/css/<path:filename>")
# def serve_static3(filename):
#     return send_from_directory('./static/static/css', filename)

# if __name__ == "__main__":
#     app.run(debug=True, host='0.0.0.0', port=8000)