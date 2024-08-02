import streamlit as st
from io import BytesIO
from PyPDF2 import PdfReader
from streamlit_option_menu import option_menu
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import os
from PIL import Image
import pytesseract as pyt
pyt.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
import fitz  # PyMuPDF
from time import sleep
from transformers import pipeline, logging as transformers_logging

# Suppress warnings from transformers library
transformers_logging.set_verbosity_error()

# Set up summarization pipeline
def create_summarizer():
    try:
        summarizer = pipeline("summarization")
        return summarizer
    except Exception as e:
        st.error(f"Error initializing summarizer: {e}")
        return None

st.set_page_config(page_title="PDF Sensitive Information Masker", layout="wide")

# Custom CSS for additional styling
st.markdown("""
    <style>
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
        padding: 1rem;
    }
    .stProgress .st-bo {
        background-color: #0d6efd;
    }
    .accordion-button:not(.collapsed) {
        color: #0d6efd;
        background-color: #e7f1ff;
    }
    .typing-animation {
        width: 100%;
        white-space: nowrap;
        overflow: hidden;
        border-right: 0.15em solid orange;
        animation:
            typing 3.5s steps(40, end),
            blink-caret 0.75s step-end infinite;
        display: block;
    }

    @keyframes typing {
        from { width: 0; }
        to { width: 100%; }
    }

    @keyframes blink-caret {
        from, to { border-color: transparent; }
        50% { border-color: orange; }
    }
    </style>
    """, unsafe_allow_html=True)

if 'selected' not in st.session_state:
    st.session_state.selected = "Home"

with st.sidebar:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.image("Desktop/logo.png", width=250, use_column_width=True)
    st.markdown("<h1 style='text-align: center; font-size: 150%; font-weight: bold;'>PDF SENSITIVE INFORMATION MASKER</h1>", unsafe_allow_html=True)
    selected = option_menu(
        menu_title="Main Menu",
        options=["Home", "Optical Character Recognition", "Text Summarizer"],
        icons=["house", "cloud-upload", "book"],
        default_index=0,
    )
    st.session_state.selected = selected

def extract_and_concatenate_text(pdf_file):
    reader = PdfReader(pdf_file)
    all_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            words = text.split()
            concatenated_text = ' '.join(words)
            all_text.append(concatenated_text)
    return '\n'.join(all_text)

def enumerate_words(text):
    words = text.split()
    enumerated_dict = {i + 1: word for i, word in enumerate(words)}
    return enumerated_dict

def find_phone_numbers(enumerated_dict):
    phone_number_index = []
    phone_number_pattern = re.compile(r'^(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}$')
    for key, value in enumerated_dict.items():
        if phone_number_pattern.search(value):
            phone_number_index.append(key)
    return phone_number_index

def find_emails(enumerated_dict):
    email_index = []
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    for key, value in enumerated_dict.items():
        if email_pattern.search(value):
            email_index.append(key)
    return email_index

def find_number_sequences(enumerated_dict):
    number_index = []
    sequence_pattern = re.compile(r'\b\d{4} \d{4} \d{4}\b')
    phone_pattern = re.compile(r'\b\d{10}\b')
    for key, value in enumerated_dict.items():
        if sequence_pattern.search(value) or phone_pattern.search(value):
            number_index.append(key)
    return number_index

def redact_words_with_numbers(enumerated_dict):
    number_pattern = re.compile(r'\d')
    redacted_indices = []
    for key, value in enumerated_dict.items():
        if number_pattern.search(value):
            redacted_indices.append(key)
    return redacted_indices

def redacted(text, indices):
    words = text.split()
    for index in indices:
        words[index - 1] = "[REDACTED]"
    return ' '.join(words)

def create_pdf(text_to_insert, file_name):
    doc = SimpleDocTemplate(file_name, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(text_to_insert, styles["Normal"]))
    doc.build(story)

def extract_images_from_pdf(pdf_file):
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    images = []
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]
            image = Image.open(BytesIO(image_bytes))
            images.append(image)
    pdf_document.close()
    return images

def ocr_image(image):
    text = pyt.image_to_string(image)
    return text

def extract_text_from_pdf_images(pdf_file):
    images = extract_images_from_pdf(pdf_file)
    texts = [ocr_image(image) for image in images]
    return " ".join(texts)

