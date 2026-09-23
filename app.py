import streamlit as st
import numpy as np
from PIL import Image, ImageOps
from tensorflow.keras.models import load_model
import json
import io
from google.oauth2.service_account import Credentials
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

# --- GOOGLE DRIVE INITIALIZATION ---
@st.cache_resource
def init_drive():
    # Load the JSON credentials from Streamlit Secrets
    creds_dict = json.loads(st.secrets["GOOGLE_JSON"])
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    service = build('drive', 'v3', credentials=creds)
    return service

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
    st.set_page_config(page_title="My Face Login", layout="centered")

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
                
                # Make sure this matches your labels.txt exactly!
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
        
        st.title("📁 Google Drive Manager")
        st.write("Files uploaded here are saved directly to your Google Drive folder.")
        
        try:
            drive_service = init_drive()
            folder_id = st.secrets["DRIVE_FOLDER_ID"]

            # 1. FILE UPLOADER
            uploaded_file = st.file_uploader("Select a file to upload")
            if uploaded_file is not None:
                if st.button("Save to Drive"):
                    with st.spinner("Uploading to Google Drive..."):
                        file_bytes = uploaded_file.getvalue()
                        
                        # Prepare the file metadata and media buffer for Google Drive
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
            
            # Ask Google Drive for a list of all files inside your specific folder ID
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
            st.write("Ensure your GOOGLE_JSON and DRIVE_FOLDER_ID are correct in Streamlit Secrets.")

if __name__ == "__main__":
    main()
