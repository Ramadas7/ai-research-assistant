from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import Config

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=Config.CHUNK_SIZE,
    chunk_overlap=Config.CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_document(raw_chunks: list[dict]) -> list[dict]:
    """
    raw_chunks come from document_loader.extract_pdf_content()['chunks'].
    Only 'text' chunks get split further - tables and image descriptions are
    usually already a coherent, self-contained unit, so splitting them would
    just break a table in half or cut a figure description mid-sentence.
    """
    final_chunks = []
    for raw in raw_chunks:
        if raw["type"] == "text" and len(raw["content"]) > Config.CHUNK_SIZE:
            pieces = _splitter.split_text(raw["content"])
            for piece in pieces:
                final_chunks.append({**raw, "content": piece})
        else:
            final_chunks.append(raw)
    return final_chunks
