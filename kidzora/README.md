# KidZora E-Commerce Platform

A multi-vendor e-commerce platform for kids' products built with Python Flask and Supabase.

## Overview

KidZora is a comprehensive e-commerce platform designed specifically for kids' products where:
- **Admins** oversee all users, manage commissions, and generate reports
- **Sellers** manage products and orders from their shops
- **Buyers** shop for kids' products
- **Riders** handle deliveries

## Tech Stack

- **Backend**: Python 3.10+, Flask
- **Database**: Supabase (PostgreSQL with real-time capabilities)
- **Authentication**: Supabase Auth
- **Storage**: Supabase Storage
- **Frontend**: Jinja2 templates, Bootstrap 5, JavaScript
- **API**: RESTful APIs for mobile app integration

## Features

### Admin Features
- ✅ User management (approve/reject sellers & riders)
- ✅ Ban/activate users
- ✅ Commission overview and tracking
- ✅ Report generation (sales, users, commissions, activity)
- ✅ Coupon management
- ✅ Direct messaging with sellers
- ✅ Dashboard with statistics

### Seller Features
- 📋 Product management (CRUD)
- 📋 Order management
- 📋 Shop profile management
- 📋 Earnings tracking
- 📋 Chat with admin

### Buyer Features
- 📋 Browse and search products
- 📋 Shopping cart
- 📋 Order placement
- 📋 Order tracking
- 📋 Profile management

### Rider Features
- 📋 Delivery assignments
- 📋 Order status updates
- 📋 Earnings tracking
- 📋 Profile management

## Project Structure

```
kidzora/
├── run.py                    # Application entry point
├── config.py                 # Configuration settings
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── extensions.py        # Supabase and Flask extensions
│   ├── models/              # Database models
│   │   ├── profile.py       # User profiles
│   │   ├── seller.py        # Seller profiles
│   │   ├── rider.py         # Rider profiles
│   │   ├── product.py       # Products
│   │   ├── order.py         # Orders
│   │   ├── coupon.py        # Coupons
│   │   ├── message.py       # Messages
│   │   ├── transaction.py   # Transactions
│   │   └── report.py        # Reports
│   ├── routes/              # Web routes
│   │   ├── admin.py         # Admin routes
│   │   ├── seller.py        # Seller routes
│   │   ├── buyer.py         # Buyer routes
│   │   ├── rider.py         # Rider routes
│   │   └── api/             # API routes
│   │       ├── admin.py     # Admin API
│   │       ├── seller.py    # Seller API
│   │       ├── buyer.py     # Buyer API
│   │       └── rider.py     # Rider API
│   ├── services/            # Business logic
│   ├── utils/               # Helper functions
│   │   └── decorators.py    # Auth decorators
│   ├── templates/           # Jinja2 templates
│   │   ├── base.html        # Base template
│   │   └── admin/           # Admin templates
│   └── static/              # Static assets
│       ├── css/
│       ├── js/
│       └── images/
└── tests/                   # Test files
```

## Installation

### Prerequisites
- Python 3.10+
- Node.js (for frontend assets, optional)
- Supabase account

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd kidzora
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your Supabase credentials:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SECRET_KEY=your-secret-key
   ```

5. **Set up Supabase database**
   - Create a new project in Supabase
   - Run the SQL schema provided in `database/schema.sql`
   - Set up Row Level Security (RLS) policies
   - Configure authentication providers

6. **Run the application**
   ```bash
   python run.py
   ```

   The application will be available at `http://localhost:5000`

## Database Schema

### Core Tables

#### profiles
Extended user information with role-based access control
- `id` (UUID, Primary Key)
- `email` (Text, Unique)
- `first_name`, `last_name` (Text)
- `phone` (Text)
- `role` (Text: admin, seller, buyer, rider)
- `is_approved` (Boolean)
- `is_banned` (Boolean)
- `address` (JSONB)
- `created_at`, `updated_at` (Timestamp)

#### sellers
Seller-specific information
- `id` (UUID, Primary Key)
- `user_id` (Foreign Key to profiles)
- `shop_name`, `shop_description` (Text)
- `business_permit`, `valid_id` (Text)
- `bank_account`, `bank_name` (Text)

#### riders
Rider-specific information
- `id` (UUID, Primary Key)
- `user_id` (Foreign Key to profiles)
- `vehicle_type` (Text: motorcycle, bicycle, car)
- `vehicle_plate` (Text)
- `driver_license` (Text)
- `license_expiry` (Date)

