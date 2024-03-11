from flask import Flask, request
from flask_restx import Api

app = Flask(__name__)
api = Api(app, version='1.0', title='TodoMVC API',
          description='A simple TodoMVC API',
          )


@app.before_request
def before_request():
    request.app_id = request.headers.get('x-monkeys-appid')
    request.user_id = request.headers.get('x-monkeys-userid')
    request.team_id = request.headers.get('x-monkeys-teamid')
    request.workflow_instance_id = request.headers.get('x-monkeys-workflow-instanceid')


@app.get("/manifest.json")
def get_manifest():
    return {
        "schema_version": "v1",
        "namespace": 'monkeys_tools_text',
        "auth": {
            "type": "none"
        },
        "api": {
            "type": "openapi",
            "url": "/swagger.json"
        },
        "contact_email": "dev@inf-monkeys.com",
    }
