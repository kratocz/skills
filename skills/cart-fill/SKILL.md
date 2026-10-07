---
name: cart-fill
description: "Fill e-shop carts in the user's own logged-in browser from a vetted item list — each item added by exact part number from the product detail page (listing-card buttons often report success and add nothing), quantities set, then the whole cart read back: lines, pre-ticked paid extras (insurance, gift wrap, extended returns), delivery preselection and totals with an arithmetic check; anything the user did not ask for is reported, never removed, and the order button is never pressed. Use when the user says „naházej mi to do košíku", „přidej do košíku", „nachystej mi košík", „dej mi to do košíku, ať v tom neudělám chybu", \"add these to my cart\", \"put it in the basket\", \"fill my cart\", \"prepare the cart for me\". Not for finding or comparing prices — that is a research task; not for completing the order — that stays with the user."
license: MIT
---

# cart-fill — procedure

A cart is a draft, not a purchase: everything here is reversible, which is exactly why the agent may do it and must stop one click short of the order. The failure modes this skill exists for were all met on 2026-10-04/05 across two shops: a listing-card "add to cart" button that showed a success message and added nothing; an add dialog whose extras (insurance, gift wrapping) read as "on" to the accessibility layer while being unticked in the DOM; a price that moved +21.5 % between the morning research and the evening cart; and a paid service sitting in the cart that the agent had not added — it was the user's, and removing it would have been the real mistake.

Every quoted user-facing string below is an example written in Czech; phrase the actual report in the language the user is using.

## 0. Input contract

Work only from a vetted list: shop, exact model or part number, quantity, expected price, condition (new, not refurbished/opened unless the user said so). Each line should come from a prior research step the user approved; this skill does not choose products. A line missing the part number or the expected price → ask before adding („U jedné položky nemám přesné PN — myslíš tuhle variantu, nebo tu s jiným číslem?"). Never substitute a similar product silently; if the exact item is gone, report it and leave the line out.

## 1. The browser session

Use the user's own browser session, already logged in — that is what makes the cart theirs. Open your own tab, do not reuse or close tabs the user has open. Before adding anything, confirm the header shows the user as logged in (a name, an account menu); an anonymous cart is a different cart and vanishes with the session. Decline non-essential cookies if a banner appears; do not accept terms or change account settings. Closing your last tab may dissolve the automation's tab group — re-read the tab context before the next action rather than reusing stale tab ids.

## 2. Add from the product detail page, never from a listing card

For each line: search the shop by part number (on Alza the search URL `search.htm?exps=<PN>` works where product-id URLs 404; a product name without the part number may return unrelated items — toys, accessories). Open the product detail and verify, in this order: name, part number on the page, price against the expected price, availability (in stock vs "at supplier"/pre-order), condition (the new-item tab, not the opened/refurbished one). Where the page has a quantity field, set it before adding; otherwise add once and raise the quantity in the confirmation dialog or in the cart.

Click the detail page's own add button. If nothing visible happens — no dialog, the header item count unchanged — the click on the element reference did not register: click by screen coordinates on the button instead, then re-check. Treat the shop's own confirmation (a dialog saying the item was added, the header count incremented, a cart-value popup) as the only proof; a "Added" badge on a listing card is not.

Price drift: add the item anyway (the cart is reversible) but record the delta; availability drift to "at supplier" or pre-order → do not add, report. A price more than a few percent off the expected one is the first line of the final report, not a footnote.

## 3. Extras in the add dialog

Shops pre-offer paid extras in the add dialog: extended warranty, gift wrapping, longer return windows, "PC upgrade" services. Read their state from the DOM (`input[type=checkbox]` → `checked`), not from the accessibility label — a checkbox whose value is literally "on" is reported as "on" by page readers while unchecked. Never tick anything. Close the dialog with "continue shopping", not with the button that proceeds to checkout.

## 4. Multi-shop lists

Finish one shop completely — add, verify its cart — before starting the next; two half-filled carts are harder to reconcile than one wrong one. Record each shop's cart total as the shop shows it, with and without VAT where both are displayed.

## 5. Read the cart back

Open the real cart page (Alza: `Order1.htm`; Senetic: no `/cart` URL — the mini-cart opens from the header icon) and extract every line: product name, part number, quantity, unit price, line total; every service line and whether it is selected (DOM state again); the preselected delivery and payment method; the totals. Check the arithmetic — sum of line totals plus selected services must equal the total; a mismatch means a selected service or a changed price you have not seen. Compare against the input list line by line.

## 6. The report

A table per shop: item, quantity, price, availability/delivery as the shop states it, then the shop total. Then, in this order:

1. anything that differs from the vetted list — price deltas, quantities, items not added and why;
2. anything in the cart the user did not ask for — a paid service, a leftover item — **reported, not removed**: „V košíku je navíc placená služba (prodloužené vrácení) u jedné položky, kterou jsem nepřidával; nechal jsem ji tam, může být tvoje." Remove only on the user's explicit instruction, because the cart may hold their own choices;
3. what the user should do at checkout that the agent cannot: order as a private person where a B2B-oriented shop would otherwise drop the 14-day withdrawal right; re-read price and stock if hours or days pass before they order — carts do not freeze prices;
4. the explicit statement that no order was placed.

## 7. Never

Never press order, checkout, pay or confirm; never enter or change address, payment or account details; never apply or remove discount codes, loyalty points or vouchers; never delete lines you did not add; never accept terms. Close your own tabs when done.

## Shop quirks (verified dates)

- **Alza (2026-10-04/05):** listing-card "Do košíku" shows „Přidáno do košíku" and adds nothing — use the detail page. The add dialog has −/+ quantity controls and pre-offers insurance and gift wrapping unticked. Cart at `Order1.htm`; the header cart link's `title` carries the count („Přejít do košíku - aktuálně N položek"). Page-reading right after navigation may still see the previous page — wait a couple of seconds before reading.
- **Senetic (2026-10-04):** quantity field on the detail page before "Přidat do košíku"; each add opens a popup with „Hodnota košíku" excluding and including VAT, which doubles as the running total; `/cart` returns 404, the mini-cart opens from the header icon and lists per-line delivery dates. Prices moved +21.5 % within one day on a RAM module — always re-read before the user orders.
