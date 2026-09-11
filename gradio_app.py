"""
Fake News Verifier — Gradio app for Hugging Face Spaces.

Wraps the existing multi-agent verification pipeline (app/agents/orchestrator.py)
in a Gradio Blocks UI. No auth, no database — each verification is stateless
and scoped to the browser session (gr.State), which fits the Spaces demo model.

Runs with zero API keys out of the box (ENABLE_MOCK_MODE=true by default).
To use real data, set the following as *Secrets* in your Space settings:
    ENABLE_MOCK_MODE=false
    SERPAPI_KEY=...
    GROQ_API_KEY=gsk_...
    NEWSAPI_KEY=...
    HUGGINGFACE_API_KEY=...
    ASSEMBLYAI_API_KEY=...
"""
import base64
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import gradio as gr
import pandas as pd

from app.config import get_settings
from app.agents.orchestrator import VerificationOrchestrator
from app.utils.pdf_export import build_verification_pdf

settings = get_settings()
orchestrator = VerificationOrchestrator()

VERDICT_STYLE = {
    "true": ("#16a34a", "#dcfce7", "✅ TRUE"),
    "false": ("#dc2626", "#fee2e2", "❌ FALSE"),
    "misleading": ("#d97706", "#fef3c7", "⚠️ MISLEADING"),
    "unverified": ("#6b7280", "#f3f4f6", "❔ UNVERIFIED"),
}


# ---------------------------------------------------------------------------
# Core pipeline call + result formatting
# ---------------------------------------------------------------------------

async def _run_pipeline(input_type: str, content: Optional[str] = None, file_data: Optional[str] = None) -> Dict[str, Any]:
    result = await orchestrator.verify(input_type=input_type, content=content, file_data=file_data)
    result["input_type"] = input_type
    result["id"] = 1  # single-session demo, no persistent IDs
    result["created_at"] = datetime.now(timezone.utc)
    return result


def _verdict_html(result: Dict[str, Any]) -> str:
    verdict = (result.get("verdict") or "unverified").lower()
    color, bg, label = VERDICT_STYLE.get(verdict, VERDICT_STYLE["unverified"])
    score = result.get("trust_score")
    confidence = result.get("confidence")
    score_display = f"{score:.0f}/100" if score is not None else "N/A"
    conf_display = f"{confidence * 100:.0f}%" if confidence is not None else "N/A"

    return f"""
    <div style="border-radius:12px;padding:20px;background:{bg};border:1px solid {color}33;">
      <div style="font-size:22px;font-weight:700;color:{color};">{label}</div>
      <div style="display:flex;gap:24px;margin-top:10px;">
        <div><div style="font-size:12px;color:#6b7280;">TRUST SCORE</div>
             <div style="font-size:28px;font-weight:700;color:{color};">{score_display}</div></div>
        <div><div style="font-size:12px;color:#6b7280;">CONFIDENCE</div>
             <div style="font-size:28px;font-weight:700;color:#374151;">{conf_display}</div></div>
      </div>
    </div>
    """


def _factors_df(result: Dict[str, Any]) -> pd.DataFrame:
    factors = result.get("explanation") or []
    if not factors:
        return pd.DataFrame(columns=["Factor", "Score", "Max", "Weight", "Description"])
    return pd.DataFrame([
        {
            "Factor": f["factor"],
            "Score": f["score"],
            "Max": f["max"],
            "Weight": f"{int(f['weight'] * 100)}%",
            "Description": f["description"],
        }
        for f in factors
    ])


def _factors_chart_df(result: Dict[str, Any]) -> pd.DataFrame:
    factors = result.get("explanation") or []
    return pd.DataFrame([
        {"Factor": f["factor"], "Score %": round((f["score"] / f["max"]) * 100, 1) if f["max"] else 0}
        for f in factors
    ])


def _sources_md(result: Dict[str, Any]) -> str:
    sources = result.get("sources") or []
    if not sources:
        return "_No sources found._"
    lines = []
    for s in sources:
        title = s.get("title", "Untitled source")
        publisher = s.get("publisher") or ""
        rating = s.get("textual_rating") or ""
        url = s.get("url")
        line = f"- **{title}**"
        if publisher:
            line += f" — {publisher}"
        if rating:
            line += f" _({rating})_"
        if url:
            line += f"  \n  [{url}]({url})"
        lines.append(line)
    return "\n".join(lines)


def _recommendations_md(result: Dict[str, Any]) -> str:
    recs = result.get("recommendations") or []
    if not recs:
        return "_No specific recommendations._"
    return "\n".join(f"- {r}" for r in recs)


def _ai_summary_md(result: Dict[str, Any]) -> str:
    summary = result.get("ai_summary")
    return summary if summary else "_No AI analysis available for this result._"


def _extracted_text(result: Dict[str, Any]) -> str:
    return result.get("extracted_text") or "No text extracted."


def _agent_logs(result: Dict[str, Any]) -> list:
    return result.get("agent_logs") or []


def _format_all(result: Dict[str, Any]) -> Tuple[str, str, pd.DataFrame, pd.DataFrame, str, str, str, list, Dict[str, Any]]:
    return (
        _verdict_html(result),
        _ai_summary_md(result),
        _factors_df(result),
        _factors_chart_df(result),
        _sources_md(result),
        _recommendations_md(result),
        _extracted_text(result),
        _agent_logs(result),
        result,  # stored in gr.State for PDF export
    )


def _empty_outputs(message: str) -> Tuple[str, str, pd.DataFrame, pd.DataFrame, str, str, str, list, Optional[Dict]]:
    banner = f"""<div style="border-radius:12px;padding:16px;background:#fee2e2;border:1px solid #dc262633;
                 color:#991b1b;">{message}</div>"""
    return banner, "", pd.DataFrame(), pd.DataFrame(), "", "", "", [], None


