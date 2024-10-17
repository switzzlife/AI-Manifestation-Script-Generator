import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from app import app, db
from models import User, Script, Post, Comment, Subscription
from forms import LoginForm, RegistrationForm, ScriptGenerationForm, PostForm, CommentForm
from chat_request import send_openai_request
import stripe
from datetime import datetime
import logging

stripe.api_key = app.config['STRIPE_SECRET_KEY']

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

# Rest of the file remains unchanged
