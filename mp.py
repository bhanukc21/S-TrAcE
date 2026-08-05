from flask import Flask, render_template, request
from flask import send_from_directory
from flask import Flask, render_template, request, session, redirect, url_for
import numpy as np
import pickle
from datetime import datetime
import plotly.express as px
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder
from sklearn.decomposition import PCA
import csv
import os
import pandas as pd

app = Flask(__name__)
# Prefer SECRET_KEY from environment for stable sessions in hosting; fallback to random for dev
secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)
app.secret_key = secret_key

# Load saved or trained models
with open('kmeans_model.pkl', 'rb') as f:
    kmeans = pickle.load(f)

with open('pca_model.pkl', 'rb') as f:
    pca = pickle.load(f)

# Define manual cluster labels
manual_cluster_labels = {
    0: 'Education',
    1: 'Business',
    2: 'cinema',
    3: 'sports',
    4: 'crime'
}
def read_csv_data():
    data = {}
    with open('TrendingPosts.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            category = row['Predicted_Cluster_Label']
            if category not in data:
                data[category] = []
            data[category].append({'title': row['Text']})
    return data

# Function to append user input and predicted cluster to CSV file
def append_to_csv(user_input, predicted_cluster):
    try:
        # Get the current date
        current_date = datetime.now().strftime("%d-%m-%Y")
        

        # Get the absolute path to the CSV file 
        with open('TrendingPosts.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            # Write user input, predicted cluster, social media name, and date of adding the post to CSV
            writer.writerow(['Instagram', current_date, user_input,predicted_cluster])
        return True  # Return True if writing to CSV was successful
    except Exception as e:
        print("Error:", e)
        return False
        
 
# Home route
@app.route('/')
def home():
    username = session.get('username')
    if username:
        return render_template('home.html', username=username)
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

def write_to_csv(data):
    with open('users.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(data)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            with open('users.csv', mode='r') as file:
                reader = csv.reader(file)
                for row in reader:
                    # CSV layout: username, email, phone, password
                    if len(row) >= 4 and row[0] == username and row[3] == password:
                        session['username'] = username
                        return redirect(url_for('profile'))
        except FileNotFoundError:
            # No users file yet
            pass
        error = 'Invalid username or password.'
        return render_template('login.html', error=error)
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/profile')
def profile():
    if 'username' in session:
        return redirect(url_for('home'))



@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None  # Initialize error message variable
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        terms = request.form.get('terms')
        
        if password != confirm_password:
            return 'Passwords do not match'
        
        # Check if username or email already exists in CSV file
        with open('users.csv', mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == username or row[1] == email:
                    error = 'User already exists'
                    break  # Exit loop once user is found
            
            if error is None:  # If no error, write registration data to CSV file
                write_to_csv([username, email, phone, password])
                # Redirect to login page after successful registration
                return redirect(url_for('login'))
    
    return render_template('registration.html', error=error)  # Pass error to template


@app.route('/index')
def index():
    if 'username' in session:
        return render_template('index.html')
    else:
        return render_template('login.html')
        

@app.route("/category/<category>")
def category(category):
    return render_template("sports.html", category=category)

@app.route("/posts/<category>")
def posts(category):
    data = read_csv_data()
    posts = data.get(category, [])[:5]  # Get top 5 posts for the selected category
    return render_template("top_posts.html", category=category, posts=posts)

@app.route('/TrendingPosts.csv')
def get_cluster_results():
    # Serve the CSV file from the project root
    try:
        return send_from_directory('.', 'TrendingPosts.csv', as_attachment=True)
    except Exception:
        # Fallback to send_file if send_from_directory fails
        from flask import send_file
        return send_file('TrendingPosts.csv', as_attachment=True)





# visualization charts are generated inside the route to avoid heavy import-time work




@app.context_processor
def inject_now():
    return {'now': datetime.now()}


@app.route('/visualizations')
def display_visualizations():
    try:
        data = pd.read_csv("TrendingPosts.csv", encoding='latin-1')

        social_media_counts = data['SOCIAL MEDIA'].value_counts().reset_index()
        social_media_counts.columns = ['Social Media Platform', 'Number of Posts']

        fig_pie = px.pie(social_media_counts, values='Number of Posts', names='Social Media Platform',
                         title='Distribution of Posts by Social Media Platform')

        date_cluster_counts = data.groupby(['DATE', 'Predicted_Cluster_Label']).size().reset_index(name='Number of Posts')

        fig_stacked_bar = px.bar(date_cluster_counts, x='DATE', y='Number of Posts', color='Predicted_Cluster_Label',
                                 title='Distribution of Predicted Clusters Over Time',
                                 labels={'DATE': 'Date', 'Number of Posts': 'Number of Posts', 'Predicted_Cluster_Label': 'Predicted Cluster Label'},
                                 barmode='stack')

        fig_line_graph = px.line(date_cluster_counts, x='DATE', y='Number of Posts', color='Predicted_Cluster_Label',
                                 title='Distribution of Predicted Clusters Over Time',
                                 labels={'DATE': 'Date', 'Number of Posts': 'Number of Posts', 'Predicted_Cluster_Label': 'Predicted Cluster Label'})

        cluster_social_media_counts = data.groupby(['Predicted_Cluster_Label', 'SOCIAL MEDIA']).size().reset_index(name='count')

        fig_grouped_bar = px.bar(cluster_social_media_counts, x='Predicted_Cluster_Label', y='count', color='SOCIAL MEDIA',
                                 barmode='group',
                                 title='Distribution of Posts by Predicted Cluster and Social Media Platform',
                                 labels={'Predicted_Cluster_Label': 'Predicted Cluster Label', 'count': 'Number of Posts', 'SOCIAL MEDIA': 'Social Media Platform'})

        return render_template('visualizations.html',
                               pie_chart=fig_pie.to_html(full_html=False),
                               stacked_bar_chart=fig_stacked_bar.to_html(full_html=False),
                               line_graph=fig_line_graph.to_html(full_html=False),
                               grouped_bar_chart=fig_grouped_bar.to_html(full_html=False))
    except Exception as e:
        print('Could not build visualizations:', e)
        return render_template('visualizations.html', pie_chart='', stacked_bar_chart='', line_graph='', grouped_bar_chart='')

DBSCAN_MODEL = None
try:
    with open('DBSCAN.pkl', 'rb') as f:
        DBSCAN_MODEL = pickle.load(f)
except Exception as e:
    print('Warning: DBSCAN model not loaded:', e)
    DBSCAN_MODEL = None


# Prediction route
@app.route('/predict', methods=['POST'])
def predict():
    user_input = request.form['user_input']
    # List of cluster labels
    cluster_labels = ['cinema', 'crime', 'sports', 'business/economy', 'education/tech']
    # Get the label — be defensive about the model API and missing model
    predicted_label = 'unknown'
    if DBSCAN_MODEL is None:
        # Simple keyword fallback for demo
        for lbl in manual_cluster_labels.values():
            if lbl.lower() in user_input.lower():
                predicted_label = lbl
                break
    else:
        try:
            if hasattr(DBSCAN_MODEL, 'predict'):
                pred = DBSCAN_MODEL.predict([user_input])
                # pred might be array-like or labels
                predicted_label = pred[0] if len(pred) > 0 else str(pred)
            elif callable(DBSCAN_MODEL):
                # Some pickled functions expect (texts, labels) and return dict
                res = DBSCAN_MODEL(user_input, cluster_labels)
                if isinstance(res, dict) and 'labels' in res:
                    predicted_label = res['labels'][0]
                else:
                    predicted_label = str(res)
            else:
                predicted_label = str(DBSCAN_MODEL)
        except Exception as e:
            print('Error during prediction with DBSCAN model:', e)
            # fallback to keyword
            for lbl in manual_cluster_labels.values():
                if lbl.lower() in user_input.lower():
                    predicted_label = lbl
                    break
    # Append user input and predicted cluster to CSV file
    append_to_csv(user_input, predicted_label )
    return render_template('predict.html', user_input=user_input, predicted_label=predicted_label)


if __name__ == '__main__':
    app.run(debug=True,port=5500)



# cluster_labels = ['cinema', 'crime', 'sports', 'business/economy', 'education/tech']
# # Perform prediction
# predicted_sentences = []

# # Iterate through sentences
# for sentence in new_sentences:
#     # Get the label
#     predicted_label = DBSCAN_MODEL(sentence, cluster_labels)["labels"][0]
#     predicted_sentences.append((sentence, predicted_label))
# # Create DataFrame
# df = pd.DataFrame(predicted_sentences, columns=['POST', 'Predicted Label'])
# # Display DataFrame
# print(df)