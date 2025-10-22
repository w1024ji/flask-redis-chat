from flask import Blueprint, render_template, jsonify, request, redirect, url_for, current_app, flash
from flask_login import current_user, login_required
import re
from collections import Counter
import requests
from bs4 import BeautifulSoup
import os
import uuid
from PIL import Image
from my_app import db

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('index.html', user=current_user)

STOP_WORDS = set([
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'as', 'at',
    'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can', 'did', 'do',
    'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'has', 'have', 'having',
    'he', 'her', 'here', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it',
    'its', 'itself', 'just', 'me', 'more', 'most', 'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 'off', 'on',
    'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 's', 'same', 'she', 'should',
    'so', 'some', 'such', 't', 'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there',
    'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'we', 'were',
    'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'you', 'your', 'yours',
    'yourself', 'yourselves', 'said', 'new', 'also', 'image', 'get', 'could', 'would', 'one'
])

def get_top_words():
    URL = "https://www.bbc.com/news"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=10)
        response.raise_for_status() 

        soup = BeautifulSoup(response.content, 'html.parser')
        
        text = soup.get_text(separator=' ', strip=True).lower()
        words = re.findall(r'\b[a-z]{3,}\b', text)
        filtered_words = [word for word in words if word not in STOP_WORDS]
        word_counts = Counter(filtered_words)
        top_50_words = word_counts.most_common(50)
        
        return [{"word": word, "count": count} for word, count in top_50_words]

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return []

@main.route('/word-ranker')
def word_ranker():
    return render_template('word_ranker.html')

@main.route('/api/word-ranks')
def word_ranks_api():
    top_words = get_top_words()
    return jsonify(top_words)

def save_picture(form_picture):
    random_hex = uuid.uuid4().hex[:8]
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)

    output_size = (150, 150)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'profile_image' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['profile_image']
        
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file:
            filename = save_picture(file)
            current_user.profile_image = filename
            db.session.commit()
            
            flash('Your profile has been updated!')
            return redirect(url_for('main.profile'))

    return render_template('profile.html', title='My Profile')
