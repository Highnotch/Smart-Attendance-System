import mysql.connector as db
from mysql.connector.errors import Error as dbError
from mysql.connector import errorcode
import json
import dotenv
import os
import sys
import traceback
import cv2
import face_recognition
import numpy as np
import face_recognition
from datetime import datetime

dotenv.load_dotenv(os.path.join(os.getcwd(), '.env'))

host = os.getenv('DB_URL')
user = os.getenv('DB_USER')
password = os.getenv('DB_PASS')
db_name = os.getenv('DB_NAME')


connectUsers = db.connect(host=host, user=user, password=password, database=db_name)

def connectDB():
    global connectUsers
    try:
        connectUsers = db.connect(host = host, user = user, password = password, database=db_name)
    except dbError as err:
        connectUsers = {}
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            connectUsers['ERROR'] = "DB_ACCESS_DENIED"
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            connectUsers['ERROR'] = "BAD_DATABASE"
        else:
            connectUsers['ERROR'] = str(err)

def getCursor():
    try:
        db_cursor = connectUsers.cursor()
    except dbError:
        connectDB()
        db_cursor = connectUsers.cursor()
    finally:
        if isinstance(connectUsers, dict):
            return ['ERROR', json.dumps({'status':'ERROR', 'ERROR': connectUsers['ERROR']})]
        else:
            return ['OK', db_cursor]

def run_query(query, api='', data=''):
    status, cursor = getCursor()
    if status == 'OK':
        try:
            cursor.execute(query)
            res = list(cursor)
            connectUsers.commit()
            return res, 200
        except dbError as err:
            cursor.execute(f'insert into {db_name}.errors(api, params, error) values({api}, {str(data)}, {str(err)})')
            connectUsers.commit()
            return json.dumps({"status":"error", "message": "Something went wrong.", "error": f"{str(err)}", "traceback":traceback.format_exc()}), 500
            
    else:
        return cursor, 500


def create_attendance_table(user_name, course_name):
    table_name = generate_table_name(user_name, course_name)
    query = f'create table if not exists {db_name}.{table_name}(id int PRIMARY KEY AUTO_INCREMENT, att_datetime datetime DEFAULT NULL, user int NOT NULL, foreign key (user) references users(id))'
    res, code = run_query(query)
    if code != 200:
        return res, code
    
    return table_name, code

def generate_table_name(user_name, course_name):
    table_name = "att_"
    for i in user_name:
        if i.isalnum():
            table_name += i
    
    table_name += "_"

    for i in course_name:
        if i.isalnum():
            table_name += i

    return table_name


def encode_face(image, user_id):
    frame = cv2.imdecode(np.frombuffer(image.read(), np.uint8), cv2.IMREAD_COLOR)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    enc = face_recognition.face_encodings(frame,num_jitters=3)[0]
    enc = json.dumps(enc.tolist())

    query = f'update {db_name}.users set image_data = "{enc}" where id={user_id}'
    res, code = run_query(query)
    return res, code

def attendance_from_cv2_frame(image, course, file_name):

    query = f'select table_name from {db_name}.courses left join users on courses.instructor = users.id where courses.id={course}'
    res, code = run_query(query)
    if code != 200:
        return res, code
    
    table_name = res[0][0]

    query = f'select DISTINCT users.id, users.image_data, users.name from {db_name}.{table_name} left join {db_name}.users on {table_name}.user = users.id where {table_name}.att_datetime is null'
    res, code = run_query(query)
    if code != 200:
        return res, code
    
    students = res

    known_faces = []
    known_names = []
    known = []

    for student in students:
        if student[1] != None:
            known_faces.append(np.array(json.loads(student[1])))
            # print(known_faces[-1].shape, file=sys.stderr)
            known_names.append(student[0])
            known.append(student[2])
    
    # print(known_faces)
    result = []
    result2 = []
    face_locations = face_recognition.face_locations(image)
    face_encodings = face_recognition.face_encodings(image, face_locations,num_jitters=5)

    for face_encoding, face_location in zip(face_encodings, face_locations):
        color = (0, 0, 255)
        matches = face_recognition.compare_faces(known_faces, face_encoding, tolerance=0.5)

        face_distances = face_recognition.face_distance(known_faces, face_encoding)
        best_match_index = np.argmin(face_distances)
        top, right, bottom, left = face_location
        if matches[best_match_index]:
            name = known_names[best_match_index]
            name2 = known[best_match_index]
            result.append(name)
            result2.append(known[best_match_index])
            color = (255, 0, 0)
            cv2.putText(image, name2, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
        cv2.rectangle(image, (left, top), (right, bottom), color, 2)

    
    cv2.imwrite(f"assets/temp/{file_name}", image)

    
    for id in result:
        query = f'insert into {db_name}.{table_name}(att_datetime, user) select "{datetime.today().strftime("%Y-%m-%d %H:%M:%S")}", {id} where not exists (select 1 from {db_name}.{table_name} where user = {id} and att_datetime = "{datetime.today().strftime("%Y-%m-%d %H:%M:%S")}")'
        res, code = run_query(query)
        if code != 200:
            return res, code
    
    return result2

def update_status_file(course, status):
    dt = datetime.today().strftime("%Y-%m-%d")
    json_file = f"assets/temp/status_{course}_{dt}.json"

    if os.path.isfile(json_file):
        with open(json_file, 'r') as f:
            data = json.loads(f.read())
        
        status.extend(data)

    with open(json_file, 'w') as f:
        f.write(json.dumps(status))
