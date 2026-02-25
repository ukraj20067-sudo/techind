import os
import urllib.parse
import time
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from supabase import create_client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'TECHIND_ULTIMATE_2026'

# --- DATABASE CONFIGURATION ---
raw_password = 'utkarsh@))^'
encoded_password = urllib.parse.quote_plus(raw_password)

# Database connection - Fixed for Render/Supabase stability
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://postgres.ovqlghzmdkelxxkehcba:{encoded_password}@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 300}

db = SQLAlchemy(app)

# SUPABASE IMAGE STORAGE CONFIG
SUPABASE_URL = "https://ovqlghzmdkelxxkehcba.supabase.co"
SUPABASE_KEY = "sb_publishable_C4pYZQ43SoMUNiwHK6WGAw_gPXyZnLV"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- LOGIN SYSTEM ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id): self.id = id

@login_manager.user_loader
def load_user(user_id): return User(user_id)

# --- DATABASE MODELS ---
class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    images = db.Column(db.Text, default='https://via.placeholder.com/300') 
    title = db.Column(db.String(150), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    affiliate_link = db.Column(db.String(500))

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    primary_color = db.Column(db.String(20), default='#1D6B6B') 
    hero_bg_color = db.Column(db.String(20), default='#1D6B6B') 
    font_style = db.Column(db.String(50), default='Poppins')
    insta_link = db.Column(db.String(200), default='#')
    twitter_link = db.Column(db.String(200), default='#')
    youtube_link = db.Column(db.String(200), default='#')

# --- STARTUP DATABASE LOGIC ---
with app.app_context():
    try:
        db.create_all()
        if not Settings.query.first():
            db.session.add(Settings(primary_color='#1D6B6B', hero_bg_color='#1D6B6B', font_style='Poppins'))
            db.session.commit()
    except Exception as e:
        print(f"Startup DB Error: {e}")

# --- ROUTES ---

@app.route('/')
def home():
    try:
        settings = Settings.query.first()
        blogs = Blog.query.order_by(Blog.id.desc()).all()
        return render_template('index.html', blogs=blogs, settings=settings)
    except Exception as e:
        return "<h1>TECHIND is waking up...</h1><p>Please refresh in 10 seconds.</p>"

@app.route('/post/<int:id>')
def post(id):
    settings = Settings.query.first()
    blog = Blog.query.get_or_404(id)
    image_list = blog.images.split(',')
    return render_template('post.html', blog=blog, image_list=image_list, settings=settings)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'techind123':
            login_user(User(1))
            return redirect(url_for('admin'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    settings = Settings.query.first()
    if request.method == 'POST':
        try:
            files = request.files.getlist('thumbnails')
            urls = []
            
            for file in files:
                if file and file.filename != '':
                    # Create unique name to avoid Supabase collisions
                    filename = secure_filename(file.filename)
                    unique_name = f"{int(time.time())}_{os.urandom(2).hex()}_{filename}"
                    file_data = file.read()
                    
                    # 1. Upload to Supabase (Bucket must be 'product-images')
                    supabase.storage.from_("product-images").upload(
                        path=unique_name, 
                        file=file_data, 
                        file_options={"content-type": file.content_type}
                    )
                    
                    # 2. Get Public URL
                    res = supabase.storage.from_("product-images").get_public_url(unique_name)
                    
                    # Version-agnostic URL extraction
                    if hasattr(res, 'public_url'):
                        public_url = res.public_url
                    else:
                        public_url = str(res)
                        
                    urls.append(public_url)
            
            image_string = ",".join(urls) if urls else 'https://via.placeholder.com/300'
            
            # 3. Save to Postgres
            new_post = Blog(
                images=image_string, 
                title=request.form['title'],
                product_name=request.form['product_name'], 
                category=request.form['category'],
                content=request.form['content'], 
                affiliate_link=request.form['affiliate_link']
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for('home'))
            
        except Exception as e:
            db.session.rollback()
            # Returns exact error message to help you debug in real-time
            return f"<h1>Upload Error</h1><p>{str(e)}</p><a href='/admin'>Go Back</a>"

    return render_template('admin.html', settings=settings)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    blog = Blog.query.get_or_404(id)
    settings = Settings.query.first()
    if request.method == 'POST':
        blog.title = request.form['title']
        blog.product_name = request.form['product_name']
        blog.category = request.form['category']
        blog.content = request.form['content']
        blog.affiliate_link = request.form['affiliate_link']
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('edit.html', blog=blog, settings=settings)

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    blog = Blog.query.get_or_404(id)
    db.session.delete(blog)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/admin/settings', methods=['POST'])
@login_required
def update_theme():
    settings = Settings.query.first()
    if 'primary_color' in request.form:
        settings.primary_color = request.form.get('primary_color')
        settings.hero_bg_color = request.form.get('hero_bg_color')
    if 'insta_link' in request.form:
        settings.insta_link = request.form.get('insta_link')
        settings.twitter_link = request.form.get('twitter_link')
        settings.youtube_link = request.form.get('youtube_link')
    db.session.commit()
    return redirect(url_for('admin', tab='settings'))

if __name__ == "__main__":
    app.run(debug=True)