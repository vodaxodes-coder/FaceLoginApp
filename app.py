import streamlit as st
import numpy as np
from PIL import Image, ImageOps
from tensorflow.keras.models import load_model
import json
import io
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- SECURITY WALL INITIALIZATION ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

@st.cache_resource
def load_tm_model():
    model = load_model("keras_model.h5", compile=False)
    with open("labels.txt", "r") as f:
        labels = f.readlines()
    return model, labels

def preprocess_image(image_data):
    image = Image.open(image_data).convert("RGB")
    size = (224, 224)
    image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
    image_array = np.asarray(image)
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
    data[0] = normalized_image_array
    return data

def main():
    st.set_page_config(page_title="Best Buy Secure Portal", layout="centered")

    # ==========================================
    #             SECURITY WALL
    # ==========================================
    if not st.session_state['authenticated']:
        st.title("🔒 Security Wall")
        
        tab1, tab2 = st.tabs(["📷 Face Scan", "🔑 Use Credentials"])
        
        with tab1:
            st.write("Take a picture of your face to unlock the app.")
            camera_img = st.camera_input("Click 'Take Photo'")
            
            if camera_img is not None:
                model, labels = load_tm_model()
                processed_data = preprocess_image(camera_img)
                
                prediction = model.predict(processed_data)
                index = np.argmax(prediction)
                class_name = labels[index].strip()
                confidence_score = prediction[0][index]
                
                TARGET_CLASS = "0 Class 1"  
                
                if TARGET_CLASS in class_name and confidence_score > 0.85:
                    st.success("Face recognized! Unlocking...")
                    st.session_state['authenticated'] = True
                    st.rerun() 
                else:
                    st.error("Face not recognized. Access Denied.")

        with tab2:
            st.write("Enter your ID and Password to bypass the camera.")
            user_id = st.text_input("ID")
            user_pw = st.text_input("Password", type="password") 
            
            if st.button("Log In"):
                if user_id == "parikhshitkochar" and user_pw == "BONd2983":
                    st.success("Credentials accepted! Unlocking...")
                    st.session_state['authenticated'] = True
                    st.rerun()
                else:
                    st.error("Incorrect ID or Password. Access Denied.")

    # ==========================================
    #             SECRET APP CONTENT
    # ==========================================
    if st.session_state['authenticated']:
        st.sidebar.button("Log out", on_click=lambda: st.session_state.update({'authenticated': False}))
        
        st.title("📁 Best Buy File Manager")
        st.write("Securely upload reports and documents to Google Drive.")
        
        try:
            oauth_json = json.loads(st.secrets["GOOGLE_OAUTH_JSON"])
            redirect_uri = st.secrets["REDIRECT_URI"]
            folder_id = st.secrets["DRIVE_FOLDER_ID"]
            
            # Setup OAuth Flow
            flow = Flow.from_client_config(
                oauth_json,
                scopes=['https://www.googleapis.com/auth/drive'],
                redirect_uri=redirect_uri
            )
            
            # Catch the return code from Google after login
            if "code" in st.query_params:
                # Retrieve the code verifier from session memory
                if "code_verifier" in st.session_state:
                    flow.code_verifier = st.session_state["code_verifier"]
                    
                flow.fetch_token(code=st.query_params["code"])
                st.session_state["google_creds"] = flow.credentials
                st.query_params.clear()
                st.rerun()
                
            # If not logged into Google yet, show the login button
            if "google_creds" not in st.session_state:
                auth_url, _ = flow.authorization_url(prompt='consent')
                # Save the code verifier to session memory before clicking the link
                st.session_state["code_verifier"] = flow.code_verifier
                
                st.info("You must link your Google Account to upload files.")
                st.link_button("🔐 Log in with Google", auth_url)
                
            # If logged in, show the uploader and files
            else:
                creds = st.session_state["google_creds"]
                drive_service = build('drive', 'v3', credentials=creds)
                
                # 1. FILE UPLOADER
                uploaded_file = st.file_uploader("Select a file to upload")
                if uploaded_file is not None:
                    if st.button("Save to Drive"):
                        with st.spinner("Uploading to Google Drive..."):
                            file_bytes = uploaded_file.getvalue()
                            file_metadata = {'name': uploaded_file.name, 'parents': [folder_id]}
                            media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=uploaded_file.type, resumable=True)
                            
                            drive_service.files().create(
                                body=file_metadata, 
                                media_body=media, 
                                fields='id'
                            ).execute()
                            
                            st.success(f"'{uploaded_file.name}' saved to Drive!")
                            st.rerun()

                st.divider()
                
                # 2. FILE VIEWER & DELETER
                st.subheader("Saved Files")
                
                results = drive_service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="files(id, name)"
                ).execute()
                
                files = results.get('files', [])
                
                if not files:
                    st.info("Your Google Drive folder is currently empty.")
                else:
                    for file_data in files:
                        file_name = file_data['name']
                        file_id = file_data['id']
                        
                        col1, col2 = st.columns([4, 1])
                        col1.write(f"📄 {file_name}")
                        
                        if col2.button("Delete", key=f"del_{file_id}"):
                            drive_service.files().delete(fileId=file_id).execute()
                            st.rerun()

        except Exception as e:
            st.error(f"⚠️ Drive connection error: {e}")

if __name__ == "__main__":
    main()
