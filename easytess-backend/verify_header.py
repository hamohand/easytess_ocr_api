from app.services.pdf_extractor import extract_pdf
import json

def test():
    pdf_path = "Extract[2].pdf"
    print(f"Extraction depuis {pdf_path}")
    content, stats = extract_pdf(pdf_path, strategy="auto", include_metadata=True)
    
    tables = [b for b in content if b["type"] == "tableau"]
    for t in tables:
        metadata = t.get("metadata", {})
        print(f"Tableau {t['numero']} sur page {t['page']}:")
        print(f"  a_entete: {metadata.get('a_entete')}")
        print(f"  entetes: {metadata.get('entetes')}")
        print("---")

if __name__ == "__main__":
    test()
