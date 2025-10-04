from flask import Flask

# Create an instance of the Flask class
app = Flask(__name__)

# Define a "route" for the main page
@app.route('/')
def home():
    return "Hello, Chat App!"