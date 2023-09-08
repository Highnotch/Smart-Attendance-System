from flask import Flask
from flask import request, session, redirect
from model import face_search
import cv2
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash
from utils import run_query, create_attendance_table, encode_face, attendance_from_cv2_frame, update_status_file
import dotenv
import os
import sys
from datetime import datetime
import traceback
import face_recognition
import base64
import time


dotenv.load_dotenv(os.path.join(os.getcwd(), '.env'))
db_name = os.getenv('DB_NAME')
session_secret_key = os.getenv('SECRET_KEY')


import json

app = Flask(__name__)
app.secret_key = session_secret_key


@app.route('/api/v1/test', methods=['GET'])
def test_server():
    return "Server is running."


@app.route('/api/v1/face_recognition', methods=['POST'])
def face_recognition2():
    try:
        if 'image' in request.files:
            image = request.files['image']
            frame = cv2.imdecode(np.frombuffer(image.read(), np.uint8), cv2.IMREAD_COLOR)
            return json.dumps({"status": "ok", "result": face_search(frame)})
        else:
            return json.dumps({"status":"error", "message": "No Image Selected."}), 400
    except Exception as e:
        return json.dumps({"status":"error", "message":"Something went wrong.", "error": str(e), "traceback":traceback.format_exc()}), 500


