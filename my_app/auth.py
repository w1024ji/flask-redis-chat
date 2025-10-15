import os
import requests
from flask import Blueprint, redirect, url_for, request, current_app
from flask_login import login_user, logout_user, login_required
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.contrib.github import make_github_blueprint, github
from flask_dance.consumer import OAuth2ConsumerBlueprint

from .models import User
from . import db, login_manager

auth = Blueprint('auth', __name__)

# --- User Loader ---
@login_manager.user_loader
def load_user(user_id):
    """Loads user from the database."""
    return User.query.get(int(user_id))

# --- Google OAuth Setup ---
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
    redirect_url="/google/authorized"
)
auth.register_blueprint(google_bp, url_prefix="/login")

@auth.route('/google/authorized')
def google_authorized():
    if not google.authorized: return redirect(url_for("main.home"))
    resp = google.get("/oauth2/v2/userinfo")
    assert resp.ok, resp.text
    user_info = resp.json()
    user = User.query.filter_by(social_id=f"google_{user_info['id']}").first()
    if not user:
        user = User(social_id=f"google_{user_info['id']}", nickname=user_info['name'])
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for("main.home"))

# --- GitHub OAuth Setup ---
github_bp = make_github_blueprint(
    client_id=os.getenv("GITHUB_OAUTH_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_OAUTH_CLIENT_SECRET"),
    redirect_url="/github/authorized"
)
auth.register_blueprint(github_bp, url_prefix="/login")

@auth.route('/github/authorized')
def github_authorized():
    if not github.authorized: return redirect(url_for("main.home"))
    resp = github.get("/user")
    assert resp.ok, resp.text
    user_info = resp.json()
    user = User.query.filter_by(social_id=f"github_{user_info['id']}").first()
    if not user:
        user = User(social_id=f"github_{user_info['id']}", nickname=user_info['login'])
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for("main.home"))

# --- Kakao Manual OAuth ---
@auth.route("/login/kakao")
def kakao_login():
    client_id = current_app.config["KAKAO_OAUTH_CLIENT_ID"]
    redirect_uri = url_for("auth.kakao_authorized", _external=True)
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?"
        f"response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"
    )
    return redirect(kakao_auth_url)

@auth.route('/kakao/authorized')
def kakao_authorized():
    code = request.args.get("code")
    token_url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": current_app.config["KAKAO_OAUTH_CLIENT_ID"],
        "redirect_uri": url_for("auth.kakao_authorized", _external=True),
        "code": code,
    }
    token_response = requests.post(token_url, data=data)
    token_json = token_response.json()

    if 'error' in token_json:
        return f"Kakao token error: {token_json.get('error_description', '')}", 400

    access_token = token_json.get("access_token")
    user_info_url = "https://kapi.kakao.com/v2/user/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_info_response = requests.get(user_info_url, headers=headers)
    user_info = user_info_response.json()

    kakao_nickname = user_info['properties']['nickname']
    social_id_str = f"kakao_{user_info['id']}"

    user = User.query.filter_by(social_id=social_id_str).first()
    if not user:
        user = User(social_id=social_id_str, nickname=kakao_nickname)
        db.session.add(user)
        db.session.commit()
    
    login_user(user)
    return redirect(url_for("main.home"))


# --- Logout ---
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.home"))
