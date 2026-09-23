import streamlit as st
import numpy as np
from PIL import Image, ImageOps
from tensorflow.keras.models import load_model

# 1. This tells the app we are locked out by default
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# 2. This loads your AI model into the app
@st.cache_resource
def load_tm_model():
    model = load_model("keras_model.h5", compile=False)
    with open("labels.txt", "r") as f:
        labels = f.readlines()
    return model, labels

# 3. This changes the webcam photo into a format the AI understands
def preprocess_image(image_data):
    image = Image.open(image_data).convert("RGB")
    size = (224, 224)
    image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
    image_array = np.asarray(image)
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
    data[0] = normalized_image_array
    return data

# 4. This is the main screen you will see
def main():
    st.set_page_config(page_title="My Face Login", layout="centered")

    # --- THIS IS THE SECURITY WALL ---
    if st.session_state['authenticated'] == False:
        st.title("🔒 Security Wall")
        st.write("Take a picture of your face to unlock the app.")
        
        # Opens the webcam
        camera_img = st.camera_input("Click 'Take Photo'")
        
        if camera_img is not None:
            model, labels = load_tm_model()
            processed_data = preprocess_image(camera_img)
            
            # The AI guesses who is in the photo
            prediction = model.predict(processed_data)
            index = np.argmax(prediction)
            class_name = labels[index].strip()
            confidence_score = prediction[0][index]
            
            # >>> CHANGE THIS LINE to match what is inside your labels.txt file! <<<
            TARGET_CLASS = "0 Class 1"  
            
            if TARGET_CLASS in class_name and confidence_score > 0.85:
                st.success("Face recognized! Unlocking...")
                st.session_state['authenticated'] = True
                st.rerun() # Refreshes the page to show the secret content
            else:
                st.error("Face not recognized. Access Denied.")

    # --- THIS IS THE SECRET APP CONTENT ---
    if st.session_state['authenticated'] == True:
        
        # A button to lock it back up
        st.sidebar.button("Log out", on_click=lambda: st.session_state.update({'authenticated': False}))
        
        st.title("🎉 Welcome inside!")
        st.write("You made it past the security wall. You can build the rest of your app right here.")

if __name__ == "__main__":
    main()