from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_dance.contrib.google import make_google_blueprint, google
from dotenv import load_dotenv

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
load_dotenv()

# --- 기본 설정 ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'chat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
REDIS_URL = "redis://localhost:6379"

# --- 확장 프로그램 초기화 --- 
socketio = SocketIO(app, message_queue=REDIS_URL, async_mode='threading')
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# --- Flask-Dance Google OAuth Setup ---
blueprint = make_google_blueprint(
    client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
    redirect_url="/google/authorized" 
)
app.register_blueprint(blueprint, url_prefix="/login")

# --- 모델 정의 ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(100), nullable=False, unique=True)
    nickname = db.Column(db.String(100), nullable=False)

# --- 사용자 로더 설정 ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------
@app.route('/')
def home():
    return render_template('index.html', user=current_user)

@app.route('/google/authorized')
def google_authorized():
    if not google.authorized:
        return redirect(url_for("home"))
    
    resp = google.get("/oauth2/v2/userinfo")
    assert resp.ok, resp.text
    user_info = resp.json()

    user = User.query.filter_by(social_id=user_info['id']).first()
    if not user:
        user = User(social_id=user_info['id'], nickname=user_info['name'])
        db.session.add(user)
        db.session.commit()
    
    login_user(user)
    return redirect(url_for("home"))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

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


