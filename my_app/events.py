from flask_socketio import emit
from flask_login import current_user
from . import socketio
import os
import google.generativeai as genai
from flask import request

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        print("Gemini model loaded successfully.")
    except Exception as e:
        print(f"WARNING: Could not configure Gemini. LLM-Bot will be disabled. Error: {e}")
        model = None
else:
    print("WARNING: GOOGLE_API_KEY environment variable not set. LLM-Bot will be disabled.")
    model = None

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        print(f'Client connected: {current_user.nickname}')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected.')

@socketio.on('chat message')
def handle_message(message):
    msg_text = message.get('data', '').strip()
    if not msg_text:
        return 

    # --- LLM Bot Logic ---
    if msg_text.lower().startswith('@llm'):
        if not model:
            bot_response_text = "The LLM-Bot is not configured on the server. (Missing API key)"
        else:
            prompt = msg_text[4:].strip()
            print(f"Sending prompt to LLM: '{prompt}'")
            try:
                # Call the Gemini API
                response = model.generate_content(prompt)
                bot_response_text = response.text
            except Exception as e:
                print(f"Error calling Gemini API: {e}")
                bot_response_text = "Sorry, I'm having trouble thinking right now."
        
        bot_message = {
            'user': 'LLM-Bot',
            'message': bot_response_text
        }
        # Broadcast the message. The JS will see 'LLM-Bot' and put it on the right side.
        emit('chat message', bot_message, broadcast=True)

    # --- Real-Time Chat Logic ---
    elif current_user.is_authenticated:
        print(f"Message from {current_user.nickname}: {msg_text}")
        
        user_message = {
            'user': current_user.nickname,
            'message': msg_text,
            'profile_image': current_user.profile_image
        }
        # Broadcast the message. The JS will see a username and put it on the left side.
        emit('chat message', user_message, broadcast=True)

