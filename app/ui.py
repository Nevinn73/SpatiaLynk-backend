"""
ui.py

Gradio UI for demoing the SpatiaLynk multi-level recommender.

- Clean, minimal layout
- No dropdown: all results shown as cards
- Uses modern font and pastel accents
"""

from __future__ import annotations

from typing import Tuple

import gradio as gr

from app.multilevel import multilevel_recommend


CUSTOM_CSS = """
:root {
    --sl-primary: #2563eb;
    --sl-bg: #f5f7fb;
    --sl-card-bg: #ffffff;
    --sl-accent: #0ea5e9;
    --sl-muted: #6b7280;
    --sl-radius-lg: 18px;
    --sl-shadow-soft: 0 14px 35px rgba(15, 23, 42, 0.08);
}

body, .gradio-container, input, button, textarea {
    font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}

.gradio-container {
    background: radial-gradient(circle at top left, #e0f2fe 0, #f5f7fb 45%, #f9fafb 100%);
}

#app-container {
    max-width: 720px;
    margin: 0 auto;
    padding: 32px 16px 40px 16px;
}

#search-card {
    background: var(--sl-card-bg);
    border-radius: var(--sl-radius-lg);
    box-shadow: var(--sl-shadow-soft);
    padding: 20px 18px 18px 18px;
    margin-top: 8px;
    margin-bottom: 20px;
}

#search-button {
    width: 100%;
    font-weight: 600;
    border-radius: 999px;
    background: linear-gradient(135deg, var(--sl-primary), var(--sl-accent)) !important;
    border: none !important;
}

#search-button:hover {
    opacity: 0.96;
}

#results-area {
    margin-top: 8px;
}

.card {
    background: var(--sl-card-bg);
    border-radius: var(--sl-radius-lg);
    padding: 16px 18px 14px 18px;
    box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
    margin-bottom: 14px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
}

.badge {
    padding: 4px 9px;
    border-radius: 999px;
    font-weight: 600;
}

.badge-level {
    background: rgba(37, 99, 235, 0.08);
    color: #1d4ed8;
}

.badge-category {
    background: rgba(14, 165, 233, 0.10);
    color: #0369a1;
}

.card-title {
    font-size: 16px;
    font-weight: 650;
    margin: 2px 0 0 0;
}

.card-subtitle {
    font-size: 12px;
    color: var(--sl-muted);
}

.card-body {
    font-size: 13px;
    color: #111827;
    line-height: 1.45;
}

.card-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: 11px;
    color: var(--sl-muted);
}

.card-meta span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.card-map {
    margin-top: 2px;
    font-size: 11px;
    color: #0f766e;
}

.alert {
    border-radius: var(--sl-radius-lg);
    padding: 12px 14px;
    font-size: 13px;
    margin-top: 12px;
    background: #ecfeff;
    border: 1px solid #06b6d4;
    color: #0f172a;
}

.alert.error {
    background: #fef2f2;
    border-color: #f87171;
    color: #7f1d1d;
}
"""


def build_cards_html(response: dict) -> str:
    level = response.get("level", "city")
    pois = response.get("results", []) or []

    if not pois:
        return '<div class="alert error">❗ No places were found. Try a different query or fewer constraints.</div>'

    cards = []
    for poi in pois:
        name = poi.get("name", "Unknown place")
        category = str(poi.get("category", "")).replace("_", " ").title()
        district = str(poi.get("district", "") or "").title()
        region = str(poi.get("region", "") or "").title()
        characteristic = poi.get("characteristic") or "A recommended place that matches your interests."
        price = poi.get("price") or ""
        popularity = poi.get("popularity")
        lat = poi.get("lat")
        lon = poi.get("lon")

        location_line = " • ".join([x for x in [district, region] if x])

        meta_bits = []
        if popularity not in (None, "", "nan"):
            meta_bits.append(f"⭐ {popularity} popularity")
        if price:
            meta_bits.append(f"💰 {price}")

        coords = ""
        if lat not in (None, "") and lon not in (None, ""):
            try:
                coords = f"📍 {float(lat):.4f}, {float(lon):.4f}"
            except Exception:
                coords = f"📍 {lat}, {lon}"

        card_html = f"""
        <div class="card">
            <div class="card-header">
                <span class="badge badge-level">{level.title()}</span>
                <span class="badge badge-category">{category or "Place"}</span>
            </div>
            <h3 class="card-title">{name}</h3>
            <p class="card-subtitle">{location_line}</p>
            <p class="card-body">{characteristic}</p>
            <div class="card-meta">
                {''.join(f'<span>{bit}</span>' for bit in meta_bits)}
            </div>
            <div class="card-map">{coords}</div>
        </div>
        """
        cards.append(card_html)

    return "\n".join(cards)


def handle_search(query: str, k: int) -> Tuple[str, str]:
    query = (query or "").strip()
    if not query:
        return (
            '<div class="alert">Type something like <b>"Fun things to do in Singapore"</b> or <b>"Cafes in the east"</b> to get started ✨</div>',
            "",
        )

    try:
        response = multilevel_recommend(query, int(k))
    except Exception as e:
        return (
            f'<div class="alert error">Oops, something went wrong: {e}</div>',
            "",
        )

    html = build_cards_html(response)

    explanation_md = ""
    exp = response.get("explanation")
    if exp:
        level_reason = exp.get("level_reason", "")
        category_reason = exp.get("category_reason", "")
        bullets = []
        if level_reason:
            bullets.append(f"- {level_reason}")
        if category_reason:
            bullets.append(f"- {category_reason}")
        if bullets:
            explanation_md = "### Why these places?\n" + "\n".join(bullets)

    return html, explanation_md


def build_ui() -> gr.Blocks:
    with gr.Blocks(css=CUSTOM_CSS, title="SpatiaLynk Explorer") as demo:
        with gr.Column(elem_id="app-container"):
            gr.Markdown(
                "## Hi, Explorer 👋\n"
                "Find fun things to do around Singapore. Try prompts like:\n"
                "- **Fun things to do in Singapore**\n"
                "- **Cafes in the east**\n"
                "- **Places to shop in Hougang**"
            )

            with gr.Group(elem_id="search-card"):
                query = gr.Textbox(
                    label="Search",
                    placeholder="Fun things to do in Singapore",
                    value="Fun things to do in Singapore",
                    lines=1,
                )
                k_slider = gr.Slider(
                    minimum=1,
                    maximum=10,
                    step=1,
                    value=5,
                    label="Number of suggestions",
                )
                search_btn = gr.Button("Search", elem_id="search-button")

            results_html = gr.HTML(label="", elem_id="results-area")
            explanation_md = gr.Markdown(label="", visible=True)

            search_btn.click(
                fn=handle_search,
                inputs=[query, k_slider],
                outputs=[results_html, explanation_md],
            )

        return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch()
