# Interface acceptance

The interface uses a forest green navigation area, warm neutral workspace and teal
controls. The same styling applies to input, verification, simulation and evaluation.
Canvas cards show conversation, workflow graphs and conceptual maps together.
Select a step or edge to see its responsibility, condition and source passages.
User and model content is rendered as plain text; raw JSON is available only in
explicit report downloads.

Desktop controls support dragging, background panning, centered zoom, reset and
fitting all cards. Focus a card heading and use arrow keys to reposition it. On
narrow screens, cards stack vertically and diagrams scroll within their cards.
Mobile users can scroll long workflows horizontally without widening the page.
Board state lasts for the current Streamlit session; saved analyses and guided
drafts are durable, but chat transcripts are not yet a durable archive.

## Repeatable browser check

Install `.[dev,browser]`, then `python -m playwright install chromium`.
Run `python tests/browser_check.py`. An installed Chrome binary can instead be
provided with `--browser-path`. Screenshots and logs go to `.local/browser-results`.
The runner starts its own fixture server on an available local port, uses synthetic
data and does not access the production database or ChatGPT account.

Checked on 2026-11-12 using Chrome at 1440×1100 and 390×844: source selection by
keyboard, distinct parallel and loop routes, keyboard card movement, zoom/reset,
fit-all visibility, exact query display without duplicate submission, layout
retention across reruns, mobile stacking with no page overflow, card removal and
absence of JavaScript errors. Desktop and mobile screenshots were visually reviewed.
This is targeted browser acceptance, not a comprehensive accessibility certification.
