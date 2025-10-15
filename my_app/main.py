from flask import Blueprint, render_template
from flask_login import current_user

main = Blueprint('main', __name__)

@main.route('/')
def home():
    """Renders the main chat page."""
    return render_template('index.html', user=current_user)
