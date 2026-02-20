from pathlib import Path
from typing import List, Optional, Dict, Any
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from config import config

class VectorStoreService:
    def __init__(self):
        self.embeddings = None
        self.vector_store = None
        self.is_initialized = False
        
    def initialize(self):
        if self.is_initialized:
            return
        print("[VectorStore] Initializing embeddings model...")
        self.embeddings = HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL, model_kwargs={"device": "cpu"})
        self.is_initialized = True
        print("[VectorStore] Embeddings model loaded")
        
    def load_or_create_vectorstore(self, force_rebuild: bool = False):
        self.initialize()
        index_path = config.VECTOR_STORE_PATH
        index_file = index_path / "index.faiss"
        if not force_rebuild and index_file.exists():
            print("[VectorStore] Loading existing vector store...")
            try:
                self.vector_store = FAISS.load_local(str(index_path), self.embeddings, allow_dangerous_deserialization=True)
                print(f"[VectorStore] Loaded vector store with {self.vector_store.index.ntotal} documents")
                return True
            except Exception as e:
                print(f"[VectorStore] Error loading vector store: {e}")
        print("[VectorStore] Creating new vector store...")
        self.vector_store = FAISS.from_texts(["N.A.T. AI Assistant (Natasha) is ready."], self.embeddings)
        self.save_vectorstore()
        return True
    
    def add_documents(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> bool:
        if not self.vector_store:
            self.load_or_create_vectorstore()
        try:
            self.vector_store.add_texts(texts, metadatas)
            self.save_vectorstore()
            print(f"[VectorStore] Added {len(texts)} documents")
            return True
        except Exception as e:
            print(f"[VectorStore] Error adding documents: {e}")
            return False
    
    def add_learning_files(self) -> Dict[str, Any]:
        learning_path = config.LEARNING_DATA_PATH
        if not learning_path.exists():
            print(f"[VectorStore] Learning path does not exist: {learning_path}")
            return {"success": False, "message": "Learning path not found"}
        all_texts = []
        sources = []
        print(f"[VectorStore] Loading learning files from {learning_path}")
        for file_path in learning_path.glob("*.txt"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip():
                        all_texts.append(content)
                        sources.append(file_path.name)
                        print(f"[VectorStore] Loaded: {file_path.name} ({len(content)} chars)")
            except Exception as e:
                print(f"[VectorStore] Error reading {file_path.name}: {e}")
        if all_texts:
            self.load_or_create_vectorstore()
            existing_count = self.vector_store.index.ntotal if self.vector_store else 0
            self.add_documents(all_texts)
            new_count = self.vector_store.index.ntotal if self.vector_store else 0
            return {"success": True, "documents_added": len(all_texts), "total_documents": new_count, "sources": sources}
        return {"success": False, "message": "No learning files found"}
    
    def similarity_search(self, query: str, k: int = 3) -> List[Document]:
        if not self.vector_store:
            self.load_or_create_vectorstore()
        try:
            return self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            print(f"[VectorStore] Error in similarity search: {e}")
            return []
    
    def get_relevant_context(self, query: str, max_length: int = 2000) -> str:
        docs = self.similarity_search(query, k=5)
        context_parts = []
        current_length = 0
        for doc in docs:
            content = doc.page_content
            if current_length + len(content) <= max_length:
                context_parts.append(content)
                current_length += len(content)
        return "\n\n".join(context_parts)
    
    def save_vectorstore(self):
        if not self.vector_store:
            return
        try:
            config.VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
            self.vector_store.save_local(str(config.VECTOR_STORE_PATH))
            print(f"[VectorStore] Saved to {config.VECTOR_STORE_PATH}")
        except Exception as e:
            print(f"[VectorStore] Error saving: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        if not self.vector_store:
            self.load_or_create_vectorstore()
        doc_count = self.vector_store.index.ntotal if self.vector_store else 0
        return {"loaded": self.is_initialized, "document_count": doc_count, "model": config.EMBEDDING_MODEL, "path": str(config.VECTOR_STORE_PATH)}

vector_store_service = VectorStoreService()
