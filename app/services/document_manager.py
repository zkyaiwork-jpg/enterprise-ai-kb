import logging
from app.core.paths import DOCUMENTS_DIR
from app.services.vector_store import collection

DOCUMENT_DIR = DOCUMENTS_DIR
logger = logging.getLogger(__name__)


def list_documents():

    DOCUMENT_DIR.mkdir(
        exist_ok=True
    )

    files = []

    for file in DOCUMENT_DIR.iterdir():

        if file.is_file():

            files.append(
                {
                    "filename": file.name,
                    "size": file.stat().st_size
                }
            )

    return files



def delete_document(filename: str):

    result = collection.get()

    logger.info("Document deletion lookup completed vector_count=%s", len(result.get("ids") or []))

    ids = result["ids"]

    if ids:
        collection.delete(
            ids=ids
        )


    return {
        "delete_count": 0
    }