# Text summarizer function
def summarize_text(text):
    summarizer = create_summarizer()
    if summarizer:
        try:
            summary = summarizer(text, max_length=200, min_length=50, do_sample=False)
            return summary[0]['summary_text']
        except Exception as e:
            st.error(f"Error summarizing text: {e}")
            return "Summary could not be generated."
    return "Summarizer is not available."

if st.session_state.selected == "Home":
    st.title("Mask Sensitive Information.")

    lines = [
        "PDF Sensitive Information Masker is a web application designed to safeguard your sensitive data.",
        "Our tool utilizes advanced algorithms to identify and obscure sensitive data points.",
        "Ensuring compliance with data privacy regulations and protecting your sensitive information from unauthorized access."
    ]

    for line in lines:
        st.markdown(f"<p class='typing-animation'>{line}</p>", unsafe_allow_html=True)
        sleep(2)  # Add a short delay between lines if needed

    uploaded_files = st.file_uploader("Choose a PDF file", accept_multiple_files=True, type=["pdf"])
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            with st.spinner("Processing..."):
                progress_bar = st.progress(0)
                
                # Simulate time delay for processing
                text = extract_and_concatenate_text(uploaded_file)
                progress_bar.progress(25)
                
                enumerated = enumerate_words(text)
                progress_bar.progress(50)
                
                phone_numbers = find_phone_numbers(enumerated)
                found_sequences = find_number_sequences(enumerated)
                words_and_numbers = redact_words_with_numbers(enumerated)
                emails = find_emails(enumerated)
                progress_bar.progress(75)
                
                redacted_text = redacted(text, phone_numbers + emails + found_sequences + words_and_numbers)
                
                pdf_dir = "pdf_files"
                os.makedirs(pdf_dir, exist_ok=True)
                file_name = os.path.join(pdf_dir, "output.pdf")
                
                create_pdf(redacted_text, file_name)
                progress_bar.progress(100)
                
                st.write("Filename:", uploaded_file.name)
                st.write(text)
                st.title("Sensitive information has been redacted")
                st.success("PDF created successfully!")
                with open(file_name, "rb") as f:
                    st.download_button(
                        label="Download PDF",
                        data=f,
                        file_name="output.pdf",
                        mime="application/pdf"
                    )

if st.session_state.selected == "Optical Character Recognition":
    st.title("PDF OCR Extractor with Pattern Detection")
    uploaded_files = st.file_uploader("Choose a PDF file to run optical character recognition", accept_multiple_files=True)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file is not None:
                with st.spinner("Processing..."):
                    progress_bar = st.progress(0)
                    
                    # Simulate time delay for processing
                    concatenated_text = extract_text_from_pdf_images(uploaded_file)
                    progress_bar.progress(50)
                    
                    enumerated_words = enumerate_words(concatenated_text)
                    phone_indices = find_phone_numbers(enumerated_words)
                    email_indices = find_emails(enumerated_words)
                    sequence_indices = find_number_sequences(enumerated_words)
                    redacted_indices = redact_words_with_numbers(enumerated_words)
                    progress_bar.progress(75)
                    
                    redacted_text = redacted(concatenated_text, redacted_indices)
                    progress_bar.progress(100)
                    
                    with st.expander("View Extracted Text"):
                        st.write(concatenated_text)
                    with st.expander("View Redacted Text"):
                        st.write(redacted_text)
                    with st.expander("View Detected Patterns"):
                        st.write("Phone Number Indices:", phone_indices)
                        st.write("Email Indices:", email_indices)
                        st.write("Number Sequence Indices:", sequence_indices)
                        st.write("Redacted Indices:", redacted_indices)

if st.session_state.selected == "Text Summarizer":
    st.title("Text Summarizer")
    uploaded_files = st.file_uploader("Choose a PDF file to summarize", accept_multiple_files=True, type=["pdf"])
    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file is not None:
                with st.spinner("Processing..."):
                    progress_bar = st.progress(0)
                    
                    # Simulate time delay for processing
                    text = extract_and_concatenate_text(uploaded_file)
                    progress_bar.progress(50)
                    
                    summary = summarize_text(text)
                    progress_bar.progress(100)
                    
                    st.write("Filename:", uploaded_file.name)
                    st.write("Extracted Text:")
                    st.write(text)
                    st.write("Summary:")
                    st.write(summary)
