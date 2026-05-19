# KidZora — Full Project Audit & Improvement Plan
> Generated: March 8, 2026  
> Stack: Flask · Supabase (PostgreSQL + Storage + Auth) · Bootstrap 5 · Vanilla JS

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Architecture & Cross-Module Connections](#2-architecture--cross-module-connections)
3. [Auth / Registration Module](#3-auth--registration-module)
4. [Buyer Module](#4-buyer-module)
5. [Seller Module](#5-seller-module)
6. [Rider Module](#6-rider-module)
7. [Admin Module](#7-admin-module)
8. [Shared / Cross-Cutting Concerns](#8-shared--cross-cutting-concerns)
9. [Styles & Frontend](#9-styles--frontend)
10. [Database & Backend Services](#10-database--backend-services)
11. [Security](#11-security)
12. [Priority Summary](#12-priority-summary)

---

## 1. Project Overview

KidZora is a Philippine kids-focused marketplace with four user roles:

| Role   | Purpose |
|--------|---------|
| **Buyer** | Browses and purchases second-hand & new kids items |
| **Seller** | Lists products, manages inventory/orders/coupons |
| **Rider** | Accepts delivery jobs, completes order deliveries |
| **Admin** | Platform oversight, approvals, payouts, analytics |

**Current state:** ~80 % of the core happy-path is implemented. Most missing pieces are edge-case flows, payment integration, real-time polish, and missing CSS files.

---

## 2. Architecture & Cross-Module Connections

### Data Flow Diagram (text)
```
Buyer ──(places order)──► Order Table ──(triggers notify)──► Seller notified
                                 │
                  Seller ──(confirms/prepares)──► Order status updated
                                 │
                  Rider ──(accepts from "available" pool)──► Rider assigned
                                 │
                  Rider ──(delivers)──► Buyer confirms "Completed"
                                 │
              Commission auto-calculated ──► Admin sees in analytics
                                 │
              Seller requests payout ──► Admin approves/rejects
```

### What's Connected ✅
- `orders` table is the central hub; all four roles read/write to it
- `notifications` table receives events from `services/notify.py` — all roles
- `messages` table powers the real-time chat between buyer↔seller and buyer↔rider
- `order_items` → `products` → `product_variants` chain is fully wired
- `return_requests` flows buyer → seller → admin (escalation path)
- `rider_ratings` — buyers can rate riders after delivery
- `product_reviews` — buyers can review products after completed orders
- Email service (`services/email.py`) fires on key order lifecycle events
- Payout path: seller earns → requests payout → admin approves → funds released

### What's Disconnected / Missing 🔴
- [x] **Rider ↔ Seller chat** — AJAX-based embedded chat added to `rider/delivery_detail.html` and `seller/order_detail.html`; uses existing `rider.chat_send/poll/typing` and `seller.chat_send/poll/typing` endpoints with 3-second polling and typing indicators
- [x] **Admin ↔ Any user direct message** — Message button added to `users_list.html` (all non-admin roles) and `users_pending.html` (sellers & riders); "Message User" button added to the user detail modal footer via `users-list.js`; backend `admin.chat_with_seller` route already handled all users
- [x] **Buyer ↔ Admin contact** — Full support ticket system built: `support_tickets` + `support_replies` DB tables (`Database_Setup_Step27_Support_Tickets.sql`); buyer routes `buyer.support` (list + create) / `buyer.support_detail` (thread + reply); admin routes `admin.support_tickets` (queue with status/priority/category filters) / `admin.support_detail` (thread + admin reply + status/priority controls); "Help" link added to buyer navbar; "Support Tickets" added to admin sidebar; in-app notifications fire on new ticket, buyer reply, admin reply, and status change
- [x] **Order → Rider rating** — the `rider_ratings` DB table exists and the rider can see ratings, but there is **no UI in the buyer's order detail to submit a rating** to a rider
- [x]**Delivery fee** is calculated in `checkout.py` but the `delivery_fee` column on orders is not guaranteed to be read back correctly in the rider earnings calculation (rider earnings use `order.delivery_fee`)
- [x] **Commission rate inconsistency**: all hard-coded constants removed; every file now reads `current_app.config['COMMISSION_RATE']` which is driven by `config.py` (default `0.05`, overridable via `COMMISSION_RATE` env var). Files fixed: `checkout.py`, `seller/analytics.py`, `seller/payouts.py`, `admin/analytics.py`, `admin/reports.py`, `models/transaction.py`, `buyer/orders.py`

---

## 3. Auth / Registration Module

### What's Implemented ✅
- Login with email + password (Supabase Auth)
- Registration for buyer, seller, and rider (multi-step with document upload)
- Email verification flow
- Forgot password / reset
- "Banned" user page
- Role-based redirect after login

### What's Missing / Needs Work 🔴

#### Missing Features
- [ ] **Social login** (Google / Facebook OAuth) — no integration at all
- [ ] **Two-factor authentication (2FA / OTP)** — not implemented
- [ ] **Email change flow** — users cannot change their email address
- [ ] **Account deletion / data export** — no GDPR-compliant self-service delete
- [ ] **Remember me** — `login_user()` is called without the `remember=True` option wired to a checkbox
- [ ] **Session expiry notice** — users get a silent redirect to login with no "your session expired" message

#### Needs Cleanup / Upgrade
- [ ] **Multiple duplicate registration templates** exist: `register.html`, `register_fixed.html`, `register_single.html`, `register_step1.html`, `register_terms.html` — only one canonical flow should remain; dead files should be deleted
- [ ] Password change uses a raw `requests.put()` call directly to Supabase Admin REST API — should be moved into a dedicated helper in `services/` or `utils/`
- [ ] Registration validation is mostly server-side only; add client-side validation (password strength meter, real-time "email already taken" check)
- [ ] No rate limiting on the login endpoint — brute-force risk

---

## 4. Buyer Module

### What's Implemented ✅
- Unified landing page (authenticated + public view)
- Product browse with search, category, age-group, condition, price filters
- Product detail page with variant selection, reviews display, seller shop preview
- Session-based cart with quantity controls and stock validation
- Checkout with Philippine region-based delivery fees and coupon application
- Orders list with progress-step tracker
- Order detail with status history
- Return / refund request with file evidence upload (up to 5 files × 30 MB)
- Product reviews (submit + media upload, requires completed order)
- Wishlist (toggle add/remove, AJAX + form fallback)
- Chat inbox (buyer ↔ seller real-time messages)
- In-app notifications page (marks all read on view)
- Profile settings (name, address, avatar, password change)

### What's Missing 🔴

#### High Priority
- [x] **Rate your Rider** — star-rating card added to the right column of `buyer/order_detail.html` under "Your Rider"; interactive 1–5 star form posts to `buyer.rate_rider`; shows read-only stars + Edit button when already rated; `rider_rating` data fetched in `order_detail` route and `rate_rider` POST route handles upsert with `on_conflict='order_id'`
- [x] **Cart persistence** — `cart_items` DB table added (`Database_Setup_Step31_Cart_Items.sql`); `_db_sync()` writes full cart to DB on every mutation; `_db_load()` restores it when session is missing; `_get_cart()` auto-restores from DB on session expiry; `_save_cart()` always syncs to DB; login handler in `auth.py` merges DB cart into session so cart survives logout/session expiry/device switch
- [ ] **Payment gateway** — checkout only supports COD (Cash on Delivery). GCash / PayMaya / credit card integration (e.g., Paymongo) is completely missing
- [x] **Order cancellation by buyer** — "Request Cancellation" button in `buyer/order_detail.html` for `pending`/`confirmed` orders; `cancel_order` POST route at `/buyer/orders/<id>/cancel`; `pending` orders cancel immediately, `confirmed` orders create a `pending_review` request for the seller; banners show pending/rejected state; seller receives notification via `notify_cancel_requested`

#### Medium Priority
- [x] **Saved / multiple delivery addresses** — profile stores only one address; buyer can't save multiple shipping addresses and pick one at checkout
- [x] **Reorder** — "Buy Again" button on completed and cancelled orders (list + detail); `reorder` POST route re-adds all still-available items to cart, skips OOS items with warnings, redirects to cart
- [x] **Recently viewed products** — session-based tracking in `product_detail` (max 10, most-recent-first); fetched in `dashboard.py` filtering inactive products; displayed as "Recently Viewed" card grid on landing page before New Arrivals
- [ ] **Product comparison** — no side-by-side comparison feature
- [ ] **Bundle / gift sets** — no bundle product type
- [x] **Seller follow / subscribe** — `seller_follows` DB table; follow/unfollow AJAX toggle at `POST /buyer/shop/<id>/follow`; Follow button on shop page + product detail seller card; "Shops You Follow" grid on landing page; `push_new_product` notifies all followers when seller lists a new active product

#### Low Priority
- [ ] **Live order tracking map** — GPS-based delivery map using rider location
- [ ] **Loyalty points / referral program** — no points system
- [x] SEO meta tags per page (title, description, og:image) are missing from most templates
- [x] `browse.html` and `shop.html` clearly differentiated — `browse.html` is the multi-seller catalog (full search + filter, now shows "by [Shop Name]" seller attribution on every card linking to the store); `shop.html` is a single-seller storefront (store banner, follow button, now has "Browse Products → Store Name" breadcrumb establishing hierarchy); seller names batch-fetched in `browse_products()` route; active category pill highlighted in shop filter

#### Styles / UX
- [x] No dedicated CSS file for `checkout.html` — created `static/css/buyer/checkout.css`; all inline styles extracted to named classes (`checkout-summary-sticky`, `checkout-item-img`, `coupon-card`, `coupon-stripe`, etc.); linked via `{% block extra_css %}`
- [x] No dedicated CSS for `notifications.html`, `profile.html`, `returns.html`, `wishlist.html`, `inbox.html` — dedicated CSS files created in `static/css/buyer/`; inline `<style>` blocks and `style=""` attributes extracted; `profile.html` inline script also extracted to `static/js/buyer/profile.js`
- [x] Browse page filter sidebar collapses on mobile but state is not remembered after filter submit — mobile-only `#browseFilterPanel` collapse added; `browse.js` (new) auto-opens if filters active, persists open/close choice in `sessionStorage`; `browse.css` (new) hides panel on `<768px`, always visible on `md+`
- [x] Cart empty state graphic could be improved — replaced plain icon with an inline SVG illustrated cart (floating animation, gold star + pink dot decorations, kids-theme colour palette); added "My Favourites" CTA alongside "Browse Products"; inline `<style>` block extracted to `static/css/buyer/cart.css`
- [x] Checkout page order summary sticky sidebar on mobile — `.checkout-summary-sticky` reverts to `position:static` at `<992px` via media query in `checkout.css`

---

## 5. Seller Module

### What's Implemented ✅
- Dashboard with order counts, revenue snapshot
- Product CRUD (create, edit, delete) with image upload and product variants
- Order management (view, update status: pending → confirmed → preparing → ready_for_pickup → out_for_delivery → cancelled)
- Order detail with buyer info and items
- Return request review (approve / reject / escalate to admin)
- Return detail
- Product reviews list with reply / delete-reply
- Seller-level coupons (create, edit, delete, toggle active)
- Analytics page (revenue charts by daily/weekly/monthly/yearly)
- Payout request (earnings summary, withdrawal request form)
- Chat inbox (seller ↔ buyer)
- Seller notifications page
- Profile settings (business info, address, avatar, password)

### What's Missing 🔴

#### High Priority
- [x] **Low-stock / out-of-stock alerts** — `push_low_stock()` + `LOW_STOCK_THRESHOLD = 5` added to `services/notify.py`; hooked into both variant and non-variant stock deduction paths in `buyer/checkout.py` (STEP 4); fires `'low_stock'` or `'out_of_stock'` ntype to seller with direct link to `/seller/products/{id}/edit`; seller notifications template updated with matching icons/colours; all calls fire-and-forget wrapped in `try/except`
- [ ] **Bulk product upload** — no CSV/Excel import for sellers with large catalogs
- [x] **Commission rate fix** — all files now read `current_app.config['COMMISSION_RATE']`; no more hard-coded values
- [x] **Product deletion is permanent** — `is_deleted BOOLEAN DEFAULT FALSE` column added (`Database_Setup_Step32_Soft_Delete_Products.sql`); seller "Delete" action replaced with soft-archive (`is_deleted=True, is_active=False`); new `product_restore` route restores to inactive; products list has "Archived" status filter showing archived count badge; archived rows are dimmed with Restore button; all public buyer queries (`browse`, `shop`, `product_detail`, `dashboard`) exclude `is_deleted=True` products; order history fully preserved

#### Medium Priority
- [x] **Sale / promotional price** — `sale_price`, `sale_starts_at`, `sale_ends_at` columns added (`Database_Setup_Step33_Sale_Price.sql`); `app/utils/pricing.py` has `effective_price()` + `annotate_sale()` helpers; seller product form has "Sale / Promotional Price" section with date-range scheduling and a live preview; SALE badge shown on seller products list; all buyer-facing views (browse, product detail, cart, landing page cards) show sale price with strikethrough original; cart + buy-now capture effective price at add-time; `product-form.js` shows live sale preview while typing
- [x] **Store customization** — `shop_banner_url TEXT` + `about_store TEXT` added to sellers table (`Database_Setup_Step35_Store_Customization.sql`); seller profile form has "Store Customization" section with shop name, short description, about textarea, and banner image upload with live preview; `shop-banners` Supabase bucket used (1400×480); buyer store page shows banner behind header and "About the Store" card when set
- [ ] **Product duplication** — can't clone an existing product to create a variant quickly
- [ ] **Inventory bulk edit** — updating stock for 50 variants requires 50 separate form submits
- [ ] **Payout method configuration** — no way to save bank account details; each payout request has no structured bank-account fields (just a free-text note?)
- [x] **Seller coupon usage analytics** — coupons page now shows 4 summary stat cards (total coupons, active, times used, total discount given) + a "Total Discount Given" column per coupon with last-used date, and a mini progress bar on usage count when a limit is set
- [x] **Return auto-approval timer** — admin sets `return_auto_approve_days` via the Platform Settings modal (Commission page); pending returns older than that many days are auto-approved every 5 minutes via a throttled `before_request` hook; seller returns list shows a per-row countdown badge; buyer return detail shows the auto-approve date

#### Low Priority
- [x] **Seller-to-Rider chat** — embedded "Message Rider" chat panel in `seller/order_detail.html` (appears once a rider is assigned); embedded "Message Seller" panel in `rider/delivery_detail.html` with quick-message buttons and typing indicator; seller inbox has a Riders tab and rider inbox has a Sellers tab for ongoing conversations
- [x] **Product SEO fields** — `slug`, `meta_title`, `meta_description` columns added to `products` table (`Database_Setup_Step37_Product_SEO_Fields.sql`); seller product form has a collapsible "SEO & URL" section with slug (auto-generated from name with uniqueness, editable), meta title (≤60 chars with live counter), and meta description (≤155 chars with live counter); SEO-friendly URL `/p/<slug>` route added (`buyer.product_detail_by_slug`); `product_detail.html` uses custom meta_title/meta_description when set and canonical URL points to the slug URL when available
- [ ] **Product video upload** — only images are supported
- [x] Product form has drag-and-drop image reorder — both existing saved images (`#currentImages`) and newly uploaded previews (`#imagePreviewGrid`) are sortable via HTML5 DnD; first image gets a blue "Main" badge; drag order is serialized into a hidden `images_order` input and respected on save; new-image FileList rebuilt from DOM order via `kzRebuildDt()`

#### Styles / UX
- [x] Seller analytics chart library (presumably Chart.js) is loaded but there is no loading skeleton — shimmer skeletons added to all 4 chart cards and all 6 KPI value slots; `setSkeletons(true/false)` toggled in `loadData()` on every period fetch; canvases start hidden and are revealed after data arrives
- [x] Mobile sidebar toggle works but overlaps content on small screens — converted to a fixed off-canvas drawer on `<768px`; sidebar slides in with `transform: translateX()`, a semi-transparent backdrop overlay appears behind it, clicking the overlay (or pressing Escape or resizing to desktop) closes the drawer; main content stays full-width at all times; tablet (`768–991px`) gets a narrower 220px in-flow sidebar
- [x] Products table page has no bulk-select checkboxes for mass actions — select-all checkbox added to thead, per-row checkboxes added to tbody; sticky bulk-action toolbar appears above the table when any rows are selected showing count + Activate / Deactivate / Archive / Restore / Clear buttons; actions POST to new `POST /seller/products/bulk-action` route and update the DOM in-place without a full page reload

---

## 6. Rider Module

### What's Implemented ✅
- Dashboard with delivery summary
- Available pickups list (orders at `preparing` status with no rider assigned)
- Accept order → auto-assigns rider and moves status to `out_for_delivery`
- My deliveries list
- Delivery detail with chat, status update (mark delivered), buyer address display
- Earnings page (date-filtered list of completed deliveries)
- Ratings page (list of buyer ratings with stats)
- Chat inbox (rider ↔ buyer)
- Profile settings (name, address, password)

### What's Missing 🔴

#### High Priority
- [x] **Avatar upload for Rider** — `_save_avatar()` added to `rider/utils.py` (identical to buyer's: resizes to 320×320 webp, uploads to `avatars/` Supabase bucket); `rider/profile.py` now imports and calls it on POST, saving the URL to `profiles.avatar_url`; `rider/profile.html` form gets `enctype="multipart/form-data"`, right-column card replaced with avatar preview circle (shows existing photo or initial letter), "Upload Photo" file input, and live client-side preview JS
- [x] **Rider availability toggle (online/offline)** — `is_available BOOLEAN DEFAULT TRUE` column added to `riders` table (`Database_Setup_Step38_Rider_Availability.sql`); `POST /rider/toggle-availability` route updates the flag; a context processor in `rider/utils.py` injects `rider_is_available` into every rider template; navbar gets an Online/Offline pill button with green dot; dashboard shows a status banner with Go Offline/Go Online button; `available.html` shows an offline warning banner with a "Go Online" shortcut; accepting an order while offline is blocked server-side; `push_new_pickup()` added to `services/notify.py` notifies all `is_active=True, is_available=True` riders when a seller marks an order as `preparing`; `seller/orders.py` calls it on the `preparing` status transition
- [x] **Proof of delivery** — `proof_of_delivery_url TEXT` column added to `orders` table (`Database_Setup_Step39_Proof_Of_Delivery.sql`); `_save_proof_photo()` helper added to `rider/utils.py` (uploads to `delivery-proofs/<order_id>.webp` Supabase bucket, resizes to 1280×960 WebP); `mark_delivered` route now requires a photo upload — returns a flash error and redirects back if missing or upload fails; `delivery_detail.html` "Mark as Delivered" section replaced with a form that has `enctype="multipart/form-data"`, a `capture="environment"` file input (opens camera on mobile), live FileReader preview with green border, and a confirm dialog with spinner; already-delivered orders show the proof photo below the status badge; buyer `order_detail.html` shows the proof photo thumbnail (links to full-size) in both the `delivered` "Order Received" banner and the `completed` confirmation block
- [ ] **Rider payout / withdrawal** — sellers have `payout_requests` but riders have **no withdrawal system** — earnings are tracked but can't be withdrawn
- [x] **Accepted order lock** — once a rider accepts an order, the status jumps directly to `out_for_delivery` without a `ready_for_pickup` intermediate that the seller controls; there is a workflow sequencing issue here

#### Medium Priority
- [x] **Order rejection / hand-back** — once accepted, a rider cannot return an order; no "I can't complete this" flow
- [ ] **Navigation / map integration** — delivery detail shows buyer address as text only; no integrated map link (even a simple Google Maps deep link)
- [x] **Re-upload documents after rejection** — soft-reject flow sets `rejection_reason` on the profile row; rejected riders can log in and see a "Documents Rejected" card on `rider/profile.html` with file inputs for all 3 docs; `POST /rider/profile/documents` re-uploads them, clears `rejection_reason`, and returns the rider to the admin pending queue
- [x] **Rider-level notifications** — `rider/notifications.py` created; `GET /rider/notifications` fetches and marks-read all notifications; sidebar "Notifications" link added to `rider/base.html`; dedicated `notifications.html` template with rider-specific icon/colour mapping for `new_pickup`, `order_completed`, `rider_payout_approved/rejected`, `message_received`, `rating`, `cancel` types; `notifications.css` in `static/css/rider/`
- [x] **Push notifications** — Web Push (VAPID, no FCM) implemented: `push_subscriptions` DB table (`Database_Setup_Step40_Push_Subscriptions.sql`); `services/push.py` wraps `pywebpush` to deliver to all active subscriptions for a user and auto-prunes 410-Gone entries; `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_MAILTO` added to `config.py`; API endpoints `GET /api/v1/notifications/vapid-public-key`, `POST /api/v1/notifications/subscribe`, `POST /api/v1/notifications/unsubscribe`; `/sw.js` route serves `static/sw.js` at origin root with `Service-Worker-Allowed: /`; `static/js/kidzora-push.js` registers the SW, requests permission, and posts subscription to backend — auto-prompts rider with a dismissible banner on first visit; `#kzPushToggleBtn` in rider navbar to toggle on/off; `push_new_pickup`, `push_rider_payout_event`, `push_rider_handback` in `services/notify.py` fire both in-app rows and Web Push; ridersreceive alerts even when the tab is closed

#### Low Priority
- [x] **Delivery history export** — riders can't export their earnings/deliveries to CSV
- [ ] **Rider leaderboard / badges** — no gamification

#### Styles / UX
- [x] Delivery detail page chat section uses a dark chat theme but available.html and deliveries.html use the standard light Bootstrap theme — visual inconsistency
- [x] Earnings page has no chart — just a plain list; a line chart by day would be valuable
- [ ] Ratings page bar chart is CSS-only with no accessible labels

---

## 7. Admin Module

### What's Implemented ✅
- Dashboard (user counts, pending approvals, commission summary, recent transactions)
- Pending user approvals (sellers and riders) with document viewer modal
- Full user list with ban / unban / filter
- Commission overview (period filter, per-transaction list)
- Analytics (revenue charts, order counts, per-period breakdowns)
- Reports (sales report with CSV export)
- Payout requests (approve / reject with notification)
- Returns dispute resolution (escalated returns from buyers)
- Coupons management (platform-wide coupon CRUD)
- Unban requests (`unban_requests.html` template exists)

### What's Missing 🔴

#### High Priority
- [x] **Unban request full flow** — `unban_requests.html` template exists but the route in `admin/users.py` may not fully handle the approve/reject flow end-to-end; needs verification
- [x] **Product moderation** — dedicated `product_reports` moderation flow added: buyer can report listings from `buyer/product_detail.html`; admin queue at `/admin/product-moderation` lists reports with status filters and supports **Hide Listing**, **Remove Listing** (soft delete), or **Dismiss Report** actions; implemented in `app/routes/admin/product_moderation.py` with sidebar link in `admin/base.html` and DB migration `Database_Setup_Step41_Product_Reports.sql`
- [x] **Commission rate setting via UI** — implemented in `admin/commission.html` + `POST /admin/commission/settings` (`app/routes/admin/commission.py`), persisted in `platform_settings` (`commission_rate` key). Fallback calculations now consistently use `get_commission_rate()` in `buyer/orders.py`, `seller/payouts.py`, and `models/transaction.py`; admin commission labels also display the live configured rate.

#### Medium Priority
- [ ] **Bulk user actions** — no select-all + bulk approve/ban/reject for pending users
- [ ] **Content moderation queue for reviews** — buyers can submit reviews but admin can't see or moderate them
- [x] **Audit log viewer** — implemented with `audit_logs` table (`Database_Setup_Step42_Audit_Logs.sql`), reusable logger (`app/services/audit_log.py`), and admin page at `/admin/audit-logs` (`app/routes/admin/audit_logs.py`, `app/templates/admin/audit_logs.html`) with filters and pagination. Key admin actions now write logs: user moderation (approve/reject/ban/unban), seller/rider payout approvals/rejections, and commission/platform settings updates.
- [ ] **Site-wide announcement / banner** — no way to push a maintenance message or promotion to all users
- [ ] **Seller store approval** — admin approves the *user account* of a seller but there is no separate process to approve/reject their *store listing* before products go live
- [x] **Admin → User direct message** — implemented: admin can initiate chats from `users_list.html` and `users_pending.html` via “Message User”/“Message Seller/Rider” buttons, and from inbox via the “New Conversation” panel (all non-admin users are listed with direct links to `/admin/chat/<other_user_id>`). Backend handled by `app/routes/admin/chat.py` (`/admin/inbox` + `/admin/chat/<other_user_id>`).
- [x] **System health dashboard** — implemented at `/admin/system-health` with DB connectivity check, row-count cards for key tables, Supabase storage bucket object/size stats, and recent application error logs. Added route/template (`app/routes/admin/system_health.py`, `app/templates/admin/system_health.html`), sidebar link in `admin/base.html`, and error capture via Flask exception signal into `app_error_logs` (`app/services/app_error_log.py`, `Database_Setup_Step43_App_Error_Logs.sql`).

#### Low Priority
- [x] **User growth chart** — Line chart at `/admin/analytics` in bottom-right section showing user registrations over time, with daily/weekly/monthly/yearly bucketing matching other analytics charts. Backend aggregates new users by period, frontend renders with Chart.js (cyan line, area fill). Data already available in analytics API response.
- [ ] **Rider performance report** — no per-rider delivery count / on-time rate report
- [x] **Product performance report** — implemented at `/admin/reports` with "Product Performance" report type option; shows top 10 best-selling products + all products sold during period; summary KPIs: unique products, total quantity, total revenue, average per product. Both CSV and PDF export available via dropdown in reports list. CSV includes summary + top 10 + all products tables. PDF prints with same data in print-friendly format. Data from completed orders within date range, aggregated by product_id from order_items table.
- [ ] **Admin impersonation / "view as user"** — helpful for debugging user-reported issues
- [x] Reports page missing: user growth, category sales breakdown, monthly active buyers — all three report types implemented at `/admin/reports` with full CSV export

#### Styles / UX
- [x] **Admin CSS files** — 5 dedicated CSS files created for admin templates (commission, returns, orders, users, unban_requests) extracted inline styles and added responsive mobile/tablet design; linked in respective templates via `{% block extra_css %}`
- [x] **Dashboard charts empty states** — admin analytics (charts: Revenue, Orders, New Users) and seller analytics (charts: Revenue, Orders, Status) now display friendly empty-state messaging with icons when no data is available for the selected period; prevented rendering of empty charts with informative text and illustration
- [ ] Mobile admin experience is untested — sidebar collapses but tables overflow horizontally

---

## 8. Shared / Cross-Cutting Concerns

### Real-Time Chat
- `kidzora-realtime.js` and `services/chat.js` exist
- Supabase Realtime channel subscription is set up
- `services/chat.py` provides `set_typing` / `is_typing` helpers (likely using a Supabase table, not WebSocket)
- [ ] **Missing**: typing indicator is stored in DB but the real-time subscription to the `typing_indicators` channel needs to be confirmed working end-to-end
- [ ] **Missing**: message delivery receipts (`is_delivered` is in the schema but confirmation of delivery display in chat UI needs review)
- [ ] **Missing**: file / image attachments in chat — text only currently

### Notifications
- `services/notify.py` pushes rows to `notifications` table
- Each role has a notifications page
- [x] **Missing**: real-time unread badge count update without page reload — Supabase Realtime subscription implemented in `kidzora-notifications-realtime.js`; listens for INSERT/UPDATE events on notifications table and syncs badge count live
- [x] **Missing**: browser push notifications (Web Push API / FCM) for offline alerts — Web Push (VAPID) fully implemented across all user roles; Service Worker registration (`kidzora-push.js` + `sw.js`), VAPID subscription management via `/subscribe` and `/unsubscribe` endpoints, permission prompting; Web Push toggle button + `kz-role` meta tag in navbar for buyer, seller, admin, rider; backend `send_push()` integration in `notify.py` for push delivery; auto-prunes invalid (410 Gone) subscriptions
- [x] **Duplication**: API endpoint and page routes both implement notification fetching — extracted shared utility service `app/services/notifications.py` with three functions: `fetch_notifications(user_id, limit, since, unread_only)`, `mark_all_read(user_id)`, `mark_notifications_read(user_id, ids)`; refactored API routes (`api/notifications.py`) and all page routes (buyer, seller, rider) to call shared service; eliminated code duplication and reduced maintenance burden

### Email Service
- [x] **Missing**: HTML email templates are all inline strings — extracted all HTML email templates to dedicated Jinja2 files in `app/templates/emails/`: base layout (`base.html`), order status (`order_status.html`), cancellation flow (cancel_requested/approved/rejected), return/refund flow (return_submitted_buyer/seller, return_seller_approved/rejected, return_escalated, return_admin_approved/denied/resolved_seller), and order placement (order_placed_buyer/seller). Refactored `services/email.py` to use `render_template()` instead of f-strings, reducing code by ~400 lines and improving maintainability and styling consistency.
- [x] **Done**: email for new message received — added `notify_new_message()` function in `services/email.py`, created `app/templates/emails/message_received.html` template, hooked into all 4 chat_send endpoints (buyer, seller, admin, rider) to send email notification when user receives offline chat message.
- [x] **Done**: welcome email after registration approval — added `notify_welcome_approved()` function in `services/email.py`, created `app/templates/emails/welcome_registered.html` template with role-specific (seller/rider) content, hooked into `admin/users.py` `approve_user` route to send welcome email immediately after approval.
- [x] **Done**: low-stock alert email to sellers — added `notify_low_stock_email()` function in `services/email.py`, created `app/templates/emails/low_stock_alert.html` template with role-specific messaging for out-of-stock vs low-stock, hooked into `push_low_stock()` in `services/notify.py` to send email whenever seller inventory falls below threshold or is depleted.

### Session & Cart
- Cart is session-stored (server-side session)
- [x] **Done**: guest cart merge on login — removed `@login_required` from `cart_add`, `cart_update`, `cart_remove`, `cart_clear` routes; updated `_get_cart()` and `_save_cart()` to differentiate guest (session-only) vs authenticated buyer (DB-synced) flows; guest can now browse and add items to session cart; when guest logs in, login handler in `auth.py` merges accumulated session cart with user's persisted DB cart (session items take priority); after merge, all future cart operations sync to DB
- [x] **Missing**: cart items are lost when session expires or user logs out from another device — `cart_items` DB table + `_db_sync`/`_db_load` in `cart.py` + merge-on-login in `auth.py`

### API Layer (`app/routes/api/`)
- API endpoints exist for: notifications, buyer actions, seller actions, rider actions, admin actions
- [ ] **Missing**: API versioning (e.g., `/api/v1/`) — future mobile app needs a stable versioned API
- [ ] **Missing**: API authentication middleware (JWT / API key) for the Flutter mobile app mentioned in `MOBILE_FLUTTER_GUIDE.md`
- [ ] **Missing**: rate limiting on all API endpoints

### Flutter / Mobile App
- `MOBILE_FLUTTER_GUIDE.md` and `MOBILE_SYNC_GUIDE.md` exist documenting planned mobile integration
- [ ] **Missing**: the Flutter app itself is not in this repository
- [ ] **Missing**: the web API is not yet structured as a REST/JSON API — it's a mix of form-based routes and AJAX endpoints

---

## 9. Styles & Frontend

### CSS File Gaps
Every template below currently has **no dedicated CSS file** — styling relies entirely on Bootstrap and inherited global styles:

| Template | Path | Has dedicated CSS? |
|----------|------|--------------------|
| `checkout.html` | `buyer/` | ✅ |
| `notifications.html` | `buyer/` | ✅ |
| `profile.html` | `buyer/` | ✅ |
| `returns.html` | `buyer/` | ✅ |
| `return_detail.html` | `buyer/` | ❌ |
| `wishlist.html` | `buyer/` | ✅ |
| `inbox.html` | `buyer/` | ✅ |
| `commission.html` | `admin/` | ❌ |
| `orders.html` | `admin/` | ❌ |
| `order_detail.html` | `admin/` | ❌ |
| `returns.html` | `admin/` | ❌ |
| `return_detail.html` | `admin/` | ❌ |
| `unban_requests.html` | `admin/` | ❌ |
| `users_list.html` | `admin/` | ❌ |
| `users_pending.html` | `admin/` | ❌ |
| `earnings.html` | `rider/` | ❌ |
| `ratings.html` | `rider/` | ❌ |
| `available.html` | `rider/` | ❌ |
| `dashboard.html` | `rider/` | ❌ |
| `profile.html` | `rider/` | ❌ |

### CSS Duplication / Structure Issues
- [x] `chat.css` and `chat-dark.css` live at `static/css/` root AND `static/css/rider/chat.css` — consolidated: moved `rider/chat.css` to root as `embedded-chat.css` for shared embedded chat panel styling; updated references in `rider/base.html` and `seller/base.html`; removed duplicate `msg-bubble` styles from `rider.css` (now provided by `embedded-chat.css`)
- [x] `rider.css` and `seller.css` live at `static/css/` root but role-specific overrides live in subfolders — **Resolved**: verified that both `rider/base.html` and `seller/base.html` use component-based approach (linking individual files from subfolders like `rider/layout.css`, `seller/sidebar.css`, etc.), matching the pattern used by buyer and admin modules. Root-level `rider.css` and `seller.css` are legacy monolithic files that are **NOT referenced anywhere** and should be deleted. Pattern now consistent: all role-specific CSS organized in subfolders (`buyer/`, `seller/`, `rider/`, `admin/`) with component-based split files.
- [x] `landing.css` is in `buyer/` subfolder but the landing template is now in `templates/landing.html` (not buyer-scoped) — **Resolved**: deleted outdated duplicate `buyer/landing.css`; template correctly references `css/public/landing.css` which contains the authoritative public landing page styling

### JavaScript Gaps
- [x] No dedicated JS files for buyer: `cart.html`, `orders.html`, `returns.html`, `wishlist.html`, `notifications.html`, `profile.html` — **Resolved**: created 5 new JS files in `static/js/buyer/`: 
  - `cart.js`: quantity increment/decrement logic; removed inline `onclick` handlers from template
  - `orders.js`: order card interactions and currency formatting utility
  - `returns.js`: return request row interactions and status label mapping
  - `wishlist.js`: product card hover effects and add-to-cart/remove feedback
  - `notifications.js`: notification type/color utilities and view-details interactions
  - All templates updated to link their respective JS files via `{% block extra_js %}`
- [x] Admin JS is comprehensive (`analytics.js`, `orders.js`, `users-list.js`, etc.) but rider JS is sparse — only `base.js`, `delivery-detail.js`, `ratings.js` — **Resolved**: created 6 new JS files in `static/js/rider/`:
  - `dashboard.js`: availability toggle and stat card formatting
  - `available.js`: delivery acceptance with confirmation dialog; card hover effects
  - `deliveries.js`: tab switching between active/history; delivery card interactions
  - `payouts.js`: payout method selection field toggling; withdrawal amount validation
  - `inbox.js`: conversation list interactions and message input validation
  - `notifications.js`: notification type/icon utilities and card interactions
  - Removed inline `onsubmit="return confirm(...)"` handler from available.html (moved to available.js)
  - Removed inline `function toggleMethodFields()` from payouts.html (moved to payouts.js)
- [x] **No shared utility library** — **Resolved**: created `static/js/kidzora-utils.js` consolidating all reusable utilities:
  - `formatCurrency(amount)`: Philippine peso formatting with thousands separator (used in buyer/orders.js, rider/dashboard.js, rider/payouts.js)
  - `formatPayoutAmount(amount)`: alias for formatCurrency
  - `formatDeliveryCount(count)`: ensures integer count (used in rider/dashboard.js)
  - `getNotificationType(type)`: human-readable notification label mapping (used in rider/notifications.js)
  - `getNotificationIcon(type)`: Font Awesome icon class by notification type (used in buyer/notifications.js, rider/notifications.js)
  - `getNotificationColor(type)`: Bootstrap text color class by notification type (used in buyer/notifications.js)
  - `getStatusLabel(status)`: return request status display label (used in buyer/returns.js)
  - `getDeliveryStatusClass(status)`: Bootstrap badge class for delivery status (used in rider/deliveries.js)
  - Removed duplicate implementations from: buyer/orders.js, buyer/notifications.js, buyer/returns.js, rider/dashboard.js, rider/deliveries.js, rider/notifications.js, rider/payouts.js
  - Updated 7 templates to load `kidzora-utils.js` before their module-specific JS: buyer/orders.html, buyer/notifications.html, buyer/returns.html, rider/dashboard.html, rider/notifications.html, rider/deliveries.html, rider/payouts.html
  - All 8 functions now exported globally and available to any JS file without duplication

### UI / UX Issues
- [ ] **Dark mode** — seller admin panel supports a dark sidebar but there is no site-wide toggle or `prefers-color-scheme` support
- [x] **Loading skeletons** — **Resolved**: comprehensive skeleton system implemented across the platform:
  - **CSS Library** (`kidzora-skeletons.css`): 
    - Shimmer animation with smooth gradient movement (2.5s infinite loop)
    - Predefined skeleton block types: `.skeleton-chart`, `.skeleton-stat-box`, `.skeleton-list-item`, `.skeleton-table-row`, `.skeleton-product-card`, `.skeleton-modal-*`, `.skeleton-button`
    - Support for rounded variants: `.rounded`, `.rounded-lg`, `.rounded-xl`
    - State management: `.skeleton-visible`, `.skeleton-hidden` with CSS transitions
    - Dark mode support via `@media (prefers-color-scheme: dark)` with adjusted shimmer colors
  - **JS Utility Library** (`kidzora-skeletons.js`):
    - `showSkeleton(containerId)`: Show skeleton placeholder, hide content
    - `hideSkeleton(containerId)`: Hide skeleton, show content
    - `setSkeleton(containerId, show)`: Toggle skeleton visibility
    - `withSkeleton(containerId, asyncOperation)`: Promise wrapper for async data loading
    - `showSkeletonFor(containerId, duration)`: Auto-hide after time duration
    - Batch operations: `setSkeletons(show)`, `showSkeletonsBy(selector)`, `hideSkeletonsBy(selector)`
    - HTML pattern: `<div data-skeleton>` for skeleton markup, `<div data-skeleton-content>` for real content
  - **Admin Analytics Enhanced**:
    - KPI cards now show shimmer skeleton instead of spinner while loading
    - Chart canvases hidden during fetch, shown when data arrives
    - `setKpiSpinners()` replaced with skeleton styling
    - `fillKpis()` removes skeleton classes and reveals data
  - **Seller Analytics Already Implemented**:
    - Pre-existing `setSkeletons(true/false)` function in `seller/analytics.js`
    - Charts and KPI cards show skeletons during data fetch
    - Integrated into `loadData()` promise chain
  - **Global Availability**:
    - Both CSS and JS loaded in `base.html` for all pages
    - Ready to use on any future async-loading page (buyer notifications, rider earnings, modals, etc.)
  - **Example Usage**:
    ```html
    <div id="data-container">
      <div data-skeleton>
        <div class="skeleton-stat-box">
          <div class="skeleton-stat-title"></div>
          <div class="skeleton-stat-value"></div>
        </div>
      </div>
      <div data-skeleton-content style="display: none;">
        <!-- Real content here -->
      </div>
    </div>
    ```
    ```javascript
    withSkeleton('data-container', 
      fetch('/api/data').then(r => r.json())
    );
    ```
- [x] **Empty states** — Comprehensive illustrated empty-state system implemented with custom SVG illustrations and animations for list pages (wishlist, orders, notifications)

### Empty-State System Implementation

**Global Libraries Created:**
- `app/static/css/kidzora-empty-states.css` (380 lines)
  - `.empty-state` container with gradient background and fade-in animation
  - `.empty-state__icon` with floating animation for illustration SVG
  - `.empty-state__title` and `.empty-state__description` with staggered fadeInUp animations
  - `.empty-state__btn` primary/secondary button variants with gradient overlays
  - Variant classes: `--wishlist` (pink), `--orders` (blue), `--notifications` (amber), `--inbox` (cyan), `--returns` (purple)
  - Responsive design for mobile/tablet with reduced padding and font sizes
  - Dark mode support via `@media (prefers-color-scheme: dark)`
  - Decorative twinkling star animations with staggered timing
  
- `app/static/js/kidzora-empty-states.js` (158 lines)
  - `showEmptyState(containerId)` — Show [data-empty-state], hide [data-empty-content]
  - `hideEmptyState(containerId)` — Reverse visibility (CSS transitions on .skeleton-visible/.skeleton-hidden)
  - `setEmptyState(containerId, show)` — Toggle wrapper function
  - `showEmptyStatesBy(selector)` / `hideEmptyStatesBy(selector)` — Batch operations
  - `setEmptyStateByCount(containerId, itemCount)` — Automatically show/hide based on count
  - `setEmptyStates(show, ...containers)` — Variadic batch setter
  - `withEmptyState(containerId, asyncOperation)` — Promise wrapper with auto-management
  - `showEmptyStateFor(containerId, duration)` — Auto-hide after timeout
  - `updateEmptyStateMessage(containerId, title, description)` — Dynamic message updates
  - `checkAndToggleEmptyState(items, containerId, showIfEmpty)` — Conditional visibility on array length

**Global Integration:**
- Both CSS and JS linked in `base.html` (lines 42, 225) for site-wide availability
- Available to all pages without per-page imports

**Buyer Module Implementation:**
1. **buyer/wishlist.html** — Replaced card-based "No Favorites Yet" message
   - SVG illustration: Pink heart with floating animation, decorative stars
   - Variant class: `.empty-state--wishlist` (pink gradient)
   - CTA: "Explore Products" button to browse_products
   - Enhanced buyer/wishlist.js: Added initialization check for .col card count

2. **buyer/orders.html** — Replaced card-based "No orders yet" message
   - SVG illustration: Shopping bag icon with stylized lines and decorative elements
   - Variant class: `.empty-state--orders` (blue gradient)
   - CTA: "Start Shopping" button to browse_products
   - Enhanced buyer/orders.js: Added initialization check for .order-card count

3. **buyer/notifications.html** — Replaced centered text "No notifications yet" message
   - SVG illustration: Bell icon with decorative sound waves and floating elements
   - Variant class: `.empty-state--notifications` (amber gradient)
   - Message: "All Caught Up!" with description about order/activity updates
   - CTA: "Continue Shopping" button to browse_products
   - Enhanced buyer/notifications.js: Added initialization check for .card count

**HTML Pattern (data attributes):**
```html
<div id="container-id">
  <div data-empty-state class="empty-state empty-state--variant">
    <!-- SVG icon, title, description, action button -->
  </div>
  <div data-empty-content>
    <!-- Real content here -->
  </div>
</div>
```

**JavaScript Usage:**
```javascript
// On page load, check item count
if (itemCount === 0) {
  window.showEmptyState('container-id');
} else {
  window.hideEmptyState('container-id');
}

// Dynamic management
window.setEmptyState('orders-container', orders.length === 0);
window.updateEmptyStateMessage('orders-container', 'No Orders', 'Your message here');
```

**Responsive & Accessible:**
- Mobile-optimized: Reduced icon size (100px on mobile vs 120px on desktop), smaller font sizes
- Animation: Smooth fade-in on load (0.5s), float animation on icon (3s infinite)
- Color-coded: Each empty state variant has distinct gradient (pink for wishlist, blue for orders, amber for notifications)
- Dark mode: Gradient backgrounds and text colors adjust automatically via prefers-color-scheme media query
- SVG illustrations: Custom hand-coded SVG icons (not external images) for instant load with decorative elements

**Next Steps (Future Enhancements):**
- Implement on seller pages (products, earnings, messages)
- Implement on rider pages (deliveries, earnings)
- Implement on cart page with custom illustration and product browsing CTA
- Add admin dashboard empty states for reports
- Consider adding empty state animations for dynamic AJAX-loaded content

---

- [x] **Form validation UX** — Real-time inline field validation with error feedback implemented across all critical user forms

### Form Validation System Implementation

**Global Libraries Created:**
- `app/static/css/kidzora-form-validation.css` (520 lines)
  - `.form-control.is-invalid` / `.is-valid` states with animated error/success icons (red ✕ / green ✓)
  - `.invalid-feedback` / `.valid-feedback` message containers with slideInDown animation
  - `.form-group.has-error` / `.has-success` / `.is-validating` states for group-level styling
  - Password strength meter (`.password-strength-meter`) with 4-level bars (weak/fair/good/strong)
  - Character counter (`.char-counter`) with warning/danger states at 75%/90% filled
  - Form submit button states (`.is-loading`) with spinner animation
  - Dark mode support via `@media (prefers-color-scheme: dark)`
  - Responsive design for mobile (reduced font sizes, adjusted spacing)
  - Validation animations: `slideInDown` for error messages, `shake` on submit with errors, `pulse` for loading
  
- `app/static/js/kidzora-form-validation.js` (580 lines)
  - **Validation Engine**:
    - `isValidEmail(email)` — RFC-compliant email validation
    - `validatePassword(password)` — Strength checking: 8+ chars, uppercase, lowercase, number, special char; returns { isValid, strength: 'weak'|'fair'|'good'|'strong', score: 0-4 }
    - `validateField(value, rules)` — Universal validator supporting: required, email, password, minLength, maxLength, pattern, match, custom function
  - **Field Management**:
    - `markFieldInvalid(field, errorMessage)` — Add is-invalid class, show error container, update form-group state
    - `markFieldValid(field, successMessage)` — Add is-valid class, hide errors, show optional success message
    - `clearFieldValidation(field)` — Remove all validation states and messages
  - **Real-Time Validation**:
    - `setupValidation(field, rules, onValidChange)` — Blur listener for full validation, input listener for error recovery
    - `setupPasswordMeter(passwordField, meterContainer)` — Updates strength bars/text on input
    - `setupCharCounter(field, counterContainer)` — Shows remaining chars, warns at 75%/90%
  - **Form-Level**:
    - `validateForm(form)` — Validates all `[data-validate]` fields, shows shake animation if errors
    - `resetFormValidation(form)` — Clears all field states
    - `setupFormSubmit(form, onSubmit)` — Prevents default if invalid, calls callback if valid
    - `setButtonLoading(button, loadingText)` — Disables button, adds spinner, preserves original text
    - `clearButtonLoading(button)` — Removes spinner, re-enables, restores text
  - **Async Helpers**:
    - `checkEmailAvailable(email, endpoint)` — Deferred validation for "email already registered" checks
  - **HTML Pattern**: Fields use `data-validate='{"type":"email","required":true,...}'` attribute for declarative validation

**Global Integration:**
- Both CSS and JS linked in `base.html` (lines 44, 227) for site-wide availability
- Validation rules defined as JSON in `data-validate` attributes on input fields
- All validation is progressive: real-time feedback when field has been blurred, on-submit comprehensive check

**Forms Enhanced:**
1. **auth/login.html**
   - Email field: Real-time email format validation, required
   - Password field: Optional real-time password validation on blur
   - Inline error messages below each field
   - Form prevents submit if email is invalid

2. **buyer/checkout.html**
   - Phone: PH phone format validation (`/^(\+63|0)[0-9]{9,10}$/`)
   - Region: Required, min 3 chars
   - Province/City/Barangay/Street: Required, min 2-3 chars
   - Postal Code: Max 4 chars
   - Address Label (optional save): Max 30 chars
   - Each address field wrapped in `.form-group` for consistent styling
   - Form prevents submit if any required field is invalid
   - Real-time validation on blur, re-validates on input if field already has error

**Validation Features:**
- ✅ Real-time blur-triggered validation with immediate feedback
- ✅ Error messages with smooth slideInDown animation
- ✅ Field-level visual feedback (red border, error icon, message text)
- ✅ Form-group-level state management (has-error, has-success)
- ✅ Loading state for async operations (spinner on button, disabled state)
- ✅ Password strength meter with color-coded bars
- ✅ Character counter for textarea/input with maxlength
- ✅ Dark mode support with adjusted colors
- ✅ Mobile-responsive font sizes and spacing
- ✅ Keyboard-accessible (no event hijacking, natural form behavior)
- ✅ Progressive enhancement (works with server-side validation as fallback)

**Configuration via data-validate JSON:**
```json
{
  "type": "email|password|url|phone",
  "required": true,
  "minLength": 8,
  "maxLength": 50,
  "pattern": /regex/,
  "patternError": "Custom error message",
  "match": fieldValue,
  "matchError": "Custom match error",
  "custom": function(value) { return true or "error message"; }
}
```

**Example Usage (HTML):**
```html
<div class="form-group">
  <label class="form-label">Email</label>
  <input type="email" class="form-control" name="email"
         data-validate='{"type":"email","required":true}'>
</div>

<div class="form-group">
  <label class="form-label">Password</label>
  <input type="password" class="form-control" name="password"
         data-validate='{"type":"password"}' id="passwordField">
  <div id="strengthMeter"></div>
</div>
```

**Example Usage (JavaScript):**
```javascript
// Real-time validation on specific field
window.setupValidation('#email', { type: 'email', required: true });

// Password strength meter
window.setupPasswordMeter('#passwordField', '#strengthMeter');

// Character counter
window.setupCharCounter('#bio', '#charCounter');

// Form-level validation on submit
window.setupFormSubmit('form', function(e) {
  console.log('Form is valid, submitting...');
  // Custom submission logic if needed
});
```

**Next Steps (Future Enhancements):**
- Implement on all remaining forms (seller product, buyer profile, seller profile, rider profile, support tickets, etc.)
- Add async email availability check on registration forms (`checkEmailAvailable`)
- Add custom password confirmation validator on all password change forms
- Add file upload validators (size, type, dimensions for images)
- Add conditional required fields (fields required only if another field has a value)
- Server-side validation error display in existing error containers (backward compatible)
- Accessibility labels (`aria-describedby`) linking errors to invalid fields
- Internationalization of error messages (i18n)

---

---

## 10. Database & Backend Services

### Schema Observations
- `orders` uses `total_amount` in some places and `total` in others — the `seller/payouts.py` queries `total` but `order_detail.html` displays `total_amount`; needs a single canonical column name
- `transactions` table exists but the `Transaction` model is used only for commission summary — it may not be populated on every order completion
- `seller_coupons` table exists alongside the platform `coupons` table — the checkout flow handles both but there is no admin UI for viewing/moderating seller coupons
- `chat_delivered` migration step exists (Step 25) suggesting `is_delivered` was added later — ensure all old messages have a default value

### Missing Database Items
- [x] No `cart_items` table (cart is session-only) — added in `Database_Setup_Step31_Cart_Items.sql`
- [ ] No `addresses` table (multiple saved addresses per user)
- [x] **Rider payout system** — `rider_payout_requests` table (Database_Setup_Step40_Rider_Payout_Requests.sql) with withdrawal request submission, admin approval/rejection workflow, earnings calculation (total_earned, total_paid_out, pending_lock, available), notifications (push_rider_payout_approved/rejected), and audit logging. Routes: GET `/rider/payouts` (earnings summary + history + withdrawal form), POST `/rider/payouts/request` (validates minimum ₱100, checks balance, limits to 1 pending per rider); admin routes: GET `/admin/rider-payouts` (filterable queue), POST `/admin/rider-payouts/<id>/approve/reject` (with notifications and audit logs).
- [x] **Product reports moderation** — `product_reports` table (Database_Setup_Step41_Product_Reports.sql) with buyer report submission from `buyer/product_detail.html`; admin queue at `GET /admin/product-moderation` with status filters (pending/approved/rejected); actions: **Hide Listing** (hides from browse but keeps data), **Remove Listing** (soft delete), **Dismiss Report** with optional notes. Implemented in `app/routes/admin/product_moderation.py` with sidebar link in `admin/base.html` and template `admin/product_moderation.html`.
- [ ] No `email_logs` or `notification_logs` table for debugging delivery failures
- [x] **Audit logs system** — `audit_logs` table (Database_Setup_Step42_Audit_Logs.sql) tracks all admin actions with actor, action, entity, target user, and JSON details; reusable `log_admin_action()` helper in `app/services/audit_log.py`; admin viewer at `GET /admin/audit-logs` (`app/routes/admin/audit_logs.py`, `app/templates/admin/audit_logs.html`) with **comprehensive filtering**: action, admin, affected user, entity ID, date range (from/to); **statistics dashboard** showing top 5 most active admins and top 10 most common actions from recent 500 logs; **CSV export** endpoint at `GET /admin/audit-logs/export` (respects all active filters); **enhanced pagination** showing page info with item count ranges; collapsible JSON details view per log entry; logs all user approval/rejection/ban/unban, payout approvals/rejections, platform settings changes.

### Services Improvements
- [ ] `services/email.py` — all HTML is inline strings; ex  tract to proper Jinja2 email templates in `templates/emails/`
- [ ] `services/notify.py` — no batching; each event fires one INSERT; should support bulk notify (e.g., "all users" announcements)
- [ ] `services/chat.py` — `set_typing` / `is_typing` helpers need verification that they work with Supabase Realtime and don't accumulate stale rows
- [ ] No `services/payment.py` — payment processing has zero abstraction; when a gateway (Paymongo / GCash) is added it will need a service layer
- [ ] No `services/search.py` — full-text product search is done raw in the route; should be extracted and could be upgraded to use Postgres `tsvector` / full-text search

### Config / Environment
- [x] `COMMISSION_RATE` is defined in `config.py` as `0.05` but overridden by hard-coded `0.10` in `checkout.py` and `seller/analytics.py` — all files now read `current_app.config['COMMISSION_RATE']`
- [ ] `MAIL_PASSWORD` is hard-coded in `config.py` — must be in `.env` only, never committed to source control
- [ ] No `.env.example` file for onboarding new developers
- [ ] No `FLASK_ENV` / `APP_ENV` check to distinguish dev/staging/production

---

## 11. Security

### Issues to Fix

| Severity | Issue | Location |
|----------|-------|----------|
| 🔴 High | `MAIL_PASSWORD` hard-coded in `config.py` — exposed in source control | `config.py:25` |
| 🔴 High | No CSRF tokens on HTML forms — all POST forms are vulnerable to CSRF attacks | All templates |
| 🔴 High | No rate limiting on `/auth/login`, `/auth/register`, or API endpoints — brute-force risk | `auth.py` |
| 🟠 Medium | Session-based cart can be tampered if session secret is weak; default `SECRET_KEY` is `'dev-secret-key-change-in-production'` | `config.py:7` |
| 🟠 Medium | File uploads do not enforce `MAX_FILE_SIZE` before reading into memory — a 1 GB upload hits Flask before the 150 MB limit check | `returns.py`, `reviews.py` |
| 🟠 Medium | Product search uses `.or_()` with user input — sanitization exists but should use parameterized queries / PostgREST `textSearch` | `buyer/products.py` |
| 🟡 Low | `supabase_admin` (service role key) is used broadly in route handlers — least-privilege principle violated | All routes |
| 🟡 Low | Password change makes a raw HTTP call to Supabase Admin with service key inline in route — move to `utils/auth.py` | `buyer/profile.py`, `seller/profile.py`, `rider/profile.py` |
| 🟡 Low | No `Content-Security-Policy` header | `app/__init__.py` |

---

## 12. Priority Summary

### 🔴 Fix Immediately (Bugs / Data Integrity)
1. **Commission rate inconsistency** — `checkout.py` and `seller/analytics.py` use `0.10`; `admin/analytics.py` and `config.py` use `0.05`. Pick one and read from `config.py` everywhere.
2. **`MAIL_PASSWORD` in source code** — move to `.env` and add `.env.example`
3. **No CSRF protection** — add Flask-WTF `CSRFProtect()` and `{{ form.hidden_tag() }}` or `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` to all POST forms
4. **Soft-delete products** — add `is_deleted` flag; hard-deleting products with order history corrupts order item display
5. **`total` vs `total_amount`** column name inconsistency on `orders` table — standardize

### 🟠 High Value Features (Next Sprint)
1. ~~**Rate your Rider**~~ ✅ — star rating card in `buyer/order_detail.html`, `rate_rider` POST route, upsert to `rider_ratings`
2. ~~**Buyer order cancellation**~~ ✅ — cancel button + modal in `buyer/order_detail.html`, `cancel_order` route handles immediate (pending) and request-based (confirmed) flows
3. ~~**Cart persistence**~~ ✅ — `cart_items` DB table, write-through sync on every mutation, auto-restore on session expiry, merge on login
4. **Rider avatar upload** — add `_save_avatar()` call to `rider/profile.py` to match buyer/seller
5. **Rider payout system** — create `rider_payout_requests` table and admin approval UI
6. **Proof of delivery** — add photo upload when rider marks delivery as complete
7. **Email templates** — extract inline HTML strings in `services/email.py` to `templates/emails/*.html`

### 🟡 Medium Priority (Following Sprint)
1. Payment gateway (Paymongo / GCash)
2. Low-stock notifications for sellers
3. Multiple saved delivery addresses for buyers
4. Seller bulk product upload (CSV)
5. Rider online/offline availability toggle
6. Admin product moderation queue
7. Real-time unread notification badge update

### ⚪ Nice to Have (Backlog)
1. Dark mode across all modules
2. Flutter mobile app API layer (versioned REST + JWT)
3. SEO meta tags per page
4. Loading skeleton screens
5. Loyalty points / referral system
6. Product comparison
7. Seller store banner / customization
8. Rider GPS delivery map
9. Audit log UI for admin
