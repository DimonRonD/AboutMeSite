import os
from typing import Iterable

import chromadb
from chromadb.utils import embedding_functions


class RagService:
    def __init__(self, app_config):
        self._config = app_config
        chroma_api_key = app_config.get("CHROMA_OPENAI_API_KEY") or app_config.get("OPENAI_API_KEY")
        if not chroma_api_key:
            raise ValueError(
                "OpenAI API key for Chroma is not set. Configure CHROMA_OPENAI_API_KEY "
                "or OPENAI_API_KEY."
            )
        self._client = chromadb.PersistentClient(path=app_config["CHROMA_DB_PATH"])
        self._collection = self._client.get_or_create_collection(
            name=app_config["CHROMA_COLLECTION_NAME"],
            embedding_function=embedding_functions.OpenAIEmbeddingFunction(
                api_key=chroma_api_key,
                model_name=app_config["OPENAI_EMBEDDING_MODEL"],
            ),
        )

    def search(self, question: str, top_k: int | None = None) -> list[str]:
        if not question.strip():
            return []
        effective_top_k = top_k or self._config["RAG_TOP_K"]
        results = self._collection.query(query_texts=[question], n_results=effective_top_k)
        docs = results.get("documents", [])
        if not docs:
            return []
        return docs[0]

    def index_source_documents(self) -> int:
        source_dir = self._config["RAG_SOURCE_DIR"]
        if not os.path.isdir(source_dir):
            return 0

        docs: list[str] = []
        ids: list[str] = []
        metas: list[dict] = []
        for filepath in _iter_text_files(source_dir):
            with open(filepath, "r", encoding="utf-8") as source_file:
                content = source_file.read().strip()
            if not content:
                continue
            doc_id = filepath.replace("\\", "/")
            docs.append(content)
            ids.append(doc_id)
            metas.append({"source": doc_id})

        if not docs:
            return 0

        existing_ids = set(self._collection.get(include=[], limit=100000).get("ids", []))
        new_docs = []
        new_ids = []
        new_metas = []
        for idx, doc_id in enumerate(ids):
            if doc_id in existing_ids:
                continue
            new_docs.append(docs[idx])
            new_ids.append(doc_id)
            new_metas.append(metas[idx])

        if not new_docs:
            return 0

        self._collection.add(documents=new_docs, ids=new_ids, metadatas=new_metas)
        return len(new_docs)


def _iter_text_files(base_dir: str) -> Iterable[str]:
    for root, _, files in os.walk(base_dir):
        for filename in files:
            if filename.lower().endswith((".txt", ".md", ".rst")):
                yield os.path.join(root, filename)
