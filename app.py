from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# Create an instance of the Flask class
app = Flask(__name__)
# It's good practice to set a secret key for security
app.config['SECRET_KEY'] = 'mysecret!' 

# Wrap the Flask app with SocketIO
# The async_mode is set to 'threading' for simplicity with the Flask dev server
socketio = SocketIO(app, async_mode='threading')

# Define a route for the main page to serve the HTML
@app.route('/')
def home():
    return render_template('index.html')

# Define an event handler for when a user connects
@socketio.on('connect')
def handle_connect():
    print('Client connected!')

@socketio.on('chat message')
def handle_message(msg):
    print('Message: ' + msg)
    # Broadcast the message to all connected clients
    emit('chat message', msg, broadcast=True)





# This is needed to run the app with SocketIO
if __name__ == '__main__':
    socketio.run(app, debug=True)


