from flask_sqlalchemy import SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@host/dbname'
db = SQLAlchemy(app)

class PatientData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    age = db.Column(db.Integer)
    # other columns...

# Query example
patients = PatientData.query.all()
