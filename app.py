import streamlit as st
from food_recognition import classify_food
from recipe_retrieval import get_recipes
from PIL import Image
import io

# Resize the image
def resize_image(image_file, max_size=(1024, 1024)):
    with Image.open(image_file) as img:
        img.thumbnail(max_size, Image.Resampling.LANCZOS)  # LANCZOS is the updated filter
        output = io.BytesIO()
        img.save(output, format="JPEG")
        output.seek(0)  # Go back to the start of the BytesIO object
        return output

# UI components
st.title("Food Detection and Recipe Finder")

st.header("Upload Image")
uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        # Resize the image before processing it
        resized_image = resize_image(uploaded_file)
        image = Image.open(resized_image)  # Open the resized image for display
        
        st.image(image, caption="Uploaded Image", use_container_width=True)

        # Save the resized image to a temporary file (if needed for classifier)
        temp_file = "temp_image.jpg"
        image.save(temp_file)

        if st.button("Detect Food and Get Recipes"):
            # Classify food from the image
            detected_food = classify_food(temp_file)
            
            if detected_food:
                st.write(f"Detected Food: {', '.join(detected_food)}")
                
                # Retrieve recipes for detected food
                recipes = get_recipes(detected_food)
                
                if recipes:
                    st.write("Recipes:")
                    for recipe in recipes:
                        st.write(f"- {recipe}")
                else:
                    st.write("No recipes found.")
            else:
                st.write("No food items detected.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

else:
    st.warning("Please upload an image file.")
