from sqlalchemy import create_engine
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
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
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    password = Column(String)
    role = Column(String)
    def __repr__(self):
        return "<User(id=%d name='%s', password='%s', role='%s')>" % (
                                self.id, self.name, self.password, self.role)

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

from flask import Flask, json, jsonify, render_template, request, send_from_directory
app = Flask(__name__)
     
@app.route("/")
def index():
    return render_template("index.html", message="Dynamic content!")   

@app.route("/listUsers", methods=['GET'])
def listUsers():
    users = session.query(User).all()
    return render_template("listUsers.html", users=users)

@app.route("/addUser", methods=['GET', 'POST'])
def addUser():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        role = request.form['role']
        newUser(name, password, role)
    return render_template("addUser.html")

@app.route("/addUserBulk", methods=['GET', 'POST'])
def addUserBulk():
    if request.method == 'POST':
        try:
            data = json.loads(request.form["listOfUsers"])
            if not isinstance(data, list):
                raise ValueError
            for item in data:
                newUser(item["name"], item["password"], item["role"])
        except (ValueError, KeyError, TypeError):
            return "JSON inválido: esperado uma lista de utilizadores.", 400
    return render_template("addUserBulk.html")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)
