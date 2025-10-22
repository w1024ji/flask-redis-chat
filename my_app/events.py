from flask_socketio import emit
from flask_login import current_user
from . import socketio

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
