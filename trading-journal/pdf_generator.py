import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.platypus.flowables import KeepTogether
from PIL import Image as PILImage


def generate_trade_pdf(trade_data: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        name='TitleCustom',
        parent=styles['Title'],
        fontSize=22,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#16213e'),
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderPadding=0,
    ))

    styles.add(ParagraphStyle(
        name='SubHeader',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=colors.HexColor('#0f3460'),
        spaceBefore=8,
        spaceAfter=4,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='BodyCustom',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#2d2d2d'),
        alignment=TA_JUSTIFY
    ))

    styles.add(ParagraphStyle(
        name='SmallNote',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#666666'),
        leading=10
    ))

    styles.add(ParagraphStyle(
        name='OutcomeWin',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#27ae60'),
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name='OutcomeLoss',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#e74c3c'),
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name='OutcomeMissed',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#f39c12'),
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    ))

    elements = []

    # ─── TITLE PAGE ───
    elements.append(Spacer(1, 60))
    elements.append(Paragraph("SMC TRADING JOURNAL", styles['TitleCustom']))
    elements.append(Spacer(1, 10))

    elements.append(HRFlowable(
        width="80%", thickness=2,
        color=colors.HexColor('#1a1a2e'),
        spaceAfter=10, spaceBefore=4
    ))

    pair_text = f"{trade_data.get('pair', 'N/A')} — {trade_data.get('direction', '')} Trade"
    elements.append(Paragraph(pair_text, ParagraphStyle(
        'PairTitle', parent=styles['Title'], fontSize=18,
        textColor=colors.HexColor('#0f3460')
    )))

    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        f"Date: {trade_data.get('date', 'N/A')} | Session: {trade_data.get('session', 'N/A')}",
        ParagraphStyle('DateLine', parent=styles['Normal'],
                       fontSize=11, alignment=TA_CENTER,
                       textColor=colors.HexColor('#555555'))
    ))

    elements.append(Spacer(1, 20))

    # Outcome badge
    outcome = trade_data.get('outcome', 'N/A')
    outcome_style = 'OutcomeWin' if outcome == 'Win' else \
        'OutcomeLoss' if outcome == 'Loss' else 'OutcomeMissed'
    outcome_symbol = '✅ WIN' if outcome == 'Win' else \
        '❌ LOSS' if outcome == 'Loss' else \
        '⚠️ MISSED' if outcome == 'Missed' else '➖ BREAKEVEN'
    elements.append(Paragraph(outcome_symbol, styles[outcome_style]))

    if trade_data.get('pnl') is not None:
        pnl_val = trade_data['pnl']
        pnl_color = '#27ae60' if pnl_val >= 0 else '#e74c3c'
        pnl_text = f"P&L: ${pnl_val:+.2f}"
        if trade_data.get('pnl_percent') is not None:
            pnl_text += f" ({trade_data['pnl_percent']:+.2f}%)"
        elements.append(Paragraph(pnl_text, ParagraphStyle(
            'PnL', parent=styles['Normal'], fontSize=14,
            alignment=TA_CENTER, textColor=colors.HexColor(pnl_color),
            fontName='Helvetica-Bold'
        )))

    elements.append(Spacer(1, 30))

    # ─── TRADE OVERVIEW TABLE ───
    elements.append(Paragraph("TRADE OVERVIEW", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=colors.HexColor('#cccccc'), spaceAfter=8))

    overview_data = [
        ['Pair', trade_data.get('pair', 'N/A'),
         'Direction', trade_data.get('direction', 'N/A')],
        ['Outcome', trade_data.get('outcome', 'N/A'),
         'Session', trade_data.get('session', 'N/A')],
        ['Entry', str(trade_data.get('entry_price', 'N/A')),
         'Stop Loss', str(trade_data.get('sl_price', 'N/A'))],
        ['TP1', str(trade_data.get('tp1_price', 'N/A')),
         'TP2', str(trade_data.get('tp2_price', 'N/A'))],
        ['R:R', str(trade_data.get('risk_reward', 'N/A')),
         'Position Size', str(trade_data.get('position_size', 'N/A'))],
    ]

    overview_table = Table(overview_data, colWidths=[80, 140, 80, 140])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f5')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f0f0f5')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#1a1a2e')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(overview_table)
    elements.append(Spacer(1, 16))

    # ─── SMC ANALYSIS ───
    elements.append(Paragraph("SMC ANALYSIS", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=colors.HexColor('#cccccc'), spaceAfter=8))

    elements.append(Paragraph("Higher Timeframe Context", styles['SubHeader']))

    smc_htf = [
        ['HTF Bias', trade_data.get('htf_bias', 'N/A')],
        ['HTF Timeframe', trade_data.get('htf_timeframe', 'N/A')],
        ['Structure', trade_data.get('htf_structure', 'N/A')],
        ['POI Type', trade_data.get('poi_type', 'N/A')],
        ['POI Timeframe', trade_data.get('poi_timeframe', 'N/A')],
    ]

    htf_table = Table(smc_htf, colWidths=[120, 340])
    htf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(htf_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Lower Timeframe Entry", styles['SubHeader']))

    liq_text = "Yes" if trade_data.get('liquidity_sweep') else "No"
    if trade_data.get('liquidity_sweep') and trade_data.get('liquidity_type'):
        liq_text += f" — {trade_data['liquidity_type']}"

    ref_text = "Yes" if trade_data.get('refined_entry') else "No"
    if trade_data.get('refined_entry') and trade_data.get('refined_poi'):
        ref_text += f" — {trade_data['refined_poi']}"

    smc_ltf = [
        ['LTF Timeframe', trade_data.get('ltf_timeframe', 'N/A')],
        ['Entry Trigger', trade_data.get('ltf_trigger', 'N/A')],
        ['Liquidity Sweep', liq_text],
        ['Refined Entry', ref_text],
    ]

    ltf_table = Table(smc_ltf, colWidths=[120, 340])
    ltf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f5e9')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(ltf_table)
    elements.append(Spacer(1, 16))

    # ─── EXECUTION SUMMARY ───
    elements.append(Paragraph("EXECUTION SUMMARY", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=colors.HexColor('#cccccc'), spaceAfter=8))

    summary_data = [
        ['Step', 'Detail'],
        ['HTF Bias', f"{trade_data.get('htf_bias', 'N/A')} "
                     f"({trade_data.get('htf_timeframe', '')} "
                     f"{trade_data.get('htf_structure', '')})"],
        ['POI', f"{trade_data.get('poi_type', 'N/A')} on "
                f"{trade_data.get('poi_timeframe', 'N/A')}"],
        ['Wait For', f"Price retrace into "
                     f"{trade_data.get('poi_type', 'zone')}"],
        ['LTF Trigger', f"{trade_data.get('ltf_timeframe', 'N/A')} "
                        f"{trade_data.get('ltf_trigger', 'N/A')}"],
        ['SL', f"{'Above' if trade_data.get('direction') == 'Short' else 'Below'}"
               f" {trade_data.get('poi_timeframe', '')} "
               f"{trade_data.get('poi_type', 'zone')} "
               f"@ {trade_data.get('sl_price', 'N/A')}"],
        ['TP', f"TP1: {trade_data.get('tp1_price', 'N/A')} | "
               f"TP2: {trade_data.get('tp2_price', 'N/A')}"],
    ]

    summary_table = Table(summary_data, colWidths=[100, 360])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f5f5f5')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#fafafa')]),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 16))

    # ─── TRADER NOTES ───
    elements.append(Paragraph("TRADER NOTES", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=colors.HexColor('#cccccc'), spaceAfter=8))

    notes_sections = [
        ('Pre-Trade Plan', trade_data.get('pre_trade_notes')),
        ('Post-Trade Review', trade_data.get('post_trade_notes')),
        ('Mistakes Identified', trade_data.get('mistakes')),
        ('Lessons Learned', trade_data.get('lessons')),
    ]

    for title, content in notes_sections:
        if content and content.strip():
            elements.append(Paragraph(title, styles['SubHeader']))
            elements.append(Paragraph(content, styles['BodyCustom']))
            elements.append(Spacer(1, 6))

    # Emotional state
    emotions = []
    if trade_data.get('emotion_before'):
        emotions.append(f"Before: {trade_data['emotion_before']}")
    if trade_data.get('emotion_during'):
        emotions.append(f"During: {trade_data['emotion_during']}")
    if trade_data.get('emotion_after'):
        emotions.append(f"After: {trade_data['emotion_after']}")

    if emotions:
        elements.append(Paragraph("Emotional State", styles['SubHeader']))
        elements.append(Paragraph(" | ".join(emotions), styles['BodyCustom']))
        elements.append(Spacer(1, 12))

    # ─── AI ANALYSIS ───
    if trade_data.get('ai_analysis'):
        elements.append(PageBreak())
        elements.append(Paragraph("AI ANALYSIS (Groq)", styles['SectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1,
                                   color=colors.HexColor('#cccccc'), spaceAfter=8))

        # Parse markdown-ish content into paragraphs
        ai_text = trade_data['ai_analysis']
        for line in ai_text.split('\n'):
            line = line.strip()
            if not line:
                elements.append(Spacer(1, 4))
            elif line.startswith('# '):
                elements.append(Paragraph(
                    line[2:], styles['SectionHeader']))
            elif line.startswith('## '):
                elements.append(Paragraph(
                    line[3:], styles['SubHeader']))
            elif line.startswith('### '):
                elements.append(Paragraph(
                    line[4:], styles['SubHeader']))
            elif line.startswith('**') and line.endswith('**'):
                elements.append(Paragraph(
                    f"<b>{line.strip('*')}</b>", styles['BodyCustom']))
            elif line.startswith('- ') or line.startswith('* '):
                bullet_text = line[2:]
                # Handle bold within bullets
                bullet_text = bullet_text.replace('**', '<b>', 1)
                bullet_text = bullet_text.replace('**', '</b>', 1)
                elements.append(Paragraph(
                    f"• {bullet_text}", styles['BodyCustom']))
            elif line.startswith('|'):
                # Skip table formatting lines in markdown
                if set(line.replace('|', '').replace('-', '').strip()) == set():
                    continue
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if cells:
                    elements.append(Paragraph(
                        " | ".join(cells), styles['SmallNote']))
            else:
                # Handle inline bold
                formatted = line.replace('**', '<b>', 1)
                formatted = formatted.replace('**', '</b>', 1)
                while '**' in formatted:
                    formatted = formatted.replace('**', '<b>', 1)
                    formatted = formatted.replace('**', '</b>', 1)
                elements.append(Paragraph(formatted, styles['BodyCustom']))

    # ─── SCREENSHOTS ───
    screenshots = trade_data.get('screenshots', [])
    if screenshots:
        elements.append(PageBreak())
        elements.append(Paragraph("TRADE SCREENSHOTS", styles['SectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1,
                                   color=colors.HexColor('#cccccc'), spaceAfter=8))

        page_width = A4[0] - 40 * mm  # Available width
        max_img_width = page_width
        max_img_height = 280  # Max height in points

        for i, shot in enumerate(screenshots):
            filepath = shot.get('filepath', '')
            if not os.path.exists(filepath):
                continue

            try:
                pil_img = PILImage.open(filepath)
                img_w, img_h = pil_img.size

                # Calculate scaling
                scale = min(max_img_width / img_w, max_img_height / img_h, 1.0)
                display_w = img_w * scale
                display_h = img_h * scale

                # Label
                label_parts = []
                if shot.get('label'):
                    label_parts.append(shot['label'])
                if shot.get('timeframe'):
                    label_parts.append(f"[{shot['timeframe']}]")
                label_text = " ".join(label_parts) if label_parts else f"Screenshot {i + 1}"

                elements.append(Paragraph(
                    f"<b>{label_text}</b>", styles['SubHeader']))

                if shot.get('description'):
                    elements.append(Paragraph(
                        shot['description'], styles['SmallNote']))
                    elements.append(Spacer(1, 4))

                img = Image(filepath, width=display_w, height=display_h)
                elements.append(img)
                elements.append(Spacer(1, 16))

            except Exception as e:
                elements.append(Paragraph(
                    f"[Could not load image: {filepath} — {str(e)}]",
                    styles['SmallNote']))

    # ─── FOOTER ───
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=colors.HexColor('#cccccc'), spaceAfter=6))
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"Trade ID: {trade_data.get('trade_id', 'N/A')[:8]}",
        styles['SmallNote']
    ))

    # Build PDF
    doc.build(elements)
    return output_path