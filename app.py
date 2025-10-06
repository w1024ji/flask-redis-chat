from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin


# --- 기본 설정 ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
REDIS_URL = "redis://localhost:6379"

# --- 확장 프로그램 초기화 --- 
socketio = SocketIO(app, message_queue=REDIS_URL, async_mode='threading')
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

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
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected! sid: {request.sid}')

@socketio.on('chat message')
def handle_message(msg):
    sender_id = request.sid
    
    message_with_sender = f"User {sender_id[:5]}: {msg}"
    
    print(f'Message from {sender_id}: {msg}')
    emit('chat message', message_with_sender, broadcast=True)





if __name__ == '__main__':
    socketio.run(app, debug=True)


