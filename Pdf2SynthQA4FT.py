import json
import time
import requests
import os
import logging
from tkinter import Tk
from tkinter.filedialog import askdirectory
import fitz  # PyMuPDF
from tqdm import tqdm
import sys
from itertools import cycle

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TextProcessor")

# Ollama API details
def get_api_details():
    """Prompt user to enter API details."""
    print("\n--- Ollama API Configuration ---")
    host = input("Enter the Ollama API host (e.g., http://192.168.x.x:11434): ").strip()
    model_name = input("Enter the model name (e.g., llama3.1:8b-instruct-q8_0): ").strip()

    if not host or not model_name:
        logger.error("Both host and model name are required. Exiting.")
        exit(1)

    return host, model_name

HOST, MODEL_NAME = get_api_details()

history = {'internal': [], 'visible': []}  # To keep track of question-answer pairs

# Enhanced Command to instruct the API
command = (
    "You are an API that converts bodies of text into multiple question-answer pairs. "
    "Each pair should be in the following JSON format: "
    "{\"question\": \"<question>\", \"instruction\": \"<instruction>\", \"answer\": \"<answer>\"}. "
    "Always include the full name of the Act in both the question and answer without fail; and Article/Section, if available. "
    "For each question-answer pair, provide a generic instruction that would guide someone to generate clear, accurate, and relevant answers in a similar context. "
    "Give as detailed answers as possible and if possible with examples and scenarios. "
    "The instruction should be based on the content of the question and answer but should be generic and applicable to similar questions. "
    "Avoid extraneous formatting or text unless required. Only give the json and no other comment."
)

def get_chunking_option():
    """Prompt user for the chunking delimiter, max length, and overlap if rolling."""
    print("\n--- Chunking Configuration ---")
    print("1. Fixed size (default)")
    print("2. Based on a delimiter (e.g., '.', ',', '(', etc.)")
    print("3. Rolling chunking with overlap")

    choice = input("Enter your choice (1, 2, or 3): ").strip()
    max_length = int(input("Enter the maximum chunk size (e.g., 1000): ").strip())

    if choice == "1":
        return "fixed", None, max_length, None
    elif choice == "2":
        delimiter = input("Enter the delimiter (e.g., '.', ',', '(', etc.): ").strip()
        if not delimiter:
            logger.error("Delimiter cannot be empty. Exiting.")
            exit(1)
        return "delimiter", delimiter, max_length, None
    elif choice == "3":
        overlap = int(input("Enter the overlap size (e.g., 200): ").strip())
        return "rolling", None, max_length, overlap
    else:
        logger.error("Invalid choice. Please select either 1, 2, or 3. Exiting.")
        exit(1)

def chunk_text(text, method="fixed", max_length=1000, delimiter=None, overlap=None):
    """
    Split large text into smaller chunks, prioritizing size, and optionally refining by delimiters.
    Additionally, support for rolling chunking with overlap.

    Parameters:
        text (str): The text to be chunked.
        method (str): "fixed" for fixed-size chunks, "delimiter" for splitting by a delimiter, "rolling" for rolling chunks.
        max_length (int): Maximum chunk length.
        delimiter (str): The delimiter to split by (used only if method="delimiter").
        overlap (int): The number of characters to overlap between consecutive chunks (used only if method="rolling").

    Returns:
        list: A list of text chunks.
    """
    if method == "fixed":
        # Basic fixed-size chunking
        return [text[i:i + max_length] for i in range(0, len(text), max_length)]

    elif method == "delimiter" and delimiter:
        # First, split by size
        preliminary_chunks = [text[i:i + max_length] for i in range(0, len(text), max_length)]
        refined_chunks = []

        for chunk in preliminary_chunks:
            if delimiter in chunk:
                # Split within the size-constrained chunk by delimiter
                parts = chunk.split(delimiter)
                current_chunk = ""
                for part in parts:
                    if len(current_chunk) + len(part) + len(delimiter) <= max_length:
                        current_chunk += part + delimiter
                    else:
                        refined_chunks.append(current_chunk.strip())
                        current_chunk = part + delimiter
                if current_chunk:
                    refined_chunks.append(current_chunk.strip())
            else:
                refined_chunks.append(chunk.strip())

        return refined_chunks

    elif method == "rolling" and overlap is not None:
        # Rolling chunking with overlap
        chunks = []
        start_idx = 0

        while start_idx < len(text):
            end_idx = start_idx + max_length
            chunks.append(text[start_idx:end_idx])

            # Move the start index backward by overlap size for the next chunk
            start_idx = end_idx - overlap

        return chunks

    else:
        logger.error("Invalid chunking method or missing overlap/delimiter. Exiting.")
        exit(1)

