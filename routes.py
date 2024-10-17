import os
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from urllib.parse import urlparse, urljoin
from werkzeug.utils import secure_filename
from app import app, db, login_manager
from models import User, Script, Post, Comment, Subscription
from forms import LoginForm, RegistrationForm, ScriptGenerationForm, PostForm, CommentForm
from chat_request import send_openai_request
import stripe
from datetime import datetime, utcnow

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or not is_safe_url(next_page):
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

# ... (rest of the file remains unchanged)