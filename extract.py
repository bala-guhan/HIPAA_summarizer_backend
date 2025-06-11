import time
from typing import Dict, Any
import fitz
from fastapi import HTTPException


def extract_pdf_content(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extract all content from PDF using PyMuPDF
    
    Args:
        pdf_bytes: PDF file as bytes
        
    Returns:
        Dictionary containing extracted content
    """
    try:
        # Open PDF from bytes
        start = time.time()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Initialize result dictionary
        result = {
            "text": "",
            "pages": [],
            "metadata": {},
            "page_count": len(doc),
            "tables": []
        }
        
        # Extract metadata
        result["metadata"] = doc.metadata
        
        # Extract content from each page
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text from page
            page_text = page.get_text()
            result["text"] += page_text + "\n"
            
            # Store page-specific information
            page_info = {
                "page_number": page_num + 1,
                "text": page_text,
                "char_count": len(page_text),
                "word_count": len(page_text.split()) if page_text else 0
            }
            
            # Try to extract tables from page
            try:
                page_tables = page.find_tables()
                if page_tables:
                    page_tables_data = []
                    for table_num, table in enumerate(page_tables):
                        table_data = table.extract()
                        page_tables_data.append({
                            "table_number": table_num + 1,
                            "data": table_data,
                            "rows": len(table_data),
                            "columns": len(table_data[0]) if table_data else 0
                        })
                    page_info["tables"] = page_tables_data
                    result["tables"].extend(page_tables_data)
            except Exception as e:
                # If table extraction fails, continue without tables
                page_info["tables"] = []
            
            result["pages"].append(page_info)
        
        processing_duration = time.time() - start
        # Clean up
        doc.close()
        
        # Add summary statistics
        result["summary"] = {
            "total_characters": len(result["text"]),
            "total_words": len(result["text"].split()) if result["text"] else 0,
            "total_tables": len(result["tables"]),
            "pages_with_content": sum(1 for page in result["pages"] if page["char_count"] > 0)
        }
        
        return result, processing_duration
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")