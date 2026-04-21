import os
import tempfile
from pathlib import Path
from fpdf import FPDF
from bidi.algorithm import get_display
from google import genai
from google.genai import types

FONT_PATH = str(Path(__file__).parent.parent / "fonts" / "ArialUnicode.ttf")

SUMMARY_PROMPT = """סכם את המסמך הזה בעברית בצורה מובנית ומפורטת.
החזר את הסיכום בפורמט הבא בדיוק, כל נקודה בשורה נפרדת:

כותרת: [שם הנושא הראשי]

נושאים עיקריים:
- [נושא 1]
- [נושא 2]
- [נושא 3]
- [המשך לפי הצורך]

סיכום מפורט:
[שלוש עד חמש שורות המסכמות את התוכן החשוב]

מושגים מרכזיים:
- [מושג 1] - [הסבר קצר]
- [מושג 2] - [הסבר קצר]
- [המשך לפי הצורך]

חשוב: כתוב כל נקודה בשורה משלה. אל תשתמש בתווים מיוחדים כמו כוכביות או נקודות מיוחדות."""


def summarize_pdf_with_gemini(pdf_path: str) -> str:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            SUMMARY_PROMPT
        ]
    )

    print(f"📄 Gemini summary:\n{response.text}\n---")
    return response.text


def build_summary_pdf(summary_text: str, output_path: str):
    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()
    pdf.add_font("ArialUnicode", "", FONT_PATH, uni=True)
    pdf.add_font("ArialUnicode", "B", FONT_PATH, uni=True)

    effective_width = pdf.w - pdf.l_margin - pdf.r_margin

    # Page title
    pdf.set_font("ArialUnicode", "B", 18)
    pdf.cell(0, 14, get_display("סיכום מסמך"), ln=True, align="R")
    pdf.set_draw_color(80, 80, 80)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

    for line in summary_text.splitlines():
        line = line.strip()
        if not line:
            pdf.ln(2)
            continue

        # Section headers end with ":"
        if line.endswith(":") and len(line) < 50:
            pdf.ln(3)
            pdf.set_font("ArialUnicode", "B", 13)
            pdf.cell(0, 9, get_display(line), ln=True, align="R")
            pdf.set_font("ArialUnicode", "", 11)

        # Bullet lines starting with "-"
        elif line.startswith("-"):
            content = line[1:].strip()
            display = get_display(content)
            # Indent bullet from right
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(effective_width - 5, 7, "  " + display, align="R")

        else:
            pdf.set_font("ArialUnicode", "", 11)
            pdf.multi_cell(effective_width, 7, get_display(line), align="R")

    pdf.output(output_path)


def process_lecture_pdf(pdf_path: str) -> str:
    summary_text = summarize_pdf_with_gemini(pdf_path)

    output_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    output_path = output_file.name
    output_file.close()

    build_summary_pdf(summary_text, output_path)
    return output_path
