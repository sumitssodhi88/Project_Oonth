import os
from docx import Document
import tkinter as tk
from tkinter import filedialog

def doc_to_txt(doc_path, txt_path):
    """Convert a DOCX file to TXT."""
    doc = Document(doc_path)
    text = [para.text for para in doc.paragraphs]
    with open(txt_path, 'w', encoding='utf-8') as txt_file:
        txt_file.write("\n".join(text))

def convert_all_docs_in_folder(folder_name):
    """Convert all DOCX files in the folder to TXT and save them in the parent folder."""
    # Get the parent folder path
    parent_folder = os.path.abspath(os.path.join(folder_name, '..'))

    # Create the folder to store TXT files if it doesn't exist
    output_folder = os.path.join(parent_folder, 'txt_files')
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Loop through all files in the provided folder
    for filename in os.listdir(folder_name):
        file_path = os.path.join(folder_name, filename)
        
        if filename.endswith('.docx') and os.path.isfile(file_path):
            # Create the output file path for the TXT file
            txt_filename = os.path.splitext(filename)[0] + '.txt'
            txt_path = os.path.join(output_folder, txt_filename)
            
            # Convert DOCX to TXT
            doc_to_txt(file_path, txt_path)
            print(f"Converted {filename} to {txt_filename}")

# Create a Tkinter root window (it won't be shown)
root = tk.Tk()
root.withdraw()  # Hide the root window

# Ask the user to choose a folder containing DOCX files
folder_name = filedialog.askdirectory(title="Select Folder Containing DOCX Files")

if folder_name:
    # Convert all DOCX files in the chosen folder
    convert_all_docs_in_folder(folder_name)
else:
    print("No folder was selected.")
