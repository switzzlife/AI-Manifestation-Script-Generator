import os
from flask import jsonify, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user, login_user, logout_user
from app import app, db
from models import User, Script, Post, Comment
from forms import LoginForm, RegistrationForm, ScriptGenerationForm, PostForm, CommentForm, AudioCustomizationForm
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
from openai import OpenAI
from urllib.parse import urlparse

# ... (keep the existing code)

@app.route('/get_background_music/<filename>')
@login_required
def get_background_music(filename):
    audio_folder = os.path.join(current_app.static_folder, 'audio')
    file_path = os.path.join(audio_folder, filename)
    
    # Remove duplicate .mp3 extension if present
    if file_path.endswith('.mp3.mp3'):
        file_path = file_path[:-4]
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404

# ... (keep the rest of the existing code)
