import pandas as pd
import numpy as np
import os
import uuid
from flask import Flask, request, render_template_string, redirect, url_for, flash
from werkzeug.utils import secure_filename
import joblib

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'supersecretkey123'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load Models (Fallback to simulated behavior if not found)
def load_models():
    try:
        return {
            'diabetes': {
                'rf': joblib.load('models/diabetes_rf.pkl'),
                'gb': joblib.load('models/diabetes_gb.pkl'),
                'features': ['Glucose', 'BMI', 'Age', 'Family_Diabetes', 'Physical_Activity']
            },
            'hypertension': {
                'nn': joblib.load('models/hypertension_nn.pkl'),
                'svm': joblib.load('models/hypertension_svm.pkl'),
                'features': ['Blood_Pressure', 'Salt_Intake', 'BMI', 'Family_Hypertension', 'Stress_Level']
            },
            'asthma': {
                'xgb': joblib.load('models/asthma_xgb.pkl'),
                'lr': joblib.load('models/asthma_lr.pkl'),
                'features': ['Respiratory_Rate', 'Allergies', 'Pollution_Exposure', 'Family_Asthma', 'Smoking_Status']
            },
            'heart_attack': {
                'dt': joblib.load('models/heart_attack_dt.pkl'),
                'knn': joblib.load('models/heart_attack_knn.pkl'),
                'features': ['Cholesterol', 'Age', 'Family_Heart', 'Smoking', 'Blood_Pressure']
            }
        }
    except Exception as e:
        print(f"[INFO] Could not load ML models: {e}. Using simulated predictions.")

        # Return dummy functions
        class DummyModel:
            def predict_proba(self, X):
                return [[1 - x[-1]/100, x[-1]/100] for x in X]

        return {
            'diabetes': {
                'rf': DummyModel(),
                'gb': DummyModel(),
                'features': ['Glucose', 'BMI', 'Age', 'Family_Diabetes', 'Physical_Activity']
            },
            'hypertension': {
                'nn': DummyModel(),
                'svm': DummyModel(),
                'features': ['Blood_Pressure', 'Salt_Intake', 'BMI', 'Family_Hypertension', 'Stress_Level']
            },
            'asthma': {
                'xgb': DummyModel(),
                'lr': DummyModel(),
                'features': ['Respiratory_Rate', 'Allergies', 'Pollution_Exposure', 'Family_Asthma', 'Smoking_Status']
            },
            'heart_attack': {
                'dt': DummyModel(),
                'knn': DummyModel(),
                'features': ['Cholesterol', 'Age', 'Family_Heart', 'Smoking', 'Blood_Pressure']
            }
        }

ml_models = load_models()

@app.route('/')
def index():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Multi-Disease Prediction</title>
    </head>
    <body>
        <h1>Upload Health Data</h1>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <ul style="color:red;">
            {% for message in messages %}
              <li>{{ message }}</li>
            {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}
        <form method="POST" action="/upload" enctype="multipart/form-data">
            <input type="file" name="file" accept=".xls,.xlsx">
            <button type="submit">Upload</button>
        </form>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext not in ['xls', 'xlsx']:
        flash('Invalid file type. Please upload an Excel file (.xls or .xlsx)')
        return redirect(url_for('index'))

    temp_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, temp_filename)
    file.save(file_path)

    try:
        df = pd.read_excel(file_path)
        if len(df) > 500:
            os.remove(file_path)
            flash('File contains more than 500 individuals.')
            return redirect(url_for('index'))

        results = []
        for idx, row in df.iterrows():

            # Helper to extract features safely
            def get_features(model_name):
                return [row[col] for col in ml_models[model_name]['features']]

            # Diabetes
            features = get_features('diabetes')
            prob_diabetes = (
                ml_models['diabetes']['rf'].predict_proba([features])[0][1] +
                ml_models['diabetes']['gb'].predict_proba([features])[0][1]
            ) / 2 * 100

            # Hypertension
            features = get_features('hypertension')
            prob_hypertension = (
                ml_models['hypertension']['nn'].predict_proba([features])[0][1] +
                ml_models['hypertension']['svm'].predict_proba([features])[0][1]
            ) / 2 * 100

            # Asthma
            features = get_features('asthma')
            prob_asthma = (
                ml_models['asthma']['xgb'].predict_proba([features])[0][1] +
                ml_models['asthma']['lr'].predict_proba([features])[0][1]
            ) / 2 * 100

            # Heart Attack
            features = get_features('heart_attack')
            prob_heart_attack = (
                ml_models['heart_attack']['dt'].predict_proba([features])[0][1] +
                ml_models['heart_attack']['knn'].predict_proba([features])[0][1]
            ) / 2 * 100

            results.append({
                'id': idx + 1,
                'diabetes': round(prob_diabetes, 2),
                'hypertension': round(prob_hypertension, 2),
                'asthma': round(prob_asthma, 2),
                'heart_attack': round(prob_heart_attack, 2)
            })

        os.remove(file_path)

        results_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Prediction Results</title>
            <style>
                table, th, td {
                    border: 1px solid black;
                    padding: 8px;
                    text-align: center;
                    border-collapse: collapse;
                }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <h1>Disease Prediction Results</h1>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Diabetes (%)</th>
                    <th>Hypertension (%)</th>
                    <th>Asthma (%)</th>
                    <th>Heart Attack (%)</th>
                </tr>
                {% for r in results %}
                <tr>
                    <td>{{ r.id }}</td>
                    <td>{{ r.diabetes }}</td>
                    <td>{{ r.hypertension }}</td>
                    <td>{{ r.asthma }}</td>
                    <td>{{ r.heart_attack }}</td>
                </tr>
                {% endfor %}
            </table>
            <br><a href="/">Upload Another File</a>
        </body>
        </html>
        '''
        return render_template_string(results_html, results=results)

    except KeyError as ke:
        flash(f'Missing expected column in data: {ke}')
    except Exception as e:
        flash(f'Error processing file: {str(e)}')
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
