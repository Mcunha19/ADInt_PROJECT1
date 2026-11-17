from sqlalchemy import create_engine
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Float
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from sqlalchemy.orm import sessionmaker
import os

#SLQ access layer initialization
DATABASE_FILE = "correctionDB.sqlite"
db_exists = False
if os.path.exists(DATABASE_FILE):
    db_exists = True
    print("\t database already exists")

engine = create_engine('sqlite:///%s'%(DATABASE_FILE), echo=False) #echo = True shows all SQL calls

Base = declarative_base()

#Declaration of data
class ProfessorAssignment(Base):
    __tablename__ = 'professor_assignment'
    id = Column(Integer, primary_key=True)
    prof_id = Column(Integer)
    exam_id = Column(Integer)
    question_number = Column(Integer)
    def __repr__(self):
        return "<ProfessorAssignment(id=%d prof_id='%d', exam_id='%d', question_number='%d')>" % (
                                self.id, self.prof_id, self.exam_id, self.question_number)

def newProfessorAssignment(prof_id, exam_id, question_number):
    assignment = ProfessorAssignment(prof_id=prof_id, exam_id=exam_id, question_number=question_number)
    session.add(assignment)
    session.commit()

def listProfessorAssignments():
    return session.query(ProfessorAssignment).all()

def listProfessorAssignmentsOrdered():
    return session.query(ProfessorAssignment).order_by(
        ProfessorAssignment.exam_id,
        ProfessorAssignment.question_number,
    ).all()

def getFirstProfessorAssignmentByExamAndQuestion(exam_id, question_number):
    return session.query(ProfessorAssignment).filter_by(
        exam_id=exam_id,
        question_number=question_number,
    ).first()

class ExamCorrectionPdf(Base):
    __tablename__ = 'exam_correction_pdf'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer)
    resolution_pdf_file = Column(String)
    def __repr__(self):
        return "<ExamCorrectionPdf(id=%d exam_id='%d', resolution_pdf_file='%s')>" % (
                                self.id, self.exam_id, self.resolution_pdf_file)

def newExamCorrectionPdfs(exam_id, resolution_pdf_file):
    exam_pdf = ExamCorrectionPdf(exam_id=exam_id, resolution_pdf_file=resolution_pdf_file)
    session.add(exam_pdf)
    session.commit()

def listExamCorrectionPdfs():
    return session.query(ExamCorrectionPdf).all()

def getExamCorrectionPdfById(id):
    return session.get(ExamCorrectionPdf, id)

class QuestionCorrection(Base):
    __tablename__ = 'question_correction'
    id = Column(Integer, primary_key=True)
    exam_correction_pdf_id = Column(Integer, ForeignKey('exam_correction_pdf.id'))
    question_number = Column(Integer)
    page_pdf_file = Column(String)
    evaluated = Column(Boolean)
    grade = Column(Float)
    exam_correction_pdf = relationship("ExamCorrectionPdf", backref="question_corrections")
    def __repr__(self):
        return "<QuestionCorrection(id=%d exam_correction_pdf_id='%d', question_number=%d, page_pdf_file='%s', evaluated=%d, grade=%f)>" % (
                                self.id, self.exam_correction_pdf_id, self.question_number, self.page_pdf_file, self.evaluated, self.grade)

def newQuestionCorrection(exam_correction_pdf_id, question_number, page_pdf_file, evaluated, grade):
    correction = QuestionCorrection(exam_correction_pdf_id=exam_correction_pdf_id, question_number=question_number, page_pdf_file=page_pdf_file, evaluated=evaluated, grade=grade)
    session.add(correction)
    session.commit()

def listQuestionCorrections():
    return session.query(QuestionCorrection).all()

def getQuestionCorrectionById(id):
    return session.get(QuestionCorrection, id)

def getQuestionCorrectionsByEvaluated(evaluated):
    return session.query(QuestionCorrection).filter(QuestionCorrection.evaluated.is_(evaluated)).all()


Base.metadata.create_all(engine) #Create tables for the data models

Session = sessionmaker(bind=engine)
session = Session()

from flask import Flask, render_template, request, abort, flash, redirect, send_file, url_for
from werkzeug.utils import secure_filename
import pymupdf
from pathlib import Path
from uuid import uuid4
import process_student_answers

app = Flask(__name__)
     
app.secret_key = "correction-service-development-key"
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

SERVICE_DIRECTORY = Path(__file__).resolve().parent
FILES_DIRECTORY = SERVICE_DIRECTORY / "files"
FILES_DIRECTORY.mkdir(parents=True, exist_ok=True)

def get_safe_file_path(path_value):
    path = Path(path_value).resolve()
    if not path.is_relative_to(FILES_DIRECTORY.resolve()) or not path.is_file():
        abort(404)
    return path


@app.route("/")
def index():
    return render_template(
        "index.html",
        assignment_count=session.query(ProfessorAssignment).count(),
        pdf_count=session.query(ExamCorrectionPdf).count(),
        question_count=session.query(QuestionCorrection).count(),
        corrected_count=session.query(QuestionCorrection).filter_by(evaluated=True).count(),
    )


