import pickle
import face_recognition
import numpy as np

def face_search(image, tolerance=0.5):
    # Load pickle file
    f = pickle.load(open('pickles/sample.p', 'rb'))
    known_faces, known_names = f

    result = []

    # Detect Faces
    face_locations = face_recognition.face_locations(image)
    face_encodings = face_recognition.face_encodings(image, face_locations,num_jitters=5)

    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_faces, face_encoding, tolerance)

        face_distances = face_recognition.face_distance(known_faces, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_names[best_match_index]
            result.append(name)

    return result