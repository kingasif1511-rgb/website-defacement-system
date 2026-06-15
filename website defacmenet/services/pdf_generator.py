import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_scan_pdf(website, scan_result, filepath):
    """
    Generates a professional PDF defacement scan report.
    Args:
        website: Website DB model instance
        scan_result: ScanResult DB model instance
        filepath: Absolute destination path for the PDF file
    """
    # Create the document template
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles (Premium Security Theme: Dark Slate & Cyan/Red)
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0B0F19'),
        spaceAfter=15
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1F2A38'),
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )
    
    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#374151')
    )
    
    code_style = ParagraphStyle(
        'CodeText',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=6,
        spaceAfter=6
    )

    story = []
    
    # Header Banner / Logo Placeholder
    story.append(Paragraph("WEBSITE DEFACEMENT SCAN REPORT", title_style))
    story.append(Paragraph("System Security Assessment & Integrity Check Log", normal_style))
    story.append(Spacer(1, 0.15 * inch))
    
    # Divider line
    divider = Table([[""]], colWidths=[530])
    divider.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 1.5, colors.HexColor('#6F42C1')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 0.15 * inch))
    
    # Metadata Details Table
    status_color = '#00FF87' if scan_result.status == 'safe' else ('#FF3B30' if scan_result.status == 'defaced' else '#FF9500')
    status_label = scan_result.status.upper()
    
    data = [
        [Paragraph("<b>Website Name:</b>", normal_style), Paragraph(website.name, normal_style)],
        [Paragraph("<b>Target URL:</b>", normal_style), Paragraph(website.url, normal_style)],
        [Paragraph("<b>Scan Timestamp:</b>", normal_style), Paragraph(scan_result.scanned_at.strftime('%Y-%m-%d %H:%M:%S UTC'), normal_style)],
        [Paragraph("<b>Integrity Status:</b>", normal_style), Paragraph(f"<font color='{status_color}'><b>{status_label}</b></font>", normal_style)],
        [Paragraph("<b>Change Severity:</b>", normal_style), Paragraph(scan_result.severity or "N/A", normal_style)],
        [Paragraph("<b>Response Speed:</b>", normal_style), Paragraph(f"{scan_result.duration_ms} ms", normal_style)],
    ]
    
    meta_table = Table(data, colWidths=[130, 400])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.2 * inch))
    
    # Summary of findings
    story.append(Paragraph("Executive Summary", section_heading))
    if scan_result.status == 'safe':
        summary_text = (
            "The monitoring engine successfully scanned the target URL. No modifications were "
            "detected when compared to the active baseline. The current SHA-256 hash matches the "
            "registered baseline. No further administrative action is required."
        )
    elif scan_result.status == 'defaced':
        summary_text = (
            f"<b>CRITICAL ALERT:</b> The monitoring engine detected unauthorized modifications on the website. "
            f"The severity of this incident has been marked as <b>{scan_result.severity}</b>. "
            f"The differences between the baseline configuration and current state have been logged. "
            f"See details in the difference report section below. Review baseline configuration immediately."
        )
    else:
        summary_text = (
            f"<b>SCAN SYSTEM ERROR:</b> The scanner was unable to retrieve the target webpage during this cycle. "
            f"Details of the HTTP request or timeout error are recorded in the error log: {scan_result.diff_report}."
        )
    
    story.append(Paragraph(summary_text, normal_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Diff analysis if defaced
    if scan_result.status == 'defaced' and scan_result.diff_report:
        story.append(Paragraph("Detected Differences (Unified Diff)", section_heading))
        story.append(Paragraph("The following snippet highlights the line-by-line differences between the original baseline (-) and current scan (+):", normal_style))
        story.append(Spacer(1, 0.05 * inch))
        
        # Limit diff output in PDF to prevent huge documents
        diff_lines = scan_result.diff_report.splitlines()
        max_lines = 40
        if len(diff_lines) > max_lines:
            truncated_diff = "\n".join(diff_lines[:max_lines]) + "\n\n[... Diff Truncated due to size ...]"
        else:
            truncated_diff = scan_result.diff_report
            
        # Format the diff block
        diff_cell = Paragraph(truncated_diff.replace('\n', '<br/>').replace(' ', '&nbsp;').replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;'), code_style)
        
        diff_table = Table([[diff_cell]], colWidths=[530])
        diff_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        
        # Add to story using KeepTogether to keep it clean if possible
        story.append(KeepTogether([diff_table]))
        story.append(Spacer(1, 0.2 * inch))
        
    # Security Recommendations
    story.append(Paragraph("Security Recommendations", section_heading))
    recommendations = (
        "1. If this change was authorized, access the dashboard to **Update Baseline** for this website.<br/>"
        "2. If this change was unauthorized, perform security audits of your web server and CMS logs.<br/>"
        "3. Check for SQL Injection (SQLi), Cross-Site Scripting (XSS), or compromised server credentials.<br/>"
        "4. Restore the website contents from a clean off-site backup."
    )
    story.append(Paragraph(recommendations, normal_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Footer info
    story.append(Paragraph("<font size='8' color='#9CA3AF'>Report compiled automatically by Antigravity Website Defacement Monitor.</font>", normal_style))
    
    # Build document
    doc.build(story)
