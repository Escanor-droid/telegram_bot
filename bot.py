#!/usr/bin/env python3
"""
Telegram Bot for Plagiarism & AI Content Detection
Uses Claude API for AI detection + DuckDuckGo for plagiarism (100% free)
"""

import os
import io
import json
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
import anthropic

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Configuration  ← ONLY change these two lines
# ─────────────────────────────────────────────

TELEGRAM_TOKEN = ""       # ✅ replace after revoking old one
ANTHROPIC_API_KEY = ""     # ✅ replace after regenerating

# ─────────────────────────────────────────────
# Anthropic Client
# ─────────────────────────────────────────────

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ─────────────────────────────────────────────
# Text Extraction Helpers
# ─────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    except Exception as e:
        logger.error(f"DOCX extraction error: {e}")
        return ""


def extract_text(file_bytes: bytes, filename: str) -> str:
    fn = filename.lower()
    if fn.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif fn.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    else:
        return file_bytes.decode("utf-8", errors="ignore")

# ─────────────────────────────────────────────
# AI Detection via Claude
# ─────────────────────────────────────────────

def detect_ai_content(text: str) -> dict:
    """Use Claude to analyse if text is AI-generated."""
    truncated = text[:4000]

    response = client.messages.create(
        model="claude-opus-4-5",           # ✅ fixed model name
        max_tokens=900,
        messages=[{
            "role": "user",
            "content": f"""You are an expert forensic linguist specialising in detecting AI-generated text.
Analyse the following text and respond ONLY with a JSON object (no markdown, no extra text) in this exact format:
{{
  "ai_probability": <integer 0-100>,
  "verdict": "<Human-written | Likely AI | Definitely AI>",
  "confidence": "<Low | Medium | High>",
  "indicators": ["<indicator 1>", "<indicator 2>", "<indicator 3>"],
  "summary": "<2-3 sentence plain-English explanation>"
}}

Text to analyse:
\"\"\"
{truncated}
\"\"\"
"""
        }]
    )

    raw = response.content[0].text.strip()
    try:
        return json.loads(raw)
    except Exception:
        return {
            "ai_probability": 0,
            "verdict": "Unknown",
            "confidence": "Low",
            "indicators": [],
            "summary": raw
        }

# ─────────────────────────────────────────────
# Plagiarism Check via DuckDuckGo (free, no key)
# ─────────────────────────────────────────────

