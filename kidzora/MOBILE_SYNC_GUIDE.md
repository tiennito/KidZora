# KidZora Mobile ↔ Admin Web Sync Guide

> The Flask admin web panel reads directly from your **Supabase** `profiles` and `riders` tables.
> As long as your Flutter app writes the correct columns to those same tables, the admin panel will see the data **instantly** — no extra sync, no API needed.

---

## How It Works

```
Flutter App  ──── INSERT ────►  Supabase DB  ◄──── SELECT ────  Flask Admin Web
  (mobile)         (same tables)                                    (web panel)
```

The admin's pending list at `/admin/users/pending` runs this query:
```python
# From app/routes/admin/users.py
pending_riders = Profile.get_all({'role': 'rider',  'is_approved': False})
pending_buyers = Profile.get_all({'role': 'buyer',  'is_approved': True})
```

So your Flutter app just needs to insert a row into `profiles` (and `riders` for riders). That's it.

---

## Step 1 — Supabase Credentials in Flutter

In your existing Flutter project, set up the Supabase client with the **same** keys from your `.env` file:

```dart
// lib/core/supabase_config.dart  (or wherever you keep config)
import 'package:supabase_flutter/supabase_flutter.dart';

const supabaseUrl     = 'YOUR_SUPABASE_URL';         // from .env → SUPABASE_URL
const supabaseAnonKey = 'YOUR_SUPABASE_ANON_KEY';    // from .env → SUPABASE_ANON_KEY

Future<void> initSupabase() async {
  await Supabase.initialize(url: supabaseUrl, anonKey: supabaseAnonKey);
}

final supabase = Supabase.instance.client;
```

---

## Step 2 — RLS Policies (run once in Supabase SQL Editor)

Your Flask backend uses the **service role key** which bypasses RLS. The Flutter app uses the **anon key**, so you need to allow inserts from authenticated users. Run this in your Supabase project → **SQL Editor**:

```sql
-- Allow a newly signed-up user to insert their own profile row
CREATE POLICY "Users can insert own profile"
ON public.profiles
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = id);

-- Allow a rider to insert their own riders row
CREATE POLICY "Riders can insert own rider row"
ON public.riders
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Allow authenticated users to read their own profile
CREATE POLICY "Users can read own profile"
ON public.profiles
FOR SELECT
TO authenticated
USING (auth.uid() = id);

-- Allow riders to read their own rider row
CREATE POLICY "Riders can read own rider row"
ON public.riders
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);
```

> If you already have RLS policies, check **Supabase → Authentication → Policies** to avoid duplicates.

---

## Step 3 — Supabase Storage Bucket for Rider Documents (run once)

Go to **Supabase → Storage** and create a bucket:
- **Name:** `rider-documents`
- **Public:** OFF (private)

Then add this RLS policy so riders can upload their own files:

```sql
CREATE POLICY "Riders can upload own documents"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'rider-documents' AND (storage.foldername(name))[1] = auth.uid()::text);
```

---

## Step 4 — Auth Service (Flutter)

This service handles sign-up, inserts the profile, and for riders also creates the `riders` row and uploads documents.

