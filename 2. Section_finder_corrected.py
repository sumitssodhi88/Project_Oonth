from docx import Document
import re
import tkinter as tk
from tkinter import filedialog
import os

# Function to modify text
def modify_section_text(text):
    # Regex to match section numbers with one or two periods before the dash
    # We ensure that there is no additional period in the text before the dash
    text = re.sub(r'(\d+[A-Za-z]*\.\s[^—.]*\.)(—)', r'Section \1\2', text)
    return text

# Create a Tkinter root window (hidden)
root = tk.Tk()
root.withdraw()

# Ask user to select the input Word file
input_file = filedialog.askopenfilename(title="Select a Word file", filetypes=[("Word Documents", "*.docx")])

# Check if the user selected a file
if input_file:
    # Load the Word file
    doc = Document(input_file)

    # Iterate through paragraphs and modify them
    for para in doc.paragraphs:
        # Only process paragraphs that have one or two periods before the dash (and avoid more periods)
        if re.search(r'\d+[A-Za-z]*\.\s[^—]*\.\s?—', para.text):
            modified_text = modify_section_text(para.text)
            para.text = modified_text

    # Determine the folder path one level up from the selected file
    folder_path = os.path.dirname(input_file)
    parent_folder = os.path.dirname(folder_path)

    # Create the 'with_sections' folder if it doesn't exist
    output_folder = os.path.join(parent_folder, "with_sections")
    os.makedirs(output_folder, exist_ok=True)

    # Set the output file path with the same filename as input but inside 'with_sections' folder
    output_file = os.path.join(output_folder, os.path.basename(input_file))

    # Save the modified Word file
    doc.save(output_file)

    print(f"File saved as: {output_file}")
else:
    print("No file selected.")