def run(user_input, chunk_idx=0):
    """Run the Ollama API model with the given input."""
    logger.info(f"Submitting chunk {chunk_idx + 1} to API.")
    try:
        url = f"{HOST}/v1/chat/completions"
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": user_input}]
        }
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            response_data = response.json()
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', None)

            if content:
                # Log the raw API response for debugging
                logger.info(f"Raw API response content for chunk {chunk_idx + 1}: {content[:500]}")

                # Attempt to fix malformed JSON if needed
                try:
                    if content.startswith("[") and content.endswith("]"):
                        # If JSON-like but malformed, try sanitizing
                        content = content.replace("}\n{", "},{")
                        response_json = json.loads(content)  # Decode into JSON

                        # Validate response structure
                        qa_pairs = []
                        for item in response_json:
                            if isinstance(item, dict) and "question" in item and "answer" in item:
                                qa_pairs.append(item)

                        if not qa_pairs:
                            logger.warning(f"Malformed content structure in chunk {chunk_idx + 1}")
                            return None

                        return qa_pairs
                    else:
                        logger.error(f"Response format invalid for chunk {chunk_idx + 1}")
                        return None
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decoding failed for chunk {chunk_idx + 1}: {content[:500]} | Error: {e}")
                    return None
            else:
                logger.warning(f"API response content is empty for chunk {chunk_idx + 1}.")
                return None
        else:
            logger.warning(f"API call failed with status {response.status_code} for chunk {chunk_idx + 1}: {response.text}")
            return None
    except requests.RequestException as e:
        logger.error(f"Request error for chunk {chunk_idx + 1}: {e}")
        return None


def save_to_json(data, output_path):
    """Save responses to a JSON file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
        logger.info(f"Saved chunk output to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save JSON file at {output_path}: {e}")

def read_pdf(file_path):
    """Read PDF content using PyMuPDF."""
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text("text")
    return text

def read_text_file(file_path):
    """Read text file content."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def ask_for_folder():
    """Ask user for folder containing PDF or TXT files."""
    print("\n--- File Selection ---")
    Tk().withdraw()
    folder_path = askdirectory(title="Select Folder Containing PDF/TXT Files")
    if not folder_path:
        logger.error("No folder selected. Exiting.")
        exit(1)
    return folder_path

def display_static_status_bar(message):
    """Display a static status bar on the CLI."""
    sys.stdout.write(f"\r{message.ljust(80)}")
    sys.stdout.flush()

import os

def process_folder_with_status_bar(folder_path, method, delimiter, max_length, overlap):
    """Process all files in the folder with a status bar."""
    logger.info(f"Processing folder: {folder_path}")
    files = os.listdir(folder_path)
    valid_files = [f for f in files if f.lower().endswith(('.pdf', '.txt'))]

    if not valid_files:
        logger.error("No valid PDF or TXT files found in the selected folder. Exiting.")
        exit(1)

    for file_name in valid_files:
        file_path = os.path.join(folder_path, file_name)
        logger.info(f"Processing file: {file_path}")
        text = ""

        if file_name.lower().endswith(".pdf"):
            text = read_pdf(file_path)
        elif file_name.lower().endswith(".txt"):
            text = read_text_file(file_path)

        # Removing unnecessary whitespace and newlines
        text = text.replace("\n", " ").strip()

        file_name_without_extension = os.path.splitext(file_name)[0]

        # Create FT_Dataset folder inside the current folder if it doesn't exist
        output_folder = os.path.join(folder_path, "FT_Dataset")
        os.makedirs(output_folder, exist_ok=True)

        # Get chunks based on the selected chunking method
        chunks = chunk_text(text, method, max_length, delimiter, overlap)

        for idx, chunk in enumerate(chunks):
            chunk_with_filename = f"File: {file_name_without_extension}\n\n{chunk} "
            user_input = command + "\nNew chunk:\n" + chunk_with_filename

            retries = 3
            response = None
            for attempt in range(retries):
                response = run(user_input, chunk_idx=idx)
                if response:
                    break
                logger.warning(f"Empty response for chunk {idx + 1}, retrying ({attempt + 1}/{retries})...")

            if response:
                if isinstance(response, list) and response:
                    # Add metadata and context
                    for item in response:
                        if isinstance(item, dict):
                            item["metadata"] = file_name_without_extension
                            item["context"] = chunk
                    
                    # Save the chunked output in FT_Dataset folder
                    output_file_path = os.path.join(output_folder, f"{file_name_without_extension}_chunk_{idx + 1}.json")
                    save_to_json(response, output_file_path)

                    # Save internal and visible history
                    history['internal'].extend([f"Q: {item['question']} A: {item['answer']}" for item in response if isinstance(item, dict)])
                    history['visible'].extend([item for item in response if isinstance(item, dict)])
                else:
                    logger.warning(f"Unexpected or empty response format for chunk {idx + 1}: {response}")
            else:
                logger.warning(f"No valid response for chunk {idx + 1}, skipping saving JSON.")

        # Reset history for the next file
        history['internal'].clear()
        history['visible'].clear()
        display_static_status_bar(f"Finished processing file {file_name_without_extension}.")

def main():
    """Main entry point of the script."""
    folder_path = ask_for_folder()
    method, delimiter, max_length, overlap = get_chunking_option()

    # Process files in the selected folder
    process_folder_with_status_bar(folder_path, method, delimiter, max_length, overlap)

if __name__ == "__main__":
    main()
