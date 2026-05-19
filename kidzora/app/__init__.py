from flask import Flask, redirect, url_for, render_template, got_request_exception
from flask_login import LoginManager, current_user
from config import config
from app.extensions import supabase, supabase_admin, login_manager

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.jinja_env.auto_reload = True

    # ── Custom Jinja2 filters ──────────────────────────────────────────────────
    @app.template_filter('currency')
    def currency_filter(value):
        """Format a number as ₱ with commas, e.g. 13930.5 → '13,930.50'"""
        try:
            return '{:,.2f}'.format(float(value))
        except (TypeError, ValueError):
            return '0.00'
    
    # Initialize extensions
    login_manager.init_app(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.seller import seller_bp
    from app.routes.buyer import buyer_bp
    from app.routes.rider import rider_bp
    from app.routes.api.admin import admin_api_bp
    from app.routes.api.seller import seller_api_bp
    from app.routes.api.buyer import buyer_api_bp
    from app.routes.api.rider import rider_api_bp
    from app.routes.api.notifications import notif_api_bp
    from app.routes.delivery_zones import delivery_zones_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(seller_bp, url_prefix='/seller')
    app.register_blueprint(buyer_bp, url_prefix='/buyer')
    app.register_blueprint(rider_bp, url_prefix='/rider')
    app.register_blueprint(delivery_zones_bp)
    
    # API routes
    app.register_blueprint(admin_api_bp, url_prefix='/api/v1/admin')
    app.register_blueprint(seller_api_bp, url_prefix='/api/v1/seller')
    app.register_blueprint(buyer_api_bp, url_prefix='/api/v1/buyer')
    app.register_blueprint(rider_api_bp, url_prefix='/api/v1/rider')
    app.register_blueprint(notif_api_bp, url_prefix='/api/v1/notifications')

    # ── Auto-approve overdue return requests (fires at most once per 5 min) ──
    from app.utils.auto_approve_returns import maybe_run_auto_approvals

    @app.before_request
    def _check_auto_approve_returns():
        maybe_run_auto_approvals()

    # ── Capture unhandled request exceptions into app_error_logs ─────────────
    from app.services.app_error_log import log_app_error

    def _capture_unhandled_exception(sender, exception, **extra):
        log_app_error(exception, level='error')

    got_request_exception.connect(_capture_unhandled_exception, app)

    # Main routes
    @app.route('/')
    def index():
        from collections import Counter
        from flask import session
        from app.utils.pricing import annotate_sale
        
        # Non-buyer authenticated users go to their own dashboards
        # Buyers see the landing page (marketplace home)
        if current_user.is_authenticated and current_user.role != 'buyer':
            role_map = {
                'admin':  'admin.dashboard',
                'seller': 'seller.dashboard',
                'rider':  'rider.dashboard',
            }
            return redirect(url_for(role_map.get(current_user.role, 'auth.login')))

        # ─ FOR AUTHENTICATED BUYERS: Show personalized landing with products ─
        if current_user.is_authenticated and current_user.role == 'buyer':
            new_products = []
            best_products = []
            best_stores = []
            followed_shops = []
            recently_viewed = []
            wishlisted_ids = set()
            stats = {'orders': 0, 'wishlist': 0}
            
            try:
                # New arrivals
                r = supabase_admin.table('products').select('*').eq('is_active', True).eq('is_deleted', False) \
                      .order('created_at', desc=True).limit(8).execute()
                new_products = r.data or []
                for p in new_products:
                    annotate_sale(p)
            except Exception:
                pass
            
            try:
                # Best-selling products
                items_r = supabase_admin.table('order_items').select('product_id, quantity').execute()
                items = items_r.data or []
                counts = Counter()
                for i in items:
                    counts[i['product_id']] += (i.get('quantity') or 1)
                top_pids = [pid for pid, _ in counts.most_common(8)]
                if top_pids:
                    pr = supabase_admin.table('products').select('*').in_('id', top_pids).eq('is_active', True) \
                           .eq('is_deleted', False).execute()
                    pid_map = {p['id']: p for p in (pr.data or [])}
                    best_products = [pid_map[pid] for pid in top_pids if pid in pid_map]
                    for p in best_products:
                        annotate_sale(p)
            except Exception:
                pass
            
            # Fallback to newest if no order history
            if not best_products:
                best_products = new_products[:8]
            
            try:
                # Best-selling stores
                orders_r = supabase_admin.table('orders').select('seller_id').execute()
                orders = orders_r.data or []
                s_counts = Counter(o['seller_id'] for o in orders if o.get('seller_id'))
                top_sids = [sid for sid, _ in s_counts.most_common(6)]
                if not top_sids:
                    any_s = supabase_admin.table('sellers').select('id').limit(6).execute()
                    top_sids = [s['id'] for s in (any_s.data or [])]
                if top_sids:
                    sellers_r = supabase_admin.table('sellers').select('id,user_id,shop_name,shop_description') \
                                   .in_('id', top_sids).execute()
                    for s in (sellers_r.data or []):
                        prod_r = supabase_admin.table('products').select('images').eq('seller_id', s['id']) \
                                   .eq('is_active', True).limit(1).execute()
                        avatar = None
                        if prod_r.data:
                            imgs = prod_r.data[0].get('images') or []
                            avatar = imgs[0] if imgs else None
                        s['avatar'] = avatar
                        s['order_count'] = s_counts.get(s['id'], 0)
                        best_stores.append(s)
            except Exception:
                pass
            
            try:
                # Buyer's orders and wishlist stats
                order_count = supabase_admin.table('orders').select('id', count='exact') \
                                .eq('buyer_id', current_user.id).execute()
                stats['orders'] = order_count.count or 0
                wl_count = supabase_admin.table('wishlists').select('id', count='exact') \
                             .eq('buyer_id', current_user.id).execute()
                stats['wishlist'] = wl_count.count or 0
            except Exception:
                pass
            
            try:
                # Recently viewed products
                rv_ids = session.get('recently_viewed') or []
                if rv_ids:
                    rv_rows = supabase_admin.table('products').select('id,name,price,images,condition') \
                               .in_('id', rv_ids).eq('is_active', True).eq('is_deleted', False).execute().data or []
                    rv_map = {p['id']: p for p in rv_rows}
                    recently_viewed = [rv_map[i] for i in rv_ids if i in rv_map]
                    for p in recently_viewed:
                        annotate_sale(p)
            except Exception:
                pass
            
            try:
                # Followed shops
                sf_rows = supabase_admin.table('seller_follows').select('seller_id') \
                    .eq('buyer_id', str(current_user.id)).order('created_at', desc=True).execute().data or []
                followed_ids = [r['seller_id'] for r in sf_rows]
                if followed_ids:
                    sellers_r = supabase_admin.table('sellers').select('id,user_id,shop_name') \
                        .in_('id', followed_ids).execute().data or []
                    s_map = {s['id']: s for s in sellers_r}
                    for sid in followed_ids:
                        if sid not in s_map:
                            continue
                        s = dict(s_map[sid])
                        try:
                            av_r = supabase_admin.table('products').select('images') \
                                .eq('seller_id', sid).eq('is_active', True).limit(1).execute()
                            imgs = (av_r.data[0].get('images') or []) if av_r.data else []
                            s['avatar'] = imgs[0] if imgs else None
                        except Exception:
                            s['avatar'] = None
                        followed_shops.append(s)
            except Exception:
                pass
            
            try:
                # Wishlisted IDs
                all_pids = [p['id'] for p in recently_viewed + new_products + best_products]
                if all_pids:
                    wl_r = supabase_admin.table('wishlists').select('product_id') \
                             .eq('buyer_id', current_user.id).in_('product_id', all_pids).execute()
                    wishlisted_ids = {row['product_id'] for row in (wl_r.data or [])}
            except Exception:
                pass
            
            return render_template('landing.html',
                                   new_products=new_products,
                                   best_products=best_products,
                                   best_stores=best_stores,
                                   followed_shops=followed_shops,
                                   recently_viewed=recently_viewed,
                                   wishlisted_ids=wishlisted_ids,
                                   stats=stats)

        # ─ FOR UNAUTHENTICATED VISITORS: Show public landing with featured products ─
        featured = []
        best_stores = []
        stats = {'products': 0, 'sellers': 0, 'buyers': 0, 'orders': 0}
        try:
            r_feat = supabase_admin.table('products') \
                .select('id,name,price,images') \
                .eq('is_active', True) \
                .order('created_at', desc=True) \
                .limit(8).execute()
            featured = r_feat.data or []

            r_prod  = supabase_admin.table('products').select('id', count='exact').eq('is_active', True).execute()
            r_sell  = supabase_admin.table('sellers').select('id', count='exact').eq('is_verified', True).execute()
            r_buy   = supabase_admin.table('profiles').select('id', count='exact').eq('role', 'buyer').execute()
            r_ord   = supabase_admin.table('orders').select('id', count='exact').execute()
            stats = {
                'products': r_prod.count  or 0,
                'sellers':  r_sell.count  or 0,
                'buyers':   r_buy.count   or 0,
                'orders':   r_ord.count   or 0,
            }
        except Exception:
            pass
        
        # Fetch top stores for unauthenticated visitors
        try:
            orders_r = supabase_admin.table('orders').select('seller_id').execute()
            orders = orders_r.data or []
            s_counts = Counter(o['seller_id'] for o in orders if o.get('seller_id'))
            top_sids = [sid for sid, _ in s_counts.most_common(6)]
            if not top_sids:
                any_s = supabase_admin.table('sellers').select('id').limit(6).execute()
                top_sids = [s['id'] for s in (any_s.data or [])]
            if top_sids:
                sellers_r = supabase_admin.table('sellers').select('id,user_id,shop_name,shop_description') \
                               .in_('id', top_sids).execute()
                for s in (sellers_r.data or []):
                    prod_r = supabase_admin.table('products').select('images').eq('seller_id', s['id']) \
                               .eq('is_active', True).limit(1).execute()
                    avatar = None
                    if prod_r.data:
                        imgs = prod_r.data[0].get('images') or []
                        avatar = imgs[0] if imgs else None
                    s['avatar'] = avatar
                    s['order_count'] = s_counts.get(s['id'], 0)
                    best_stores.append(s)
        except Exception:
            pass

        return render_template('landing.html', featured=featured, best_stores=best_stores, stats=stats)
    
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'kidzora-api'}

    @app.route('/sw.js')
    def service_worker():
        """Serve the service worker from the origin root (required for full-scope push)."""
        from flask import send_from_directory
        response = send_from_directory(app.static_folder, 'sw.js')
        response.headers['Content-Type']          = 'application/javascript'
        response.headers['Service-Worker-Allowed'] = '/'
        response.headers['Cache-Control']          = 'no-cache, no-store, must-revalidate'
        return response

    return app
