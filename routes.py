import os
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
from app import app, db, login_manager
from models import User, Script, Post, Comment, Subscription
from forms import LoginForm, RegistrationForm, ScriptGenerationForm, PostForm, CommentForm
from chat_request import send_openai_request
import stripe

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/')
def index():
    return render_template('index.html')

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
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/profile')
@login_required
def profile():
    scripts = current_user.scripts.order_by(Script.created_at.desc()).all()
    return render_template('profile.html', user=current_user, scripts=scripts)

@app.route('/generate_script', methods=['GET', 'POST'])
@login_required
def generate_script():
    if not current_user.is_paid:
        flash('You need a paid subscription to generate scripts.')
        return redirect(url_for('subscribe'))
    form = ScriptGenerationForm()
    if form.validate_on_submit():
        prompt = f"Generate a manifestation script for {form.goal.data} with a focus on {form.focus.data} and a duration of {form.duration.data} minutes. The script should be inspiring, positive, and tailored to the user's specific goal. Include affirmations and visualizations related to the goal."
        try:
            script_content = send_openai_request(prompt)
            script = Script(content=script_content, author=current_user)
            db.session.add(script)
            db.session.commit()
            flash('Your manifestation script has been generated and saved!')
            return redirect(url_for('view_script', script_id=script.id))
        except Exception as e:
            flash(f'An error occurred while generating the script: {str(e)}')
            return redirect(url_for('generate_script'))
    return render_template('generate_script.html', form=form)

@app.route('/view_script/<int:script_id>')
@login_required
def view_script(script_id):
    script = Script.query.get_or_404(script_id)
    if script.author != current_user:
        flash('You do not have permission to view this script.')
        return redirect(url_for('profile'))
    return render_template('view_script.html', script=script)

@app.route('/community')
@login_required
def community():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    form = PostForm()
    comment_form = CommentForm()
    return render_template('community.html', posts=posts, form=form, comment_form=comment_form)

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!')
        return redirect(url_for('community'))
    return redirect(url_for('community'))

@app.route('/add_comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, author=current_user, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been added!')
        return redirect(url_for('community'))
    return redirect(url_for('community'))

@app.route('/subscribe')
@login_required
def subscribe():
    return render_template('subscribe.html')

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': os.environ.get('STRIPE_PRICE_ID'),
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
    session_id = request.args.get('session_id')
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.client_reference_id == str(current_user.id):
                subscription = Subscription(
                    user_id=current_user.id,
                    stripe_customer_id=session.customer,
                    stripe_subscription_id=session.subscription,
                    active=True,
                    current_period_end=datetime.fromtimestamp(session.expires_at)
                )
                current_user.is_paid = True
                db.session.add(subscription)
                db.session.commit()
                flash('Thank you for subscribing!')
            else:
                flash('Invalid session ID')
        except Exception as e:
            flash(f'An error occurred: {str(e)}')
    return redirect(url_for('profile'))

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ.get('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    if event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        user_subscription = Subscription.query.filter_by(stripe_subscription_id=subscription['id']).first()
        if user_subscription:
            user_subscription.active = False
            user_subscription.user.is_paid = False
            db.session.commit()

    return '', 200
