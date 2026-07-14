"""
utils/reports.py
-----------------
MILESTONE 6, Section 1: builds the three export formats (PDF, Excel,
CSV) from a list of Trainee objects, plus the downloadable sample Excel
template used by the Import feature.

Every function here returns an in-memory BytesIO buffer, NOT a file
written to disk. This is deliberate: reports are generated on demand
and streamed straight to the admin's browser download - we don't want
to litter the server's disk with a new report file every time someone
clicks "Export PDF". routes/reports.py sends each buffer back to the
browser with Flask's send_file().
"""

import io
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from utils.security import mask_aadhaar


REPORT_COLUMNS = [
    "Name", "Gender", "Age", "Mobile", "Aadhaar", "Reference ID",
    "Training Date", "Certificate Status",
]


def _trainees_to_rows(trainees):
    """
    Converts a list of SQLAlchemy Trainee objects into a list of plain
    Python dicts matching REPORT_COLUMNS - shared by all three export
    formats so the PDF, Excel, and CSV reports always show EXACTLY the
    same data, in the same order, with no risk of one format silently
    drifting out of sync with the others.
    """
    rows = []
    for t in trainees:
        rows.append({
            "Name": t.full_name,
            "Gender": t.gender,
            "Age": t.age,
            "Mobile": t.mobile_number,
            "Aadhaar": mask_aadhaar(t.aadhaar_number),
            "Reference ID": t.reference_id,
            "Training Date": t.training_date.strftime("%d-%b-%Y") if t.training_date else "",
            "Certificate Status": "Uploaded" if t.certificate_filename else "Pending",
        })
    return rows


def build_excel_report(trainees):
    """
    Builds an .xlsx report using Pandas (DataFrame) with OpenPyXL as the
    underlying engine (Pandas delegates actual .xlsx writing to
    OpenPyXL - this is the standard combination the assignment asked
    for). A summary row with the Generated Date and Total Count is
    appended after the data rows.
    """
    rows = _trainees_to_rows(trainees)
    df = pd.DataFrame(rows, columns=REPORT_COLUMNS)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Trainees")

        worksheet = writer.sheets["Trainees"]
        summary_row = len(df) + 3
        worksheet.cell(row=summary_row, column=1, value="Generated Date:")
        worksheet.cell(row=summary_row, column=2, value=datetime.now().strftime("%d-%b-%Y %I:%M %p"))
        worksheet.cell(row=summary_row + 1, column=1, value="Total Count:")
        worksheet.cell(row=summary_row + 1, column=2, value=len(df))

        # Widen columns a little so the exported file doesn't look
        # cramped the moment someone opens it in Excel.
        for i, column in enumerate(REPORT_COLUMNS, start=1):
            worksheet.column_dimensions[worksheet.cell(row=1, column=i).column_letter].width = max(14, len(column) + 4)

    buffer.seek(0)
    return buffer


def build_csv_report(trainees):
    """
    Builds a .csv report using Pandas' to_csv(). CSV has no concept of
    "extra summary rows in a different style", so we simply append two
    plain rows at the bottom with the same generated-date/total-count
    information the Excel and PDF reports show.
    """
    rows = _trainees_to_rows(trainees)
    df = pd.DataFrame(rows, columns=REPORT_COLUMNS)

    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.write(f"\nGenerated Date:,{datetime.now().strftime('%d-%b-%Y %I:%M %p')}\n")
    buffer.write(f"Total Count:,{len(df)}\n")

    # send_file() needs BYTES, not a text string - encode before handing
    # it back to the route.
    byte_buffer = io.BytesIO(buffer.getvalue().encode("utf-8"))
    byte_buffer.seek(0)
    return byte_buffer


def build_pdf_report(trainees):
    """
    Builds a .pdf report using ReportLab's Platypus layout engine
    (SimpleDocTemplate + Table) - the standard way to build a real
    multi-page table-based PDF report in Python, as opposed to manually
    drawing text at x/y coordinates.

    Landscape A4 is used because this table has several columns - portrait
    orientation would make the text uncomfortably cramped.
    """
    rows = _trainees_to_rows(trainees)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=4)
    subtitle_style = ParagraphStyle("ReportSubtitle", parent=styles["Normal"], textColor=colors.grey, fontSize=9)

    elements = [
        Paragraph("Cyber Awareness Training Portal — Trainee Report", title_style),
        Paragraph(f"Generated Date: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}  |  Total Count: {len(rows)}", subtitle_style),
        Spacer(1, 10),
    ]

    if rows:
        # ReportLab's Table wants a plain list-of-lists, header row
        # first - build that directly from our shared rows structure.
        table_data = [REPORT_COLUMNS] + [[row[col] for col in REPORT_COLUMNS] for row in rows]

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No trainee records available yet.", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def build_sample_import_template():
    """
    Builds the downloadable "Sample Excel Template" for the Import
    feature - just the correct column headers plus ONE example row, so
    the admin can see exactly what format each column expects before
    filling in their own real data.
    """
    sample_row = {
        "Name": "Rahul Sharma",
        "Gender": "Male",
        "Age": 28,
        "Mobile": "9876543210",
        "Aadhaar": "123456789012",
        "Reference ID": "REF001",
        "Training Date": "2026-07-10",
    }
    df = pd.DataFrame([sample_row])

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Trainees")
        worksheet = writer.sheets["Trainees"]
        for i, column in enumerate(df.columns, start=1):
            worksheet.column_dimensions[worksheet.cell(row=1, column=i).column_letter].width = max(14, len(column) + 4)
    buffer.seek(0)
    return buffer
