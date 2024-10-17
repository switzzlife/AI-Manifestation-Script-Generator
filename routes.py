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
from datetime import datetime, timedelta

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

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        if form.profile_photo.data:
            filename = secure_filename(form.profile_photo.data.filename)
            form.profile_photo.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.profile_photo = filename
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/profile')
@login_required
def profile():
    scripts = Script.query.filter_by(user_id=current_user.id).order_by(Script.created_at.desc()).all()
    return render_template('profile.html', user=current_user, scripts=scripts)

@app.route('/generate_script', methods=['GET', 'POST'])
@login_required
def generate_script():
    if not current_user.is_paid:
        flash('You need to subscribe to generate scripts.', 'warning')
        return redirect(url_for('subscribe', next='generate_script'))
    
    form = ScriptGenerationForm()
    if form.validate_on_submit():
        prompt = f"Generate a manifestation script for the following goal: {form.goal.data}. Focus on {form.focus.data}. The script should be {form.duration.data} minutes long, with a {form.tone.data} tone. Use {form.visualization.data} visualization and {form.affirmation_style.data} affirmations."
        
        try:
            generated_script = send_openai_request(prompt)
            new_script = Script(content=generated_script, user_id=current_user.id)
            db.session.add(new_script)
            db.session.commit()
            return redirect(url_for('view_script', script_id=new_script.id))
        except Exception as e:
            flash(f'Error generating script: {str(e)}', 'error')
            return redirect(url_for('generate_script'))
    
    return render_template('generate_script.html', form=form)

@app.route('/view_script/<int:script_id>')
@login_required
def view_script(script_id):
    script = Script.query.get_or_404(script_id)
    if script.user_id != current_user.id:
        flash('You do not have permission to view this script.', 'error')
        return redirect(url_for('profile'))
    return render_template('view_script.html', script=script)

@app.route('/subscribe')
@login_required
def subscribe():
    return render_template('subscribe.html', stripe_publishable_key=app.config['STRIPE_PUBLIC_KEY'])

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': app.config['STRIPE_PRICE_ID'],
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=url_for('subscribe_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('subscribe', _external=True),
            client_reference_id=current_user.id,
        )
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        return jsonify(error=str(e)), 403

@app.route('/subscribe/success')
@login_required
def subscribe_success():
    return render_template('subscribe_success.html')

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, app.config['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        fulfill_order(session)

    return 'Success', 200

def fulfill_order(session):
    user_id = session.get('client_reference_id')
    user = User.query.get(user_id)
    if user:
        user.is_paid = True
        subscription = Subscription(
            user_id=user.id,
            stripe_customer_id=session.get('customer'),
            stripe_subscription_id=session.get('subscription'),
            active=True,
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(subscription)
        db.session.commit()

@app.route('/community', methods=['GET', 'POST'])
@login_required
def community():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('community'))
    
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('community.html', title='Community', form=form, posts=posts)

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'errors': form.errors}), 400

@app.route('/add_comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, author=current_user, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'errors': form.errors}), 400

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
