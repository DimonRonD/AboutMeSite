import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from rag_service import RagService


def main():
    app = create_app()
    with app.app_context():
        rag_service = RagService(app.config)
        indexed_count = rag_service.index_source_documents()
        print(f"Indexed documents: {indexed_count}")


if __name__ == "__main__":
    main()