```dart
// lib/services/auth_service.dart
import 'dart:io';
import 'package:supabase_flutter/supabase_flutter.dart';

final _supabase = Supabase.instance.client;

class AuthService {

  // ─────────────────────────────────────────────
  //  BUYER REGISTRATION
  //  After this runs, admin sees the buyer in the
  //  full users list (role=buyer, is_approved=true)
  // ─────────────────────────────────────────────
  static Future<void> registerBuyer({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    required String phone,
    required String region,
    required String province,
    required String city,
    required String barangay,
    required String buildingNumber,
    required String streetName,
    required String postalCode,
  }) async {
    // 1. Create the Supabase auth user
    final authResp = await _supabase.auth.signUp(
      email: email,
      password: password,
    );

    final userId = authResp.user?.id;
    if (userId == null) throw Exception('Sign-up failed.');

    // 2. Insert into profiles table
    //    Admin reads: role='buyer', is_approved=true
    await _supabase.from('profiles').insert({
      'id':              userId,
      'email':           email,
      'first_name':      firstName,
      'last_name':       lastName,
      'phone':           phone,
      'role':            'buyer',      // ← admin filters on this
      'is_approved':     true,         // ← buyers are auto-approved
      'is_banned':       false,
      'building_number': buildingNumber,
      'street_name':     streetName,
      'city':            city,
      'postal_code':     postalCode,
      'region':          region,
      'province':        province,
      'barangay':        barangay,
      'country':         'Philippines',
      'newsletter':      false,
    });
  }

  // ─────────────────────────────────────────────
  //  RIDER REGISTRATION
  //  After this runs, admin sees the rider in the
  //  pending riders list (role=rider, is_approved=false)
  //  and can view uploaded documents
  // ─────────────────────────────────────────────
  static Future<void> registerRider({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    required String phone,
    required String region,
    required String province,
    required String city,
    required String barangay,
    required String buildingNumber,
    required String streetName,
    required String postalCode,
    required File licensedIdFile,
    required File receiptFile,
    required File corFile,
  }) async {
    // 1. Create the Supabase auth user
    final authResp = await _supabase.auth.signUp(
      email: email,
      password: password,
    );

    final userId = authResp.user?.id;
    if (userId == null) throw Exception('Sign-up failed.');

    // 2. Insert into profiles table
    //    Admin reads: role='rider', is_approved=false → shows in pending list
    await _supabase.from('profiles').insert({
      'id':              userId,
      'email':           email,
      'first_name':      firstName,
      'last_name':       lastName,
      'phone':           phone,
      'role':            'rider',      // ← admin filters on this
      'is_approved':     false,        // ← riders need admin approval
      'is_banned':       false,
      'building_number': buildingNumber,
      'street_name':     streetName,
      'city':            city,
      'postal_code':     postalCode,
      'region':          region,
      'province':        province,
      'barangay':        barangay,
      'country':         'Philippines',
      'newsletter':      false,
    });

    // 3. Upload documents to Supabase Storage
    final licensedIdUrl = await _uploadDoc(licensedIdFile, userId, 'licensed_id');
    final receiptUrl    = await _uploadDoc(receiptFile,    userId, 'original_receipt');
    final corUrl        = await _uploadDoc(corFile,        userId, 'cor');

    // 4. Insert into riders table
    //    Admin reads: licensed_id_url, original_receipt_url, certificate_of_registration_url
    await _supabase.from('riders').insert({
      'user_id':                          userId,
      'licensed_id_url':                  licensedIdUrl,
      'original_receipt_url':             receiptUrl,
      'certificate_of_registration_url':  corUrl,
      'is_active':                        true,
    });
  }

  // ─────────────────────────────────────────────
  //  Upload a document to Supabase Storage
  //  Returns a signed URL valid for 10 years
  // ─────────────────────────────────────────────
  static Future<String> _uploadDoc(File file, String userId, String docType) async {
    final ext   = file.path.split('.').last.toLowerCase();
    final path  = '$userId/${docType}_$userId.$ext';   // e.g. abc123/licensed_id_abc123.jpg
    final bytes = await file.readAsBytes();

    await _supabase.storage
        .from('rider-documents')
        .uploadBinary(path, bytes,
            fileOptions: const FileOptions(upsert: true));

    return await _supabase.storage
        .from('rider-documents')
        .createSignedUrl(path, 60 * 60 * 24 * 365 * 10); // 10-year signed URL
  }

  // ─────────────────────────────────────────────
  //  Check if rider has been approved by admin
  //  Call this on the rider's home/pending screen
  // ─────────────────────────────────────────────
  static Future<bool> isRiderApproved(String userId) async {
    final resp = await _supabase
        .from('profiles')
        .select('is_approved')
        .eq('id', userId)
        .single();
    return resp['is_approved'] == true;
  }
}
```

---

## Step 5 — What Admin Sees After Mobile Registration

### Buyer registered from mobile
The buyer appears immediately in the admin's **full users list** (`/admin/users`) because `is_approved = true`. No action needed from admin.

### Rider registered from mobile
The rider appears in **Pending Riders** (`/admin/users/pending`) because `is_approved = false`. The admin:
1. Opens the pending riders table
2. Clicks **View** → sees their name, phone, address, and uploaded documents (licensed ID, OR, CR)
3. Clicks **Approve** or **Reject**

