import logging
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable

logger = logging.getLogger(__name__)

class PDFGenerator:
    """Generate professional PDF resumes"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.custom_styles = {
            'ResumeTitle': ParagraphStyle(
                'ResumeTitle',
                parent=self.styles['Title'],
                fontSize=18,
                textColor=colors.darkblue,
                alignment=1,  # Center
                spaceAfter=0.2*inch
            ),
            'SectionHeader': ParagraphStyle(
                'SectionHeader',
                parent=self.styles['Heading2'],
                fontSize=14,
                textColor=colors.darkblue,
                spaceBefore=0.15*inch,
                spaceAfter=0.1*inch,
                borderWidth=1,
                borderColor=colors.darkblue,
                borderPadding=3
            ),
            'ContactInfo': ParagraphStyle(
                'ContactInfo',
                parent=self.styles['Normal'],
                fontSize=10,
                alignment=1,  # Center
                spaceAfter=0.15*inch
            ),
            'ResumeBody': ParagraphStyle(
                'ResumeBody',
                parent=self.styles['Normal'],
                fontSize=11,
                spaceAfter=0.08*inch,
                leftIndent=0.2*inch
            ),
            'BulletPoint': ParagraphStyle(
                'BulletPoint',
                parent=self.styles['Normal'],
                fontSize=10,
                leftIndent=0.3*inch,
                bulletIndent=0.1*inch,
                spaceAfter=0.05*inch
            )
        }
    
    async def generate_resume_pdf(self, resume_content: str, user_name: str) -> BytesIO:
        """Generate professional PDF from resume content"""
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch
            )
            
            # Build content
            story = []
            
            # Add header with branding
            story.extend(self.create_header(user_name))
            
            # Process resume content
            story.extend(self.process_resume_content(resume_content))
            
            # Add footer
            story.extend(self.create_footer())
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            return buffer
            
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            raise Exception("Failed to generate PDF")
    
    def create_header(self, user_name: str) -> list:
        """Create PDF header"""
        header = []
        
        # Add subtle ATS branding
        ats_brand = Paragraph(
            "Surya's ATS-Optimized Professional Resume",
            self.custom_styles['ContactInfo']
        )
        header.append(ats_brand)
        header.append(Spacer(1, 0.1*inch))
        
        # Add separator line
        header.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        header.append(Spacer(1, 0.2*inch))
        
        return header
    
    def process_resume_content(self, content: str) -> list:
        """Process and format resume content"""
        story = []
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if not line:
                story.append(Spacer(1, 0.05*inch))
                continue
            
            # Check if line is a section header
            if self.is_section_header(line):
                if current_section:
                    story.append(Spacer(1, 0.1*inch))
                
                story.append(Paragraph(line.upper(), self.custom_styles['SectionHeader']))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
                current_section = line
                
            elif line.startswith('•') or line.startswith('-') or line.startswith('*'):
                # Bullet points
                clean_line = line[1:].strip()
                story.append(Paragraph(f"• {clean_line}", self.custom_styles['BulletPoint']))
                
            else:
                # Regular content
                if len(line) > 100:  # Long paragraphs
                    story.append(Paragraph(line, self.custom_styles['ResumeBody']))
                else:  # Short lines (likely contact info or titles)
                    if current_section is None:  # Contact info at top
                        story.append(Paragraph(line, self.custom_styles['ContactInfo']))
                    else:
                        story.append(Paragraph(line, self.custom_styles['ResumeBody']))
        
        return story
    
    def is_section_header(self, line: str) -> bool:
        """Check if line is a section header"""
        section_keywords = [
            'SUMMARY', 'PROFILE', 'OBJECTIVE', 'EXPERIENCE', 'EMPLOYMENT',
            'WORK EXPERIENCE', 'PROFESSIONAL EXPERIENCE', 'EDUCATION',
            'SKILLS', 'TECHNICAL SKILLS', 'CORE COMPETENCIES', 'CERTIFICATIONS',
            'ACHIEVEMENTS', 'PROJECTS', 'CONTACT', 'PERSONAL DETAILS'
        ]
        
        line_upper = line.upper().strip()
        
        # Check exact matches
        if line_upper in section_keywords:
            return True
        
        # Check if line contains section keywords and is short enough
        if len(line_upper) <= 30:
            for keyword in section_keywords:
                if keyword in line_upper:
                    return True
        
        return False
    
    def create_footer(self) -> list:
        """Create PDF footer"""
        footer = []
        
        footer.append(Spacer(1, 0.3*inch))
        footer.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        
        footer_text = f"Generated on {datetime.now().strftime('%B %d, %Y')} • Surya ATS Resume Bot • 98% ATS Compatibility"
        footer.append(Paragraph(footer_text, self.custom_styles['ContactInfo']))
        
        return footer