import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import chromadb
import requests

load_dotenv()

DOCUMENTS_PATH = os.getenv("DOCUMENTS_PATH", "./documents")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./vectordb")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

def get_embedding(text: str) -> list:
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text}
    )
    response.raise_for_status()
    return response.json()["embedding"]

def read_pdf(filepath: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(filepath)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

def read_docx(filepath: str) -> str:
    from docx import Document
    doc = Document(filepath)
    return "\n".join([para.text for para in doc.paragraphs])

def read_txt(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def ingest_documents():
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(
        name="grade12_documents",
        metadata={"hnsw:space": "cosine"}
    )

    documents_path = Path(DOCUMENTS_PATH)
    if not documents_path.exists():
        print(f"Documents folder not found: {DOCUMENTS_PATH}")
        sys.exit(1)

    all_files = []
    for ext in ["*.pdf", "*.docx", "*.txt"]:
        all_files.extend(documents_path.rglob(ext))

    if not all_files:
        print("")
        print("No documents found yet.")
        print("Add PDF, DOCX or TXT files to the documents/ folder then run this script again.")
        print("")
        print("Your document folders are:")
        print(f"  ~/grade12-tutor/documents/past_papers/")
        print(f"  ~/grade12-tutor/documents/curriculum/")
        print(f"  ~/grade12-tutor/documents/memos/")
        print(f"  ~/grade12-tutor/documents/textbooks/")
        print("")
        print("On Windows, your Downloads folder is accessible at:")
        print(f"  /mnt/c/Users/Zboy/Downloads/")
        print("")
        sys.exit(0)

    print(f"Found {len(all_files)} documents to process...")

    for file_path in all_files:
        print(f"\nProcessing: {file_path.name}")
        category = file_path.parent.name

        try:
            if file_path.suffix.lower() == ".pdf":
                text = read_pdf(str(file_path))
            elif file_path.suffix.lower() == ".docx":
                text = read_docx(str(file_path))
            elif file_path.suffix.lower() == ".txt":
                text = read_txt(str(file_path))
            else:
                continue
        except Exception as e:
            print(f"  ERROR reading {file_path.name}: {e}")
            continue

        if not text.strip():
            print(f"  SKIP: {file_path.name} appears empty or unreadable")
            continue

        chunks = chunk_text(text)
        print(f"  Split into {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            chunk_id = f"{file_path.stem}_{i}"
            existing = collection.get(ids=[chunk_id])
            if existing["ids"]:
                continue
            try:
                embedding = get_embedding(chunk)
                collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[{
                        "source": file_path.name,
                        "category": category,
                        "chunk_index": i
                    }]
                )
                print(f"  Stored chunk {i+1}/{len(chunks)}", end="\r")
            except Exception as e:
                print(f"\n  ERROR embedding chunk {i}: {e}")

        print(f"  Done: {file_path.name}                    ")

    total = collection.count()
    print(f"\n✓ Ingestion complete. {total} chunks stored in the vector database.")

if __name__ == "__main__":
    ingest_documents()