Once the admin clicks **Approve**, the `is_approved` column is set to `true` in Supabase. Your Flutter app can check this with `AuthService.isRiderApproved(userId)`.

---

## Step 6 — Rider Approval Status Screen (Flutter)

Show this screen after a rider registers, and poll for approval status:

```dart
// lib/screens/rider_pending_screen.dart
import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class RiderPendingScreen extends StatefulWidget {
  const RiderPendingScreen({super.key});

  @override
  State<RiderPendingScreen> createState() => _RiderPendingScreenState();
}

class _RiderPendingScreenState extends State<RiderPendingScreen> {
  bool _isApproved = false;

  @override
  void initState() {
    super.initState();
    _listenForApproval();
  }

  void _listenForApproval() {
    final userId = Supabase.instance.client.auth.currentUser?.id;
    if (userId == null) return;

    // Real-time subscription — fires the moment admin clicks Approve
    Supabase.instance.client
        .from('profiles')
        .stream(primaryKey: ['id'])
        .eq('id', userId)
        .listen((data) {
          if (data.isNotEmpty && data[0]['is_approved'] == true) {
            setState(() => _isApproved = true);
          }
        });
  }

  @override
  Widget build(BuildContext context) {
    if (_isApproved) {
      // Redirect to rider home once approved
      WidgetsBinding.instance.addPostFrameCallback((_) {
        Navigator.pushReplacementNamed(context, '/rider-home');
      });
    }

    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.hourglass_top, size: 64, color: Colors.amber),
              const SizedBox(height: 24),
              const Text(
                'Application Under Review',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              const Text(
                'Your rider application has been submitted. The admin will review your documents and approve your account. This page will update automatically.',
                style: TextStyle(color: Colors.grey),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              const CircularProgressIndicator(),
            ],
          ),
        ),
      ),
    );
  }
}
```

> This uses **Supabase Realtime** — the screen updates the instant the admin clicks Approve, no polling needed.

---

## Column Mapping Reference

This is the exact data your Flutter app must write so the Flask admin reads it correctly:

### `profiles` table
| Column | Buyer value | Rider value | Where admin uses it |
|--------|------------|-------------|---------------------|
| `id` | `auth.user.id` | `auth.user.id` | Primary key |
| `role` | `'buyer'` | `'rider'` | Filter for pending/user list |
| `is_approved` | `true` | `false` | Pending list shows `false` only |
| `is_banned` | `false` | `false` | Ban system |
| `first_name` | ✅ | ✅ | Display name |
| `last_name` | ✅ | ✅ | Display name |
| `email` | ✅ | ✅ | Contact / login |
| `phone` | ✅ | ✅ | Contact |
| `region` | ✅ | ✅ | Address display |
| `province` | ✅ | ✅ | Address display |
| `city` | ✅ | ✅ | Address display |
| `barangay` | ✅ | ✅ | Address display |
| `building_number` | ✅ | ✅ | Address display |
| `street_name` | ✅ | ✅ | Address display |
| `postal_code` | ✅ | ✅ | Address display |
| `country` | `'Philippines'` | `'Philippines'` | Address display |

### `riders` table
| Column | Value | Where admin uses it |
|--------|-------|---------------------|
| `user_id` | `auth.user.id` | Joins to profiles |
| `licensed_id_url` | Supabase Storage signed URL | Doc viewer in pending modal |
| `original_receipt_url` | Supabase Storage signed URL | Doc viewer in pending modal |
| `certificate_of_registration_url` | Supabase Storage signed URL | Doc viewer in pending modal |
| `is_active` | `true` | Status indicator |

---

## Quick Test Checklist

- [ ] Copy `SUPABASE_URL` and `SUPABASE_ANON_KEY` from your `.env` into Flutter
- [ ] Run the RLS policy SQL in Supabase SQL Editor
- [ ] Create the `rider-documents` storage bucket (private)
- [ ] Add the storage RLS policy
- [ ] Register a **buyer** from Flutter → open `/admin/users` on the web → should appear
- [ ] Register a **rider** from Flutter → open `/admin/users/pending` on the web → should appear in the Pending Riders table with documents viewable
