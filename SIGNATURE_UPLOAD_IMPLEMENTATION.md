# Signature Upload Implementation

## Overview
Implemented signature upload functionality for instructors and organization members. This allows users to upload, update, and retrieve digital signatures for courses.

## API Endpoints

### 1. Get Signature
**Endpoint:** `GET /api/v1/instructors/get-signature/`
**Authentication:** Required (IsAuthenticated)
**Description:** Retrieve the current user's signature

**Response:**
```json
{
  "success": true,
  "message": "Signature retrieved successfully.",
  "data": {
    "id": "uuid",
    "name": "John Doe",
    "email": "john@example.com",
    "signature": "signatures/path/to/signature.png",
    "signature_url": "http://example.com/media/signatures/path/to/signature.png"
  },
  "status_code": 200
}
```

### 2. Upload/Update Signature
**Endpoint:** `POST /api/v1/instructors/get-signature/`
**Authentication:** Required (IsAuthenticated)
**Content-Type:** multipart/form-data
**Description:** Upload or update the current user's signature

**Request:**
```
File upload: signature (image/jpeg, image/png, image/gif)
Max size: 5MB
```

**Response:**
```json
{
  "success": true,
  "message": "Signature uploaded successfully.",
  "data": {
    "id": "uuid",
    "name": "John Doe",
    "email": "john@example.com",
    "signature": "signatures/path/to/signature.png",
    "signature_url": "http://example.com/media/signatures/path/to/signature.png"
  },
  "status_code": 200
}
```

### 3. Upload Signature (Alternative)
**Endpoint:** `POST /api/v1/instructors/upload-signature/`
**Authentication:** Required (IsAuthenticated)
**Content-Type:** multipart/form-data
**Description:** Alternative endpoint for uploading signatures

**Request & Response:** Same as endpoint 2

## File Modifications

### 1. `apps/instructors/serializers.py`
Added two new serializers:

#### SignatureUploadSerializer
- Validates signature file (image format, max 5MB)
- Ensures only JPEG, PNG, and GIF formats are allowed
- Provides clear validation error messages

#### UserSignatureSerializer
- Serializes User model with signature field
- Includes signature_url for absolute path to the uploaded file
- Read-only fields: id, name, email

### 2. `apps/instructors/views.py`
Added two new view classes:

#### SignatureUploadAPIView
- Accepts POST requests for signature upload
- Updates both User and Instructor models
- Returns uploaded signature details
- Handles file parsing with MultiPartParser and FormParser

#### MyInstructorSignatureAPIView
- GET: Retrieve current user's signature
- POST: Upload/update current user's signature
- Deletes old signature files when updating
- Updates both User and Instructor models
- Returns updated signature details

### 3. `apps/instructors/urls.py`
Already configured with proper URL routes:
- `/instructors/upload-signature/` → SignatureUploadAPIView
- `/instructors/get-signature/` → MyInstructorSignatureAPIView

## Database Tables Modified

### User Model
- `signature` field (ImageField) - Already exists
- Stores path to uploaded signature image
- Location: `signatures/` directory

### Instructor Model
- `signature` field (ImageField) - Already exists
- Stores path to uploaded signature image
- Location: `signatures/` directory

## Features

1. **Dual Storage:** Signature is stored in both User and Instructor models for flexibility
2. **File Validation:** Validates file type and size before upload
3. **Old File Cleanup:** Removes old signature files when new ones are uploaded
4. **Absolute URLs:** Signature URLs are returned as absolute paths
5. **Error Handling:** Clear error messages for validation failures
6. **Organization Scoping:** Both instructors and organization members can upload signatures

## File Validation

- **Allowed Formats:** JPEG, PNG, GIF
- **Max File Size:** 5MB
- **Content Type Validation:** Checks MIME type against allowed types

## Usage Examples

### Using cURL

#### Get Signature
```bash
curl -X GET http://localhost:8000/api/v1/instructors/get-signature/ \
  -H "Authorization: Bearer <token>"
```

#### Upload Signature
```bash
curl -X POST http://localhost:8000/api/v1/instructors/get-signature/ \
  -H "Authorization: Bearer <token>" \
  -F "signature=@/path/to/signature.png"
```

### Using Python Requests

```python
import requests

# Get signature
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/api/v1/instructors/get-signature/", headers=headers)
print(response.json())

# Upload signature
files = {"signature": open("/path/to/signature.png", "rb")}
response = requests.post("http://localhost:8000/api/v1/instructors/get-signature/", 
                        headers=headers, files=files)
print(response.json())
```

### Using JavaScript/Fetch

```javascript
// Get signature
const response = await fetch("http://localhost:8000/api/v1/instructors/get-signature/", {
  headers: {
    "Authorization": `Bearer ${token}`
  }
});
const data = await response.json();
console.log(data);

// Upload signature
const formData = new FormData();
formData.append("signature", fileInput.files[0]);

const uploadResponse = await fetch("http://localhost:8000/api/v1/instructors/get-signature/", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${token}`
  },
  body: formData
});
const uploadData = await uploadResponse.json();
console.log(uploadData);
```

## Error Handling

### Invalid File Type
**Status Code:** 400
```json
{
  "success": false,
  "message": "Invalid signature file.",
  "data": {
    "signature": ["Only JPEG, PNG, and GIF images are allowed."]
  },
  "status_code": 400
}
```

### File Too Large
**Status Code:** 400
```json
{
  "success": false,
  "message": "Invalid signature file.",
  "data": {
    "signature": ["Signature file size must not exceed 5MB."]
  },
  "status_code": 400
}
```

### Not Authenticated
**Status Code:** 401
```json
{
  "success": false,
  "message": "Authentication credentials were not provided.",
  "status_code": 401
}
```

## File Storage

Signature files are stored in:
- **Media Path:** `media/signatures/`
- **Relative URLs:** `signatures/[filename]`
- **Absolute URLs:** Generated by `build_absolute_uri()` method

## Security Considerations

1. **Authentication Required:** All endpoints require user authentication
2. **File Type Validation:** Only allowed image formats are accepted
3. **File Size Limit:** 5MB maximum to prevent abuse
4. **User Isolation:** Users can only upload/retrieve their own signatures
5. **Old File Cleanup:** Previous signature files are automatically deleted

## Testing Checklist

- [ ] Authenticated user can upload signature
- [ ] Authenticated user can retrieve signature
- [ ] File type validation works (reject non-image files)
- [ ] File size validation works (reject > 5MB)
- [ ] Old signature is deleted when new one is uploaded
- [ ] Both User and Instructor models are updated
- [ ] Absolute URLs are returned correctly
- [ ] Unauthenticated users cannot access endpoints
- [ ] Response format matches specification
- [ ] Error messages are clear and helpful

## Integration Notes

1. **Frontend:** Use multipart/form-data for file uploads
2. **Storage:** Files stored in MEDIA_ROOT/signatures/
3. **Database:** Both User and Instructor signatures updated atomically
4. **URLs:** Use signature_url field for displaying images
5. **Cleanup:** Old files automatically removed on update

## Future Enhancements

1. Add signature verification/authentication
2. Implement digital signature encryption
3. Add batch signature operations
4. Implement signature templates
5. Add signature audit logging
6. Support for multiple signature formats (PDF, etc.)
7. Integration with document signing services
8. Signature expiration and renewal
