from sqlalchemy import create_engine
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

import datetime
from sqlalchemy.orm import sessionmaker
import os

#SLQ access layer initialization
DATABASE_FILE = "database.sqlite"
db_exists = False
if os.path.exists(DATABASE_FILE):
    db_exists = True
    print("\t database already exists")

engine = create_engine('sqlite:///%s'%(DATABASE_FILE), echo=False) #echo = True shows all SQL calls

Base = declarative_base()

#Declaration of data
class ProfessorAssignment(Base):
    __tablename__ = 'professor_assignment'
    id = Column(String, primary_key=True)
    prof_id = Column(String)
    exam_id = Column(String)
    question_number = Column(String)
    def __repr__(self):
        return "<ProfessorAssignment(id=%s prof_id='%s', exam_id='%s', question_number='%s')>" % (
                                self.id, self.prof_id, self.exam_id, self.question_number)

class ExamCorrectionPdfs(Base):
    __tablename__ = 'exam_correction_pdfs'
    id = Column(String, primary_key=True)
    exam_id = Column(String)
    pdf_file = Column(String)
    def __repr__(self):
        return "<ExamCorrectionPdfs(id=%s exam_id='%s', pdf_file='%s')>" % (
                                self.id, self.exam_id, self.pdf_file)

class QuestionCorrection(Base):
    __tablename__ = 'question_correction'
    id = Column(String, primary_key=True)
    exam_correction_pdfs = Column(String)
    page_pdf_file = Column(String)
    evaluated = Column(Boolean)
    grade = Column(Float)
    def __repr__(self):
        return "<QuestionCorrection(id=%s exam_correction_pdfs='%s', page_pdf_file='%s', evaluated=%d, grade=%f)>" % (
                                self.id, self.exam_correction_pdfs, self.page_pdf_file, self.evaluated, self.grade)

def newUser(name, password, role):
    user = User(name = name, password = password, role = role)
    session.add(user)
    session.commit()

def listUsers():
    return session.query(User).all()

def getUsersByRole(role):
    return session.query(User).filter(User.role == role).all()


Base.metadata.create_all(engine) #Create tables for the data models

Session = sessionmaker(bind=engine)
session = Session()

from flask import Flask, jsonify, render_template, request, send_from_directory
app = Flask(__name__)
     
@app.route("/")
def index():
    return render_template("index.html", message="Dynamic content!")   

@app.route("/listFiles", defaults={'directory': ''})
@app.route("/listFiles/<path:directory>")
def listFiles(directory):
    # TODO 1
    #get dir listing
    returnable = False
    parent_directory = ''
    if directory != '':
        directory = '/' + directory
        parent_directory = os.path.dirname(directory)
        returnable = True
    if parent_directory == '/':
        parent_directory = ''

    files = [f for f in os.listdir(f"./files{directory}") if os.path.isfile(os.path.join(f"./files{directory}", f))]
    context = {
        "files": [],
        "folders": [f for f in os.listdir(f"./files{directory}") if os.path.isdir(os.path.join(f"./files{directory}", f))],
        "directory": directory,
        "parent_directory": parent_directory,
        "returnable": returnable
    }

    for file in files:
        context["files"].append({
            "filename": file,
            "download_count": getDownloadCountByFileName(file)
        })
    print(context)
    return render_template("listFiles.html", context=context) 

@app.route('/getFile/<path:filename>')
def getFile(filename):
    #TODO 3
    # file verification
    FOLDER=os.path.join("./files", filename)
    if not os.path.exists(FOLDER) or not os.path.isfile(FOLDER):
        return render_template("error.html", file=filename)

    newDownload(file_name=filename, download_date=datetime.datetime.now(), ip_address=request.remote_addr)

    #TODO 5
    # send file
    return send_from_directory("./files", filename, as_attachment=True)

# TODO 4
# redirected page


@app.route("/newFile", methods=['GET', 'POST'])
def newFileForm():
    #TODO 6
    #createFile

    if request.method == 'POST':
        filename = request.form['fileName']
        content = request.form['fileContent']

        with open(os.path.join("./files", filename), 'w') as f:
            f.write(content)

    return render_template("newFile.html")


#TODO 7
#upload files

@app.route("/uploadFile", methods=['GET', 'POST'])
def uploadFileForm():
    if request.method == 'POST':
        file = request.files['file']
        print(type(file))

        file.save(os.path.join("./files", file.filename))

    return render_template("uploadFile.html")


# TODO 8
#/files

@app.route("/files")
def files():
    return jsonify(os.listdir("./files"))


@app.route('/downloads/<path:filename>')
def getFileDownloads(filename):
    FOLDER=os.path.join("./files", filename)
    if not os.path.exists(FOLDER) or not os.path.isfile(FOLDER):
        return render_template("error.html", file=filename)

    context = {
        'files': [
            {
                'filename': filename,
                'download_count': getDownloadCountByFileName(filename)
            }
        ]
    }

    return render_template("file.html", context=context)

@app.route('/downloads/json/<path:filename>')
def getFileDownloadsJson(filename):
    FOLDER=os.path.join("./files", filename)
    if not os.path.exists(FOLDER) or not os.path.isfile(FOLDER):
        return render_template("error.html", file=filename)

    context = {
        'files': [
            {
                'filename': filename,
                'download_count': getDownloadCountByFileName(filename)
            }
        ]
    }

    return context


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)