#### products
Product catalog
- `id` (UUID, Primary Key)
- `seller_id` (Foreign Key to sellers)
- `name`, `description` (Text)
- `price` (Numeric)
- `category`, `age_group`, `condition` (Text)
- `stock_quantity` (Integer)
- `images` (Array of URLs)
- `is_active` (Boolean)

#### orders
Order management
- `id` (UUID, Primary Key)
- `buyer_id`, `seller_id`, `rider_id` (Foreign Keys)
- `items` (JSONB)
- `total_amount`, `commission`, `seller_earnings` (Numeric)
- `delivery_address` (JSONB)
- `status` (Text: pending, confirmed, preparing, ready_for_pickup, out_for_delivery, delivered, cancelled)
- `payment_status` (Text: pending, paid, refunded)

#### coupons
Discount management
- `id` (UUID, Primary Key)
- `code` (Text, Unique)
- `discount_type` (Text: percentage, fixed)
- `discount_value` (Numeric)
- `min_order_amount`, `max_discount_amount` (Numeric)
- `usage_limit`, `usage_count` (Integer)
- `expires_at` (Timestamp)
- `is_active` (Boolean)

#### messages
Chat system
- `id` (UUID, Primary Key)
- `sender_id`, `receiver_id` (Foreign Keys)
- `content` (Text)
- `message_type` (Text: text, image, file)
- `is_read` (Boolean)

#### transactions
Financial records
- `id` (UUID, Primary Key)
- `order_id`, `seller_id` (Foreign Keys)
- `amount`, `commission_amount`, `seller_earnings` (Numeric)
- `type` (Text: commission, payout, refund)
- `status` (Text: pending, completed, failed)

#### reports
Generated reports
- `id` (UUID, Primary Key)
- `report_type` (Text: sales, users, commissions, activity)
- `title`, `description` (Text)
- `parameters`, `data` (JSONB)
- `generated_by` (Foreign Key to profiles)
- `start_date`, `end_date` (Timestamp)

## API Endpoints

### Admin API (`/api/v1/admin`)
- `GET /users/pending` - List pending users
- `POST /users/<user_id>/approve` - Approve user
- `POST /users/<user_id>/ban` - Ban user
- `GET /commission` - Get commission data
- `GET /reports` - Generate report
- `POST /coupons` - Create coupon
- `PUT /coupons/<id>` - Update coupon
- `DELETE /coupons/<id>` - Delete coupon
- `GET /messages/<seller_id>` - Get conversation

### Seller API (`/api/v1/seller`)
- `GET /products` - List products
- `POST /products` - Create product
- `PUT /products/<id>` - Update product
- `DELETE /products/<id>` - Delete product
- `GET /orders` - List orders
- `PUT /orders/<id>/status` - Update order status

### Buyer API (`/api/v1/buyer`)
- `GET /products` - Browse products
- `POST /cart` - Add to cart
- `POST /orders` - Place order
- `GET /orders` - View orders

### Rider API (`/api/v1/rider`)
- `GET /orders` - Available deliveries
- `POST /orders/<id>/accept` - Accept delivery
- `PUT /orders/<id>/status` - Update delivery status

## Security Features

- **Authentication**: Supabase Auth with JWT tokens
- **Authorization**: Role-based access control
- **Row Level Security**: Database-level security policies
- **Input Validation**: Server-side validation for all inputs
- **CSRF Protection**: Flask-WTF CSRF protection
- **File Upload Security**: File type and size validation

## Commission System

The platform automatically deducts a 5% commission from every completed order:
- Order placed → Payment processed → Commission calculated → Seller receives 95% → Platform receives 5%

## Mobile App Integration

The platform exposes RESTful APIs for mobile app development:
- Flutter/Dart compatible endpoints
- JWT-based authentication
- Real-time updates via Supabase Realtime
- File upload capabilities

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Style
Follow PEP 8 guidelines. Use flake8 for linting:
```bash
flake8 app/
```

### Database Migrations
Use Supabase migration tools or manual SQL scripts.

## Deployment

### Production Setup
1. Set environment variables for production
2. Configure Supabase production project
3. Set up proper SSL certificates
4. Configure reverse proxy (nginx)
5. Set up monitoring and logging

### Environment Variables
```bash
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
SUPABASE_URL=https://your-production-project.supabase.co
SUPABASE_ANON_KEY=your-production-anon-key
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## Roadmap

- [ ] Complete seller, buyer, and rider implementations
- [ ] Add real-time notifications
- [ ] Implement advanced search and filtering
- [ ] Add review and rating system
- [ ] Implement analytics dashboard
- [ ] Add multi-language support
- [ ] Develop mobile apps (Flutter)
- [ ] Add payment gateway integration
- [ ] Implement inventory management
- [ ] Add shipping and tax calculations
