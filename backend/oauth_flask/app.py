
from flask import Flask, redirect, request, jsonify
import os, yaml

app = Flask(__name__)

with open("config/auth/providers.yaml") as f:
    PROVIDERS = yaml.safe_load(f)["providers"]

@app.route("/oauth/<provider>/login")
def login(provider):
    p = PROVIDERS[provider]
    redirect_uri = request.url_root + f"oauth/{provider}/callback"
    scope = " ".join(p["scopes"])
    url = f"{p['auth_url']}?client_id={os.getenv(p.get('client_id_env',''))}&redirect_uri={redirect_uri}&response_type=code&scope={scope}"
    return redirect(url)

@app.route("/oauth/<provider>/callback")
def callback(provider):
    code = request.args.get("code")
    return jsonify({"provider": provider, "code": code})
