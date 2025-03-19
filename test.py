import pathlib
import base64
import requests
import streamlit as st
import cv2
import os
from PIL import Image

# Load API Key securely from Streamlit secrets
API_KEY = 'AIzaSyB40JCVNmmLfjtvXYETQOiXL7G7w1czKfQ'
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={API_KEY}"

# Function to encode image to base64
def encode_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Function for scenario-specific input
def ai_chemist_simulation(scenario):
    if scenario == "Diet-Friendly Recipes":
        target = st.text_input(f"Enter dietary requirements for {scenario}:")
        constraints, stability = "", ""
    elif scenario == "Ingredient-Based Recipes":
        target = st.text_input(f"Enter main ingredients for {scenario}:")
        constraints = st.text_input(f"Enter any constraints or preferences for {scenario}:")
        stability = ""
    elif scenario == "Quick Meals":
        target = st.text_input(f"Enter the desired meal type for {scenario}:")
        constraints = ""
        stability = st.text_input(f"Enter any time constraints for {scenario}:")
    return target, constraints, stability

# Streamlit App Layout
st.title("AI Recipe Predictor")

# Select scenario
scenario = st.selectbox(
    "Select a Scenario",
    ("Diet-Friendly Recipes", "Ingredient-Based Recipes", "Quick Meals")
)

# Get user inputs based on the scenario
target, constraints, stability = ai_chemist_simulation(scenario)

# Capture Image Using Laptop Camera
def capture_image():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow to fix MSMF errors

    if not cap.isOpened():
        st.error("Error: Camera not accessible!")
        return None

    st.write("Capturing image... Please wait.")
    ret, frame = cap.read()
    cap.release()

    if ret:
        image_path = "captured_image.jpg"
        cv2.imwrite(image_path, frame)
        return image_path
    else:
        st.error("Failed to capture image!")
        return None

# Button to open camera and take photo
if st.button("Capture Image from Camera"):
    image_path = capture_image()
    if image_path:
        st.image(image_path, caption="Captured Image", use_column_width=True)

# File uploader for images
uploaded_files = st.file_uploader("Upload food images...", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
image_paths = []

# Save uploaded images temporarily
if uploaded_files:
    for idx, img in enumerate(uploaded_files):
        try:
            image = Image.open(img)
            st.image(image, use_column_width=True)

            # Convert to RGB if necessary
            if image.mode == 'RGBA':
                image = image.convert('RGB')

            temp_path = pathlib.Path(f"temp_image_{idx}.jpg")
            image.save(temp_path, format="JPEG")
            image_paths.append(str(temp_path))
        except Exception as e:
            st.error(f"Error processing image: {e}")

# Function to send request to Google API
def fetch_recipes(prompt, image_paths):
    image_inputs = []

    for image_path in image_paths:
        base64_image = encode_image(image_path)
        image_inputs.append({
            "inlineData": {
                "mimeType": "image/jpeg",
                "data": base64_image
            }
        })

        # Remove the temp image after encoding
        os.remove(image_path)

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}] + image_inputs}
        ],
        "generationConfig": {
            "maxOutputTokens": 2000,  # Increase token limit for multiple responses
            "temperature": 0.9,  # Increase creativity
            "topK": 40
        }
    }

    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code == 200:
            # Extract multiple responses if available
            candidates = response.json().get("candidates", [])
            recipes = [cand.get("content", {}).get("parts", [{}])[0].get("text", "No response") for cand in candidates]
            return recipes
        else:
            return [f"Error: {response.status_code} - {response.text}"]
    except Exception as e:
        return [f"Error: {str(e)}"]

# Main function to generate recipes
def main():
    if st.button("Predict Recipes"):
        with st.spinner("Generating Recipes..."):
            # Generate prompt based on scenario
            if scenario == "Diet-Friendly Recipes":
                prompt = ("Provide 3 different step-by-step diet-friendly recipes that meet the following dietary requirements: "
                          f"{target}. Include ingredient quantities, cooking time, preparation steps, and nutritional information.")
            elif scenario == "Ingredient-Based Recipes":
                prompt = ("Generate 3 different full recipes using the following ingredients: "
                          f"{target}. Ensure each recipe is well-balanced, includes clear step-by-step cooking instructions, "
                          "estimated cooking time, and tips for maximizing flavor. Consider the following constraints: "
                          f"{constraints}.")
            elif scenario == "Quick Meals":
                prompt = ("Provide 3 quick meal recipes that can be prepared in under 30 minutes. Include a list of ingredients, "
                          "clear step-by-step cooking instructions, estimated cooking time, and serving suggestions. "
                          f"Consider these constraints: {stability}.")

            # Use uploaded images or captured image
            if image_paths or "captured_image.jpg" in os.listdir():
                if "captured_image.jpg" in os.listdir():
                    image_paths.append("captured_image.jpg")

                # Get multiple responses
                recipes = fetch_recipes(prompt, image_paths)

                # Display recipes
                for idx, recipe in enumerate(recipes, start=1):
                    st.subheader(f"Recipe {idx}")
                    st.write(recipe)
            else:
                st.error("No images provided! Please capture or upload an image.")

# Run the main function
if __name__ == "__main__":
    main()