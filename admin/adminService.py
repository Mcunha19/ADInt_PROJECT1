from huggingface_hub import User
from sqlalchemy import create_engine
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base, joinedload
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

import datetime
from sqlalchemy.orm import sessionmaker
import os

#SLQ access layer initialization
DATABASE_FILE = "adminDB.sqlite"
db_exists = False
if os.path.exists(DATABASE_FILE):
    db_exists = True
    print("\t database already exists")

engine = create_engine('sqlite:///%s'%(DATABASE_FILE), echo=False) #echo = True shows all SQL calls

Base = declarative_base()

#Declaration of data
class Exam(Base):
    __tablename__ = 'exam'
    id = Column(Integer, primary_key=True)
    course = Column(String)
    date = Column(DateTime)
    def __repr__(self):
        return "<Exam(id='%d', course='%s', date='%s')>" % (
                                self.id, self.course, self.date)

def newExam(date, course):
    exam = Exam(course = course, date = date)
    session.add(exam)
    session.commit()

def getExams():
    return session.query(Exam).all()

def getExamsByCourse(course):
    return session.query(Exam).filter(Exam.course == course).all()

def getExamsByDate(date):
    return session.query(Exam).filter(Exam.date == date).all()

class EnrolledStudent(Base):
    __tablename__ = 'enrolled_student'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    exam_id = Column(Integer, ForeignKey('exam.id'))
    exam = relationship("Exam", backref="enrolled_students")
    def __repr__(self):
        return "<EnrolledStudent(id='%d', user_id='%d', exam_id='%d')>" % (
                                self.id, self.user_id, self.exam_id)

def newEnrolledStudent(user_id, exam_id):
    enrolled_student = EnrolledStudent(user_id = user_id, exam_id = exam_id)
    session.add(enrolled_student)
    session.commit()

def getEnrolledStudents():
    return session.query(EnrolledStudent).options(joinedload(EnrolledStudent.exam)).all()

def getEnrolledStudentsByUserId(user_id):
    return session.query(EnrolledStudent).filter(EnrolledStudent.user_id == user_id).all()

def getEnrolledStudentsByExamId(exam_id):
    return session.query(EnrolledStudent).filter(EnrolledStudent.exam_id == exam_id).all()

def countEnrolledStudentsByExamId(exam_id):
    return session.query(EnrolledStudent).filter(EnrolledStudent.exam_id == exam_id).count()


Base.metadata.create_all(engine) #Create tables for the data models

Session = sessionmaker(bind=engine)
session = Session()

from xmlrpc import client as xmlrpc_client
from flask import Flask, json, jsonify, render_template, request, send_from_directory
app = Flask(__name__)

printing_service = xmlrpc_client.ServerProxy("http://localhost:8002/RPC")
     
@app.route("/")
def index():
    return render_template("index.html", message="Dynamic content!")   

@app.route("/listExams", methods=['GET'])
def listExams():
    exams = getExams()
    return render_template("listExams.html", exams=exams)

@app.route("/addExam", methods=['GET', 'POST'])
def addExam():
    if request.method == 'POST':
        date = datetime.datetime.fromisoformat(request.form['date'])
        course = request.form['course']
        newExam(date, course)
    return render_template("addExam.html")

@app.route("/listEnrolledStudents", methods=['GET'])
def listEnrolledStudents():
    enrolled_students = getEnrolledStudents()
    return render_template("listEnrolledStudents.html", enrolled_students=enrolled_students)

@app.route("/addBulkEnrolledStudents", methods=['GET', 'POST'])
def addBulkEnrolledStudents():
    if request.method == 'POST':
        try:
            data = json.loads(request.form["listOfEnrolledStudents"])
            if not isinstance(data, list):
                raise ValueError
            for item in data:
                newEnrolledStudent(item["user_id"], item["exam_id"])
        except (ValueError, KeyError, TypeError):
            return "Invalid JSON: expected a list of enrolled students.", 400
    return render_template("addBulkEnrolledStudents.html")

@app.route("/orderPrintingSheets", methods=['GET', 'POST'])
def orderPrintingSheets():
    if request.method == 'POST':
        exam_id = request.form['examId']
        exam_question_count = 4
        enrolled_student_count = countEnrolledStudentsByExamId(exam_id)
        printSuccess = printing_service.print_resolution_sheets(exam_id, exam_question_count, enrolled_student_count)
        print(f"Printing resolution sheets for exam {exam_id} with {enrolled_student_count} students: {'Success' if printSuccess else 'Failure'}")
        return render_template("orderPrintingSheets.html", printSuccess=printSuccess, exam_id=exam_id)
    return render_template("orderPrintingSheets.html")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8001, debug=True)