@app.route('/api/v1/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data['email']
        password = data['password']
        is_instructor = data['is_instructor']

        query = f'select email, password, name, id from {db_name}.users where email="{email}"'
        res, code = run_query(query)
        if code != 200:
            return res, code
        
        if len(res) == 0:
            return json.dumps({"status":"error", "message": "No user found for this email. Please sign up instead."}), 400
        else:
            if check_password_hash(res[0][1], password):
                session["email"] = email
                session["name"] = res[0][2]
                session["user_id"] = res[0][3]
                session["is_instructor"] = is_instructor
                return json.dumps({"status": "ok"}), 200
            
            return json.dumps({"status":"error", "message":"Wrong Password."}), 400

    except Exception as e:
        return json.dumps({"status":"error", "message":"Something went wrong.", "error": str(e), "traceback":traceback.format_exc()}), 500


@app.route('/api/v1/logout', methods=['GET'])
def logout():
    try:
        session.clear()
        return json.dumps({"status":"ok"}), 200
    except Exception as e:
        return json.dumps({"status":"error", "error":str(e), "traceback":traceback.format_exc()}), 500

@app.route('/api/v1/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        email = data['email']
        password = generate_password_hash(data['password'])
        name = data['name']
        is_instructor = data["is_instructor"]

        query = f'select email from {db_name}.users where email="{email}"'
        res, code = run_query(query)
        if code != 200:
            return res, code
        
        if len(list(res)) > 0:
            return json.dumps({"status":"error", "message": "This email is already taken. Please login instead."}), 400

        query = f'insert into {db_name}.users(name, email, password) values("{name}", "{email}", "{password}")'
        res, code = run_query(query)
        if code != 200:
            return res, code
        
        query = f'select LAST_INSERT_ID()'
        res, code = run_query(query)
        if code != 200:
            return res, code
        
        session["name"] = name
        session["email"] = email
        session["user_id"] = res[0][0] 
        session["is_instructor"] = is_instructor
        return json.dumps({"status": "ok"}), 200
    
    except Exception as e:
        return json.dumps({"status":"error", "error": str(e), "traceback":traceback.format_exc()}), 500


@app.route('/api/v1/logged_user', methods=['GET'])
def get_logged_user():
    if "name" in session and "email" in session and "is_instructor" in session:
        return json.dumps({"status":"ok", "is_instructor": session["is_instructor"]}), 200
    else:
        return json.dumps({"status":"error"}), 400

@app.route('/api/v1/switch', methods=['GET'])
def switch():
    try:
        if "user_id" in session:
            session["is_instructor"] = not session["is_instructor"]
            return json.dumps({"status":"ok"}), 200
        else:
            return json.dumps({"status":"error", "message":"Please Login again."}), 400
    except Exception as e:
        return json.dumps({"status":"error", "message":"Something went wrong.", "error":str(e), "traceback":traceback.format_exc()}), 500


@app.route('/api/v1/courses', methods=['GET', 'POST'])
def courses():
    if "user_id" not in  session:
        return json.dumps({"status":"error", "message": "Please Login again."}), 400
    
    try:
        if session["is_instructor"]:
            if request.method == 'GET':
                query = f'select id, code, name, table_name from {db_name}.courses where instructor={session["user_id"]}'
                res, code = run_query(query)
                if code != 200:
                    return res, code
                
                for i in range(len(res)):
                    query = f'select count(user) from {db_name}.{res[i][3]} where att_datetime is null'
                    res1, code = run_query(query)
                    if code == 200:
                        res[i] = res[i] + res1[0] 
                    else:
                        res[i] = res[i] + ("-",)
                    
                    query = f'select DATE_FORMAT(max(att_datetime), "%Y/%m/%d") from {db_name}.{res[i][3]}'
                    res2, code = run_query(query)
                    if code == 200:
                        res[i] = res[i] + res2[0]
                    else:
                        res[i] = res[i] + ("-",)
                return json.dumps({"status":"ok", "result": res, "name":session['name'], "is_instructor": session["is_instructor"]}), 200
            
            elif request.method == 'POST':
                data = request.get_json()
                code1 = data['code'].upper()
                name = data['name']
                instructor = session['user_id']
                res, code = create_attendance_table(session['name'], code1)
                if code != 200:
                    return res, code
                
                query = f'insert into {db_name}.courses(code, name, instructor, table_name) values("{code1}", "{name}", {instructor}, "{res}")'
                
                res, code = run_query(query)
                if code != 200:
                    return res, code
                
                query = f'select id, name, code, instructor from {db_name}.courses where id=LAST_INSERT_ID()'
                print(3, file=sys.stderr)
                res, code = run_query(query)
                if code != 200:
                    return res, code
                
                res = {
                    "id":res[0][0],
                    "name":res[0][1],
                    "code":res[0][2],
                    "instructor":res[0][3]
                }
                
                return json.dumps({"status":"ok", "is_instructor":True, "result": res, "name":session["name"]}), 200
        
        else:
            if request.method == 'GET':

                query = 'show tables'
                res, code = run_query(query)
                if code != 200:
                    return res, code
                taken_courses = []
                out = []
                for table1 in res:
                    table = table1[0]
                    if table[0:3] == 'att':
                        query = f'select user from {db_name}.{table} where user={session["user_id"]}'
                        res1, code = run_query(query)
                        if code != 200:
                            return res1, code
                        if(len(res1) > 0):
                            query = f'select max(att_datetime) from {db_name}.{table}'
                            temp, code = run_query(query)
                            if code != 200:
                                return res, code
                            latest_class = ""
                            if(len(temp) > 0): 
                                latest_class = "No classes yet."
                            else:
                                latest_class = temp[0][0]
                            query = f'select courses.id, courses.code, courses.name, users.name from {db_name}.courses left join users on courses.instructor = users.id where courses.table_name="{table}"'
                            res2, code = run_query(query)
                            if code != 200:
                                return res2, code
                            taken_courses.append(res2[0][0])
                            out.append({"id":res2[0][0], "code":res2[0][1], "name":res2[0][2],"instructor":res2[0][3], "latest_class":latest_class})
                
                
                # Get all courses
                query = f'select courses.id, CONCAT("[", courses.code, "] - ", courses.name, " by " , users.name) from {db_name}.courses left join {db_name}.users on courses.instructor = users.id'
                res, code = run_query(query)
                if code != 200:
                    return res, code
                student_courses = []
                for c in res:
                    if c[0] not in taken_courses:
                        student_courses.append(c)
                return json.dumps({"status":"ok", "result": out, "is_instructor":session["is_instructor"], "name":session["name"], "courses":student_courses}), 200

            elif request.method == 'POST':
                data = request.get_json()
                course_id = data["course_id"]
                user_id = session["user_id"]
                
                query = f'select table_name from {db_name}.courses where id={course_id}'
                res, code = run_query(query)
                if code != 200:
                    return res, code
                if len(res) == 0:
                    return json.dumps({"status":"error", "message":"Course does not exist."}), 400
                
                table_name = res[0][0]
                query = f'insert into {db_name}.{table_name}(att_datetime, user) values(null, {user_id})'
                res, code = run_query(query)
                if code != 200:
                    return res, code
                
                return json.dumps({"status":"ok"}), 200


    except Exception as e:
        return json.dumps({"status":"error", "error":str(e), "traceback":traceback.format_exc()}), 500


@app.route('/api/v1/course', methods=['GET'])
def course_get():
    try:
        if "course" not in session:
            return json.dumps({"status":"error", "message": "No Course Selected"}), 400
        
        if session["is_instructor"] or True:
            id = session["course"]
            query = f'select courses.id, courses.code, courses.name, users.name, table_name from {db_name}.courses left join users on courses.instructor = users.id where courses.id={id}'
            res, code = run_query(query)
            if code != 200:
                return res, code
            
            course_id = res[0][0]
            course_code = res[0][1]
            course_name = res[0][2]
            instructor_name = res[0][3]
            table_name = res[0][4]

            table = {
                "id" : course_id,
                "code": course_code,
                "name": course_name,
                "instructor": instructor_name,
            }

            query = f'select DISTINCT users.id, users.name from {db_name}.{table_name} left join {db_name}.users on {table_name}.user = users.id where {table_name}.att_datetime is null'
            res, code = run_query(query)
            if code != 200:
                return res, code
            
            students = res

            query = f'select DISTINCT DATE_FORMAT({table_name}.att_datetime, "%Y/%m/%d") from {db_name}.{table_name} where att_datetime is not null'
            res, code = run_query(query)
            if code != 200:
                return res, code
            days = res

            result = {}
            for student in students:
                query = f'select DATE_FORMAT(att_datetime, "%Y/%m/%d") from {db_name}.{table_name} left join {db_name}.users on {table_name}.user = users.id where {table_name}.att_datetime is not null and {table_name}.user={student[0]}'
                res, code = run_query(query)
                if code != 200:  
                    return res, code
                
                query = f'select count(DISTINCT DATE_FORMAT(att_datetime, "%Y/%m/%d")) / {len(days)} * 100 from {db_name}.{table_name} left join {db_name}.users on {table_name}.user = users.id where {table_name}.att_datetime is not null and {table_name}.user={student[0]}'
                res2, code = run_query(query)
                if code != 200:
                    return res2, code

                result[student[0]] = [float(res2[0][0] if res2[0][0] is not None else 0), res]

            # query = f'select DATE_FORMAT({table_name}.att_datetime, "%Y/%m/%d"), users.name from {db_name}.{table_name} left join {db_name}.users on {table_name}.user = users.id where {table_name}.att_datetime is not null'
            # res, code = run_query(query)
            # if code != 200:
            #     return res, code
            
            # result = res


            return json.dumps({"status":"ok", "table":table, "result":result, "students":students, "days":days, "name":session["name"], "is_instructor":session["is_instructor"]}), 200
        


    except Exception as e:
        return json.dumps({"status":"error", "error":str(e), "traceback":traceback.format_exc()}), 500
 


@app.route('/api/v1/course/<int:id>', methods=['GET', 'POST', 'PUT','DELETE'])
def course(id):
    try:
        if session["is_instructor"]:
            if request.method == 'GET':
                session["course"] = id
                return json.dumps({"status": "ok"}), 200
            
            elif request.method == 'PUT':
                data = request.get_json()
                id = data['id']
                code = data['code']
                name = data['name']
                instructor = session['user_id']
                query = f'update {db_name}.courses set code="{code}", name="{name}" where id={id}'
                res, code = run_query(query)
                if code != 200:
                    return res, code

                res = {
                    "id":id,
                    "name":name,
                    "code":code,
                    "instructor":instructor
                }
                
                return json.dumps({"status":"ok", "result": res}), 200
            
            elif request.method == 'DELETE':
                data = request.get_json()
        else:
            if request.method == 'GET':
                session["course"] = id
                return json.dumps({"status": "ok"}), 200

    
    except Exception as e:
        return json.dumps({"status":"error", "error":str(e), "traceback":traceback.format_exc()}), 500


@app.route('/api/v1/upload_image', methods=['POST'])
def upload_image():
    if "user_id" not in session:
        return json.dumps({"status":"error", "message":"Please Login again."}), 400
    try:
        if 'add-your-image-input' in request.files:
            image = request.files['add-your-image-input']
            res, code = encode_face(image, session["user_id"])
            if code != 200:
                return res, code
            
            return json.dumps({"status":"ok", "message":"Your profile image has been updated."}), 200

        else:
            return json.dumps({"status":"error", "message": "No Image Selected."}), 400

    except Exception as e:
        return json.dumps({"status":"error", "message":"Something went wrong.", "error": str(e), "traceback":traceback.format_exc()}), 500

# Mark Attendance by uploading one image through web interface
@app.route("/api/v1/mark_attendance", methods=['POST'])
def mark_attendance():

    try:
        course = session["course"]
        if 'add-your-image-input' in request.files:
            image = request.files['add-your-image-input']
            frame = cv2.imdecode(np.frombuffer(image.read(), np.uint8), cv2.IMREAD_COLOR)
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Save the image
            status = []
            file_name = f"{course}-upload-{time.time()}.jpg"

            status.append({"camera":"upload", "image":f"temp/{file_name}", "error":None})
            update_status_file(course, status)

            result2 = attendance_from_cv2_frame(frame, course, file_name)

            return json.dumps({"status":"ok", "result":result2}), 200           

        else:
            return json.dumps({"status":"error", "message": "No Image Selected."}), 400
    except Exception as e:
        return json.dumps({"status":"error", "message":"Something went wrong.", "error": str(e), "traceback":traceback.format_exc()}), 500

# Receive images through RPI camera server 
@app.route('/api/v1/mark_attendance_rpi', methods=['POST'])
def mark_attendance_rpi():
    try:
        data = json.loads(request.data)
        course = data["course"]
        del data["course"]

        # Write/Append the incoming data to a JSON file
        status = []
        for camera in data.keys():
            timestamp = time.time()
            if data[camera]["status"] == 'ok':
                # Save the image
                file_name = f"{course}-{camera}-{timestamp}.jpg"
                try:
                    decode = base64.b64decode(data[camera]["image"])
                    buffer = np.frombuffer(decode, np.uint8)
                    frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
                    
                    attendance_from_cv2_frame(frame, course, file_name)

                    status.append({"camera":camera, "image":f"temp/{file_name}", "error": None})
                
                except Exception as e:
                    status.append({"camera":camera, "image":None, "error":str(e), "traceback":traceback.format_exc()})
            else:
                status.append({"camera":camera, "image":None, "error":data[camera]["status"]})

        update_status_file(course, status)
        return json.dumps({"status":"ok"}), 200    


    except Exception as e:
        print(str(e), file=sys.stderr)
        return json.dumps({"status":"error", "message":"Something went wrong.", "error": str(e), "traceback":traceback.format_exc()}), 500

