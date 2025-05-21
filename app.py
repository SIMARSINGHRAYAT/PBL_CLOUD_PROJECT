#!/usr/bin/env python3
import os
import uuid
import json
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory, flash
import pandas as pd
from openpyxl import load_workbook

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Folders for uploads and predictions
UPLOAD_FOLDER = 'uploads'
PREDICTIONS_FOLDER = 'predictions'
HISTORY_FILE = 'history.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PREDICTIONS_FOLDER, exist_ok=True)

# Mocked disease prediction model
def predict_disease(row):
    age = row.get('Age', 0)
    bmi = row.get('BMI', 0)
    cholesterol = row.get('Cholesterol', 0)
    blood_pressure = row.get('Blood Pressure', 0)

    diseases = []

    if age > 50 and cholesterol > 240:
        diseases.append('Heart Disease')
    if bmi > 30:
        diseases.append('Diabetes')
    if age < 30 and bmi < 18:
        diseases.append('Asthma')
    if blood_pressure > 140:
        diseases.append('Hypertension')

    return ', '.join(diseases) if diseases else 'None'

# Templates as strings
base_html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Medical Prediction System</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap @5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background-color: #f8f9fa; }
    .card {
      border-radius: 0.5rem;
      box-shadow: 0 0.25rem 0.75rem rgba(0,0,0,0.1);
    }
    .alert {
      margin-bottom: 1rem;
    }
    .btn-success {
      font-weight: bold;
    }
  </style>
</head>
<body>
  <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
    <div class="container-fluid">
      <a class="navbar-brand" href="/">Medical Prediction System</a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav"
        aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav ms-auto">
          <li class="nav-item"><a class="nav-link" href="/">Upload</a></li>
          <li class="nav-item"><a class="nav-link" href="/history">History</a></li>
        </ul>
      </div>
    </div>
  </nav>

  <div class="container mt-4">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap @5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

index_html = """
{% extends "base.html" %}
{% block content %}
<div class="card shadow-sm">
  <div class="card-header text-center bg-primary text-white">
    <h4>Upload Patient Data</h4>
  </div>
  <div class="card-body">
    <form method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <label for="file" class="form-label">Select an Excel File (.xlsx)</label>
        <input class="form-control" type="file" name="file" accept=".xlsx" required>
      </div>
      <button type="submit" class="btn btn-success w-100">Upload & Predict</button>
    </form>
  </div>
</div>
{% endblock %}
"""

results_html = """
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Prediction Results</h2>

<table class="table table-bordered table-hover">
  <thead class="table-light">
    <tr>
      {% for key in data[0].keys() %}
        <th>{{ key }}</th>
      {% endfor %}
    </tr>
  </thead>
  <tbody>
    {% for row in data %}
      <tr>
        {% for val in row.values() %}
          <td>{{ val }}</td>
        {% endfor %}
      </tr>
    {% endfor %}
  </tbody>
</table>

<nav aria-label="Page navigation">
  <ul class="pagination justify-content-center">
    {% if pagination.prev %}
      <li class="page-item"><a class="page-link" href="?page={{ pagination.prev }}">Previous</a></li>
    {% else %}
      <li class="page-item disabled"><span class="page-link">Previous</span></li>
    {% endif %}
    <li class="page-item active"><span class="page-link">{{ pagination.current }} of {{ pagination.total }}</span></li>
    {% if pagination.next %}
      <li class="page-item"><a class="page-link" href="?page={{ pagination.next }}">Next</a></li>
    {% else %}
      <li class="page-item disabled"><span class="page-link">Next</span></li>
    {% endif %}
  </ul>
</nav>

<h2 class="mt-5 mb-3">Disease Distribution</h2>
<canvas id="diseaseChart" width="400" height="200"></canvas>

<a href="{{ url_for('download', filename=result_id) }}" class="btn btn-success mt-3">Download Results</a>

<script src="https://cdn.jsdelivr.net/npm/chart.js "></script>
<script>
  const ctx = document.getElementById('diseaseChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: Object.keys({{ disease_counts|tojson }}),
      datasets: [{
        label: 'Number of Cases',
        data: Object.values({{ disease_counts|tojson }}),
        backgroundColor: [
          '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'
        ]
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  });
</script>
{% endblock %}
"""

history_html = """
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Prediction History</h2>
<table class="table table-striped table-hover">
  <thead>
    <tr>
      <th>ID</th>
      <th>Date</th>
      <th>Action</th>
      <th>Rows</th>
    </tr>
  </thead>
  <tbody>
    {% for entry in history %}
      <tr>
        <td>{{ entry.id[:8] }}</td>
        <td>{{ entry.timestamp }}</td>
        <td><a href="{{ url_for('results', result_id=entry.result_file) }}" class="btn btn-primary btn-sm">View</a></td>
        <td>{{ entry.rows }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if not file or not file.filename.endswith('.xlsx'):
            flash('Please upload a valid Excel (.xlsx) file.', 'danger')
            return redirect(url_for('index'))

        try:
            filename = str(uuid.uuid4()) + '.xlsx'
            file.save(os.path.join(UPLOAD_FOLDER, filename))

            df = pd.read_excel(os.path.join(UPLOAD_FOLDER, filename))
            df['Prediction'] = df.apply(predict_disease, axis=1)
            result_file = f'results_{filename}'
            df.to_excel(os.path.join(PREDICTIONS_FOLDER, result_file), index=False)

            history_entry = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'file': filename,
                'result_file': result_file,
                'rows': len(df),
            }

            with open(HISTORY_FILE, 'a') as f:
                f.write(json.dumps(history_entry) + '\n')

            flash('File processed successfully!', 'success')
            return redirect(url_for('results', result_id=result_file))

        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')
            return redirect(url_for('index'))

    return render_template_string(index_html)

@app.route('/results/<result_id>')
def results(result_id):
    file_path = os.path.join(PREDICTIONS_FOLDER, result_id)
    df = pd.read_excel(file_path)
    page = int(request.args.get('page', 1))
    per_page = 10
    start = (page - 1) * per_page
    end = start + per_page
    paginated_data = df.iloc[start:end].to_dict(orient='records')

    total_pages = (len(df) + per_page - 1) // per_page
    pagination = {
        'current': page,
        'total': total_pages,
        'prev': page - 1 if page > 1 else None,
        'next': page + 1 if page < total_pages else None,
    }

    disease_counts = {'Heart Disease': 0, 'Asthma': 0, 'Diabetes': 0, 'Hypertension': 0, 'None': 0}
    for pred in df['Prediction']:
        for disease in str(pred).split(', '):
            disease_counts[disease] += 1

    return render_template_string(
        results_html,
        data=paginated_data,
        pagination=pagination,
        disease_counts=disease_counts,
        result_id=result_id
    )

@app.route('/download/<filename>')
def download(filename):
    path = os.path.join(PREDICTIONS_FOLDER, filename)
    return send_from_directory(PREDICTIONS_FOLDER, filename, as_attachment=True)

@app.route('/history')
def history():
    try:
        with open(HISTORY_FILE, 'r') as f:
            lines = f.readlines()
        history_list = [json.loads(line) for line in lines]
        return render_template_string(history_html, history=history_list)
    except FileNotFoundError:
        return render_template_string(history_html, history=[])

if __name__ == '__main__':
    app.run(debug=True)