import base64
from html import escape
from pathlib import Path


PERMIT_FILE_NAME = "道路使用許可.pdf"


def get_permit_pdf_path(base_dir, restriction_id):
    return Path(base_dir) / "data" / "documents" / str(restriction_id) / PERMIT_FILE_NAME


def make_permit_link_html(base_dir, restriction_id):
    permit_path = get_permit_pdf_path(base_dir, restriction_id)

    if not permit_path.exists():
        return "未登録"

    pdf_data = base64.b64encode(permit_path.read_bytes()).decode("ascii")
    pdf_href = f"data:application/pdf;base64,{pdf_data}"

    return (
        f'<a href="{pdf_href}" target="_blank" rel="noopener noreferrer">'
        f'{escape(PERMIT_FILE_NAME)}</a>'
    )
