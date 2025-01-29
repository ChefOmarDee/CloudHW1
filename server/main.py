from flask import Flask, request, render_template, jsonify, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from io import BytesIO
from PIL import Image
from google.cloud import storage, datastore
import uuid
import os 

app = Flask(__name__)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./env.json"

app.secret_key = '89c25124aeaafe4fdcf01a2724187847'  # Change this to a secure secret key

# Initialize Google Cloud clients
storage_client = storage.Client()
datastore_client = datastore.Client()
print(datastore_client.project)  # Should match your GCP project ID


bucket_name = "chefbuckets"

# Authentication middleware
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if email already exists
        query = datastore_client.query(kind='users')
        query.add_filter('email', '=', email)
        existing_user = list(query.fetch(limit=1))
        
        if existing_user:
            flash('Email already exists')
            return redirect(url_for('signup'))
        
        # Create new user
        entity = datastore.Entity(key=datastore_client.key('users'))
        entity.update({
            'email': email,
            'password': password  # In production, hash this password!
        })
        datastore_client.put(entity)
        
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check user credentials
        query = datastore_client.query(kind='users')
        query.add_filter('email', '=', email)
        query.add_filter('password', '=', password)  # In production, compare hashed passwords!
        user = list(query.fetch(limit=1))
        
        if user:
            session['user_email'] = email
            return redirect(url_for('gallery'))
        else:
            flash('Invalid credentials')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def gallery():
    # Fetch images for the current user
    query = datastore_client.query(kind='images')
    query.add_filter('useremail', '=', session['user_email'])
    images = list(query.fetch())
    return render_template('gallery.html', images=images)

@app.route('/upload', methods=['GET'])
@login_required
def upload_page():
    return render_template('upload_image.html')

@app.route('/upload-image', methods=['POST'])
@login_required
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image part in the request"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
        
        # Upload to Cloud Storage
        image_data = file.read()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(unique_filename)
        blob.upload_from_file(
            BytesIO(image_data),
            content_type=file.content_type
        )
        
        # Store image metadata in Datastore
        entity = datastore.Entity(key=datastore_client.key('images'))
        entity.update({
            'useremail': session['user_email'],
            'imagelink': f"https://storage.googleapis.com/{bucket_name}/{unique_filename}"
        })
        datastore_client.put(entity)
        
        return redirect(url_for('gallery'))
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="localhost", port=8080, debug=True)