# ---------------------------------------------------------------------------
# Tab handlers
# ---------------------------------------------------------------------------

async def verify_text_handler(text: str):
    if not text or not text.strip():
        return _empty_outputs("Please enter some text to verify.")
    result = await _run_pipeline("text", content=text.strip())
    return _format_all(result)


async def verify_url_handler(url: str):
    if not url or not url.strip():
        return _empty_outputs("Please enter a URL to verify.")
    if not url.strip().lower().startswith(("http://", "https://")):
        return _empty_outputs("URL must start with http:// or https://")
    result = await _run_pipeline("url", content=url.strip())
    return _format_all(result)


async def verify_image_handler(image_path: str):
    if not image_path:
        return _empty_outputs("Please upload an image.")
    with open(image_path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode("utf-8")
    result = await _run_pipeline("image", file_data=file_data)
    return _format_all(result)


async def verify_audio_handler(audio_path: str):
    if not audio_path:
        return _empty_outputs("Please upload an audio file.")
    with open(audio_path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode("utf-8")
    result = await _run_pipeline("audio", file_data=file_data)
    return _format_all(result)


def export_pdf_handler(result_state: Optional[Dict[str, Any]]):
    if not result_state:
        gr.Warning("Run a verification first, then export the report.")
        return None
    pdf_buffer = build_verification_pdf(result_state)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(pdf_buffer.read())
    tmp.close()
    return tmp.name


# ---------------------------------------------------------------------------
# UI layout
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
.gradio-container {max-width: 1100px !important; margin: auto;}
footer {visibility: hidden}
"""

mock_badge = (
    "🟡 **Mock Mode: ON** — running with simulated data, no API keys needed. "
    "Set `ENABLE_MOCK_MODE=false` and add API key secrets in your Space settings for live data."
    if settings.ENABLE_MOCK_MODE else
    "🟢 **Mock Mode: OFF** — using live external APIs."
)

with gr.Blocks(title="Fake News Verifier", css=CUSTOM_CSS, theme=gr.themes.Soft()) as demo:
    result_state = gr.State(value=None)

    gr.Markdown("# 🛡️ Agentic AI Fake News Verifier")
    gr.Markdown(
        "A multi-agent pipeline (Ingestion → Search → Trust Scoring → Explanation) "
        "verifies text, article URLs, images, and audio, and returns an explainable "
        "trust score with sources and recommendations."
    )
    gr.Markdown(mock_badge)

    with gr.Tabs():
        with gr.TabItem("📝 Text"):
            text_input = gr.Textbox(
                label="Paste text to verify",
                placeholder="Paste a news article, social media post, or claim here...",
                lines=8,
                max_lines=20,
            )
            text_btn = gr.Button("Verify Text", variant="primary")
            gr.Examples(
                examples=[
                    ["Scientists confirm that drinking 8 glasses of water a day cures the common cold."],
                    ["The city council approved a new $2M budget for public park renovations this year."],
                ],
                inputs=[text_input],
            )

        with gr.TabItem("🔗 URL"):
            url_input = gr.Textbox(
                label="News article URL",
                placeholder="https://example.com/news/article-headline",
            )
            url_btn = gr.Button("Verify URL", variant="primary")
            gr.Markdown("_Fetches the page and extracts the article text automatically._")

        with gr.TabItem("🖼️ Image"):
            image_input = gr.Image(label="Upload an image", type="filepath")
            image_btn = gr.Button("Verify Image", variant="primary")

        with gr.TabItem("🎙️ Audio"):
            audio_input = gr.Audio(label="Upload an audio file", type="filepath")
            audio_btn = gr.Button("Verify Audio", variant="primary")

    gr.Markdown("---")
    gr.Markdown("## Result")

    verdict_html = gr.HTML()

    with gr.Group(visible=True):
        gr.Markdown("### ✨ AI Analysis")
        ai_summary_md = gr.Markdown()

    with gr.Row():
        with gr.Column(scale=1):
            factors_chart = gr.BarPlot(
                x="Factor", y="Score %", title="Trust Factor Breakdown",
                y_lim=[0, 100], height=280,
            )
        with gr.Column(scale=1):
            factors_table = gr.Dataframe(
                headers=["Factor", "Score", "Max", "Weight", "Description"],
                label="Factor Details", wrap=True,
            )

    with gr.Accordion("📄 Extracted Content", open=False):
        extracted_text_box = gr.Textbox(label="", lines=6, interactive=False)

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🔎 Sources & Evidence")
            sources_md = gr.Markdown()
        with gr.Column():
            gr.Markdown("### 💡 Recommendations")
            recommendations_md = gr.Markdown()

    with gr.Accordion("🤖 Agent Execution Logs", open=False):
        agent_logs_json = gr.JSON()

    with gr.Row():
        export_btn = gr.Button("⬇️ Download PDF Report")
        pdf_file = gr.File(label="Report", visible=True)

    outputs = [verdict_html, ai_summary_md, factors_table, factors_chart, sources_md,
               recommendations_md, extracted_text_box, agent_logs_json, result_state]

    text_btn.click(verify_text_handler, inputs=[text_input], outputs=outputs)
    url_btn.click(verify_url_handler, inputs=[url_input], outputs=outputs)
    image_btn.click(verify_image_handler, inputs=[image_input], outputs=outputs)
    audio_btn.click(verify_audio_handler, inputs=[audio_input], outputs=outputs)
    export_btn.click(export_pdf_handler, inputs=[result_state], outputs=[pdf_file])

    gr.Markdown(
        "---\n"
        "⚠️ _Educational/research project. Trust scores are probabilistic assessments "
        "and should not be treated as definitive legal or journalistic proof._"
    )


if __name__ == "__main__":
    import os
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
    )
