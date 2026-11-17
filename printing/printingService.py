import pymupdf
from sqlalchemy import create_engine
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

import datetime
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

#SLQ access layer initialization
DATABASE_FILE = "printingDB.sqlite"
db_exists = False
if os.path.exists(DATABASE_FILE):
    db_exists = True
    print("\t database already exists")

engine = create_engine('sqlite:///%s'%(DATABASE_FILE), echo=False) #echo = True shows all SQL calls

Base = declarative_base()

#Declaration of data
class ResolutionSheet(Base):
    __tablename__ = 'resolution_sheet'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer)
    sheets_pdf_file_name = Column(String)
    def __repr__(self):
        return "<ResolutionSheet(id=%d exam_id=%d, sheets_pdf_file_name='%s')>" % (
                                self.id, self.exam_id, self.sheets_pdf_file_name)

def newResolutionSheet(exam_id, sheets_pdf_file_name):
    resolution_sheet = ResolutionSheet(exam_id = exam_id, sheets_pdf_file_name = sheets_pdf_file_name)
    session.add(resolution_sheet)
    session.commit()

def getAllResolutionSheets():
    return session.query(ResolutionSheet).all()

def getUsersByRole(role):
    return session.query(User).filter(User.role == role).all()


Base.metadata.create_all(engine) #Create tables for the data models

Session = sessionmaker(bind=engine)
session = Session()

from flask import Flask, jsonify, render_template, request, send_from_directory, flash
from flaskext.xmlrpc import XMLRPCHandler
import generate_resolution_sheets
app = Flask(__name__)

handler = XMLRPCHandler('RPC')
handler.connect(app, '/RPC')
     
@app.route("/")
def index():
    resolution_sheets = getAllResolutionSheets()
    return render_template("index.html", resolution_sheets=resolution_sheets)   

@handler.register
def print_resolution_sheets(exam_id, exam_question_count, enrolled_student_count):
    merged = pymupdf.open()
    documents = []
    output_dir = Path(__file__).resolve().parent / "resolution_sheets"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "exam-{}-{}.pdf".format(
        exam_id,
        datetime.datetime.now().strftime("%Y-%m-%dT%H.%M.%S"),
    )

    output = True
    try:
        for _ in range(enrolled_student_count):
            document = generate_resolution_sheets.main()
            documents.append(document)
            merged.insert_pdf(document)

        merged.save(output_path)
        newResolutionSheet(exam_id, str(output_path))
    except Exception as e:
        flash("Error generating resolution sheets: {}".format(e), "danger")
        output = False
    finally:
        merged.close()
        for document in documents:
            document.close()

    return output


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8002, debug=True)
