# KidZora Mobile App — Flutter/Dart Guide
### Buyer & Rider Registration (Mobile Only)

> **Scope:** This guide covers only the **Buyer** and **Rider** registration flows for the Flutter mobile app. The Seller and Admin panels remain web-only (Flask).

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Project Setup](#project-setup)
3. [Folder Structure](#folder-structure)
4. [Dependencies](#dependencies)
5. [Supabase Connection](#supabase-connection)
6. [App Entry Point](#app-entry-point)
7. [Registration Flow Overview](#registration-flow-overview)
8. [Step-by-Step: Buyer Registration](#step-by-step-buyer-registration)
9. [Step-by-Step: Rider Registration](#step-by-step-rider-registration)
10. [Email OTP Verification](#email-otp-verification)
11. [Supabase Tables Reference](#supabase-tables-reference)
12. [Running the App](#running-the-app)

---

## Prerequisites

Make sure the following are installed on your machine:

| Tool | Version | Download |
|------|---------|----------|
| Flutter SDK | 3.19+ | https://flutter.dev/docs/get-started/install |
| Dart SDK | Included with Flutter | — |
| Android Studio / Xcode | Latest | For emulator/simulator |
| VS Code (optional) | Latest | With Flutter & Dart extensions |

Verify your installation:
```bash
flutter doctor
```

---

## Project Setup

```bash
# Create the Flutter project
flutter create kidzora_mobile

# Navigate into it
cd kidzora_mobile

# Open in VS Code
code .
```

---

## Folder Structure

```
kidzora_mobile/
├── lib/
│   ├── main.dart
│   ├── supabase_client.dart          # Supabase singleton
│   ├── models/
│   │   └── user_model.dart
│   ├── screens/
│   │   ├── splash_screen.dart
│   │   ├── role_select_screen.dart   # Choose Buyer or Rider
│   │   ├── auth/
│   │   │   ├── email_verify_screen.dart
│   │   │   ├── otp_screen.dart
│   │   │   ├── buyer_register_screen.dart
│   │   │   └── rider_register_screen.dart
│   │   └── home/
│   │       ├── buyer_home_screen.dart
│   │       └── rider_home_screen.dart
│   ├── services/
│   │   ├── auth_service.dart
│   │   └── email_service.dart
│   └── widgets/
│       ├── custom_text_field.dart
│       └── document_upload_tile.dart
├── assets/
│   └── images/
│       └── logo.png
└── pubspec.yaml
```

---

## Dependencies

Open `pubspec.yaml` and replace the `dependencies` section:

```yaml
dependencies:
  flutter:
    sdk: flutter

  # Supabase — connects to your existing backend
  supabase_flutter: ^2.5.0

  # Image & file picking for rider document uploads
  image_picker: ^1.1.0
  file_picker: ^8.0.0

  # HTTP requests (OTP email via your Flask or Resend SMTP)
  http: ^1.2.0

  # Navigation
  go_router: ^13.2.0

  # Storing tokens securely
  flutter_secure_storage: ^9.2.2

  # Loading state indicators
  flutter_spinkit: ^5.2.1

  # Form validation helper
  form_validator: ^2.1.1

  # Country/region picker (for address fields)
  country_state_city_picker: ^2.0.1
```

Then run:
```bash
flutter pub get
```

---

## Supabase Connection

Your existing KidZora backend already uses Supabase. Use the **same** Supabase project credentials.

Create `lib/supabase_client.dart`:

```dart
import 'package:supabase_flutter/supabase_flutter.dart';

// These values come from your existing .env / config.py
const String supabaseUrl  = 'YOUR_SUPABASE_URL';    // SUPABASE_URL from config.py
const String supabaseAnon = 'YOUR_SUPABASE_ANON_KEY'; // SUPABASE_ANON_KEY from config.py

Future<void> initSupabase() async {
  await Supabase.initialize(
    url: supabaseUrl,
    anonKey: supabaseAnon,
  );
}

// Global accessor used throughout the app
final supabase = Supabase.instance.client;
```

> **Where to find your keys:** Check your `.env` file in the Flask project root.
> `SUPABASE_URL` and `SUPABASE_ANON_KEY` are what you need here.

---

## App Entry Point

`lib/main.dart`:

```dart
import 'package:flutter/material.dart';
import 'supabase_client.dart';
import 'screens/role_select_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initSupabase();
  runApp(const KidzoraMobileApp());
}

class KidzoraMobileApp extends StatelessWidget {
  const KidzoraMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KidZora',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF4F46E5), // KidZora primary purple
        ),
        useMaterial3: true,
      ),
      home: const RoleSelectScreen(),
    );
  }
}
```

---

## Registration Flow Overview

```
App Launch
    │
    ▼
Role Select Screen
    ├── [Buyer]  ──► Email Verify ──► OTP ──► Buyer Register Form ──► Profile Created ──► Buyer Home
    └── [Rider]  ──► Email Verify ──► OTP ──► Rider Register Form ──► Profile + Riders Row Created ──► Rider Home (Pending Approval)
```

> **Note:** Riders require **admin approval** (same as the web app). After registration the rider sees a "Pending Approval" screen until the admin approves them on the web panel.

---

## Step-by-Step: Buyer Registration

### Fields Required (mirrors the web form)

| Field | Validation |
|-------|-----------|
| First Name | Required |
| Last Name | Required |
| Email | Valid email, must be verified via OTP |
| Phone | Exactly 11 digits, numbers only |
| Password | Min 8 chars, uppercase, lowercase, number, special char |
| Confirm Password | Must match password |
| Region | Required |
| Province | Required |
| City / Municipality | Required |
| Barangay | Required |
| Building / Unit Number | Required |
| Street Name | Required |
| Postal Code | Exactly 4 digits |
| Country | Default: Philippines (read-only) |
| Terms & Privacy | Must accept both |

### What happens on submit

1. Supabase Auth creates a new user (`supabase.auth.signUp`)
2. A row is inserted into the `profiles` table with `role = 'buyer'` and `is_approved = true` (buyers are auto-approved)

### Code — `lib/screens/auth/buyer_register_screen.dart`

```dart
import 'package:flutter/material.dart';
import '../../supabase_client.dart';

class BuyerRegisterScreen extends StatefulWidget {
  final String verifiedEmail;
  const BuyerRegisterScreen({super.key, required this.verifiedEmail});

  @override
  State<BuyerRegisterScreen> createState() => _BuyerRegisterScreenState();
}

class _BuyerRegisterScreenState extends State<BuyerRegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _firstNameCtrl    = TextEditingController();
  final _lastNameCtrl     = TextEditingController();
  final _phoneCtrl        = TextEditingController();
  final _passwordCtrl     = TextEditingController();
  final _confirmPassCtrl  = TextEditingController();
  final _regionCtrl       = TextEditingController();
  final _provinceCtrl     = TextEditingController();
  final _cityCtrl         = TextEditingController();
  final _barangayCtrl     = TextEditingController();
  final _buildingCtrl     = TextEditingController();
  final _streetCtrl       = TextEditingController();
  final _postalCtrl       = TextEditingController();
  bool _termsAccepted   = false;
  bool _privacyAccepted = false;
  bool _isLoading       = false;

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;
    if (!_termsAccepted || !_privacyAccepted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please accept Terms and Privacy Policy.')),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      // 1. Create auth user
      final authResp = await supabase.auth.signUp(
        email: widget.verifiedEmail,
        password: _passwordCtrl.text.trim(),
        data: {
          'first_name': _firstNameCtrl.text.trim(),
          'last_name':  _lastNameCtrl.text.trim(),
          'phone':      _phoneCtrl.text.trim(),
        },
      );

      final userId = authResp.user?.id;
      if (userId == null) throw Exception('Registration failed.');

      // 2. Insert profile row
      await supabase.from('profiles').insert({
        'id':              userId,
        'email':           widget.verifiedEmail,
        'first_name':      _firstNameCtrl.text.trim(),
        'last_name':       _lastNameCtrl.text.trim(),
        'phone':           _phoneCtrl.text.trim(),
        'role':            'buyer',
        'is_approved':     true,
        'building_number': _buildingCtrl.text.trim(),
        'street_name':     _streetCtrl.text.trim(),
        'city':            _cityCtrl.text.trim(),
        'postal_code':     _postalCtrl.text.trim(),
        'region':          _regionCtrl.text.trim(),
        'province':        _provinceCtrl.text.trim(),
        'barangay':        _barangayCtrl.text.trim(),
        'country':         'Philippines',
        'newsletter':      false,
      });

      if (!mounted) return;
      Navigator.pushReplacementNamed(context, '/buyer-home');
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Buyer Registration')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // -- Email (pre-filled, read-only) --
              Text('Email: ${widget.verifiedEmail}',
                  style: const TextStyle(color: Colors.grey)),
              const SizedBox(height: 16),

              // -- Personal Info --
              const Text('Personal Information',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const Divider(),
              TextFormField(
                controller: _firstNameCtrl,
                decoration: const InputDecoration(labelText: 'First Name *'),
                validator: (v) => v!.isEmpty ? 'Required' : null,
              ),
              TextFormField(
                controller: _lastNameCtrl,
                decoration: const InputDecoration(labelText: 'Last Name *'),
                validator: (v) => v!.isEmpty ? 'Required' : null,
              ),
              TextFormField(
                controller: _phoneCtrl,
                decoration: const InputDecoration(labelText: 'Phone Number * (11 digits)'),
                keyboardType: TextInputType.number,
                maxLength: 11,
                validator: (v) {
                  if (v == null || !RegExp(r'^[0-9]{11}$').hasMatch(v)) {
                    return 'Must be exactly 11 digits';
                  }
                  return null;
                },
              ),
              TextFormField(
                controller: _passwordCtrl,
                decoration: const InputDecoration(labelText: 'Password *'),
                obscureText: true,
                validator: (v) {
                  if (v == null || v.length < 8) return 'Min 8 characters';
                  if (!RegExp(r'[A-Z]').hasMatch(v)) return 'Needs uppercase letter';
                  if (!RegExp(r'[a-z]').hasMatch(v)) return 'Needs lowercase letter';
                  if (!RegExp(r'[0-9]').hasMatch(v)) return 'Needs a number';
                  if (!RegExp(r'[!@#\$&*~^%]').hasMatch(v)) return 'Needs a special character';
                  return null;
                },
              ),
              TextFormField(
                controller: _confirmPassCtrl,
                decoration: const InputDecoration(labelText: 'Confirm Password *'),
                obscureText: true,
                validator: (v) =>
                    v != _passwordCtrl.text ? 'Passwords do not match' : null,
              ),

              const SizedBox(height: 16),
              // -- Address --
              const Text('Location Details',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const Divider(),
              TextFormField(controller: _regionCtrl,   decoration: const InputDecoration(labelText: 'Region *'),   validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _provinceCtrl, decoration: const InputDecoration(labelText: 'Province *'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _cityCtrl,     decoration: const InputDecoration(labelText: 'City / Municipality *'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _barangayCtrl, decoration: const InputDecoration(labelText: 'Barangay *'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _buildingCtrl, decoration: const InputDecoration(labelText: 'Building / Unit Number *'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _streetCtrl,   decoration: const InputDecoration(labelText: 'Street Name *'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(
                controller: _postalCtrl,
                decoration: const InputDecoration(labelText: 'Postal Code * (4 digits)'),
                keyboardType: TextInputType.number,
                maxLength: 4,
                validator: (v) {
                  if (v == null || !RegExp(r'^[0-9]{4}$').hasMatch(v)) {
                    return 'Must be exactly 4 digits';
                  }
                  return null;
                },
              ),
              const TextField(
                decoration: InputDecoration(labelText: 'Country'),
                readOnly: true,
                controller: TextEditingController(text: 'Philippines'),
              ),

              const SizedBox(height: 16),
              // -- Agreements --
              CheckboxListTile(
                value: _termsAccepted,
                title: const Text('I agree to the Terms and Conditions'),
                onChanged: (v) => setState(() => _termsAccepted = v!),
              ),
              CheckboxListTile(
                value: _privacyAccepted,
                title: const Text('I agree to the Privacy Policy'),
                onChanged: (v) => setState(() => _privacyAccepted = v!),
              ),

              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _register,
                  child: _isLoading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text('Create Buyer Account'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

---

## Step-by-Step: Rider Registration

### Fields Required

| Field | Validation |
|-------|-----------|
| All fields from Buyer | Same rules |
| Licensed ID (photo/PDF) | Required — driver's license |
| Official Receipt / OR (photo/PDF) | Required — vehicle document |
| Certificate of Registration / CR (photo/PDF) | Required — vehicle document |

### What happens on submit

1. Supabase Auth creates a new user
2. A row is inserted into `profiles` with `role = 'rider'` and `is_approved = false`
3. Documents are uploaded to **Supabase Storage** (bucket: `rider-documents`)
4. A row is inserted into the `riders` table with the document URLs
5. Admin approves via the web panel

### Supabase Storage Setup

Before running the mobile app, create a **private** storage bucket in Supabase:

1. Go to your Supabase project → **Storage**
2. Click **New bucket**
3. Name: `rider-documents`
4. Toggle **Public bucket: OFF** (private)
5. Click **Create bucket**

### Code — `lib/screens/auth/rider_register_screen.dart`

```dart
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import '../../supabase_client.dart';

class RiderRegisterScreen extends StatefulWidget {
  final String verifiedEmail;
  const RiderRegisterScreen({super.key, required this.verifiedEmail});

  @override
  State<RiderRegisterScreen> createState() => _RiderRegisterScreenState();
}

class _RiderRegisterScreenState extends State<RiderRegisterScreen> {
  final _formKey = GlobalKey<FormState>();

  // -- Text controllers (same as buyer) --
  final _firstNameCtrl   = TextEditingController();
  final _lastNameCtrl    = TextEditingController();
  final _phoneCtrl       = TextEditingController();
  final _passwordCtrl    = TextEditingController();
  final _confirmPassCtrl = TextEditingController();
  final _regionCtrl      = TextEditingController();
  final _provinceCtrl    = TextEditingController();
  final _cityCtrl        = TextEditingController();
  final _barangayCtrl    = TextEditingController();
  final _buildingCtrl    = TextEditingController();
  final _streetCtrl      = TextEditingController();
  final _postalCtrl      = TextEditingController();

  // -- Document files --
  File? _licensedIdFile;
  File? _receiptFile;
  File? _corFile;

  bool _termsAccepted   = false;
  bool _privacyAccepted = false;
  bool _isLoading       = false;

  // Pick image or PDF for a document
  Future<File?> _pickDocument() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['jpg', 'jpeg', 'png', 'pdf'],
    );
    if (result != null && result.files.single.path != null) {
      return File(result.files.single.path!);
    }
    return null;
  }

  // Upload a file to Supabase Storage and return its public/signed URL
  Future<String?> _uploadDocument(File file, String userId, String docType) async {
    final ext      = file.path.split('.').last;
    final path     = 'riders/$userId/${docType}_$userId.$ext';
    final bytes    = await file.readAsBytes();

    await supabase.storage
        .from('rider-documents')
        .uploadBinary(path, bytes,
            fileOptions: const FileOptions(upsert: true));

    // Return signed URL (valid 10 years — adjust as needed)
    final signedUrl = await supabase.storage
        .from('rider-documents')
        .createSignedUrl(path, 60 * 60 * 24 * 365 * 10);

    return signedUrl;
  }

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;
    if (_licensedIdFile == null || _receiptFile == null || _corFile == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please upload all three rider documents.')),
      );
      return;
    }
    if (!_termsAccepted || !_privacyAccepted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please accept Terms and Privacy Policy.')),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      // 1. Create auth user
      final authResp = await supabase.auth.signUp(
        email: widget.verifiedEmail,
        password: _passwordCtrl.text.trim(),
        data: {
          'first_name': _firstNameCtrl.text.trim(),
          'last_name':  _lastNameCtrl.text.trim(),
          'phone':      _phoneCtrl.text.trim(),
        },
      );

      final userId = authResp.user?.id;
      if (userId == null) throw Exception('Registration failed.');

      // 2. Insert profile row
      await supabase.from('profiles').insert({
        'id':              userId,
        'email':           widget.verifiedEmail,
        'first_name':      _firstNameCtrl.text.trim(),
        'last_name':       _lastNameCtrl.text.trim(),
        'phone':           _phoneCtrl.text.trim(),
        'role':            'rider',
        'is_approved':     false,   // riders need admin approval
        'building_number': _buildingCtrl.text.trim(),
        'street_name':     _streetCtrl.text.trim(),
        'city':            _cityCtrl.text.trim(),
        'postal_code':     _postalCtrl.text.trim(),
        'region':          _regionCtrl.text.trim(),
        'province':        _provinceCtrl.text.trim(),
        'barangay':        _barangayCtrl.text.trim(),
        'country':         'Philippines',
        'newsletter':      false,
      });

      // 3. Upload documents to Supabase Storage
      final licensedIdUrl = await _uploadDocument(_licensedIdFile!, userId, 'licensed_id');
      final receiptUrl    = await _uploadDocument(_receiptFile!,    userId, 'original_receipt');
      final corUrl        = await _uploadDocument(_corFile!,        userId, 'cor');

      // 4. Insert riders row
      await supabase.from('riders').insert({
        'user_id':                          userId,
        'licensed_id_url':                  licensedIdUrl,
        'original_receipt_url':             receiptUrl,
        'certificate_of_registration_url':  corUrl,
        'is_active':                        true,
      });

      if (!mounted) return;
      // Show pending approval screen
      Navigator.pushReplacementNamed(context, '/rider-pending');
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // Helper widget for each document upload tile
  Widget _docTile(String label, File? file, VoidCallback onTap) {
    return ListTile(
      tileColor: Colors.grey[100],
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      leading: Icon(
        file != null ? Icons.check_circle : Icons.upload_file,
        color: file != null ? Colors.green : Colors.grey,
      ),
      title: Text(label),
      subtitle: file != null
          ? Text(file.path.split('/').last,
              style: const TextStyle(fontSize: 12, color: Colors.green))
          : const Text('Tap to upload (JPG, PNG, PDF)',
              style: TextStyle(fontSize: 12)),
      onTap: onTap,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Rider Registration')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Email: ${widget.verifiedEmail}',
                  style: const TextStyle(color: Colors.grey)),
              const SizedBox(height: 16),

              // ---- Personal Info ----
              const Text('Personal Information',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const Divider(),
              TextFormField(controller: _firstNameCtrl,   decoration: const InputDecoration(labelText: 'First Name *'),   validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _lastNameCtrl,    decoration: const InputDecoration(labelText: 'Last Name *'),    validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(
                controller: _phoneCtrl,
                decoration: const InputDecoration(labelText: 'Phone Number * (11 digits)'),
                keyboardType: TextInputType.number,
                maxLength: 11,
                validator: (v) => (v == null || !RegExp(r'^[0-9]{11}$').hasMatch(v))
                    ? 'Must be exactly 11 digits' : null,
              ),
              TextFormField(
                controller: _passwordCtrl,
                decoration: const InputDecoration(labelText: 'Password *'),
                obscureText: true,
                validator: (v) {
                  if (v == null || v.length < 8) return 'Min 8 characters';
                  if (!RegExp(r'[A-Z]').hasMatch(v)) return 'Needs uppercase letter';
                  if (!RegExp(r'[a-z]').hasMatch(v)) return 'Needs lowercase letter';
                  if (!RegExp(r'[0-9]').hasMatch(v)) return 'Needs a number';
                  if (!RegExp(r'[!@#\$&*~^%]').hasMatch(v)) return 'Needs a special character';
                  return null;
                },
              ),
              TextFormField(
                controller: _confirmPassCtrl,
                decoration: const InputDecoration(labelText: 'Confirm Password *'),
                obscureText: true,
                validator: (v) => v != _passwordCtrl.text ? 'Passwords do not match' : null,
              ),

              const SizedBox(height: 16),
              // ---- Address ----
              const Text('Location Details',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const Divider(),
              TextFormField(controller: _regionCtrl,   decoration: const InputDecoration(labelText: 'Region *'),   validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _provinceCtrl, decoration: const InputDecoration(labelText: 'Province *'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _cityCtrl,     decoration: const InputDecoration(labelText: 'City / Municipality *'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _barangayCtrl, decoration: const InputDecoration(labelText: 'Barangay *'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _buildingCtrl, decoration: const InputDecoration(labelText: 'Building / Unit Number *'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _streetCtrl,   decoration: const InputDecoration(labelText: 'Street Name *'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(
                controller: _postalCtrl,
                decoration: const InputDecoration(labelText: 'Postal Code * (4 digits)'),
                keyboardType: TextInputType.number,
                maxLength: 4,
                validator: (v) => (v == null || !RegExp(r'^[0-9]{4}$').hasMatch(v))
                    ? 'Must be exactly 4 digits' : null,
              ),

              const SizedBox(height: 16),
              // ---- Rider Documents ----
              const Text('Rider Documents',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const Divider(),
              const Text(
                'Upload clear photos or PDFs of the following documents:',
                style: TextStyle(color: Colors.grey, fontSize: 13),
              ),
              const SizedBox(height: 10),
              _docTile("Driver's License / Licensed ID *", _licensedIdFile, () async {
                final f = await _pickDocument();
                if (f != null) setState(() => _licensedIdFile = f);
              }),
              const SizedBox(height: 8),
              _docTile('Official Receipt (OR) *', _receiptFile, () async {
                final f = await _pickDocument();
                if (f != null) setState(() => _receiptFile = f);
              }),
              const SizedBox(height: 8),
              _docTile('Certificate of Registration (CR) *', _corFile, () async {
                final f = await _pickDocument();
                if (f != null) setState(() => _corFile = f);
              }),

              const SizedBox(height: 16),
              // ---- Agreements ----
              CheckboxListTile(
                value: _termsAccepted,
                title: const Text('I agree to the Terms and Conditions'),
                onChanged: (v) => setState(() => _termsAccepted = v!),
              ),
              CheckboxListTile(
                value: _privacyAccepted,
                title: const Text('I agree to the Privacy Policy'),
                onChanged: (v) => setState(() => _privacyAccepted = v!),
              ),

              const SizedBox(height: 8),
              // Pending notice for riders
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.amber[50],
                  border: Border.all(color: Colors.amber),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.info_outline, color: Colors.amber),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Rider accounts require admin approval. You will be notified once your account is reviewed.',
                        style: TextStyle(fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _register,
                  child: _isLoading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text('Submit Rider Application'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

---

## Email OTP Verification

The OTP flow mirrors the web app: send a 6-digit code to the user's email before showing the registration form.

### Code — `lib/services/email_service.dart`

```dart
import 'dart:math';
import 'package:http/http.dart' as http;
import 'dart:convert';

class EmailService {
  // Point this at your running Flask backend
  static const String _flaskBaseUrl = 'https://your-flask-app.com';

  static String generateCode() {
    final rng = Random();
    return List.generate(6, (_) => rng.nextInt(10).toString()).join();
  }

  // Calls your existing Flask /resend-code endpoint
  static Future<bool> sendOtp(String email, String code) async {
    try {
      final resp = await http.post(
        Uri.parse('$_flaskBaseUrl/resend-code'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email}),
      );
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}
```

> **Alternative:** Use Supabase's built-in OTP by calling `supabase.auth.signInWithOtp(email: email)`. This sends a magic link / OTP from Supabase directly without needing your Flask server.

---

## Supabase Tables Reference

Your mobile app writes to these existing tables:

### `profiles`
| Column | Type | Mobile sets? |
|--------|------|-------------|
| id | uuid | ✅ (from auth.user.id) |
| email | text | ✅ |
| first_name | text | ✅ |
| last_name | text | ✅ |
| phone | text | ✅ |
| role | text | ✅ (`buyer` or `rider`) |
| is_approved | boolean | ✅ (`true` for buyer, `false` for rider) |
| building_number | text | ✅ |
| street_name | text | ✅ |
| city | text | ✅ |
| postal_code | text | ✅ |
| region | text | ✅ |
| province | text | ✅ |
| barangay | text | ✅ |
| country | text | ✅ (`Philippines`) |

### `riders`
| Column | Type | Mobile sets? |
|--------|------|-------------|
| user_id | uuid | ✅ |
| licensed_id_url | text | ✅ (Supabase Storage URL) |
| original_receipt_url | text | ✅ |
| certificate_of_registration_url | text | ✅ |
| is_active | boolean | ✅ (`true`) |

---

## Running the App

### Android
```bash
# List available emulators
flutter emulators

# Launch emulator
flutter emulators --launch <emulator_id>

# Run the app
flutter run
```

### iOS (Mac only)
```bash
# Open iOS simulator
open -a Simulator

# Run
flutter run
```

### Build Release APK (Android)
```bash
flutter build apk --release
# Output: build/app/outputs/flutter-apk/app-release.apk
```

### Build Release IPA (iOS — requires Xcode on Mac)
```bash
flutter build ipa --release
```

---

## Android Permissions

Add to `android/app/src/main/AndroidManifest.xml` inside `<manifest>`:
```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
<uses-permission android:name="android.permission.CAMERA"/>
```

## iOS Permissions

Add to `ios/Runner/Info.plist`:
```xml
<key>NSCameraUsageDescription</key>
<string>KidZora needs camera access to upload rider documents.</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>KidZora needs photo library access to upload rider documents.</string>
</plist>
```

---

## Quick Checklist Before Testing

- [ ] Flutter SDK installed and `flutter doctor` passes
- [ ] `SUPABASE_URL` and `SUPABASE_ANON_KEY` copied from your `.env` into `supabase_client.dart`
- [ ] `rider-documents` storage bucket created in Supabase (private)
- [ ] RLS policies on `profiles` and `riders` allow insert for authenticated users
- [ ] `flutter pub get` run successfully
- [ ] Android emulator or iOS simulator running

---

*KidZora Mobile — Buyer & Rider Registration Guide*
