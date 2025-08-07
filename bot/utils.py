import logging
from io import BytesIO
from typing import Optional
import requests
import json
from datetime import datetime

from PyPDF2 import PdfReader
import docx

logger = logging.getLogger(__name__)

class FileProcessor:
    """Handle file processing and text extraction"""
    
    async def extract_text(self, file_bytes: bytes, filename: str) -> str:
        """Extract text from various file formats"""
        try:
            if filename.endswith('.pdf'):
                return self.extract_pdf_text(file_bytes)
            elif filename.endswith('.txt'):
                return file_bytes.decode('utf-8', errors='ignore')
            elif filename.endswith(('.docx', '.doc')):
                return self.extract_docx_text(file_bytes)
            else:
                raise ValueError(f"Unsupported file format: {filename}")
        except Exception as e:
            logger.error(f"Text extraction error for {filename}: {e}")
            return ""
    
    def extract_pdf_text(self, file_bytes: bytes) -> str:
        """Extract text from PDF file"""
        try:
            pdf_reader = PdfReader(BytesIO(file_bytes))
            text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return ""
    
    def extract_docx_text(self, file_bytes: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(BytesIO(file_bytes))
            text = ""
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            return ""