def check_plagiarism(text: str) -> list:
    """Sample key sentences and search the web for matches."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.warning("duckduckgo_search not installed. Run: pip install duckduckgo-search")
        return []

    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if len(s.strip()) > 60]
    candidates = sentences[:6]
    matches = []

    with DDGS() as ddgs:
        for sentence in candidates:
            query = f'"{sentence[:120]}"'
            try:
                results = list(ddgs.text(query, max_results=3))
                if results:
                    matches.append({
                        "sentence": sentence[:120],
                        "sources": [
                            {"title": r.get("title", ""), "url": r.get("href", "")}
                            for r in results
                        ]
                    })
            except Exception as e:
                logger.warning(f"DDG search failed: {e}")
                continue

    return matches

# ─────────────────────────────────────────────
# Report Formatter
# ─────────────────────────────────────────────

def build_report(filename: str, word_count: int, ai_result: dict, plagiarism_matches: list) -> str:
    ai_pct      = ai_result.get("ai_probability", 0)
    verdict     = ai_result.get("verdict", "Unknown")
    confidence  = ai_result.get("confidence", "Low")
    indicators  = ai_result.get("indicators", [])
    summary     = ai_result.get("summary", "")

    ai_emoji   = "🔴" if ai_pct >= 70 else ("🟡" if ai_pct >= 40 else "🟢")
    plag_emoji = "🔴" if plagiarism_matches else "🟢"

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "📋  *DOCUMENT ANALYSIS REPORT*",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📄 File: `{filename}`",
        f"📝 Words analysed: ~{word_count}",
        "",
        f"{ai_emoji} *AI CONTENT DETECTION*",
        f"• Probability: *{ai_pct}%* AI-generated",
        f"• Verdict: *{verdict}*",
        f"• Confidence: {confidence}",
    ]

    if indicators:
        lines.append("• Key indicators:")
        for ind in indicators[:4]:
            lines.append(f"  — {ind}")

    if summary:
        lines += ["", f"_{summary}_"]

    lines += ["", f"{plag_emoji} *PLAGIARISM CHECK*"]

    if plagiarism_matches:
        lines.append(f"⚠️ Found *{len(plagiarism_matches)}* sentences with potential web matches:\n")
        for i, m in enumerate(plagiarism_matches, 1):
            lines.append(f"*Match {i}:*")
            lines.append(f'"{m["sentence"][:90]}…"')
            for src in m["sources"][:2]:
                url   = src.get("url", "")
                title = src.get("title", "Source")[:50]
                if url:
                    lines.append(f"  🔗 [{title}]({url})")
            lines.append("")
    else:
        lines.append("✅ No direct web matches found in sampled sentences.")
        lines.append("_(Note: This is a sample-based check, not a full database scan)_")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "⚡ Powered by Claude AI  •  Free checks via DuckDuckGo"
    ]

    return "\n".join(lines)

# ─────────────────────────────────────────────
# Bot Handlers
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Welcome to the Plagiarism & AI Detector Bot!*\n\n"
        "Upload any document and I'll analyse it for:\n"
        "🤖 *AI-generated content* — using Claude's advanced language analysis\n"
        "🔍 *Plagiarism* — by searching the web for matching sentences\n\n"
        "*Supported formats:* PDF · DOCX · TXT\n"
        "*Completely free* — no subscription needed\n\n"
        "Just send me a file to get started ⬆️"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *How to use this bot:*\n\n"
        "1️⃣ Upload a PDF, DOCX, or TXT file\n"
        "2️⃣ Wait ~15-30 seconds for analysis\n"
        "3️⃣ Receive a detailed report with:\n"
        "   • AI probability score (0-100%)\n"
        "   • Specific AI-writing indicators\n"
        "   • Plagiarism matches with source links\n\n"
        "*Limitations:*\n"
        "• Max file size: 20 MB\n"
        "• Plagiarism check samples up to 6 sentences\n"
        "• Results are indicative, not legally conclusive\n\n"
        "/start — Show welcome message"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc          = update.message.document
    filename     = doc.file_name or "document"
    file_size_mb = (doc.file_size or 0) / (1024 * 1024)

    if file_size_mb > 20:
        await update.message.reply_text("❌ File too large. Please upload a file under 20 MB.")
        return

    fn_lower = filename.lower()
    if not (fn_lower.endswith(".pdf") or fn_lower.endswith(".docx") or fn_lower.endswith(".txt")):
        await update.message.reply_text(
            "❌ Unsupported file type.\nPlease upload a *PDF*, *DOCX*, or *TXT* file.",
            parse_mode="Markdown"
        )
        return

    status_msg = await update.message.reply_text("⏳ Downloading your document…")

    try:
        tg_file    = await context.bot.get_file(doc.file_id)
        file_bytes = await tg_file.download_as_bytearray()
    except Exception as e:
        await status_msg.edit_text(f"❌ Failed to download file: {e}")
        return

    await status_msg.edit_text("📄 Extracting text…")
    text = extract_text(bytes(file_bytes), filename)

    if not text or len(text.strip()) < 100:
        await status_msg.edit_text(
            "❌ Could not extract enough text from the document.\n"
            "Make sure it's not a scanned image-only PDF."
        )
        return

    word_count = len(text.split())

    await status_msg.edit_text("🤖 Running AI content detection…")
    try:
        loop      = asyncio.get_running_loop()          # ✅ fixed deprecation
        ai_result = await loop.run_in_executor(None, detect_ai_content, text)
    except Exception as e:
        logger.error(f"AI detection error: {e}")
        ai_result = {
            "ai_probability": 0, "verdict": "Error",
            "confidence": "Low", "indicators": [], "summary": str(e)
        }

    await status_msg.edit_text("🔍 Checking for plagiarism across the web…")
    try:
        loop               = asyncio.get_running_loop()  # ✅ fixed deprecation
        plagiarism_matches = await loop.run_in_executor(None, check_plagiarism, text)
    except Exception as e:
        logger.error(f"Plagiarism check error: {e}")
        plagiarism_matches = []

    await status_msg.edit_text("📊 Generating report…")
    report = build_report(filename, word_count, ai_result, plagiarism_matches)
    await status_msg.delete()

    if len(report) <= 4000:
        await update.message.reply_text(report, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        for chunk in [report[i:i+4000] for i in range(0, len(report), 4000)]:
            await update.message.reply_text(chunk, parse_mode="Markdown", disable_web_page_preview=True)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """If user sends plain text instead of a file, analyse it directly."""
    text = update.message.text

    if len(text) < 50:
        await update.message.reply_text(
            "Please send a *document* (PDF/DOCX/TXT) or paste *at least 50 characters* of text.",
            parse_mode="Markdown"
        )
        return

    status_msg = await update.message.reply_text("🤖 Analysing your text…")
    try:
        loop               = asyncio.get_running_loop()  # ✅ fixed deprecation
        ai_result          = await loop.run_in_executor(None, detect_ai_content, text)
        plagiarism_matches = await loop.run_in_executor(None, check_plagiarism, text)
    except Exception as e:
        await status_msg.edit_text(f"❌ Error during analysis: {e}")
        return

    report = build_report("(pasted text)", len(text.split()), ai_result, plagiarism_matches)
    await status_msg.delete()
    await update.message.reply_text(report, parse_mode="Markdown", disable_web_page_preview=True)

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot is running… Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()