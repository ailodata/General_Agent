import hashlib
import html
import io
import json
import random
import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

ASSETS = Path(__file__).parent / "assets"
AVATARS = {
    "user": str(ASSETS / "user.png"),
    "assistant": str(ASSETS / "agent.png"),
}

_THINKING_BLOCK = re.compile(r"<thinking>.*?</thinking>", re.IGNORECASE | re.DOTALL)
_OPEN_THINKING = re.compile(r"<thinking>.*$", re.IGNORECASE | re.DOTALL)
_WRAPPER_TAGS = re.compile(r"</?(?:answer|thinking)>", re.IGNORECASE)
# a tag that is only half there at the end of a streaming answer, e.g. "<ans" or "</thinki"
_PARTIAL_TAG = re.compile(
    r"</?(?:a(?:n(?:s(?:w(?:e(?:r)?)?)?)?)?|t(?:h(?:i(?:n(?:k(?:i(?:n(?:g)?)?)?)?)?)?)?)?$", re.IGNORECASE
)


def clean_text(text):
    """Remove the <answer> wrapper and any <thinking> text the agent leaks into its final answer,
    including a half-arrived tag at the end of a streaming answer."""
    text = _THINKING_BLOCK.sub("", text or "")
    text = _OPEN_THINKING.sub("", text)
    text = _WRAPPER_TAGS.sub("", text)
    return _PARTIAL_TAG.sub("", text).strip()


# Branding: override any of these under [branding] in the app's secrets. The defaults are AILO's.
BRANDING = {
    "page_title": "AILO — FORK Analytics",
    "kicker": "AILO — FORK ANALYTICS",
    "contact_email": "contact@ailodata.com",
    "file_prefix": "fork_data",
}
BRANDING.update(st.secrets.get("branding", {}))

st.set_page_config(page_title=BRANDING["page_title"], page_icon=AVATARS["assistant"])

