import os
import urllib.parse
import time
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from supabase import create_client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'TECHIND_INDIA_ULTIMATE_2026'

# --- DATABASE CONFIGURATION ---
raw_password = 'utkarsh@))^'
encoded_password = urllib.parse.quote_plus(raw_password)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://postgres.ovqlghzmdkelxxkehcba:{encoded_password}@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 300}

db = SQLAlchemy(app)

# --- SUPABASE CONFIG ---
SUPABASE_URL = "https://ovqlghzmdkelxxkehcba.supabase.co"
SUPABASE_KEY = "sb_publishable_C4pYZQ43SoMUNiwHK6WGAw_gPXyZnLV"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MODELS ---
class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    images = db.Column(db.Text) 
    title = db.Column(db.String(150), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    affiliate_link = db.Column(db.String(500)) # This is the Green "Best Buy" link
    
    # Comparison Table Slots
    store1_name = db.Column(db.String(50))
    store1_price = db.Column(db.String(20))
    store1_link = db.Column(db.String(500))
    store2_name = db.Column(db.String(50))
    store2_price = db.Column(db.String(20))
    store2_link = db.Column(db.String(500))
    store3_name = db.Column(db.String(50))
    store3_price = db.Column(db.String(20))
    store3_link = db.Column(db.String(500))

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    primary_color = db.Column(db.String(20), default='#1D6B6B') 
    hero_bg_color = db.Column(db.String(20), default='#1D6B6B')
    insta_link = db.Column(db.String(200), default='#')
    twitter_link = db.Column(db.String(200), default='#')
    youtube_link = db.Column(db.String(200), default='#')

# --- AUTH SYSTEM ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
class User(UserMixin):
    def __init__(self, id): self.id = id
@login_manager.user_loader
def load_user(uid): return User(uid)

# --- ROUTES ---
@app.route('/')
def home():
    settings = Settings.query.first()
    blogs = Blog.query.order_by(Blog.id.desc()).all()
    return render_template('index.html', blogs=blogs, settings=settings)

@app.route('/post/<int:id>')
def post(id):
    settings = Settings.query.first()
    blog = Blog.query.get_or_404(id)
    image_list = blog.images.split(',') if blog.images else []
    return render_template('post.html', blog=blog, image_list=image_list, settings=settings)

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
                    unique_name = f"{int(time.time())}_{os.urandom(2).hex()}_{secure_filename(file.filename)}"
                    supabase.storage.from_("product-images").upload(unique_name, file.read(), {"content-type": file.content_type})
                    res = supabase.storage.from_("product-images").get_public_url(unique_name)
                    urls.append(res.public_url if hasattr(res, 'public_url') else str(res))
            
            new_post = Blog(
                images=",".join(urls) if urls else 'https://via.placeholder.com/300',
                title=request.form['title'],
                product_name=request.form['product_name'],
                category=request.form['category'],
                content=request.form['content'], 
                affiliate_link=request.form.get('affiliate_link'),
                store1_name=request.form.get('store1_name'), store1_price=request.form.get('store1_price'), store1_link=request.form.get('store1_link'),
                store2_name=request.form.get('store2_name'), store2_price=request.form.get('store2_price'), store2_link=request.form.get('store2_link'),
                store3_name=request.form.get('store3_name'), store3_price=request.form.get('store3_price'), store3_link=request.form.get('store3_link')
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            return f"<h1>Upload Error</h1><p>{e}</p><a href='/admin'>Go Back</a>"
    return render_template('admin.html', settings=settings)

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
    settings.insta_link = request.form.get('insta_link')
    settings.twitter_link = request.form.get('twitter_link')
    settings.youtube_link = request.form.get('youtube_link')
    db.session.commit()
    return redirect(url_for('admin', tab='settings'))

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

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not Settings.query.first():
            db.session.add(Settings())
            db.session.commit()
    app.run(debug=True)