@app.route("/assignProfessor", methods=["GET", "POST"])
def assignProfessor():
    if request.method == "POST":
        prof_id = int(request.form["professor_id"])
        exam_id = int(request.form["exam_id"])
        question_number = int(request.form["question_number"])
    
        assignment = getFirstProfessorAssignmentByExamAndQuestion(exam_id, question_number)
        if assignment is None:
            newProfessorAssignment(prof_id, exam_id, question_number)
        else:
            assignment.prof_id = prof_id
            session.commit()
        return redirect(url_for("assignProfessor"))

    assignments = listProfessorAssignmentsOrdered()
    return render_template("assignProfessor.html", assignments=assignments)


@app.route("/upload", methods=["GET", "POST"])
def upload_pdf():
    if request.method == "POST":
        uploaded_file = request.files.get("pdf_file")
        exam_id = int(request.form["exam_id"])

        source_pdf = None
        saved_paths = []
        try:
            source_pdf = pymupdf.open(stream=uploaded_file.read(), filetype="pdf")

            exam_directory = FILES_DIRECTORY / ("exam-{}".format(exam_id))
            exam_directory.mkdir(parents=True, exist_ok=True)
            upload_token = uuid4().hex
            safe_filename = secure_filename(uploaded_file.filename) or "scan.pdf"

            exam_pdf = ExamCorrectionPdf(exam_id=exam_id, resolution_pdf_file="pending")
            session.add(exam_pdf)
            session.flush()

            original_path = exam_directory / "scan-{}-{}".format(upload_token, safe_filename)
            source_pdf.save(original_path)
            saved_paths.append(original_path)
            exam_pdf.resolution_pdf_file = str(original_path)
            
            pages = process_student_answers.split_pdf_into_pages(source_pdf)
            process_student_answers.cover_qr_codes_with_gray_squares(pages)

            for page_index, page_document in enumerate(pages[1:], start=1):
                question_number = page_index
                page_path = exam_directory / (
                    "scan-{}-question-{}.pdf".format(
                        upload_token,
                        question_number,
                    )
                )
                page_document.save(page_path)
                saved_paths.append(page_path)
                session.add(
                    QuestionCorrection(
                        exam_correction_pdf_id=exam_pdf.id,
                        question_number=question_number,
                        page_pdf_file=str(page_path),
                        evaluated=False,
                    )
                )

            session.commit()
            flash("Uploaded and split {} pages.".format(source_pdf.page_count), "success")
        except Exception:
            session.rollback()
            for path in saved_paths:
                path.unlink(missing_ok=True)
            app.logger.exception("Could not process correction PDF")
            flash("The PDF could not be processed.", "danger")
        finally:
            for page_document in pages:
                if not page_document.is_closed:
                    page_document.close()
            if source_pdf is not None:
                source_pdf.close()
        return redirect(url_for("upload_pdf"))

    pdfs = listExamCorrectionPdfs()
    return render_template("uploadExamResolution.html", pdfs=pdfs)


@app.route("/assigned")
def assigned_resolutions():
    assignment_map = {
        (row.exam_id, row.question_number): row.prof_id
        for row in session.query(ProfessorAssignment).all()
    }
    return render_template("listAssignedQuestions.html", questions=listQuestionCorrections(), assignments=assignment_map)


@app.route("/questions/<int:correction_id>", methods=["GET", "POST"])
def correct_question(correction_id):
    correction = getQuestionCorrectionById(correction_id)
    if correction is None:
        abort(404)

    if request.method == "POST":
        try:
            grade = float(request.form["grade"])
            if grade < 0 or grade > 20:
                raise ValueError
        except (ValueError):
            flash("Enter a valid grade between 0 and 20.", "danger")
            return redirect(url_for("correct_question", correction_id=correction_id))
        correction.grade = grade
        correction.evaluated = True
        session.commit()
        flash("Grade saved.", "success")
        return redirect(url_for("correct_question", correction_id=correction_id))

    assignment = getFirstProfessorAssignmentByExamAndQuestion(
        exam_id=correction.exam_correction_pdf.exam_id,
        question_number=correction.question_number,
    )
    return render_template("correctQuestion.html", correction=correction, professor_id=assignment.prof_id if assignment else None)


@app.route("/questions/<int:correction_id>/page")
def correction_page(correction_id):
    correction = getQuestionCorrectionById(correction_id)
    if correction is None:
        abort(404)
    return send_file(
        get_safe_file_path(correction.page_pdf_file),
        mimetype="application/pdf",
        as_attachment=False,
    )

@app.route("/corrected")
def corrected_answers():
    questions = getQuestionCorrectionsByEvaluated(True)
    return render_template("listCorrectedQuestion.html", questions=questions)

@app.route("/scans")
def exam_scans():
    questions = listQuestionCorrections()
    return render_template("listExamScans.html", questions=questions)

@app.route("/pdfs/<int:pdf_id>/original")
def original_exam_pdf(pdf_id):
    exam_pdf = getExamCorrectionPdfById(pdf_id)
    if exam_pdf is None:
        abort(404)
    path = get_safe_file_path(exam_pdf.resolution_pdf_file)
    return send_file(path, mimetype="application/pdf", as_attachment=False)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8003, debug=True)
