import os
import requests
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.contrib.github import make_github_blueprint, github
from dotenv import load_dotenv

load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

class Config:
    SECRET_KEY = os.urandom(24)
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'chat.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = "redis://localhost:6379"
    GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    GITHUB_OAUTH_CLIENT_ID = os.getenv("GITHUB_OAUTH_CLIENT_ID")
    GITHUB_OAUTH_CLIENT_SECRET = os.getenv("GITHUB_OAUTH_CLIENT_SECRET")
    KAKAO_OAUTH_CLIENT_ID = os.getenv("KAKAO_OAUTH_CLIENT_ID")

# --- Basic Setup ---
app = Flask(__name__)
app.config.from_object(Config)

# --- Extension Initialization ---
socketio = SocketIO(app, message_queue=app.config["REDIS_URL"], async_mode='threading')
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# --- OAuth Blueprints (app.config에서 설정을 읽어옵니다) ---
google_bp = make_google_blueprint(
    client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
    client_secret=app.config["GOOGLE_OAUTH_CLIENT_SECRET"],
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
    redirect_url="/google/authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

github_bp = make_github_blueprint(
    client_id=app.config["GITHUB_OAUTH_CLIENT_ID"],
    client_secret=app.config["GITHUB_OAUTH_CLIENT_SECRET"],
    redirect_url="/github/authorized"
)
app.register_blueprint(github_bp, url_prefix="/login")

@app.route("/login/kakao")
def kakao_login():
    client_id = app.config["KAKAO_OAUTH_CLIENT_ID"]
    redirect_uri = url_for("kakao_authorized", _external=True)
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?"
        f"response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"
    )
    return redirect(kakao_auth_url)

# --- 모델 정의 ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(100), nullable=False, unique=True)
    nickname = db.Column(db.String(100), nullable=False)

# --- 사용자 로더 설정 ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---
@app.route('/')
def home():
    return render_template('index.html', user=current_user)

@app.route('/google/authorized')
def google_authorized():
    if not google.authorized: return redirect(url_for("home"))
    resp = google.get("/oauth2/v2/userinfo")
    assert resp.ok, resp.text
    user_info = resp.json()
    user = User.query.filter_by(social_id=f"google_{user_info['id']}").first()
    if not user:
        user = User(social_id=f"google_{user_info['id']}", nickname=user_info['name'])
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for("home"))

@app.route('/github/authorized')
def github_authorized():
    if not github.authorized: return redirect(url_for("home"))
    resp = github.get("/user")
    assert resp.ok, resp.text
    user_info = resp.json()
    user = User.query.filter_by(social_id=f"github_{user_info['id']}").first()
    if not user:
        user = User(social_id=f"github_{user_info['id']}", nickname=user_info['login'])
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for("home"))


# Kakao 인증
@app.route('/kakao/authorized')
def kakao_authorized():
    code = request.args.get("code")
    token_url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": app.config["KAKAO_OAUTH_CLIENT_ID"],
        "redirect_uri": url_for("kakao_authorized", _external=True),
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
    return redirect(url_for("home"))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

# --- SocketIO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        print(f'Client connected: {current_user.nickname}')

@socketio.on('chat message')
def handle_message(msg):
    if current_user.is_authenticated:
        message_with_sender = f"{current_user.nickname}: {msg}"
        print(f'Message from {current_user.nickname}: {msg}')
        emit('chat message', message_with_sender, broadcast=True)





if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)


