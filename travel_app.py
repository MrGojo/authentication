from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField, SelectField
from wtforms.validators import DataRequired
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask_bootstrap import Bootstrap

# Flask App Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel_plans.db'  # Use your database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Add your login route name here
Bootstrap(app)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)  # For simplicity, store passwords in plain text (not recommended)
    travel_details = db.relationship('TravelDetail', backref='user', lazy=True)


class TravelDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    destination = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    travel_type = db.Column(db.String(50), nullable=False)
    interests = db.Column(db.Text, nullable=False)
    places_of_interest = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<TravelDetail {self.user.username} - {self.destination}>"

# Forms
class TravelDetailForm(FlaskForm):
    destination = StringField('Destination', validators=[DataRequired()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()])
    travel_type = SelectField('Travel Type', choices=[('solo', 'Solo'), ('group', 'Group'), ('leisure', 'Leisure'), ('adventure', 'Adventure')], validators=[DataRequired()])
    interests = TextAreaField('Interests', validators=[DataRequired()])
    places_of_interest = TextAreaField('Places of Interest', validators=[DataRequired()])

# User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
@login_required
def travel_list():
    travel_details = TravelDetail.query.filter_by(user_id=current_user.id).all()
    return render_template('travel_list.html', travel_details=travel_details)

@app.route('/create', methods=['GET', 'POST'])
@login_required
def travel_create():
    form = TravelDetailForm()
    if form.validate_on_submit():
        travel_detail = TravelDetail(
            user_id=current_user.id,
            destination=form.destination.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            travel_type=form.travel_type.data,
            interests=form.interests.data,
            places_of_interest=form.places_of_interest.data
        )
        db.session.add(travel_detail)
        db.session.commit()
        flash('Travel plan added successfully!')
        return redirect(url_for('travel_list'))
    return render_template('travel_form.html', form=form)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def travel_update(id):
    travel_detail = TravelDetail.query.get_or_404(id)
    if travel_detail.user_id != current_user.id:
        return redirect(url_for('travel_list'))  # Prevent editing other user's travel plans
    
    form = TravelDetailForm(obj=travel_detail)
    if form.validate_on_submit():
        travel_detail.destination = form.destination.data
        travel_detail.start_date = form.start_date.data
        travel_detail.end_date = form.end_date.data
        travel_detail.travel_type = form.travel_type.data
        travel_detail.interests = form.interests.data
        travel_detail.places_of_interest = form.places_of_interest.data
        db.session.commit()
        flash('Travel plan updated successfully!')
        return redirect(url_for('travel_list'))
    return render_template('travel_form.html', form=form)

@app.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def travel_delete(id):
    travel_detail = TravelDetail.query.get_or_404(id)
    if travel_detail.user_id != current_user.id:
        return redirect(url_for('travel_list'))  # Prevent deleting other user's travel plans
    
    if request.method == 'POST':
        db.session.delete(travel_detail)
        db.session.commit()
        flash('Travel plan deleted successfully!')
        return redirect(url_for('travel_list'))
    return render_template('travel_confirm_delete.html', travel_detail=travel_detail)

# HTML Templates - These should be inside a `templates` folder
# travel_list.html
'''
<!DOCTYPE html>
<html>
    <h1>Travel Plans</h1>
    <a href="{{ url_for('travel_create') }}">Add Travel Plan</a>
    <ul>
        {% for travel in travel_details %}
            <li>
                {{ travel.destination }} ({{ travel.start_date }} - {{ travel.end_date }})
                <a href="{{ url_for('travel_update', id=travel.id) }}">Edit</a>
                <a href="{{ url_for('travel_delete', id=travel.id) }}">Delete</a>
            </li>
        {% endfor %}
    </ul>
</html>
'''

# travel_form.html
'''
<!DOCTYPE html>
<html>
    <h1>{% if form.instance.id %}Edit{% else %}Add{% endif %} Travel Plan</h1>
    <form method="post">
        {{ form.hidden_tag() }}  <!-- Includes CSRF token -->
        {{ form.destination.label }} {{ form.destination() }}
        {{ form.start_date.label }} {{ form.start_date() }}
        {{ form.end_date.label }} {{ form.end_date() }}
        {{ form.travel_type.label }} {{ form.travel_type() }}
        {{ form.interests.label }} {{ form.interests() }}
        {{ form.places_of_interest.label }} {{ form.places_of_interest() }}
        <button type="submit">Save</button>
    </form>
    <a href="{{ url_for('travel_list') }}">Back to List</a>
</html>
'''

# travel_confirm_delete.html
'''
<!DOCTYPE html>
<html>
    <h1>Confirm Delete</h1>
    <p>Are you sure you want to delete "{{ travel_detail.destination }}"?</p>
    <form method="post">
        {{ form.hidden_tag() }}  <!-- Includes CSRF token -->
        <button type="submit">Yes, delete</button>
    </form>
    <a href="{{ url_for('travel_list') }}">Cancel</a>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True)
