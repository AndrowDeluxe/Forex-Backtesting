"""Shared compact-tile renderer for the per-Hauptthema section pages
(section_*.py). One Hauptthema = one sidebar row (app.py); this renders
that Hauptthema's own page: a small "SECTION" eyebrow, a header, and a
grid of small tiles (tag + icon + title only, no description -- the
description/finding lives on the linked detail page itself)."""

import streamlit as st


def render_section(icon: str, title: str, items: list[dict]) -> None:
    """items: list of {"page": str, "title": str, "icon": str, "tag": str}"""
    st.caption("SECTION")
    st.markdown(f"## {icon} {title}")
    st.caption(f"{len(items)} Kacheln")
    st.divider()

    cols = st.columns(3)
    for i, item in enumerate(items):
        with cols[i % 3]:
            with st.container(border=True):
                st.caption(item["tag"])
                st.page_link(item["page"], label=item["title"], icon=item["icon"])
