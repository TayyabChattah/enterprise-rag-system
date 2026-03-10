import io
from pathlib import Path
from pypdf import PdfReader
import docx

def extract_text_from_file(file_input) -> str:
    """
    Extract text from a file path OR a file-like object (Django upload).
    """
    # Determine the suffix
    if hasattr(file_input, 'name'):
        suffix = Path(file_input.name).suffix.lower()
    else:
        suffix = Path(file_input).suffix.lower()

    if suffix == ".pdf":
        # Handle both path string and file object
        reader = PdfReader(file_input)
        return "".join([page.extract_text() or "" for page in reader.pages])

    elif suffix == ".docx":
        # python-docx needs a stream for file objects
        doc_file = io.BytesIO(file_input.read()) if hasattr(file_input, 'read') else file_input
        document = docx.Document(doc_file)
        return "\n".join([p.text for p in document.paragraphs])

    elif suffix == ".txt":
        if hasattr(file_input, 'read'):
            return file_input.read().decode('utf-8')
        with open(file_input, "r", encoding="utf-8") as f:
            return f.read()
            
    raise ValueError(f"Unsupported format: {suffix}")



from langchain_text_splitters import RecursiveCharacterTextSplitter


def create_chunks(text: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    return splitter.split_text(text)
