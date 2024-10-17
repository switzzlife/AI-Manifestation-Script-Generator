from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from flask_wtf.file import FileField, FileRequired, FileAllowed
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    profile_photo = FileField('Profile Photo', validators=[FileRequired(), FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ScriptGenerationForm(FlaskForm):
    goal = StringField('Manifestation Goal', validators=[DataRequired()])
    focus = SelectField('Focus Area', choices=[('health', 'Health'), ('wealth', 'Wealth'), ('relationships', 'Relationships'), ('career', 'Career')], validators=[DataRequired()])
    duration = SelectField('Script Duration', choices=[('5', '5 minutes'), ('10', '10 minutes'), ('15', '15 minutes')], validators=[DataRequired()])
    tone = SelectField('Script Tone', choices=[('positive', 'Positive'), ('energetic', 'Energetic'), ('calm', 'Calm'), ('confident', 'Confident')], validators=[DataRequired()])
    visualization = SelectField('Visualization Type', choices=[('guided', 'Guided Imagery'), ('future_self', 'Future Self'), ('vision_board', 'Mental Vision Board')], validators=[DataRequired()])
    affirmation_style = SelectField('Affirmation Style', choices=[('present', 'Present Tense'), ('future', 'Future Tense'), ('gratitude', 'Gratitude-based')], validators=[DataRequired()])
    generate_audio = BooleanField('Generate Audio')
    submit = SubmitField('Generate Script')

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Create Post')

class CommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Add Comment')
