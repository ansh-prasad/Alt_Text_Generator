from docx import Document
import os

def extract_images_from_docx(doc_path):
    doc = Document(doc_path)
    image_paths = []

    for rel in doc.part.rels:
        if "image" in doc.part.rels[rel].target_ref:
            image_part = doc.part.rels[rel].target_part
            image_bytes = image_part.blob

            image_filename = f"media/uploads/{image_part.partname.split('/')[-1]}"
            with open(image_filename, "wb") as img_file:
                img_file.write(image_bytes)
            
            image_paths.append(image_filename)

    return image_paths