# AILO styling: Helvetica Neue Light, bordeaux chat input
st.markdown(
    """
    <style>
    html, body, [class*="st-"], .stMarkdown, .stChatMessage, textarea, input, button {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        font-weight: 300;
    }
    /* ...keep code in a monospace font... */
    [data-testid="stCode"], [data-testid="stCode"] *, pre, code {
        font-family: "SFMono-Regular", Menlo, Consolas, monospace !important;
        font-size: 12px !important;
    }
    /* ...and leave Streamlit's icon font alone, or icons render as words like "download" */
    [data-testid="stIconMaterial"],
    [data-testid="stIconMaterial"] * {
        font-family: "Material Symbols Rounded" !important;
        font-weight: 400 !important;
    }
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] td,
    [data-testid="stChatMessage"] th {
        font-weight: 300 !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
    }
    [data-testid="stChatMessage"] strong,
    [data-testid="stChatMessage"] b {
        font-weight: 500 !important;
    }
    /* The user's question: a bubble as wide as the text, to the right, like in common chat apps */
    [data-testid="stChatMessage"]:has(img[alt="user avatar"], [data-testid="stChatMessageContent"][aria-label*="from user"]) {
        background-color: #491C1F !important;
        margin-bottom: 0.5rem !important;
        width: fit-content !important;
        max-width: 80% !important;
        margin-left: auto !important;
        padding: 0.7rem 1.1rem !important;
        border-radius: 0.9rem !important;
    }
    [data-testid="stChatMessage"]:has(img[alt="user avatar"], [data-testid="stChatMessageContent"][aria-label*="from user"]) * {
        color: #FFFFFF !important;
    }
    [data-testid="stChatMessage"] {
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
    }
    /* Headings in answers: one calm style whatever level the agent uses (#, ## or ###) */
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2 {
        font-size: 17px !important;
        font-weight: 400 !important;
        line-height: 1.4 !important;
        color: #491C1F !important;
        padding: 0 !important;
        margin: 1.6rem 0 0.4rem 0 !important;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h4,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h5,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h6 {
        font-size: 14px !important;
        font-weight: 500 !important;
        line-height: 1.4 !important;
        color: #322D29 !important;
        padding: 0 !important;
        margin: 1.2rem 0 0.3rem 0 !important;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1 *,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2 *,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3 * {
        font-size: inherit !important;
        font-weight: inherit !important;
    }
    /* No link icon next to headings */
    [data-testid="stChatMessage"] [data-testid="stHeaderActionElements"] {
        display: none !important;
    }
    /* First heading in an answer doesn't need the extra top space */
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] > :first-child:is(h1, h2, h3, h4) {
        margin-top: 0 !important;
    }
    /* Streamlit marks elements "stale" until the script has drawn them again.
       1) A message that already has fresh content: hide its stale leftovers (no faded duplicates). */
    [data-testid="stChatMessage"]:has([data-stale="false"]) [data-stale="true"] {
        display: none !important;
    }
    /* 2) A message that has not been redrawn yet: keep it readable, not blank or faded. */
    [data-testid="stChatMessage"]:not(:has([data-stale="false"])) [data-stale="true"] {
        opacity: 1 !important;
        transition: none !important;
    }
    /* 3) Old messages left below the live ones (for example when a new question interrupts a slow
       "New chat" run): hide them completely instead of showing empty boxes. */
    [data-testid="stLayoutWrapper"]:has(> [data-testid="stChatMessage"] [data-stale="false"])
        ~ [data-testid="stLayoutWrapper"]:has(> [data-testid="stChatMessage"]):not(:has([data-stale="false"])) {
        display: none !important;
    }
    /* Answers start closer to the question above them */
    [data-testid="stChatMessage"]:has(img[alt="assistant avatar"], [data-testid="stChatMessageContent"][aria-label*="from assistant"]) {
        padding-top: 0.25rem;
    }
    [data-testid="stChatMessage"] [data-testid="stFullScreenFrame"] {
        margin-top: 1.5rem;
    }
    .ailo-status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 12px;
        font-weight: 300;
        color: #907374;
        padding: 0;
        margin-top: -14px;  /* sit tight under the question */
    }
    .ailo-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #491C1F;
        animation: ailo-pulse 1.2s ease-in-out infinite;
    }
    @keyframes ailo-pulse {
        0%, 100% { opacity: 0.25; transform: scale(0.85); }
        50% { opacity: 1; transform: scale(1); }
    }
    .ailo-kicker {
        font-size: 0.95rem;
        letter-spacing: 0.08em;
        color: #491C1F;
        margin-bottom: -0.4rem;
    }
    .ailo-title {
        font-size: 2.6rem;
        font-weight: 200;
        letter-spacing: 0.01em;
        text-transform: uppercase;
        color: #322D29;
        line-height: 1.1;
        margin-top: 0.6rem;
    }
    .ailo-subtitle {
        font-size: 1.1rem;
        font-weight: 300;
        color: #322D29;
        margin-top: 0.4rem;
        margin-bottom: 2rem;
    }
    /* Soft intro: kicker fades in, greeting appears letter by letter, subtitle word by word */
    .ailo-kicker { animation: ailo-fade 1.4s ease-out both; }
    .ailo-word { display: inline-block; white-space: nowrap; }
    .ailo-char,
    .ailo-sub-word {
        display: inline-block;
        opacity: 0;
        animation: ailo-rise 1.6s cubic-bezier(0.25, 0.1, 0.25, 1) forwards;
    }
    @keyframes ailo-fade {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes ailo-rise {
        from { opacity: 0; transform: translateY(0.15em); }
        to { opacity: 1; transform: none; }
    }
    @media (prefers-reduced-motion: reduce) {
        .ailo-kicker, .ailo-char, .ailo-sub-word {
            animation: none !important;
            opacity: 1 !important;
            transform: none !important;
        }
    }
    [data-testid="stChatInput"] > div {
        background-color: #491C1F !important;
        border-color: #491C1F !important;
        border-radius: 0.9rem !important;  /* same corner as the question bubble */
    }
    [data-testid="stChatInput"] textarea {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        caret-color: #FFFFFF !important;
        font-weight: 300;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: rgba(255, 255, 255, 0.65) !important;
        -webkit-text-fill-color: rgba(255, 255, 255, 0.65) !important;
    }
    [data-testid="stChatInput"] button {
        background-color: transparent !important;
        color: #FFFFFF !important;
    }
    [data-testid="stChatInput"] button svg {
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
    }
    /* Keep the narrow, centred column even if a viewer turns on Streamlit's "Wide mode" */
    [data-testid="stMainBlockContainer"],
    [data-testid="stBottomBlockContainer"] {
        max-width: 736px !important;
    }
    /* Figure titles (charts and tables) share the kicker style */
    .ailo-figure-title {
        font-size: 0.8rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 500;
        color: #491C1F;
        margin: 1.5rem 0 0.5rem 0;
    }
    /* Tables: agent result tables and markdown tables in answers */
    .ailo-table-wrap {
        overflow: auto;
        max-height: 420px;
        margin-bottom: 0.5rem;
    }
    .ailo-table thead th {
        position: sticky;
        top: 0;
        z-index: 1;
        background: #F5F3F1 !important;
    }
    [class*="st-key-ailo_file_"] {
        border: 1px solid #CFCBC3;
        border-radius: 0.75rem;
        min-height: 53px;
        padding: 0.35rem 22px 0.35rem 1rem;  /* icon sits 23px from the edge, like the send arrow */
        margin: 0.75rem 0 1rem 0;
        justify-content: space-between;
    }
    [class*="st-key-ailo_file_"] > div:first-child {
        flex: 1 1 auto;
        min-width: 0;
    }
    .ailo-file {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        min-width: 0;
    }
    .ailo-file-icon {
        flex: none;
        width: 14px;
        height: 18px;
        border-radius: 2px;
        background: #907374;
        clip-path: polygon(0 0, 68% 0, 100% 28%, 100% 100%, 0 100%);
    }
    .ailo-file-name {
        font-size: 13px;
        font-weight: 300;
        color: #322D29;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .ailo-file-meta {
        flex: none;
        font-size: 12px;
        font-weight: 300;
        color: #907374;
    }
    /* Thin line download icon instead of Streamlit's filled one */
    [class*="st-key-ailo_file_"] button {
        width: 20px !important;
        min-width: 20px !important;
        height: 20px !important;
        min-height: 20px !important;
        padding: 0 !important;
        background: transparent !important;
    }
    [class*="st-key-ailo_file_"] button > * {
        display: none !important;
    }
    [class*="st-key-ailo_file_"] button::before {
        content: "";
        display: block;
        width: 20px;
        height: 20px;
        background-color: #491C1F;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 4v11'/%3E%3Cpath d='M7.5 10.5 12 15l4.5-4.5'/%3E%3Cpath d='M5 19.5h14'/%3E%3C/svg%3E") center / contain no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 4v11'/%3E%3Cpath d='M7.5 10.5 12 15l4.5-4.5'/%3E%3Cpath d='M5 19.5h14'/%3E%3C/svg%3E") center / contain no-repeat;
        transition: background-color 0.2s ease;
    }
    [class*="st-key-ailo_file_"] button:hover::before {
        background-color: #907374;
    }
    [class*="st-key-ailo_file_"] [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
    /* "How was this calculated?" */
    [data-testid="stChatMessage"] [data-testid="stExpander"] details,
    [data-testid="stChatMessage"] [data-testid="stExpander"] summary {
        background: transparent !important;
    }
    [data-testid="stChatMessage"] [data-testid="stExpander"] details {
        border: none !important;
        border-top: 1px solid #E9E5E0 !important;
        border-radius: 0 !important;
        margin-top: 0.5rem;
    }
    [data-testid="stChatMessage"] [data-testid="stExpander"] summary {
        padding-left: 0 !important;
    }
    [data-testid="stChatMessage"] [data-testid="stExpanderDetails"] {
        padding-left: 0 !important;
        padding-right: 0 !important;
        border-top: none !important;  /* no line under the heading when opened */
    }
    [data-testid="stChatMessage"] [data-testid="stExpander"] summary p {
        font-size: 12px !important;
        font-weight: 300 !important;
        color: #907374 !important;
    }
    [data-testid="stChatMessage"] [data-testid="stExpander"] summary:hover p {
        color: #491C1F !important;
    }
    .ailo-query-label {
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #491C1F;
        margin: 0.25rem 0 0.25rem 0;
    }
    .ailo-query-text {
        font-size: 13px;
        font-weight: 300;
        color: #322D29;
        margin-bottom: 0.5rem;
    }
    .ailo-table-note {
        font-size: 12px;
        font-weight: 300;
        color: #907374;
        margin-bottom: 0.5rem;
    }
    [class*="st-key-ailo_dl_"] {
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    [class*="st-key-ailo_dl_"] button {
        background: transparent !important;
        border: 1px solid #CFCBC3 !important;
        border-radius: 999px !important;
        color: #491C1F !important;
        min-height: 0 !important;
        height: 1.5rem !important;
        padding: 0 0.6rem 1px 0.6rem !important;  /* 1px at the bottom puts the text at the optical middle */
        align-items: center !important;
        justify-content: center !important;
    }
    .ailo-footnote {
        font-size: 11px;
        font-style: italic;
        font-weight: 300;
        color: #907374;
        margin: 0 0 0.5rem 0;
    }
    [class*="st-key-ailo_dl_"] {
        align-items: center !important;
    }
    [class*="st-key-ailo_dl_"] > [data-testid="stElementContainer"]:has(.ailo-footnote) {
        margin-left: auto;
        width: auto !important;
        flex: 0 1 auto !important;
    }
    [class*="st-key-ailo_dl_"] .ailo-footnote {
        margin: 0;
        text-align: right;
    }
    [class*="st-key-ailo_dl_"] button:hover {
        border-color: #491C1F !important;
        background: rgba(73, 28, 31, 0.04) !important;
    }
    [class*="st-key-ailo_dl_"] button p {
        font-size: 10.5px !important;
        font-weight: 300 !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    [class*="st-key-ailo_dl_"] button > *,
    [class*="st-key-ailo_dl_"] button [data-testid="stMarkdownContainer"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        line-height: 1 !important;
    }
    .ailo-table,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        font-weight: 300;
        color: #322D29;
    }
    .ailo-table th,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] th {
        font-weight: 400 !important;
        font-size: 11px !important;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #491C1F !important;
        text-align: left;
        padding: 0.55rem 0.75rem;
        border: none;
        border-bottom: 1px solid #491C1F;
        background: transparent;
    }
    .ailo-table td,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] td {
        padding: 0.5rem 0.75rem;
        border: none;
        border-bottom: 1px solid #E9E5E0;
        background: transparent;
    }
    .ailo-table td.num,
    .ailo-table th.num {
        text-align: right;
        font-variant-numeric: tabular-nums;
    }
    .ailo-table tbody tr:hover td {
        background: rgba(73, 28, 31, 0.04);
    }
    /* Sample questions shown before the first message: small one-line chips */
    .st-key-ailo_examples {
        margin-bottom: -0.25rem;
    }
    /* Two chips per line (2 + 2): a zero-height full-width spacer is ordered between them */
    .st-key-ailo_examples [data-testid="stButtonGroup"] > div::before {
        content: "";
        order: 2;
        flex-basis: 100%;
        height: 0;
    }
    .st-key-ailo_examples [data-testid="stButtonGroup"] > div > :nth-child(-n+2) {
        order: 1;
    }
    .st-key-ailo_examples [data-testid="stButtonGroup"] > div > :nth-child(n+3) {
        order: 3;
    }
    .st-key-ailo_examples [data-testid="stWidgetLabel"] p {
        font-size: 11px !important;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #907374 !important;
        font-weight: 300 !important;
    }
    .st-key-ailo_examples button {
        background: transparent !important;
        border: 1px solid #CFCBC3 !important;
        border-radius: 999px !important;
        color: #322D29 !important;
        min-height: 0 !important;
        padding: 0.2rem 0.75rem !important;
        max-width: 100%;
        transition: border-color 0.2s ease, color 0.2s ease;
    }
    .st-key-ailo_examples button:hover {
        border-color: #491C1F !important;
        color: #491C1F !important;
    }
    .st-key-ailo_examples button p {
        font-size: 12px !important;
        font-weight: 300 !important;
        white-space: nowrap !important;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    /* Start screen: greeting sits higher than Streamlit's default 96px top margin */
    [data-testid="stMainBlockContainer"] {
        padding-top: 48px !important;
    }
    /* In a conversation (greeting hidden), start the chat just below the New chat button */
    body:has(.ailo-in-chat) [data-testid="stMainBlockContainer"] {
        padding-top: 40px !important;
    }
    /* Sidebar open/close: a thin chevron instead of Streamlit's double arrow */
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stExpandSidebarButton"],
    [data-testid="stExpandSidebarButton"] button {
        background: transparent !important;
        border: none !important;
    }
    [data-testid="stSidebarCollapseButton"] button > *,
    [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {
        display: none !important;
    }
    [data-testid="stSidebarCollapseButton"] button::before,
    [data-testid="stExpandSidebarButton"]::before {
        content: "";
        display: block;
        width: 22px;
        height: 22px;
        background-color: #491C1F;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M14.5 6.5 9 12l5.5 5.5'/%3E%3C/svg%3E") center / contain no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M14.5 6.5 9 12l5.5 5.5'/%3E%3C/svg%3E") center / contain no-repeat;
        transition: background-color 0.2s ease;
    }
    [data-testid="stExpandSidebarButton"]::before {
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9.5 6.5 15 12l-5.5 5.5'/%3E%3C/svg%3E") center / contain no-repeat;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9.5 6.5 15 12l-5.5 5.5'/%3E%3C/svg%3E") center / contain no-repeat;
    }
    [data-testid="stSidebarCollapseButton"] button:hover::before,
    [data-testid="stExpandSidebarButton"]:hover::before {
        background-color: #907374;
    }
    /* Sign-in button */
    .st-key-ailo_login {
        margin-top: 0.75rem;
    }
    .st-key-ailo_login button {
        background: #491C1F !important;
        border: 1px solid #491C1F !important;
        border-radius: 999px !important;
        min-height: 0 !important;
        padding: 0.3rem 1rem !important;
        color: #FFFFFF !important;
    }
    .st-key-ailo_login button p {
        color: #FFFFFF !important;
        font-size: 12px !important;
        font-weight: 300 !important;
    }
    .st-key-ailo_login button:hover {
        background: #5F373A !important;
        border-color: #5F373A !important;
    }
    /* Sidebar: saved chats */
    [data-testid="stSidebar"] {
        background: #EFECE8 !important;
        border-right: none !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebarResizeHandle"],
    [data-testid="stSidebarResizeHandle"]:hover,
    [data-testid="stSidebarResizeHandle"] * {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] .st-key-sidebar_new_chat button {
        background: transparent !important;
        border: 1px solid #CFCBC3 !important;
        border-radius: 999px !important;
        min-height: 0 !important;
        padding: 0.25rem 0.9rem !important;
        color: #491C1F !important;
    }
    [data-testid="stSidebar"] .st-key-sidebar_new_chat button:hover {
        background: #491C1F !important;
        border-color: #491C1F !important;
    }
    [data-testid="stSidebar"] .st-key-sidebar_new_chat button:hover p {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .st-key-sidebar_new_chat button p {
        font-size: 12px !important;
        font-weight: 300 !important;
        color: inherit;
    }
    [data-testid="stSidebar"] .st-key-sidebar_new_chat button p::before {
        content: "+";
        margin-right: 0.4rem;
    }
    /* New chat: 20px from the top, same as its distance to the left edge */
    [data-testid="stSidebar"] .st-key-sidebar_new_chat {
        margin-top: -56px;
    }
    .ailo-sidebar-label {
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #907374;
        margin: 1.25rem 0 0.25rem 0;  /* ~36px from New chat, ~20px to the block below */
    }
    .ailo-sidebar-empty {
        font-size: 12px;
        font-weight: 300;
        color: #907374;
        line-height: 1.5;
    }
    [class*="st-key-ailo_threads"] {
        gap: 0.1rem !important;
    }
    [class*="st-key-ailo_threads"] button {
        justify-content: flex-start !important;
        text-align: left;
        border-radius: 0.5rem !important;
        border: none !important;
        min-height: 0 !important;
        padding: 0.35rem 0.6rem !important;
        background: transparent !important;
        color: #322D29 !important;
    }
    [class*="st-key-ailo_threads"] button:hover {
        background: rgba(73, 28, 31, 0.06) !important;
        color: #491C1F !important;
    }
    [class*="st-key-ailo_threads"] button[kind="primary"],
    [class*="st-key-ailo_threads"] button[data-testid="stBaseButton-primary"] {
        background: rgba(73, 28, 31, 0.10) !important;
        color: #491C1F !important;
    }
    [class*="st-key-ailo_threads"] button p {
        font-size: 13px !important;
        font-weight: 300 !important;
        white-space: nowrap !important;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
    }
    [class*="st-key-ailo_threads"] button > div {
        min-width: 0;
        max-width: 100%;
        justify-content: flex-start;
    }
    /* Search field: same type size as the New chat button */
    [class*="st-key-chat_search"] input {
        font-size: 12px !important;
        font-weight: 300 !important;
        padding-top: 0.3rem !important;
        padding-bottom: 0.3rem !important;
    }
    [class*="st-key-chat_search"] [data-testid="stTextInputRootElement"] {
        min-height: 0 !important;
        height: 2.1rem !important;
    }
    [class*="st-key-chat_search"] input::placeholder {
        font-size: 12px !important;
        font-weight: 300 !important;
    }
    [class*="st-key-chat_search"] [data-testid="stIconMaterial"] {
        font-size: 16px !important;
    }
    /* The live-search script lives in an invisible iframe: take it out of the layout so it adds no gap */
    [data-testid="stSidebar"] [data-testid="stElementContainer"]:has(> iframe),
    [data-testid="stSidebar"] [data-testid="stElementContainer"]:has(iframe[height="0"]) {
        position: absolute !important;
        height: 0 !important;
        margin: 0 !important;
        overflow: hidden;
    }
    /* The search filters while typing, so Streamlit's "Press Enter to apply" hint is not needed */
    [class*="st-key-chat_search"] [data-testid="InputInstructions"] {
        display: none !important;
    }
    /* One row = one hover field. The three-dots menu floats over the right end of the title
       on hover and takes no room otherwise (like the Claude app). */
    [class*="st-key-ailo_threads"] {
        gap: 0 !important;
        margin-top: -0.25rem !important;  /* a little tighter to the search field */
        /* wider than the sidebar's padding so the hover bar sits closer to the edges */
        width: auto !important;
        max-width: none !important;
        margin-left: -0.6rem !important;
        margin-right: -0.6rem !important;
    }
    [class*="st-key-ailo_threads"] [data-testid="stHorizontalBlock"] {
        position: relative;
        gap: 0 !important;
        align-items: center !important;
        border-radius: 0.5rem;
    }
    [class*="st-key-ailo_threads"] [data-testid="stHorizontalBlock"]:hover {
        background: #E4E0DB;
    }
    [class*="st-key-ailo_threads"] [data-testid="stColumn"]:not(:has([class*="st-key-ailo_menu_"])) {
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 0 !important;
    }
    [class*="st-key-ailo_threads"] [data-testid="stColumn"]:has([class*="st-key-ailo_menu_"]) {
        position: absolute;
        right: 0.25rem;
        top: 50%;
        transform: translateY(-50%);
        width: auto !important;
        flex: none !important;
        min-width: 0 !important;
    }
    [class*="st-key-ailo_threads"] [data-testid="stHorizontalBlock"] button:hover {
        background: transparent !important;
    }
    [class*="st-key-ailo_threads"] button {
        padding: 0.2rem 0.6rem 0.2rem 0.65rem !important;  /* text lines up with the labels above */
    }
    [class*="st-key-ailo_threads"] [class*="st-key-ailo_menu_"] {
        opacity: 0;
        transition: opacity 0.15s ease;
    }
    [class*="st-key-ailo_threads"] [class*="st-key-ailo_menu_"] button {
        width: 1.5rem !important;
        height: 1.5rem !important;
        min-width: 0 !important;
        padding: 0 !important;
        justify-content: center !important;
        border-radius: 0.4rem !important;
        background: #E4E0DB !important;               /* hides the title text underneath */
        box-shadow: -0.6rem 0 0.5rem -0.1rem #E4E0DB;  /* soft fade into the title */
    }
    [class*="st-key-ailo_threads"] [class*="st-key-ailo_menu_"] button:hover {
        background: #D9D4CE !important;
    }
    [class*="st-key-ailo_threads"] [data-testid="stHorizontalBlock"]:hover [class*="st-key-ailo_menu_"],
    [class*="st-key-ailo_threads"] [data-testid="stHorizontalBlock"]:focus-within [class*="st-key-ailo_menu_"],
    [class*="st-key-ailo_threads"] [class*="st-key-ailo_menu_"]:has([aria-expanded="true"]) {
        opacity: 1;
    }
    @media (hover: none) {
        [class*="st-key-ailo_threads"] [class*="st-key-ailo_menu_"] { opacity: 1; }
    }
    /* Sidebar content fills the height so the footer can sit at the bottom */
    [data-testid="stSidebarUserContent"] {
        /* exactly the space below the sidebar header (76px): the footer is pinned at the bottom
           and only the chat list scrolls when there are more chats than fit */
        height: calc(100vh - 76px) !important;
        min-height: 0 !important;
        overflow: visible;  /* New chat sits partly above this box */
        padding-bottom: 20px !important;  /* same 20px as the left edge */
        display: flex;
        flex-direction: column;
    }
    [data-testid="stSidebarUserContent"] > div {
        flex: 1 1 auto;
        min-height: 0;
        display: flex;
        flex-direction: column;
    }
    [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {
        flex: 1 1 auto;
        min-height: 0;
    }
    /* The scrolling chat list. Side padding lets the hover bars reach past the content edge
       without being clipped. */
    [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"]:has([class*="st-key-ailo_threads"]) {
        flex: 1 1 auto !important;
        min-height: 0 !important;
        overflow-y: auto !important;
        width: auto !important;
        max-width: none !important;
        margin: 0 -20px 0 -0.6rem;   /* the scrollbar sits at the very edge of the sidebar */
        padding: 0 20px 0 0.6rem;     /* ...and the list keeps its usual width */
        scrollbar-width: thin;
        scrollbar-color: #CFCBC3 transparent;
    }
    [data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(> .st-key-ailo_sidebar_footer) {
        margin-top: auto !important;
        flex: 0 0 auto !important;  /* never squeeze the footer, or its text spills below */
    }
    .st-key-ailo_sidebar_footer {
        flex: 0 0 auto !important;
        padding-top: 0.75rem;
        gap: 0.25rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;  /* Streamlit's -16px would push the footer text past the bottom */
    }
    .st-key-ailo_sidebar_footer .ailo-sidebar-label {
        margin: 0 0 2px 0;
    }
    a.ailo-contact,
    a.ailo-contact:visited {
        display: block;
        line-height: 1.4;
        font-size: 12px;
        font-weight: 300;
        color: #491C1F !important;
        text-decoration: none;
    }
    a.ailo-contact:hover {
        text-decoration: underline;
    }
    .ailo-sidebar-user {
        font-size: 11px;
        font-weight: 300;
        color: #907374;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .ailo-after-account {
        margin-top: 0.75rem;  /* air between the account block and the contact block */
    }
    /* Sign out: same pill as New chat, right under "Signed in as ..." */
    [data-testid="stSidebar"] .st-key-logout {
        margin-top: 4px;
    }
    [data-testid="stSidebar"] .st-key-logout button {
        background: transparent !important;
        border: 1px solid #CFCBC3 !important;
        border-radius: 999px !important;
        min-height: 0 !important;
        padding: 0.25rem 0.9rem !important;
        color: #491C1F !important;
        transition: border-color 0.2s ease, background 0.2s ease;
    }
    [data-testid="stSidebar"] .st-key-logout button p {
        font-size: 12px !important;
        font-weight: 300 !important;
        color: inherit !important;
    }
    [data-testid="stSidebar"] .st-key-logout button:hover {
        background: #491C1F !important;
        border-color: #491C1F !important;
        color: #FFFFFF !important;
    }
    /* Avatars are hidden, but kept in the DOM so the user bubble can be targeted */
    [data-testid="stChatMessage"] > img[alt$="avatar"],
    [data-testid="stChatMessage"] > [data-testid="stChatMessageAvatarImage"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def animated_letters(text, start=0.4, step=0.08):
    """Wrap each letter in a span with a staggered animation delay (words kept unbroken)."""
    parts, i = [], 0
    for word in text.split(" "):
        letters = []
        for ch in word:
            letters.append(
                f'<span class="ailo-char" style="animation-delay:{start + i * step:.3f}s">'
                f"{html.escape(ch)}</span>"
            )
            i += 1
        parts.append(f'<span class="ailo-word">{"".join(letters)}</span>')
        i += 2  # small pause between words
    return " ".join(parts), start + i * step


def animated_words(text, start, step=0.16):
    """Wrap each word in a span with a staggered animation delay."""
    return " ".join(
        f'<span class="ailo-sub-word" style="animation-delay:{start + n * step:.3f}s">'
        f"{html.escape(word)}</span>"
        for n, word in enumerate(text.split(" "))
    )


def greeting():
    """Time-of-day greeting in the viewer's own timezone (the server runs in UTC)."""
    try:
        tz = ZoneInfo(st.context.timezone or "Europe/Copenhagen")
    except Exception:
        tz = ZoneInfo("Europe/Copenhagen")
    hour = datetime.now(tz).hour
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 18:
        return "Good afternoon"
    return "Good evening"


# The greeting is filled in further down, once we know whether a conversation has started
header_slot = st.empty()


def show_greeting(subtitle="What insights can I help with?"):
    title_html, title_end = animated_letters(f"{greeting()},")
    subtitle_html = animated_words(subtitle, start=title_end + 0.2)
    header_slot.markdown(
        f"""
        <div class="ailo-kicker">{html.escape(BRANDING["kicker"])}</div>
        <div class="ailo-title" aria-label="{greeting()},">{title_html}</div>
        <div class="ailo-subtitle">{subtitle_html}</div>
        """,
        unsafe_allow_html=True,
    )


# Bordeaux plus equal 12% steps towards white, used when a chart needs several colours
AILO_BORDEAUX_SCALE = ["#491C1F", "#5F373A", "#755255", "#8B6E70", "#A0898B", "#B6A4A5", "#CCBFC0"]

AILO_FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"

AILO_CHART_CONFIG = {
    "font": AILO_FONT,
    "title": {"font": AILO_FONT, "fontSize": 11, "fontWeight": 400, "color": "#491C1F", "anchor": "start"},
    "background": "transparent",
    "mark": {"color": "#491C1F"},
    # Thinner bars: each bar takes 40% of its slot (only bars, so heatmap cells stay full)
    "bar": {"color": "#491C1F", "discreteBandSize": {"band": 0.4}},
    "line": {"color": "#491C1F", "strokeWidth": 2},
    "point": {"color": "#491C1F", "filled": True, "size": 60, "opacity": 0.85},
    "arc": {"stroke": "#F5F3F1", "strokeWidth": 1.5},
    "range": {
        "category": AILO_BORDEAUX_SCALE,
        "ordinal": AILO_BORDEAUX_SCALE,
        "ramp": AILO_BORDEAUX_SCALE[::-1],
        "heatmap": AILO_BORDEAUX_SCALE[::-1],
    },
    "view": {"stroke": None},
    "padding": 16,
    "axis": {
        "grid": False,
        "labelColor": "#322D29",
        "titleColor": "#322D29",
        "labelFontWeight": 300,
        "titleFontWeight": 300,
        "labelFontSize": 11,
        "titleFontSize": 12,
        "labelPadding": 8,
        "titlePadding": 18,
        "domainColor": "#CFCBC3",
        "tickColor": "#CFCBC3",
    },
    "legend": {
        "labelColor": "#322D29",
        "titleColor": "#322D29",
        "labelFontWeight": 300,
        "titleFontWeight": 400,
    },
}


STACKABLE_MARKS = {"bar", "area"}


def _mark_type(mark):
    return mark.get("type") if isinstance(mark, dict) else mark


def darkest_at_bottom(view):
    """In stacked bars/areas, stack segments in colour order so the darkest shade sits at the bottom."""
    enc = view.get("encoding")
    if not isinstance(enc, dict) or _mark_type(view.get("mark")) not in STACKABLE_MARKS:
        return view
    color = enc.get("color")
    if not isinstance(color, dict) or "field" not in color or "order" in enc:
        return view
    if any(isinstance(enc.get(ch), dict) and enc[ch].get("stack") in (False, None) and "stack" in enc[ch]
           for ch in ("x", "y")):
        return view  # stacking explicitly turned off

    view = dict(view)
    enc = dict(enc)
    field, sort = color["field"], color.get("sort")
    if isinstance(sort, list):
        # Custom category order: stack by each value's position in that list
        view["transform"] = list(view.get("transform", [])) + [{
            "calculate": f"indexof({json.dumps(sort)}, datum[{json.dumps(field)}])",
            "as": "__ailo_stack_order",
        }]
        enc["order"] = {"field": "__ailo_stack_order", "type": "quantitative", "sort": "ascending"}
    else:
        direction = "descending" if sort == "descending" else "ascending"
        enc["order"] = {"field": field, "sort": direction}
    view["encoding"] = enc
    return view


DONUT_OUTER, DONUT_INNER = 140, 92


def as_donut(view):
    """Pies always render as a donut ring: a fixed outer radius and a large hole."""
    if _mark_type(view.get("mark")) != "arc":
        return view
    view = dict(view)
    mark = view["mark"] if isinstance(view["mark"], dict) else {"type": "arc"}
    view["mark"] = {**mark, "outerRadius": DONUT_OUTER, "innerRadius": DONUT_INNER}
    return view


def strip_fonts(obj):
    """Drop any font family the agent set, so the AILO font always applies."""
    if isinstance(obj, dict):
        return {
            k: strip_fonts(v)
            for k, v in obj.items()
            if not (k == "font" or k.endswith("Font"))
        }
    if isinstance(obj, list):
        return [strip_fonts(v) for v in obj]
    return obj


def title_text(title):
    """Plain text of a Vega-Lite title (string, list of lines or {text: ...})."""
    if isinstance(title, dict):
        title = title.get("text")
    if isinstance(title, list):
        title = " ".join(str(t) for t in title)
    return str(title).strip() if title else ""


def figure_title(text):
    if text:
        st.markdown(f'<div class="ailo-figure-title">{html.escape(text)}</div>', unsafe_allow_html=True)


def render_chart(spec):
    """Render a Vega-Lite spec from the agent in AILO style, with its title shown above in the kicker style."""
    spec = strip_fonts(dict(spec))
    figure_title(title_text(spec.pop("title", None)))
    spec = as_donut(darkest_at_bottom(spec))
    if isinstance(spec.get("layer"), list):
        spec["layer"] = [as_donut(darkest_at_bottom(layer)) for layer in spec["layer"]]
    if any(_mark_type(v.get("mark")) == "arc" for v in [spec, *spec.get("layer", [])] if isinstance(v, dict)):
        spec.setdefault("height", 2 * DONUT_OUTER + 20)
    spec["config"] = {**spec.get("config", {}), **AILO_CHART_CONFIG}
    st.vega_lite_chart(spec, use_container_width=True, theme=None)


NUMERIC_TYPES = {"FIXED", "NUMBER", "DECIMAL", "NUMERIC", "INT", "INTEGER", "BIGINT", "REAL", "FLOAT", "DOUBLE"}


def is_pct_column(col):
    """Columns the agent names with a _PCT suffix hold percent values (0-100)."""
    return str(col.get("name", "")).upper().endswith("_PCT")


def format_pct(num):
    """Same rounding as in the answers: whole numbers, one decimal below 10%, '<0.1%' for tiny values."""
    if num == 0:
        return "0%"
    if abs(num) < 0.1:
        return "<0.1%"
    value = Decimal(str(num))
    one_decimal = value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    if abs(one_decimal) < 10:
        return f"{one_decimal}%"
    return f"{value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)}%"


def humanize_value(value):
    """booking_portal -> Booking portal (display only; downloads keep the raw value)."""
    text = str(value)
    if re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", text):
        text = text.replace("_", " ")
        return text[:1].upper() + text[1:]
    return text


def column_label(col):
    name = str(col.get("name", ""))
    if is_pct_column(col):
        name = name[: -len("_PCT")]
    return name.replace("_", " ")


def format_cell(value, col):
    if value is None:
        return ""
    if is_pct_column(col):
        try:
            return format_pct(float(value))
        except (TypeError, ValueError):
            return html.escape(str(value))
    if (col.get("type") or "").upper() not in NUMERIC_TYPES:
        return html.escape(humanize_value(value))
    try:
        num = float(value)
    except (TypeError, ValueError):
        return html.escape(str(value))
    scale = col.get("scale")
    if num.is_integer() and not scale:
        return f"{int(num):,}"
    decimals = min(scale, 2) if isinstance(scale, int) and scale > 0 else 2
    return f"{num:,.{decimals}f}"


TABLE_DISPLAY_ROWS = 500
FILE_CARD_MIN_ROWS = 50   # bigger results are offered as a downloadable file instead of a long table
FILE_PREVIEW_ROWS = 10
EXTRACT_REQUEST = re.compile(
    r"\b(extract|export|download|csv|excel|xlsx|spreadsheet|file|udtr\w*|eksport\w*|fil)\b", re.I
)


EXCEL_REQUEST = re.compile(r"\b(excel|xlsx|spreadsheet|regneark)\b", re.I)


def wants_file(question):
    return bool(EXTRACT_REQUEST.search(question or ""))


def file_format(question):
    return "xlsx" if EXCEL_REQUEST.search(question or "") else "csv"


def table_dataframe(columns, rows):
    """The raw result as a DataFrame, with numeric columns as numbers (for downloads)."""
    df = pd.DataFrame(rows, columns=[c.get("name", f"col_{i}") for i, c in enumerate(columns)])
    for col in columns:
        if (col.get("type") or "").upper() in NUMERIC_TYPES:
            df[col["name"]] = pd.to_numeric(df[col["name"]], errors="coerce")
    return df


def safe_filename(title):
    name = re.sub(r"[^A-Za-z0-9]+", "_", title or "").strip("_").lower()
    return (name or BRANDING["file_prefix"])[:60]


def footnote_html(note):
    return f'<div class="ailo-footnote">{html.escape(note)}</div>'


def download_buttons(df, title, key, note=None):
    """CSV and Excel downloads of the full result, with an optional footnote on the same row."""
    name = safe_filename(title)
    excel = io.BytesIO()
    with pd.ExcelWriter(excel, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    with st.container(key=f"ailo_dl_{key}", horizontal=True):
        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{name}.csv",
            mime="text/csv",
            key=f"csv_{key}",
            on_click="ignore",
        )
        st.download_button(
            "Download Excel",
            excel.getvalue(),
            file_name=f"{name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"xlsx_{key}",
            on_click="ignore",
        )
        if note:
            st.markdown(footnote_html(note), unsafe_allow_html=True)


def table_html(columns, rows):
    is_num = [(c.get("type") or "").upper() in NUMERIC_TYPES for c in columns]
    head = "".join(
        f'<th class="{"num" if n else ""}">{html.escape(column_label(c))}</th>'
        for c, n in zip(columns, is_num)
    )
    body = "".join(
        "<tr>" + "".join(
            f'<td class="{"num" if n else ""}">{format_cell(v, c)}</td>'
            for v, c, n in zip(row, columns, is_num)
        ) + "</tr>"
        for row in rows
    )
    return (
        f'<div class="ailo-table-wrap"><table class="ailo-table"><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


def file_bytes(df, fmt):
    if fmt == "xlsx":
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Data")
        return buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return df.to_csv(index=False).encode("utf-8-sig"), "text/csv"


def render_file_card(columns, rows, title, key, fmt="csv"):
    """An extract offered as a single downloadable file: icon, file name, download button."""
    filename = f"{safe_filename(title)}.{fmt}"
    data, mime = file_bytes(table_dataframe(columns, rows), fmt)
    with st.container(key=f"ailo_file_{key}", horizontal=True, vertical_alignment="center"):
        st.markdown(
            f'<div class="ailo-file"><span class="ailo-file-icon"></span>'
            f'<span class="ailo-file-name">{html.escape(filename)}</span>'
            f'<span class="ailo-file-meta">{len(rows):,} rows</span></div>',
            unsafe_allow_html=True,
        )
        st.download_button(
            ":material/download:",
            data,
            file_name=filename,
            mime=mime,
            key=f"file_{key}",
            on_click="ignore",
            type="tertiary",
            help=f"Download {filename}",
        )


def render_table(table, key="table", as_file=False, fmt="csv"):
    """Render a result table from the agent: a styled table with downloads, or a file card for extracts."""
    result_set = table.get("result_set") or {}
    columns = (result_set.get("resultSetMetaData") or {}).get("rowType") or []
    rows = result_set.get("data") or []
    if not columns:
        return
    title = table.get("title") or ""
    if as_file or len(rows) > FILE_CARD_MIN_ROWS:
        render_file_card(columns, rows, title, key, fmt)
        return
    figure_title(title)
    note = (
        f'<div class="ailo-table-note">Showing {TABLE_DISPLAY_ROWS:,} of {len(rows):,} rows. '
        "Download for the full result.</div>"
        if len(rows) > TABLE_DISPLAY_ROWS else ""
    )
    st.markdown(table_html(columns, rows[:TABLE_DISPLAY_ROWS]) + note, unsafe_allow_html=True)
    download_buttons(table_dataframe(columns, rows), title, key)

# 1. Load configuration from Streamlit Secrets
HOST = st.secrets["SNOWFLAKE_HOST"]
PAT = st.secrets["SNOWFLAKE_PAT"]
DB = st.secrets["DATABASE"]
SCHEMA = st.secrets["SCHEMA"]
AGENT = st.secrets["AGENT_NAME"]

# 2. Define the REST endpoints
AGENT_URL = f"https://{HOST}/api/v2/databases/{DB}/schemas/{SCHEMA}/agents/{AGENT}"
URL = f"{AGENT_URL}:run"

HEADERS = {
    "Authorization": f"Bearer {PAT}",
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
}


THREADS_URL = f"https://{HOST}/api/v2/cortex/threads"
JSON_HEADERS = {
    "Authorization": f"Bearer {PAT}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Google sign-in is switched on by an [auth] section in the app's secrets. Without it the app
# runs with no sign-in and no saved chats (for local previews).
AUTH_ENABLED = "auth" in st.secrets

# With sign-in on, only signed-in viewers can ask questions. ALLOWED_EMAILS and ALLOWED_DOMAINS
# in the secrets limit who gets in; leave both out to let any Google account in.
REQUIRE_LOGIN = AUTH_ENABLED and st.secrets.get("REQUIRE_LOGIN", True)
ALLOWED_EMAILS = {e.strip().lower() for e in st.secrets.get("ALLOWED_EMAILS", [])}
ALLOWED_DOMAINS = {d.strip().lower().lstrip("@") for d in st.secrets.get("ALLOWED_DOMAINS", [])}


def is_allowed(email):
    if not (ALLOWED_EMAILS or ALLOWED_DOMAINS):
        return True
    email = (email or "").strip().lower()
    return email in ALLOWED_EMAILS or email.split("@")[-1] in ALLOWED_DOMAINS


def current_user_email():
    """The signed-in viewer's email, or None. DEV_USER_EMAIL is for local previews only."""
    if st.secrets.get("DEV_USER_EMAIL"):
        return st.secrets["DEV_USER_EMAIL"]
    if AUTH_ENABLED:
        try:
            if st.user.is_logged_in:
                return st.user.get("email")
        except Exception:
            return None
        return None
    # Without [auth], access is managed by Streamlit Cloud's sharing, which tells the app who the
    # signed-in viewer is. Locally Streamlit reports a placeholder address, which we ignore.
    try:
        email = st.user.get("email")
    except Exception:
        return None
    return email if email and email != "test@example.com" else None


def user_key(email):
    """A 16-character, non-reversible tag for the user's threads (Snowflake allows 16 bytes)."""
    return "u" + hashlib.sha256(email.strip().lower().encode()).hexdigest()[:15]


def create_thread(owner):
    try:
        resp = requests.post(THREADS_URL, headers=JSON_HEADERS, json={"origin_application": owner}, timeout=15)
        resp.raise_for_status()
        return resp.json().get("thread_id")
    except Exception:
        return None


def rename_thread(thread_id, name):
    try:
        requests.post(f"{THREADS_URL}/{thread_id}", headers=JSON_HEADERS,
                      json={"thread_name": name[:100]}, timeout=15).raise_for_status()
    except Exception:
        pass


PIN_MARK = "📌 "  # Threads have no pinned flag, so a pinned chat is a name with this prefix


def is_pinned(name):
    return (name or "").startswith(PIN_MARK)


def plain_name(name):
    """The chat title without the pin marker."""
    name = (name or "").strip()
    if name.startswith(PIN_MARK):
        name = name[len(PIN_MARK):].strip()
    return name or "Untitled chat"


def update_thread_name(thread_id, name):
    try:
        requests.post(f"{THREADS_URL}/{thread_id}", headers=JSON_HEADERS,
                      json={"thread_name": name[:100]}, timeout=15).raise_for_status()
        return True
    except Exception:
        return False


def delete_thread_api(thread_id):
    try:
        requests.delete(f"{THREADS_URL}/{thread_id}", headers=JSON_HEADERS, timeout=15).raise_for_status()
        return True
    except Exception:
        return False


@st.cache_data(ttl=300, show_spinner=False)
def list_threads(owner):
    """The user's own threads, newest first."""
    try:
        resp = requests.get(THREADS_URL, headers=JSON_HEADERS,
                            params={"origin_application": owner}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        threads = data if isinstance(data, list) else data.get("threads", data.get("data", []))
        threads = [t for t in threads if t.get("origin_application") in (None, owner)]
        return sorted(threads, key=lambda t: t.get("updated_on") or t.get("created_on") or 0, reverse=True)
    except Exception:
        return []


def thread_messages(thread_id):
    """All conversation messages in a thread, oldest first."""
    messages, last_id = [], None
    for _ in range(50):  # safety limit: 50 pages of 100 messages
        params = {"page_size": 100, "message_type": "conversation"}
        if last_id is not None:
            params["last_message_id"] = last_id
        resp = requests.get(f"{THREADS_URL}/{thread_id}", headers=JSON_HEADERS, params=params, timeout=20)
        resp.raise_for_status()
        page = resp.json().get("messages") or []
        messages.extend(page)
        if len(page) < 100:
            break
        last_id = page[-1].get("message_id")
    return sorted(messages, key=lambda m: (m.get("created_on") or 0, m.get("message_id") or 0))


def ui_message(role, payload):
    """Turn a stored thread message back into what the chat shows."""
    try:
        data = json.loads(payload) if isinstance(payload, str) else payload
    except (json.JSONDecodeError, TypeError):
        data = payload
    content = data.get("content") if isinstance(data, dict) else data if isinstance(data, list) else None
    if role == "user":
        if isinstance(content, list):
            text = " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
        else:
            text = data if isinstance(data, str) else ""
        return {"role": "user", "content": text.strip()}
    blocks = blocks_from_final(content) if isinstance(content, list) else []
    if not blocks:
        blocks = [{"type": "text", "data": data if isinstance(data, str) else ""}]
    return {"role": "assistant", "content": blocks}


def open_thread(thread_id):
    try:
        stored = thread_messages(thread_id)
    except Exception:
        st.session_state.thread_error = "Couldn't open that chat. Please try again."
        return
    st.session_state.messages = [
        ui_message(m.get("role"), m.get("message_payload"))
        for m in stored if m.get("role") in ("user", "assistant")
    ]
    st.session_state.thread_id = thread_id
    st.session_state.parent_id = stored[-1].get("message_id") if stored else 0
    for key in ("pending_prompt", "ailo_examples", "example_pick"):
        st.session_state.pop(key, None)


def iter_sse(response):
    """Yield (event, data) pairs from a server-sent events stream."""
    event, data_lines = None, []
    for line in response.iter_lines(decode_unicode=True):
        if line is None:
            continue
        if line == "":
            if data_lines:
                raw = "\n".join(data_lines)
                try:
                    yield event, json.loads(raw)
                except json.JSONDecodeError:
                    yield event, raw
            event, data_lines = None, []
        elif line.startswith("event:"):
            event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].lstrip())
    if data_lines:
        try:
            yield event, json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            pass


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_sample_questions():
    """Sample questions configured on the agent in Snowflake (empty list if unavailable)."""
    try:
        resp = requests.get(
            AGENT_URL,
            headers={"Authorization": f"Bearer {PAT}", "Accept": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        spec = resp.json().get("agent_spec") or {}
        if isinstance(spec, str):
            spec = json.loads(spec)
        questions = (spec.get("instructions") or {}).get("sample_questions") or []
        return [q["question"] for q in questions if isinstance(q, dict) and q.get("question")]
    except Exception:
        return []


def first_sentence(text):
    """Keep sample questions short: only the first sentence (up to and including ? . or !)."""
    match = re.match(r"\s*(.+?[?.!])(\s|$)", text, re.S)
    return (match.group(1) if match else text).strip()


MAX_EXAMPLES = 4


def new_chat():
    st.session_state.messages = []
    for key in ("pending_prompt", "ailo_examples", "example_pick", "thread_id", "parent_id"):
        st.session_state.pop(key, None)


def ask_example():
    choice = st.session_state.get("ailo_examples")
    if choice:
        st.session_state.pending_prompt = choice


def parse_chart_spec(raw_spec):
    if not raw_spec:
        return None
    return json.loads(raw_spec) if isinstance(raw_spec, str) else raw_spec


def find_queries(obj, found=None):
    """Collect {sql, explanation} pairs from a tool result (Cortex Analyst returns 'sql' and 'text')."""
    found = [] if found is None else found
    if isinstance(obj, dict):
        sql = obj.get("sql")
        if isinstance(sql, str) and sql.strip():
            explanation = obj.get("text") if isinstance(obj.get("text"), str) else ""
            found.append({"sql": sql.strip(), "explanation": explanation.strip()})
        for key, value in obj.items():
            if key != "sql":
                find_queries(value, found)
    elif isinstance(obj, list):
        for value in obj:
            find_queries(value, found)
    return found


def unique_queries(queries):
    seen, out = set(), []
    for q in queries:
        if q["sql"] not in seen:
            seen.add(q["sql"])
            out.append(q)
    return out


def blocks_from_final(content):
    """Turn the content of the final `response` event into our stored blocks."""
    blocks, queries = [], []
    for block in content or []:
        if block.get("type") == "tool_result":
            find_queries(block.get("tool_result", block), queries)
        block_type = block.get("type")
        if block_type == "text" and block.get("text"):
            blocks.append({"type": "text", "data": clean_text(block["text"])})
        elif block_type == "chart":
            spec = parse_chart_spec(block.get("chart", {}).get("chart_spec"))
            if spec:
                blocks.append({"type": "chart", "data": spec})
        elif block_type == "table" and block.get("table"):
            blocks.append({"type": "table", "data": block["table"]})
    if queries:
        blocks.append({"type": "queries", "data": unique_queries(queries)})
    return blocks


def render_queries(queries):
    """'How was this calculated?': the agent's reading of the question and the SQL it ran."""
    with st.expander("How was this calculated?"):
        for n, q in enumerate(queries):
            if len(queries) > 1:
                st.markdown(f'<div class="ailo-query-label">Query {n + 1}</div>', unsafe_allow_html=True)
            if q.get("explanation"):
                st.markdown(f'<div class="ailo-query-text">{html.escape(q["explanation"])}</div>',
                            unsafe_allow_html=True)
            st.code(q["sql"], language="sql", wrap_lines=True)


_MD_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_NUMBER = re.compile(r"^-?[\d,]*\.?\d+$")


def _md_row(line):
    """A table row. Leading and trailing pipes are optional in markdown tables."""
    return bool(line.strip()) and "|" in line


def _md_cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def split_markdown_tables(text):
    """Split an answer into plain text and markdown tables, so tables can get download buttons.
    Returns a list of ("text", str) and ("table", markdown_str, DataFrame, title)."""
    lines = (text or "").split("\n")
    parts, buf, i = [], [], 0
    while i < len(lines):
        if _md_row(lines[i]) and i + 1 < len(lines) and _MD_SEPARATOR.match(lines[i + 1]):
            j = i + 2
            while j < len(lines) and _md_row(lines[j]):
                j += 1
            header = _md_cells(lines[i])
            rows = [(_md_cells(l) + [""] * len(header))[: len(header)] for l in lines[i + 2 : j]]
            # a short line right above the table (a heading or label) belongs to it
            blanks = 0
            while buf and not buf[-1].strip():
                buf.pop()
                blanks += 1
            label = []
            while buf and buf[-1].strip():
                label.insert(0, buf.pop())
            heading_like = bool(label) and (
                label[-1].lstrip().startswith(("#", "**"))
                or not label[-1].rstrip().endswith((".", "!", "?", ":"))
            )
            if sum(len(l) for l in label) > 100 or not heading_like:
                buf.extend(label + [""] * blanks)
                label = []
            if buf:
                parts.append(("text", "\n".join(buf)))
                buf = []
            seen, columns = {}, []
            for h in header:
                seen[h] = seen.get(h, 0) + 1
                columns.append(h if seen[h] == 1 else f"{h} ({seen[h]})")
            df = pd.DataFrame(rows, columns=columns)
            for col in columns:
                if len(df) and df[col].map(lambda v: bool(_NUMBER.match(v))).all():
                    df[col] = pd.to_numeric(df[col].str.replace(",", ""), errors="coerce")
            title = re.sub(r"[#*:_`]+", "", " ".join(label)).strip()
            parts.append(("table", "\n".join(label + ([""] if label else []) + lines[i:j]), df, title))
            i = j
        else:
            buf.append(lines[i])
            i += 1
    if buf:
        parts.append(("text", "\n".join(buf)))
    return parts


_FOOTNOTE = re.compile(r"^\\?\*(?!\*)\s*(\S.{0,140})$")


def take_footnote(text):
    """If the text starts with a footnote line ("* fewer than 30 ..."), return (note, rest)."""
    lines = (text or "").split("\n")
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        match = _FOOTNOTE.match(line.strip())
        if match:
            return "* " + match.group(1).strip(), "\n".join(lines[:i] + lines[i + 1 :])
        break
    return None, text


def render_text(text, key):
    """Render an answer's text; every table in it also gets CSV and Excel downloads, and a footnote
    right under a table is shown small and italic on the row with the downloads."""
    cleaned = clean_text(text)
    parts = split_markdown_tables(cleaned)
    if not any(p[0] == "table" for p in parts):
        st.markdown(cleaned)
        return
    notes = {}
    for n, part in enumerate(parts):
        if part[0] == "table" and n + 1 < len(parts) and parts[n + 1][0] == "text":
            note, rest = take_footnote(parts[n + 1][1])
            if note:
                notes[n] = note
                parts[n + 1] = ("text", rest)
    for n, part in enumerate(parts):
        if part[0] == "text":
            if part[1].strip():
                st.markdown(part[1])
        else:
            st.markdown(part[1])
            note = notes.get(n)
            if len(part[2]) >= 2:
                download_buttons(part[2], part[3] or "table", f"{key}_t{n}", note=note)
            elif note:
                st.markdown(footnote_html(note), unsafe_allow_html=True)


def render_blocks(blocks, key="msg"):
    for i, item in enumerate(blocks):
        if item.get("type") == "text":
            render_text(item.get("data", ""), f"{key}_{i}")
        elif item.get("type") == "chart":
            render_chart(item.get("data"))
        elif item.get("type") == "queries":
            render_queries(item.get("data") or [])
        elif item.get("type") == "table":
            render_table(
                item.get("data") or {}, key=f"{key}_{i}",
                as_file=item.get("as_file", False), fmt=item.get("format", "csv"),
            )


def readable_status(text):
    """Snowflake sometimes sends bare codes like 'sandbox_ready' or 'RUNNING'; make them readable."""
    text = (text or "").strip()
    if text and " " not in text and (text.isupper() or "_" in text):
        text = text.replace("_", " ").lower().capitalize()
        text = re.sub(r"\bsql\b", "SQL", text, flags=re.I)
    return text


def show_status(placeholder, message):
    message = readable_status(message) or "Working"
    placeholder.markdown(
        f'<div class="ailo-status"><span class="ailo-dot"></span>{html.escape(message)}</div>',
        unsafe_allow_html=True,
    )

# 3. Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Optional sign-in: anyone can ask questions; signing in with Google saves the chats
EMAIL = current_user_email()
OWNER = user_key(EMAIL) if EMAIL else None

CONTACT_EMAIL = BRANDING["contact_email"]

# Sign-in gate: nothing else is shown until an allowed viewer has signed in
if REQUIRE_LOGIN and not EMAIL:
    show_greeting("Sign in to start asking questions.")
    with st.container(key="ailo_login"):
        st.button("Sign in with Google", on_click=st.login, args=("google",), key="login")
    st.stop()
if REQUIRE_LOGIN and not is_allowed(EMAIL):
    show_greeting("This demo is by invitation only.")
    st.markdown(
        f'<div class="ailo-sidebar-empty">{html.escape(EMAIL)} doesn\'t have access. '
        f'Write to <a class="ailo-contact" style="display:inline" href="mailto:{CONTACT_EMAIL}">'
        f"{CONTACT_EMAIL}</a> to get access.</div>",
        unsafe_allow_html=True,
    )
    with st.container(key="ailo_login"):
        st.button("Sign out", on_click=st.logout, key="logout_denied")
    st.stop()

# Live chat search: Streamlit only sends a text field's value on Enter, so a small script in the
# page hides the non-matching rows while typing (no rerun). The Python filter still applies on Enter.
LIVE_SEARCH_JS = """
<script>
(function () {
  const doc = window.parent.document;
  if (doc.getElementById("ailo-live-search")) return;
  const code = `
    (function () {
      function titleOf(row) {
        const p = row.querySelector("button p");
        if (!p) return "";
        const copy = p.cloneNode(true);
        copy.querySelectorAll("[role=img]").forEach(function (e) { e.remove(); });
        return copy.textContent.toLowerCase();
      }
      function apply() {
        const input = document.querySelector('[class*="st-key-chat_search"] input');
        const q = input ? input.value.trim().toLowerCase() : "";
        document.querySelectorAll('[class*="st-key-ailo_threads"] [data-testid="stHorizontalBlock"]')
          .forEach(function (row) {
            row.style.display = !q || titleOf(row).indexOf(q) !== -1 ? "" : "none";
          });
      }
      document.addEventListener("input", function (e) {
        if (e.target.closest && e.target.closest('[class*="st-key-chat_search"]')) apply();
      }, true);
      new MutationObserver(apply).observe(document.body, { childList: true, subtree: true });
    })();
  `;
  const el = doc.createElement("script");
  el.id = "ailo-live-search";
  el.textContent = code;
  doc.head.appendChild(el);
})();
</script>
"""



def rename_chat(thread_id, name, input_key):
    new = " ".join((st.session_state.get(input_key) or "").split())
    if not new:
        return
    if is_pinned(name):
        new = PIN_MARK + new
    if update_thread_name(thread_id, new):
        list_threads.clear()
    else:
        st.session_state.thread_error = "Couldn't rename that chat. Please try again."


def toggle_pin(thread_id, name):
    new = plain_name(name) if is_pinned(name) else PIN_MARK + plain_name(name)
    if update_thread_name(thread_id, new):
        list_threads.clear()
    else:
        st.session_state.thread_error = "Couldn't update that chat. Please try again."


def delete_chat(thread_id):
    if delete_thread_api(thread_id):
        list_threads.clear()
        if st.session_state.get("thread_id") == thread_id:
            new_chat()
    else:
        st.session_state.thread_error = "Couldn't delete that chat. Please try again."


def render_threads(slot, version=0):
    """The saved-chats list. Lives in a slot so it can be refreshed after an answer without a rerun."""
    with slot.container():
        threads = list_threads(OWNER)
        query = (st.session_state.get("chat_search") or "").strip().lower()
        if query:
            threads = [t for t in threads if query in plain_name(t.get("thread_name")).lower()]
        threads = sorted(threads, key=lambda t: not is_pinned(t.get("thread_name")))  # pinned first
        if not threads:
            text = "No chats match your search." if query else "Your chats will appear here."
            st.markdown(f'<div class="ailo-sidebar-empty">{text}</div>', unsafe_allow_html=True)
        current = st.session_state.get("thread_id")
        with st.container(key=f"ailo_threads_{version}"):
            for t in threads[:50]:
                tid = t.get("thread_id")
                name = t.get("thread_name") or ""
                title = plain_name(name)
                pinned = is_pinned(name)
                title_col, menu_col = st.columns([6, 1], gap="small", vertical_alignment="center")
                title_col.button(
                    title, key=f"thread_{tid}_{version}", on_click=open_thread, args=(tid,),
                    type="primary" if tid == current else "tertiary", use_container_width=True,
                    icon=":material/push_pin:" if pinned else None,
                )
                with menu_col.popover(":material/more_horiz:", key=f"ailo_menu_{tid}_{version}", help="Chat options"):
                    rename_key = f"rename_{tid}_{version}"
                    st.text_input("Rename chat", value=title, key=rename_key, max_chars=90)
                    st.button("Save name", key=f"save_{tid}_{version}", on_click=rename_chat,
                              args=(tid, name, rename_key), use_container_width=True)
                    st.button("Unpin" if pinned else "Pin to top", key=f"pin_{tid}_{version}",
                              on_click=toggle_pin, args=(tid, name), use_container_width=True,
                              icon=":material/keep:" if not pinned else ":material/keep_off:")
                    confirm_key = f"confirm_delete_{tid}_{version}"
                    if st.session_state.get(confirm_key):
                        st.caption("Delete this chat and all its messages permanently?")
                        st.button("Yes, delete", key=f"yes_{tid}_{version}", on_click=delete_chat,
                                  args=(tid,), use_container_width=True, type="primary")
                        st.button("Cancel", key=f"no_{tid}_{version}", use_container_width=True,
                                  on_click=lambda k=confirm_key: st.session_state.update({k: False}))
                    else:
                        st.button("Delete chat", key=f"delete_{tid}_{version}", use_container_width=True,
                                  icon=":material/delete:",
                                  on_click=lambda k=confirm_key: st.session_state.update({k: True}))


# Sidebar: New chat, saved chats (or the sign-in offer), and contact info at the bottom
with st.sidebar:
    st.button("New chat", on_click=new_chat, key="sidebar_new_chat", type="secondary")
    if OWNER:
        st.markdown('<div class="ailo-sidebar-label">Your chats</div>', unsafe_allow_html=True)
        st.text_input("Search chats", placeholder="Search chats", key="chat_search",
                      label_visibility="collapsed", icon=":material/search:")
        components.html(LIVE_SEARCH_JS, height=0)
    threads_slot = st.empty()
    if OWNER:
        render_threads(threads_slot)
    elif AUTH_ENABLED:
        st.markdown(
            '<div class="ailo-sidebar-label">Your chats</div>'
            '<div class="ailo-sidebar-empty">Sign in with Google to save your chats and find them '
            "here later. Without signing in, a chat is gone when you close the page.</div>",
            unsafe_allow_html=True,
        )
        with st.container(key="ailo_login"):
            st.button("Sign in with Google", on_click=st.login, args=("google",), key="login")

    with st.container(key="ailo_sidebar_footer"):
        signed_in = bool(OWNER and AUTH_ENABLED)
        if signed_in:
            st.markdown(f'<div class="ailo-sidebar-user">Signed in as {html.escape(EMAIL)}</div>',
                        unsafe_allow_html=True)
            st.button("Sign out", on_click=st.logout, key="logout", type="secondary")
        st.markdown(
            f'<div class="ailo-contact-block{" ailo-after-account" if signed_in else ""}">'
            '<div class="ailo-sidebar-label">Questions or feedback?</div>'
            f'<a class="ailo-contact" href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></div>',
            unsafe_allow_html=True,
        )

if st.session_state.get("thread_error"):
    st.toast(st.session_state.pop("thread_error"))

# The pinned bottom area holds the example questions (filled below) just above the chat input.
# The input is read first so the examples can disappear in the same run a question is asked.
bottom = getattr(st, "bottom", None) or getattr(st, "_bottom", st)  # st._bottom is deprecated
examples_slot = bottom.empty()
prompt = st.chat_input("Ask a question about your data...") or st.session_state.pop("pending_prompt", None)

# Greeting only on the empty start screen; it disappears as soon as the first question is sent
if not st.session_state.messages and not prompt:
    show_greeting()

# Example questions from the agent's Snowflake config, until the first question is asked
if not st.session_state.messages and not prompt:
    all_examples = list(dict.fromkeys(first_sentence(q) for q in fetch_sample_questions()))
    # A random few (MAX_EXAMPLES) per visit / new chat, kept stable while the page is open
    if all_examples and not st.session_state.get("example_pick"):
        # Own OS-backed random source, so nothing that seeds the global `random` can fix the pick
        st.session_state.example_pick = random.SystemRandom().sample(
            all_examples, min(MAX_EXAMPLES, len(all_examples))
        )
    examples = st.session_state.get("example_pick")
    if examples:
        examples_slot.pills(
            "Try asking",
            examples,
            selection_mode="single",
            key="ailo_examples",
            on_change=ask_example,
        )

# Marker the CSS uses to pull the chat up once a conversation has started
if st.session_state.messages or prompt:
    st.markdown('<div class="ailo-in-chat"></div>', unsafe_allow_html=True)


# Render past chat history
for n, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar=AVATARS[msg["role"]]):
        if msg["role"] == "assistant":
            # Same layout as a live answer (status slot + body), so Streamlit swaps it in place
            # instead of leaving a faded copy of the previous answer on screen
            st.empty()
            with st.empty().container():
                render_blocks(msg["content"] if isinstance(msg["content"], list) else
                              [{"type": "text", "data": msg["content"]}], key=f"m{n}")
        elif isinstance(msg["content"], list):
            render_blocks(msg["content"], key=f"m{n}")
        else:
            st.markdown(msg["content"])

# 4. Handle new user input
if prompt:
    # Display and record user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(prompt)

    # 5. Call the Snowflake Cortex API (streamed, so long analyses show progress)
    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        status_ph = st.empty()
        body_ph = st.empty()
        show_status(status_ph, "Thinking")

        # Format messages for Cortex Agent schema
        api_messages = []
        for msg in st.session_state.messages:
            content_text = ""
            if isinstance(msg["content"], str):
                content_text = msg["content"]
            elif isinstance(msg["content"], list):
                # Combine text fragments for message history context
                content_text = " ".join(
                    item.get("data", "")
                    for item in msg["content"]
                    if item.get("type") == "text"
                )

            api_messages.append({
                "role": msg["role"],
                "content": [{"type": "text", "text": content_text}],
            })

        payload = {
            "messages": api_messages,
            "stream": True,
        }

        # Saved chats: run inside the user's Snowflake thread. The agent then keeps the
        # conversation itself, so only the new question is sent.
        thread_id = st.session_state.get("thread_id")
        is_new_thread = False
        if OWNER and not thread_id:
            thread_id = create_thread(OWNER)
            is_new_thread = bool(thread_id)
            if thread_id:
                st.session_state.thread_id = thread_id
                st.session_state.parent_id = 0
        if OWNER and thread_id:
            payload["thread_id"] = thread_id
            payload["parent_message_id"] = st.session_state.get("parent_id") or 0
            payload["messages"] = api_messages[-1:]
        new_parent_id = None

        texts = {}       # content_index -> streamed text
        charts = []      # charts seen during the stream (fallback)
        tables = []      # tables seen during the stream (fallback)
        queries = []     # SQL the agent ran (fallback)
        final_blocks = None
        error_msg = None

        try:
            with requests.post(
                URL, headers=HEADERS, json=payload, stream=True, timeout=(10, 900)
            ) as response:
                response.raise_for_status()
                response.encoding = "utf-8"

                for event, data in iter_sse(response):
                    if not isinstance(data, dict):
                        continue

                    if event == "response.status":
                        show_status(status_ph, data.get("message") or "Working")
                    elif event == "response.tool_result.status":
                        show_status(status_ph, data.get("message") or data.get("status") or "Running query")
                    elif event == "response.thinking.delta":
                        show_status(status_ph, "Thinking")
                    elif event == "response.text.delta":
                        idx = data.get("content_index", 0)
                        texts[idx] = texts.get(idx, "") + data.get("text", "")
                        body_ph.markdown(clean_text("\n\n".join(texts[i] for i in sorted(texts))))
                    elif event == "response.chart":
                        spec = parse_chart_spec(data.get("chart_spec"))
                        if spec:
                            charts.append(spec)
                    elif event == "response.table":
                        tables.append(data)
                    elif event == "response.tool_result":
                        find_queries(data, queries)
                    elif event == "metadata":
                        meta = data.get("metadata", data)
                        if meta.get("message_id") is not None and meta.get("role") == "assistant":
                            new_parent_id = meta["message_id"]
                        elif meta.get("message_id") is not None and new_parent_id is None:
                            new_parent_id = meta["message_id"]
                    elif event == "error":
                        error_msg = data.get("message") or "The agent returned an error."
                        break
                    elif event == "response":
                        final_blocks = blocks_from_final(data.get("content"))

        except requests.exceptions.RequestException as e:
            error_msg = f"API Error: {e}"
            if getattr(e, "response", None) is not None:
                error_msg += f"\n\n{e.response.text}"

        status_ph.empty()

        if final_blocks is None:
            # Stream ended without a final event: keep what we received
            final_blocks = [
                {"type": "text", "data": clean_text(texts[i])} for i in sorted(texts) if texts[i]
            ] + [{"type": "table", "data": t} for t in tables] + [{"type": "chart", "data": c} for c in charts]
            if queries:
                final_blocks.append({"type": "queries", "data": unique_queries(queries)})

        for block in final_blocks:
            if block.get("type") == "table":
                block["as_file"] = wants_file(prompt)
                block["format"] = file_format(prompt)

        with body_ph.container():
            # Same key the message gets in the history, so its download buttons keep their identity
            render_blocks(final_blocks, key=f"m{len(st.session_state.messages)}")
            if error_msg:
                st.error(error_msg)

        if final_blocks:
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_blocks,
            })

        if OWNER and thread_id:
            if new_parent_id is not None:
                st.session_state.parent_id = new_parent_id
            if is_new_thread:
                rename_thread(thread_id, first_sentence(prompt))
            list_threads.clear()
            if not error_msg:
                # Refresh the sidebar in place. A full rerun blanks every answer while it reloads.
                render_threads(threads_slot, version=1)
