# Supabase Storage "images" Bucket - Setup & Usage Guide

## ✅ Setup Completed

Your new `images` bucket is ready to use for general-purpose image uploads in your KidZora project.

---

## 📋 Current Storage Buckets

| Bucket Name | Purpose | Public | Status |
|---|---|---|---|
| `product-images` | Product photos | ✅ Yes | Active |
| `avatars` | User profile pictures | ✅ Yes | Active |
| `review-media` | Product review photos/videos | ✅ Yes | Active |
| `return-evidence` | Return request proof files | ✅ Yes | Active |
| `delivery-proofs` | Rider delivery photos | ✅ Yes | Active |
| `shop-banners` | Store banner images | ✅ Yes | Active |
| `images` | General uploads (NEW) | ✅ Yes | New |

---

## 🚀 How to Use the "images" Bucket

### **Option 1: Simple Image Upload**

```python
from app.utils.images import upload_image

# In your route handler:
@app.route('/api/upload', methods=['POST'])
def upload_user_image():
    file = request.files['image']
    user_id = current_user.id
    
    # Upload to images bucket with auto-optimization
    url = upload_image(
        file,
        storage_path=f'user-uploads/{user_id}/{file.filename}',
        max_width=900,
        max_height=900,
        quality=82
    )
    
    return jsonify({'success': True, 'url': url})
```

### **Option 2: Video/Non-Image Upload**

```python
from app.utils.images import upload_image_raw

@app.route('/api/upload-video', methods=['POST'])
def upload_video():
    file = request.files['video']
    user_id = current_user.id
    
    # Upload as-is (no compression/optimization)
    url = upload_image_raw(
        file,
        storage_path=f'user-uploads/{user_id}/videos/{file.filename}'
    )
    
    return jsonify({'success': True, 'url': url})
```

### **Option 3: Generic Bucket Upload**

```python
from app.utils.images import upload_to_storage, upload_raw_to_storage

# For specific bucket control
url = upload_to_storage(
    file_obj,
    bucket='images',  # Explicitly specify bucket
    storage_path='my/path/image.webp',
    max_width=900,
    max_height=900,
    quality=82
)
```

---

## 📂 Recommended Path Structure

```
images/
├── user-uploads/
│   ├── {user_id}/
│   │   ├── banners/
│   │   ├── avatars/
│   │   └── uploads/
├── public-gallery/
├── temp/
└── system/
```

---

## 🔐 Security & RLS Policies

The `images` bucket has these Row-Level Security policies:

✅ **Public Read** - Anyone can view images  
✅ **Authenticated Upload** - Any logged-in user can upload  
✅ **Authenticated Update** - Any logged-in user can update images  
✅ **Authenticated Delete** - Any logged-in user can delete images  

> ⚠️ Currently, any authenticated user can delete any image. For production, consider adding ownership checks.

---

## 🛠️ Implementation Steps

1. **Run the SQL Setup:**
   ```sql
   -- In Supabase SQL Editor, run:
   -- Database_Setup_Step45_General_Images_Bucket.sql
   ```

2. **Use in Your Code:**
   ```python
   from app.utils.images import upload_image
   
   url = upload_image(file_obj, 'user-uploads/123/photo.webp')
   ```

3. **Test Upload:**
   - Create a form with `<input type="file">`
   - Send to your upload endpoint
   - Verify URL appears in Supabase Storage dashboard

---

## 📊 Image Optimization Details

When you use `upload_image()`, it automatically:

1. **Reads** the uploaded file
2. **Detects** format (JPEG, PNG, GIF, etc.)
3. **Auto-rotates** based on EXIF data (phone photos stay upright)
4. **Resizes** proportionally if larger than `max_width` × `max_height`
5. **Converts** to **WebP** (better compression, ~30-50% smaller)
6. **Uploads** with optimized quality setting
7. **Returns** public URL ready to use

### Example Optimization:
- Input: 4000×3000 JPEG (8MB)
- Output: 900×675 WebP (85KB)
- Compression: **99% smaller** ✅

---

## 🐛 Error Handling

```python
from app.utils.images import upload_image

try:
    url = upload_image(file, f'user-uploads/{user_id}/pic.webp')
    print(f'✅ Uploaded: {url}')
except RuntimeError as e:
    print(f'❌ Upload failed: {e}')
    return {'error': str(e)}, 500
```

---

## 🔗 Migration: Local Files → Supabase Storage

If you have existing local files in `app/static/uploads/`, migrate them:

```python
import os
from app.utils.images import upload_image_raw

def migrate_local_uploads():
    local_dir = 'app/static/uploads'
    for filename in os.listdir(local_dir):
        if filename.startswith('.'):
            continue
        
        filepath = os.path.join(local_dir, filename)
        with open(filepath, 'rb') as f:
            from werkzeug.datastructures import FileStorage
            file = FileStorage(f, filename=filename)
            
            url = upload_image_raw(file, f'legacy/{filename}')
            print(f'Migrated: {filename} → {url}')
```

---

## 📱 Frontend Integration

In your HTML/JavaScript:

```html
<form id="uploadForm" enctype="multipart/form-data">
  <input type="file" name="image" accept="image/*" required>
  <button type="submit">Upload</button>
  <img id="preview" style="max-width: 300px; display:none;">
</form>

<script>
document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    
    const res = await fetch('/api/upload', { method: 'POST', body: form });
    const data = await res.json();
    
    if (data.success) {
        document.getElementById('preview').src = data.url;
        document.getElementById('preview').style.display = 'block';
    }
});
</script>
```

---

## ✨ Next Steps

1. ✅ Bucket created in Supabase
2. ✅ RLS policies configured
3. ✅ Helper functions added to `app/utils/images.py`
4. → **Run the SQL setup** (Database_Setup_Step45_General_Images_Bucket.sql)
5. → **Implement** in your routes
6. → **Test** with a sample upload
7. → **Deploy** to Vercel

---

## 📚 Reference

- **Supabase Storage Docs:** https://supabase.com/docs/guides/storage
- **Upload Helpers:** `app/utils/images.py`
- **SQL Setup:** `Database_Setup_Step45_General_Images_Bucket.sql`
- **Implementation Examples:** `app/routes/seller/utils.py`, `app/routes/buyer/returns.py`
