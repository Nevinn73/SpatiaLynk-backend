# app/ui.py
import gradio as gr
import textwrap
from app.multilevel import multilevel_recommend


# ------------ helpers to format output ------------

def _flatten_pois(result: dict):
    """
    Normalise the multilevel output into a flat list of POI dicts
    for the UI.
    """
    if not result or "error" in result:
        return []

    if "results" in result and isinstance(result["results"], list):
        return result["results"]

    if "nearby" in result:
        return result["nearby"]

    if "regions" in result:
        pois = []
        for lst in result["regions"].values():
            pois.extend(lst)
        return pois

    if "districts" in result:
        pois = []
        for lst in result["districts"].values():
            pois.extend(lst)
        return pois

    return []


def _make_label(poi: dict) -> str:
    parts = [poi.get("name", "Unknown")]
    cat = poi.get("category")
    if cat:
        parts.append(f"• {cat}")
    loc_bits = []
    if poi.get("district"):
        loc_bits.append(poi["district"])
    if poi.get("region"):
        loc_bits.append(poi["region"])
    if loc_bits:
        parts.append(f"({', '.join(loc_bits)})")
    return " ".join(parts)


def _format_details(poi: dict) -> str:
    if not poi:
        return ""

    lines = []
    lines.append(f"### {poi.get('name', 'Place')}")
    meta = []

    if poi.get("category"):
        meta.append(poi["category"].title())
    if poi.get("district"):
        meta.append(poi["district"])
    if poi.get("region"):
        meta.append(poi["region"])

    if meta:
        lines.append("**Type / Area:** " + " • ".join(meta))

    if poi.get("price"):
        lines.append(f"**Price range:** {poi['price']}")

    if poi.get("popularity"):
        lines.append(f"**Popularity score:** {poi['popularity']}")

    if poi.get("street"):
        lines.append(f"**Address:** {poi['street']}")

    if poi.get("characteristic"):
        lines.append("")
        lines.append(f"**Highlights:** {poi['characteristic']}")

    # simple static map preview (just show coordinates as text)
    if poi.get("lat") and poi.get("lon"):
        lines.append("")
        lines.append(
            f"**Map preview:** lat `{poi['lat']:.5f}`, lon `{poi['lon']:.5f}`"
        )

    return "\n\n".join(lines)


# ------------ backend functions for gradio ------------

def handle_search(query: str, k: int):
    if not query or not query.strip():
        return (
            "⚠️ Please enter what you're looking for, e.g. "
            "`Places to eat in Singapore`.",
            gr.Dropdown(choices=[], value=None),
            "",
            [],
        )

    result = multilevel_recommend(query, int(k))
    pois = _flatten_pois(result)

    if not pois:
        return (
            "❗ No places were found. Try a broader query like "
            "`Things to do in Singapore` or reduce the number of suggestions.",
            gr.Dropdown(choices=[], value=None),
            "",
            [],
        )

    labels = [_make_label(p) for p in pois]
    first = pois[0]
    details_md = _format_details(first)

    return (
        "",
        gr.Dropdown(choices=labels, value=labels[0]),
        details_md,
        pois,
    )


def handle_select(label: str, pois: list):
    if not pois or not label:
        return ""
    for p in pois:
        if _make_label(p) == label:
            return _format_details(p)
    return ""


# ------------ build UI ------------

def build_ui():
    with gr.Blocks(theme=gr.themes.Soft(), title="SpatiaLynk Explorer") as demo:
        gr.Markdown(
            textwrap.dedent(
                """
                # Hi, Explorer 👋  
                Find fun things to do around Singapore.

                Try prompts like:

                - `Places to eat in Singapore`  
                - `Things to do in the West`  
                - `Where to shop in Orchard`  
                - `Fun places in Kallang`  
                """
            )
        )

        with gr.Row():
            query = gr.Textbox(
                label="Search",
                placeholder="e.g. Places to eat in Singapore",
            )

        with gr.Row():
            k = gr.Slider(
                label="Number of suggestions",
                minimum=1,
                maximum=10,
                step=1,
                value=5,
            )

        search_btn = gr.Button("Search", variant="primary")

        status = gr.Markdown("")
        dropdown = gr.Dropdown(
            label="Pick a place to see details",
            choices=[],
            interactive=True,
        )
        details = gr.Markdown("")
        state_pois = gr.State([])

        search_btn.click(
            handle_search,
            inputs=[query, k],
            outputs=[status, dropdown, details, state_pois],
        )

        dropdown.change(
            handle_select,
            inputs=[dropdown, state_pois],
            outputs=details,
        )

        gr.Markdown(
            "Built for SpatiaLynk FYP • Prototype recommender demo on localhost"
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch()

