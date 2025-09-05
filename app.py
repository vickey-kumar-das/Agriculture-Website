# -*- coding: utf-8 -*-
"""
Created on Sat Mar  2 21:46:27 2019

@author: PRATYUSH, Rahul, Somya, Abhay
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_cors import CORS
import numpy as np
import os
import pandas as pd
import requests
from sklearn.linear_model import LinearRegression
from datetime import datetime, date, timedelta, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
# import crops
# from datagovindia import DataGovIndia

# --- Constants ---
COMMODITY_PRICES_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"

# --- API Client Initialization ---
datagovin = None

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['UPLOAD_FOLDER'] = 'uploads'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'site2.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '6b1cca9b5e62d362b4ba3d82a03c75d7c682b702636990fb'
db = SQLAlchemy(app)

# Ensure the instance directory exists
instance_path = os.path.join(basedir, 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)



# --- Data Loading ---
df_market_data = pd.DataFrame()

# --- Mappings and Helper Functions ---
COMMODITY_MAP = {
    "arhar": "Atta (Wheat)",
    "bajra": "Bajra",
    "barley": "Barley",
    "copra": "Copra",
    "cotton": "Cotton",
    "sesamum": "Sesamum",
    "gram": "Gram Dal",
    "groundnut": "Groundnut Oil (Packed)",
    "jowar": "Jowar",
    "maize": "Maize",
    "masoor": "Masoor Dal",
    "moong": "Moong Dal",
    "niger": "Niger Seed",
    "paddy": "Rice",
    "ragi": "Ragi",
    "rape": "Rape Seed",
    "jute": "Jute",
    "safflower": "Safflower",
    "soyabean": "Soya Oil (Packed)",
    "sugarcane": "Sugarcane",
    "sunflower": "Sunflower Oil (Packed)",
    "urad": "Urad Dal",
    "wheat": "Wheat"
}

def get_latest_price(commodity_name):
    """Returns dummy price data. Live API has been temporarily disabled."""
    return {
        "commodity": commodity_name.capitalize(),
        "market": "N/A",
        "price": "N/A",
        "date": date.today().strftime("%d/%m/%Y"),
        "error": "Live market data is temporarily unavailable. Using placeholder data."
    }

def get_historical_prices(commodity_name, limit=365):
    """Returns empty historical data. Live API has been temporarily disabled."""
    return {"data": [], "error": "Historical market data is temporarily unavailable."}

def get_price_prediction(commodity_name):
    """Generates a price prediction based on historical data."""
    historical_result = get_historical_prices(commodity_name)
    if historical_result.get("error"):
        return {"error": historical_result["error"]}
    
    historical_data = historical_result["data"]
    if len(historical_data) < 2:
        return {"error": "Not enough historical data to make a prediction."}
    
    X = np.array([(d[0] - historical_data[0][0]).days for d in historical_data]).reshape(-1, 1)
    y = np.array([d[1] for d in historical_data])
    model = LinearRegression()
    model.fit(X, y)
    
    last_date_days = (historical_data[-1][0] - historical_data[0][0]).days
    next_day_days = last_date_days + 1
    predicted_price = model.predict(np.array([[next_day_days]]))[0]
    predicted_date = historical_data[-1][0] + timedelta(days=1)
    
    return {
        "commodity": commodity_name,
        "predicted_price": round(predicted_price, 2),
        "predicted_date": predicted_date.strftime('%d/%m/%Y'),
        "error": None
    }

# --- Database Models (omitted for brevity, they are unchanged) ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile = db.relationship('UserProfile', backref='user', uselist=False)

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location = db.Column(db.String(120), nullable=True)
    soil_type = db.Column(db.String(120), nullable=True)
    preferred_crops = db.Column(db.String(500), nullable=True)
    price_alerts = db.Column(db.Text, nullable=True)

class CropInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    optimal_temp_min = db.Column(db.Float, nullable=True)
    optimal_temp_max = db.Column(db.Float, nullable=True)
    optimal_rainfall_min = db.Column(db.Float, nullable=True)
    optimal_rainfall_max = db.Column(db.Float, nullable=True)
    soil_preference = db.Column(db.String(120), nullable=True)
    fertilizer_recommendation = db.Column(db.Text, nullable=True)
    pest_control_recommendation = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(200), nullable=True)
    prime_loc = db.Column(db.String(500), nullable=True)
    type_c = db.Column(db.String(50), nullable=True)
    export_countries = db.Column(db.String(500), nullable=True)

class ForumPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('posts', lazy=True))
    comments = db.relationship('ForumComment', backref='post', lazy=True, cascade='all, delete-orphan')

class ForumComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('comments', lazy=True))

class MarketInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mandi_name = db.Column(db.String(120), nullable=False)
    commodity_name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User', backref=db.backref('blog_posts', lazy=True))

class PageView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page_url = db.Column(db.String(500), nullable=False)
    ip_address = db.Column(db.String(100), nullable=False)
    referrer = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    

# --- Core Routes (omitted for brevity, they are unchanged) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
            flash('Login successful!', 'success')
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            new_user = User(username=username, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('signup'))
    
    all_crops_info = CropInfo.query.all()
    
    major_crops = ["wheat", "paddy", "maize", "gram"]
    live_prices = []
    for crop in major_crops:
        price_data = get_latest_price(crop)
        price_data['name'] = crop
        live_prices.append(price_data)
    
    context = {
        "live_prices": live_prices,
        "all_crops_info": all_crops_info
    }
    return render_template('index.html', context=context)

@app.route('/commodity/<name>')
def crop_profile(name):
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))
    
    crop_info = CropInfo.query.filter_by(name=name).first()
    if not crop_info:
        flash(f'Crop {name} not found.', 'danger')
        return redirect(url_for('index'))

    price_data = get_latest_price(name)
    prediction_data = get_price_prediction(name)
    
    context = {
        "name": crop_info.name,
        "price_data": price_data,
        "prediction_data": prediction_data,
        "image_url": crop_info.image_url,
        "prime_loc": crop_info.prime_loc,
        "type_c": crop_info.type_c,
        "export": crop_info.export_countries
    }
    return render_template('commodity.html', context=context)

@app.route('/image_prediction')
def image_prediction():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))
    return render_template('image_predict.html')

@app.route('/uploader', methods=['GET', 'POST'])
def uploader():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('prediction_result.html', error='No file part')
        f = request.files['file']
        if f.filename == '':
            return render_template('prediction_result.html', error='No selected file')
        if f:
            filename = secure_filename(f.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(filepath)
            recognized_crop = None
            for crop_name in COMMODITY_MAP.keys():
                if crop_name in filename.lower():
                    recognized_crop = crop_name
                    break
            if recognized_crop:
                name = recognized_crop
                price_data = get_latest_price(name)
                crop_data = crops.crop(name)
                context = {
                    "name": name,
                    "price_data": price_data,
                    "image_url": crop_data[0],
                    "prime_loc": crop_data[1],
                    "type_c": crop_data[2],
                    "export": crop_data[3]
                }
                return render_template('prediction_result.html', context=context)
            else:
                error_message = f"Could not recognize the crop from the filename: '{filename}'. Please name the file with a crop name like 'wheat.jpg' or 'paddy.png'."
                return render_template('prediction_result.html', error=error_message)
    return redirect(url_for('image_prediction'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/how_to_use')
def how_to_use():
    return render_template('how_to_use.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))
    user = User.query.get_or_404(session['user_id'])
    if request.method == 'POST':
        location = request.form['location']
        soil_type = request.form['soil_type']
        if not user.profile:
            user.profile = UserProfile(user_id=user.id)
        user.profile.location = location
        user.profile.soil_type = soil_type
        user.profile.preferred_crops = request.form.get('preferred_crops', '')
        user.profile.price_alerts = request.form.get('price_alerts', '')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=user)

@app.route('/recommendation')
def recommendation():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))
    crops_db = CropInfo.query.all()
    return render_template('recommendation.html', crops=crops_db)

@app.route('/get_recommendation', methods=['POST'])
def get_recommendation():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))
    user = User.query.get_or_404(session['user_id'])
    if not user.profile or not user.profile.location:
        flash('Please set your location in your profile before getting recommendations.', 'warning')
        return redirect(url_for('profile'))
    crop_name = request.form.get('crop_name')
    crop_image = request.files.get('crop_image')
    if crop_image and crop_image.filename != '':
        filename = secure_filename(crop_image.filename)
        for crop in CropInfo.query.all():
            if crop.name.lower() in filename.lower():
                crop_name = crop.name
                break
        if not crop_name:
            flash('Could not recognize the crop from the image.', 'danger')
            return redirect(url_for('recommendation'))
    if not crop_name:
        flash('Please select a crop or upload an image.', 'danger')
        return redirect(url_for('recommendation'))
    crop = CropInfo.query.filter_by(name=crop_name).first()
    if not crop:
        flash('Crop not found in our database.', 'danger')
        return redirect(url_for('recommendation'))
    weather_data = get_weather_forecast(user.profile.location)
    recommendation_data = get_sowing_recommendation(crop, weather_data, user.profile.soil_type)
    return render_template('recommendation.html', recommendation=recommendation_data, crops=CropInfo.query.all())

@app.route('/forum')
def forum():
    posts = ForumPost.query.order_by(ForumPost.created_at.desc()).all()
    return render_template('forum.html', posts=posts)

@app.route('/forum/new', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        flash('Please log in to create a post.', 'warning')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        user_id = session['user_id']
        if not title or not content:
            flash('Title and content are required!', 'danger')
            return redirect(url_for('create_post'))
        new_post = ForumPost(title=title, content=content, user_id=user_id)
        db.session.add(new_post)
        db.session.commit()
        flash('Post created successfully!', 'success')
        return redirect(url_for('forum'))
    return render_template('create_post.html')

@app.route('/forum/<int:post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    post = ForumPost.query.get_or_404(post_id)
    if request.method == 'POST':
        if 'user_id' not in session:
            flash('Please log in to comment.', 'warning')
            return redirect(url_for('login'))
        content = request.form['content']
        if not content:
            flash('Comment content cannot be empty!', 'danger')
            return redirect(url_for('view_post', post_id=post.id))
        new_comment = ForumComment(content=content, user_id=session['user_id'], post_id=post.id)
        db.session.add(new_comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
        return redirect(url_for('view_post', post_id=post.id))
    return render_template('view_post.html', post=post)

@app.route('/blog')
def blog():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('blog.html', posts=posts)

@app.route('/blog/new', methods=['GET', 'POST'])
def create_blog_post():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author_id = session['user_id']
        if not title or not content:
            flash('Title and content are required!', 'danger')
            return redirect(url_for('create_blog_post'))
        new_post = BlogPost(title=title, content=content, author_id=author_id)
        db.session.add(new_post)
        db.session.commit()
        flash('Blog post created successfully!', 'success')
        return redirect(url_for('blog'))
    return render_template('create_blog_post.html')



@app.route('/blog/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_blog_post(post_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))
    
    post = BlogPost.query.get_or_404(post_id)
    
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        db.session.commit()
        flash('Blog post updated successfully!', 'success')
        return redirect(url_for('view_blog_post', post_id=post.id))
        
    return render_template('manage_blog_post.html', post=post)

@app.route('/blog/<int:post_id>/delete', methods=['POST'])
def delete_blog_post(post_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))
    
    post = BlogPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Blog post deleted successfully!', 'success')
    return redirect(url_for('blog'))

@app.route('/market_info')
def market_info():
    market_data = MarketInfo.query.order_by(MarketInfo.date.desc()).all()
    return render_template('market_info.html', market_data=market_data)

@app.route('/admin/add_market_info', methods=['GET', 'POST'])
def admin_add_market_info():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        mandi_name = request.form['mandi_name']
        commodity_name = request.form['commodity_name']
        price = float(request.form['price'])
        date_str = request.form['date']
        try:
            market_date = date.fromisoformat(date_str)
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('admin_add_market_info'))
        new_market_entry = MarketInfo(mandi_name=mandi_name, commodity_name=commodity_name, price=price, date=market_date)
        db.session.add(new_market_entry)
        db.session.commit()
        flash('Market info added successfully!', 'success')
        return redirect(url_for('market_info'))
    return render_template('admin_add_market_info.html')

@app.route('/disease_prediction', methods=['GET', 'POST'])
def disease_prediction():
    crops_db = CropInfo.query.all()
    if request.method == 'POST':
        crop_name = request.form.get('crop_name')
        crop_image = request.files.get('crop_image')
        prediction_result = "Placeholder disease prediction."
        if crop_name:
            prediction_result = f"For {crop_name}, common diseases include rust, blight, and powdery mildew. Please consult a local agricultural expert for accurate diagnosis and treatment. (Placeholder)"
        else:
            prediction_result = "Please select a crop to get a disease prediction placeholder."
        return render_template('disease_prediction.html', prediction_result=prediction_result, crops=crops_db)
    return render_template('disease_prediction.html', crops=crops_db)

@app.route('/yield_prediction', methods=['GET', 'POST'])
def yield_prediction():
    crops_db = CropInfo.query.all()
    if request.method == 'POST':
        crop_name = request.form.get('crop_name')
        prediction_result = "Placeholder yield prediction."
        return render_template('yield_prediction.html', prediction_result=prediction_result, crops=crops_db)
    return render_template('yield_prediction.html', crops=crops_db)

def get_weather_forecast(location):
    if not location:
        return None
    api_key = os.environ.get("WEATHER_API_KEY")
    if not api_key:
        print("WARNING: WEATHER_API_KEY environment variable not set. Weather forecast will not be available.")
        return None
    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location}&days=7"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

def get_sowing_recommendation(crop, weather_data, soil_type):
    recommendation_text = ""
    if not weather_data:
        recommendation_text += "Weather data not available. Cannot provide detailed sowing recommendation.\n"
        return {"crop": crop, "recommendation_text": recommendation_text}

    # Extract relevant weather data for next 3 days
    avg_temp = 0
    total_precip = 0
    forecast_days = weather_data.get('forecast', {}).get('forecastday', [])
    if forecast_days:
        for i in range(min(3, len(forecast_days))):
            day_data = forecast_days[i].get('day', {})
            avg_temp += day_data.get('avgtemp_c', 0)
            total_precip += day_data.get('totalprecip_mm', 0)
        avg_temp /= min(3, len(forecast_days))

    recommendation_text += f"Current average temperature (next 3 days): {avg_temp:.1f}°C\n"
    recommendation_text += f"Total precipitation (next 3 days): {total_precip:.1f} mm\n\n"

    # Temperature recommendation
    if crop.optimal_temp_min is not None and crop.optimal_temp_max is not None:
        if avg_temp >= crop.optimal_temp_min and avg_temp <= crop.optimal_temp_max:
            recommendation_text += f"Temperature is within optimal range ({crop.optimal_temp_min}-{crop.optimal_temp_max}°C) for {crop.name}.\n"
        elif avg_temp < crop.optimal_temp_min:
            recommendation_text += f"Temperature ({avg_temp:.1f}°C) is below optimal range ({crop.optimal_temp_min}-{crop.optimal_temp_max}°C) for {crop.name}. Consider waiting.\n"
        else:
            recommendation_text += f"Temperature ({avg_temp:.1f}°C) is above optimal range ({crop.optimal_temp_min}-{crop.optimal_temp_max}°C) for {crop.name}.\n"

    # Rainfall recommendation
    if crop.optimal_rainfall_min is not None and crop.optimal_rainfall_max is not None:
        if total_precip >= crop.optimal_rainfall_min and total_precip <= crop.optimal_rainfall_max:
            recommendation_text += f"Rainfall is within optimal range ({crop.optimal_rainfall_min}-{crop.optimal_rainfall_max} mm) for {crop.name}.\n"
        elif total_precip < crop.optimal_rainfall_min:
            recommendation_text += f"Rainfall ({total_precip:.1f} mm) is below optimal range ({crop.optimal_rainfall_min}-{crop.optimal_rainfall_max} mm) for {crop.name}. Irrigation might be needed.\n"
        else:
            recommendation_text += f"Rainfall ({total_precip:.1f} mm) is above optimal range ({crop.optimal_rainfall_min}-{crop.optimal_rainfall_max} mm) for {crop.name}.\n"

    # Soil type recommendation
    if crop.soil_preference and soil_type:
        if soil_type.lower() in crop.soil_preference.lower():
            recommendation_text += f"Your soil type ({soil_type}) is suitable for {crop.name}.\n"
        else:
            recommendation_text += f"Your soil type ({soil_type}) may not be ideal for {crop.name}. Preferred soil: {crop.soil_preference}.\n"
    elif crop.soil_preference:
        recommendation_text += f"Soil preference for {crop.name}: {crop.soil_preference}. Please update your profile with soil type.\n"

    if crop.fertilizer_recommendation:
        recommendation_text += f"\nFertilizer Recommendation: {crop.fertilizer_recommendation}\n"
    if crop.pest_control_recommendation:
        recommendation_text += f"Pest Control Recommendation: {crop.pest_control_recommendation}\n"

    return {"crop": crop, "recommendation_text": recommendation_text}

def estimate_profit_loss(crop, sowing_time, weather_data):
    # This is a very simplified estimation. A real model would require:
    # 1. Cost of cultivation data (per crop, per region)
    # 2. More sophisticated yield prediction based on weather, soil, practices
    # 3. Market demand and supply dynamics

    # Placeholder for estimated yield (e.g., in kg per unit area)
    # In a real scenario, this would come from a yield prediction model or historical averages
    estimated_yield_per_unit = 1000 # Example: 1000 kg per unit (e.g., acre/hectare)

    # Get predicted market price for the crop
    price_prediction_result = get_price_prediction(crop.name)
    if price_prediction_result.get("error"):
        # If price prediction fails, return a default or error indication
        return 0, 0 # Profit, Loss

    predicted_price_per_kg = price_prediction_result.get("predicted_price", 0) / 100 # Assuming price is per quintal/100kg

    # Very basic assumed cost of cultivation (e.g., per unit area)
    # This should ideally be dynamic and based on crop, region, and practices
    assumed_cost_of_cultivation = 50000 # Example: 50,000 units of currency per unit area

    estimated_revenue = estimated_yield_per_unit * predicted_price_per_kg

    profit = 0
    loss = 0

    if estimated_revenue > assumed_cost_of_cultivation:
        profit = estimated_revenue - assumed_cost_of_cultivation
    else:
        loss = assumed_cost_of_cultivation - estimated_revenue

    return round(profit, 2), round(loss, 2)

# --- Admin Routes ---
@app.route('/admin')
def admin_redirect():
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('You do not have admin access.', 'danger')
        return redirect(url_for('login'))
    
    user_count = User.query.count()
    post_count = ForumPost.query.count()
    blog_post_count = BlogPost.query.count()
    crop_count = CropInfo.query.count()
    
    stats = {
        'user_count': user_count,
        'post_count': post_count,
        'blog_post_count': blog_post_count,
        'crop_count': crop_count
    }
    
    return render_template('admin_dashboard.html', stats=stats)

@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('You do not have admin access.', 'danger')
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['GET', 'POST'])
def admin_add_user():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin_status = request.form.get('is_admin_status') == 'on'
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8, iterations=60000)
            new_user = User(username=username, password_hash=hashed_password, is_admin=is_admin_status)
            db.session.add(new_user)
            db.session.commit()
            flash(f'User "{username}" added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin_add_user.html')

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete.id == session['user_id']:
        flash('You cannot delete your own admin account.', 'danger')
        return redirect(url_for('admin_dashboard'))
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f'User {user_to_delete.username} deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users/toggle_admin/<int:user_id>', methods=['POST'])
def admin_toggle_admin(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    user_to_toggle = User.query.get_or_404(user_id)
    if user_to_toggle.id == session['user_id']:
        flash('You cannot revoke your own admin status.', 'danger')
        return redirect(url_for('admin_dashboard'))
    user_to_toggle.is_admin = not user_to_toggle.is_admin
    db.session.commit()
    flash(f'Admin status for {user_to_toggle.username} toggled successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/crop_info')
def admin_crop_info():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    crops_db = CropInfo.query.all()
    return render_template('admin_crop_info.html', crops=crops_db)

@app.route('/admin/add_crop_info', methods=['GET', 'POST'])
def admin_add_crop_info():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        type_c = request.form.get('type_c')
        optimal_temp_min = request.form.get('optimal_temp_min')
        optimal_temp_max = request.form.get('optimal_temp_max')
        optimal_rainfall_min = request.form.get('optimal_rainfall_min')
        optimal_rainfall_max = request.form.get('optimal_rainfall_max')
        soil_preference = request.form.get('soil_preference')
        fertilizer_recommendation = request.form.get('fertilizer_recommendation')
        pest_control_recommendation = request.form.get('pest_control_recommendation')

        image_file = request.files.get('image_file')

        image_url = None
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            upload_folder = os.path.join(app.root_path, 'static', 'images')
            os.makedirs(upload_folder, exist_ok=True)
            image_path = os.path.join(upload_folder, filename)
            image_file.save(image_path)
            image_url = f'/static/images/{filename}'

        # Convert to float if not empty
        try:
            optimal_temp_min = float(optimal_temp_min) if optimal_temp_min else None
            optimal_temp_max = float(optimal_temp_max) if optimal_temp_max else None
            optimal_rainfall_min = float(optimal_rainfall_min) if optimal_rainfall_min else None
            optimal_rainfall_max = float(optimal_rainfall_max) if optimal_rainfall_max else None
        except ValueError:
            flash('Invalid number format for temperature or rainfall.', 'danger')
            return redirect(url_for('admin_add_crop_info'))

        new_crop = CropInfo(
            name=name,
            type_c=type_c,
            optimal_temp_min=optimal_temp_min,
            optimal_temp_max=optimal_temp_max,
            optimal_rainfall_min=optimal_rainfall_min,
            optimal_rainfall_max=optimal_rainfall_max,
            soil_preference=soil_preference,
            fertilizer_recommendation=fertilizer_recommendation,
            pest_control_recommendation=pest_control_recommendation,
            image_url=image_url
        )
        db.session.add(new_crop)
        db.session.commit()
        flash('Crop information added successfully!', 'success')
        return redirect(url_for('admin_crop_info'))
    return render_template('admin_add_crop_info.html')

@app.route('/admin/edit_crop_info/<int:crop_id>', methods=['GET', 'POST'])
def admin_edit_crop_info(crop_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))

    crop = CropInfo.query.get_or_404(crop_id)

    if request.method == 'POST':
        crop.name = request.form.get('name')
        crop.optimal_temp_min = float(request.form.get('optimal_temp_min')) if request.form.get('optimal_temp_min') else None
        crop.optimal_temp_max = float(request.form.get('optimal_temp_max')) if request.form.get('optimal_temp_max') else None
        crop.optimal_rainfall_min = float(request.form.get('optimal_rainfall_min')) if request.form.get('optimal_rainfall_min') else None
        crop.optimal_rainfall_max = float(request.form.get('optimal_rainfall_max')) if request.form.get('optimal_rainfall_max') else None
        crop.soil_preference = request.form.get('soil_preference')
        crop.fertilizer_recommendation = request.form.get('fertilizer_recommendation')
        crop.pest_control_recommendation = request.form.get('pest_control_recommendation')

        try:
            db.session.commit()
            flash('Crop information updated successfully!', 'success')
            return redirect(url_for('admin_crop_info'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating crop information: {e}', 'danger')
            return redirect(url_for('admin_edit_crop_info', crop_id=crop.id))

    return render_template('admin_edit_crop_info.html', crop=crop)

@app.route('/admin/delete_crop_info/<int:crop_id>', methods=['POST'])
def admin_delete_crop_info(crop_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))

    crop_to_delete = CropInfo.query.get_or_404(crop_id)
    db.session.delete(crop_to_delete)
    db.session.commit()
    flash('Crop information deleted successfully!', 'success')
    return redirect(url_for('admin_crop_info'))

@app.route('/all_commodities_prediction', methods=['GET', 'POST'])
def all_commodities_prediction():
    if 'user_id' not in session:
        flash('Please login to access this page.', 'info')
        return redirect(url_for('login'))

    user_profile = UserProfile.query.filter_by(user_id=session['user_id']).first()
    user_location = user_profile.location if user_profile and user_profile.location else None
    user_soil_type = user_profile.soil_type if user_profile and user_profile.soil_type else None

    prediction_recommendation = None
    selected_commodity = None

    if request.method == 'POST':
        commodity_id = request.form.get('commodity_id')
        selected_commodity = CropInfo.query.get_or_404(commodity_id)

        if not user_location:
            flash('Please update your profile with your location to get a sowing recommendation.', 'warning')
        elif not user_soil_type:
            flash('Please update your profile with your soil type to get a sowing recommendation.', 'warning')
        else:
            weather_data = get_weather_forecast(user_location)
            if weather_data:
                prediction_recommendation = get_sowing_recommendation(selected_commodity, weather_data, user_soil_type)
            else:
                flash('Could not fetch weather data for your location. Sowing recommendation might be limited.', 'warning')

    commodities = CropInfo.query.all()
    return render_template('all_commodities_prediction.html',
                           commodities=commodities,
                           selected_commodity=selected_commodity,
                           prediction_recommendation=prediction_recommendation)

@app.route('/admin/analytics')
def admin_analytics():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))

    # Page Views
    page_views = db.session.query(PageView.page_url, func.count(PageView.id)).group_by(PageView.page_url).order_by(func.count(PageView.id).desc()).all()

    # Unique Visitors
    unique_visitors = db.session.query(func.count(db.distinct(PageView.ip_address))).scalar()

    # Referrers
    referrers = db.session.query(PageView.referrer, func.count(PageView.id)).filter(PageView.referrer != None).group_by(PageView.referrer).order_by(func.count(PageView.id).desc()).all()

    return render_template('admin_analytics.html', page_views=page_views, unique_visitors=unique_visitors, referrers=referrers)

@app.route('/api/analytics/page_views_by_day')
def api_page_views_by_day():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({"error": "Admin access required"}), 403

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    page_views = db.session.query(
        func.date(PageView.timestamp),
        func.count(PageView.id)
    ).filter(PageView.timestamp >= seven_days_ago).group_by(func.date(PageView.timestamp)).order_by(func.date(PageView.timestamp)).all()

    labels = [view[0].strftime('%Y-%m-%d') for view in page_views]
    data = [view[1] for view in page_views]

    return jsonify({"labels": labels, "data": data})

@app.route('/api/analytics/top_pages')
def api_top_pages():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({"error": "Admin access required"}), 403

    top_pages = db.session.query(
        PageView.page_url,
        func.count(PageView.id)
    ).group_by(PageView.page_url).order_by(func.count(PageView.id).desc()).limit(5).all()

    labels = [page[0] for page in top_pages]
    data = [page[1] for page in top_pages]

    return jsonify({"labels": labels, "data": data})

# --- Main Execution ---
if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
