import os
from flask import Flask, request, render_template, redirect
import vertexai
from vertexai.preview.generative_models import GenerativeModel
import fitz  # PyMuPDF
import docx  # python-docx
from pdf2image import convert_from_path
import pytesseract

app = Flask(__name__)

# Initialize Vertex AI
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
vertexai.init(project="finalproject-458201", location="us-central1")
model = GenerativeModel(model_name="gemini-1.5-flash")

# Text extraction functions
def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    return "\n".join(page.get_text() for page in doc)

def extract_text_from_scanned_pdf(file_path):
    images = convert_from_path(file_path)
    text = ""
    for image in images:
        text += pytesseract.image_to_string(image) + "\n"
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join(para.text for para in doc.paragraphs)

def extract_text_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        files = request.files.getlist("files")
        if not files:
            return redirect(request.url)

        all_text = ""
        for file in files:
            if file.filename == "":
                continue

            file_path = os.path.join("uploads", file.filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)

            try:
                if file.filename.endswith(".pdf"):
                    try:
                        text = extract_text_from_pdf(file_path)
                    except:
                        text = extract_text_from_scanned_pdf(file_path)
                elif file.filename.endswith(".docx"):
                    text = extract_text_from_docx(file_path)
                elif file.filename.endswith(".txt"):
                    text = extract_text_from_txt(file_path)
                else:
                    print(f"Skipped unsupported file: {file.filename}")
                    continue
                # Label the text with the filename
                all_text += f"\n--- Start of {file.filename} ---\n{text}\n--- End of {file.filename} ---\n"

            except Exception as e:
                print(f"Error processing {file.filename}: {e}")

        if not all_text:
            return "No supported files found. Please upload PDF, DOCX, or TXT files."

        return render_template("chat.html", document_text=all_text, user_input="", response="")

    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    document_text = request.form.get("document_text", "")
    user_input = request.form.get("user_input", "")

    prompt = (
        f"You are an assistant helping a user understand the contents of multiple documents.\n"
        f"Each document is labeled with its filename.\n"
        f"Use the labels to reference where the information comes from.\n\n"
        f"{document_text}\n\n"
        f"User's question: {user_input}"
    )

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 2048,
        },
    )

    return render_template("chat.html", document_text=document_text, user_input=user_input, response=response.text.strip())

if __name__ == "__main__":
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.run(debug=True)
