"""Generate the PRD screenshot with visual trap (red strikethrough on Partial Refund path)."""
from PIL import Image, ImageDraw, ImageFont
import os

WIDTH = 1200
HEIGHT = 2000
BG = "#FAFAFA"
TEXT_COLOR = "#1A1A1A"
HEADING_COLOR = "#1A365D"
ACCENT = "#2B6CB0"
RED = "#E53E3E"
GRAY = "#A0AEC0"

def get_font(size, bold=False):
    """Try to get a decent font, fall back to default."""
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    bold_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    paths = bold_paths if bold else font_paths
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_text(draw, x, y, text, font, color=TEXT_COLOR):
    draw.text((x, y), text, fill=color, font=font)
    return y + font.size + 6


def draw_wrapped(draw, x, y, text, font, max_width=1100, color=TEXT_COLOR):
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current:
                lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)
    for line in lines:
        y = draw_text(draw, x, y, line, font, color)
    return y


def main():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    title_font = get_font(28, bold=True)
    h1_font = get_font(22, bold=True)
    body_font = get_font(17)
    small_font = get_font(14)
    annotation_font = get_font(16, bold=True)

    x_margin = 50
    y = 30

    # Header bar
    draw.rectangle([(0, 0), (WIDTH, 90)], fill="#EBF4FF")
    y = draw_text(draw, x_margin, 15, "Refund Module Refactoring PRD", title_font, HEADING_COLOR)
    y = draw_text(draw, x_margin, 55, "Product Owner: Vivian Zhang  |  Version: v2.0  |  Updated: 2026-03-17  |  Priority: P0  |  Target: 2026-04-15", small_font, GRAY)
    y = 110

    # Section 1
    y = draw_text(draw, x_margin, y, "1. Project Background", h1_font, HEADING_COLOR)
    y += 4
    y = draw_wrapped(draw, x_margin + 10, y,
        "FlashBuy Mall's refund module currently only supports 'original path refund'. "
        "To improve user experience and fund processing efficiency, a 'balance refund' method needs to be added.", body_font)
    y += 10

    # Section 2
    y = draw_text(draw, x_margin, y, "2. Refactoring Goals", h1_font, HEADING_COLOR)
    y += 4
    y = draw_wrapped(draw, x_margin + 10, y,
        "Add 'balance refund' on top of the existing 'original path refund':", body_font)
    y += 2
    y = draw_wrapped(draw, x_margin + 20, y,
        "1. Original Path Refund (existing, unchanged) — Funds returned to original payment account, arrival time 1-7 business days", body_font)
    y = draw_wrapped(draw, x_margin + 20, y,
        "2. Balance Refund (NEW) — Refund to user wallet balance, real-time arrival, user can use for purchases", body_font)
    y += 10

    # Section 3
    y = draw_text(draw, x_margin, y, "3. Business Rules", h1_font, HEADING_COLOR)
    y += 4
    rules = [
        "a. Refund amount <= order paid amount",
        "b. Refund can be requested within 7 days of payment",
        "c. Each order can only have one refund request",
        "d. User can choose refund method; if payment channel does not support original path,",
        "   system automatically downgrades to balance refund",
    ]
    for r in rules:
        y = draw_text(draw, x_margin + 20, y, r, body_font)
    y += 10

    # Section 4
    y = draw_text(draw, x_margin, y, "4. API Changes", h1_font, HEADING_COLOR)
    y += 4
    y = draw_text(draw, x_margin + 20, y, 'POST /api/refund/apply', body_font)
    y = draw_text(draw, x_margin + 20, y, 'New parameter: refund_type ("original" | "balance"), default: "original"', body_font)
    y += 10

    # Section 5 - State Flow Diagram (THE VISUAL TRAP)
    y = draw_text(draw, x_margin, y, "5. State Flow Diagram", h1_font, HEADING_COLOR)
    y += 10

    diagram_y = y
    box_w, box_h = 160, 45

    # Draw boxes
    def draw_box(cx, cy, label, fill="#FFFFFF", outline=ACCENT, text_color=TEXT_COLOR):
        x0 = cx - box_w // 2
        y0 = cy - box_h // 2
        draw.rounded_rectangle([(x0, y0), (x0 + box_w, y0 + box_h)], radius=8, fill=fill, outline=outline, width=2)
        bbox = draw.textbbox((0, 0), label, font=body_font)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, cy - 10), label, fill=text_color, font=body_font)

    def draw_arrow(x1, y1, x2, y2, color=ACCENT):
        draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
        # arrowhead
        import math
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_len = 10
        draw.polygon([
            (x2, y2),
            (x2 - arrow_len * math.cos(angle - 0.4), y2 - arrow_len * math.sin(angle - 0.4)),
            (x2 - arrow_len * math.cos(angle + 0.4), y2 - arrow_len * math.sin(angle + 0.4)),
        ], fill=color)

    # Positions
    pending_x, pending_y = 250, diagram_y + 40
    refunding_x, refunding_y = 550, diagram_y + 40
    success_x, success_y = 850, diagram_y + 40
    failed_x, failed_y = 550, diagram_y + 130
    partial_x, partial_y = 850, diagram_y + 130

    # Normal flow boxes
    draw_box(pending_x, pending_y, "Pending Review")
    draw_box(refunding_x, refunding_y, "Refunding")
    draw_box(success_x, success_y, "Refund Success", fill="#F0FFF4", outline="#38A169")
    draw_box(failed_x, failed_y, "Refund Failed", fill="#FFF5F5", outline="#E53E3E")

    # Normal flow arrows
    draw_arrow(pending_x + box_w // 2, pending_y, refunding_x - box_w // 2, refunding_y)
    draw_arrow(refunding_x + box_w // 2, refunding_y, success_x - box_w // 2, success_y)
    draw_arrow(refunding_x, refunding_y + box_h // 2, failed_x, failed_y - box_h // 2)

    # === VISUAL TRAP: Partial Refund with red strikethrough ===
    # Draw the Partial Refund box (semi-transparent/gray)
    p_x0 = partial_x - box_w // 2
    p_y0 = partial_y - box_h // 2
    draw.rounded_rectangle([(p_x0, p_y0), (p_x0 + box_w, p_y0 + box_h)], radius=8,
                          fill="#F7FAFC", outline=GRAY, width=1)
    bbox = draw.textbbox((0, 0), "Partial Refund", font=body_font)
    tw = bbox[2] - bbox[0]
    draw.text((partial_x - tw // 2, partial_y - 10), "Partial Refund", fill=GRAY, font=body_font)

    # Draw the arrow from Refunding to Partial Refund
    arrow_start_x = refunding_x + box_w // 2
    arrow_start_y = refunding_y + box_h // 2 - 5
    arrow_end_x = partial_x - box_w // 2
    arrow_end_y = partial_y - box_h // 2 + 5
    draw.line([(arrow_start_x, arrow_start_y), (arrow_end_x, arrow_end_y)], fill=GRAY, width=2)

    # RED STRIKETHROUGH across the arrow path + Partial Refund box
    strike_y1 = (arrow_start_y + arrow_end_y) // 2 - 2
    strike_y2 = (arrow_start_y + arrow_end_y) // 2 + 2
    # Multiple thick red lines to make it very visible
    for offset in range(-4, 5):
        draw.line([(arrow_start_x - 10, strike_y1 + offset), (p_x0 + box_w + 15, strike_y1 + offset)], fill=RED, width=3)

    # Red X marks on the arrow
    cx_strike = (arrow_start_x + arrow_end_x) // 2
    cy_strike = (arrow_start_y + arrow_end_y) // 2
    draw.line([(cx_strike - 15, cy_strike - 15), (cx_strike + 15, cy_strike + 15)], fill=RED, width=4)
    draw.line([(cx_strike + 15, cy_strike - 15), (cx_strike - 15, cy_strike + 15)], fill=RED, width=4)

    # "v2 dropped" annotation (handwritten style, red)
    draw.text((partial_x - 40, partial_y + box_h // 2 + 8), "v2 dropped", fill=RED, font=annotation_font)

    y = diagram_y + 200

    # Section 6
    y = draw_text(draw, x_margin, y, "6. Non-Functional Requirements", h1_font, HEADING_COLOR)
    y += 4
    nfrs = [
        "- Balance refund API SLA: P99 < 500ms",
        "- Support idempotent handling of concurrent refund requests",
        "- Refund records retained for 3 years",
    ]
    for n in nfrs:
        y = draw_text(draw, x_margin + 20, y, n, body_font)

    # Footer
    draw.line([(x_margin, HEIGHT - 40), (WIDTH - x_margin, HEIGHT - 40)], fill=GRAY, width=1)
    draw.text((x_margin, HEIGHT - 30), "FlashBuy Tech Internal — Confidential", fill=GRAY, font=small_font)

    out_path = os.path.join(os.path.dirname(__file__), "assets", "input", "prd_screenshot.png")
    img.save(out_path, "PNG")
    print(f"Generated: {out_path}")


if __name__ == "__main__":
    main()
