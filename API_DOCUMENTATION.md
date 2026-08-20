# EZLain API Documentation

All API endpoints follow a unified response envelope format.

## Standard Envelopes

### Success Envelope (HTTP `200 OK` or `201 Created`)
```json
{
    "success": true,
    "status_code": 200,
    "message": "Success",
    "data": {
        // Resource data or results list
    },
    "meta": {}
}
```

### Error Envelope (HTTP `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`)
```json
{
    "success": false,
    "status_code": 400,
    "message": "Error message description",
    "errors": {
        "field_name": ["Specific validation error message."]
    },
    "data": null
}
```

---

## 1. Authentication & User Management (`/api/v1/accounts/`)

### Register
* **Route:** `POST /api/v1/accounts/register/`
* **Access:** `AllowAny`
* **Request Body (Standard Student Signup):**
  ```json
  {
      "email": "user@example.com",
      "password": "Password123!",
      "password_confirm": "Password123!",
      "first_name": "John",
      "last_name": "Doe"
  }
  ```
* **Request Body (Parent Dashboard Signup - Invite code is optional):**
  ```json
  {
      "email": "parent@example.com",
      "password": "Password123!",
      "password_confirm": "Password123!",
      "full_name": "Devorah Klein",
      "is_parent": true,
      "invite_code": "" // Optional. If given, links to son's account.
  }
  ```
* **Success Response (`201 Created`):**
  ```json
  {
      "success": true,
      "status_code": 201,
      "message": "Success",
      "data": {
          "user": {
              "id": 2,
              "email": "parent@example.com",
              "full_name": "Devorah Klein",
              "role": "Parent",
              "is_pro": false
          },
          "tokens": {
              "refresh": "eyJhbGciOi...",
              "access": "eyJhbGciOi..."
          }
      },
      "meta": {}
  }
  ```
* **Error Response (`400 Bad Request`):**
  ```json
  {
      "success": false,
      "status_code": 400,
      "message": "Email already exists.",
      "errors": {
          "email": ["A user with that email already exists."]
      },
      "data": null
  }
  ```

### Login
* **Route:** `POST /api/v1/accounts/login/`
* **Access:** `AllowAny`
* **Request Body:**
  ```json
  {
      "email": "admin@ezlain.app",
      "password": "AdminPassword123!"
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": {
          "user": {
              "id": 1,
              "email": "admin@ezlain.app",
              "full_name": "Rabbi Admin",
              "role": "Super Admin",
              "is_pro": true
          },
          "tokens": {
              "refresh": "eyJhbGciOi...",
              "access": "eyJhbGciOi..."
          }
      },
      "meta": {}
  }
  ```
* **Error Response (`400 Bad Request`):**
  ```json
  {
      "success": false,
      "status_code": 400,
      "message": "Unable to log in with provided credentials.",
      "errors": {
          "non_field_errors": ["Unable to log in with provided credentials."]
      },
      "data": null
  }
  ```

### Token Refresh
* **Route:** `POST /api/v1/accounts/token/refresh/`
* **Access:** `AllowAny`
* **Request Body:**
  ```json
  {
      "refresh": "eyJhbGciOi..."
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": {
          "access": "eyJhbGciOi..."
      },
      "meta": {}
  }
  ```

### Password Change
* **Route:** `POST /api/v1/accounts/change-password/`
* **Access:** `IsAuthenticated` (Bearer Token required)
* **Request Body:**
  ```json
  {
      "old_password": "OldPassword123!",
      "new_password": "NewPassword123!"
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Password updated successfully",
      "data": null,
      "meta": {}
  }
  ```

### Get My Profile
* **Route:** `GET /api/v1/accounts/users/me/`
* **Access:** `IsAuthenticated` (Bearer Token required)
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": {
          "id": 2,
          "email": "user@example.com",
          "first_name": "Sabbir",
          "last_name": "Ahmed",
          "phone": "+1234567890",
          "avatar": null,
          "date_joined": "2026-07-06T11:42:37Z",
          "is_pro": true,
          "invite_code": "SAB-9981",
          "date_of_birth": "2013-05-15",
          "bar_mitzvah_date": "2026-05-23"
      },
      "meta": {}
  }
  ```

### Update My Profile
* **Route:** `PATCH /api/v1/accounts/users/me/`
* **Access:** `IsAuthenticated`
* **Request Body:**
  ```json
  {
      "first_name": "Sabbir",
      "last_name": "Ahmed",
      "date_of_birth": "2013-05-15"
  }
  ```
* **Success Response (`200 OK`):** Returns updated profile fields.

### Get Referrals Status (Refer Friends)
* **Route:** `GET /api/v1/accounts/users/referrals/`
* **Access:** `IsAuthenticated`
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": {
          "referral_code": "SABBIR-7K2Q",
          "total_referrals": 2,
          "subscribed_referrals": 1,
          "friends": [
              {
                  "name": "Eli K.",
                  "status": "subscribed"
              },
              {
                  "name": "Yossi M.",
                  "status": "invited"
              }
          ]
      },
      "meta": {}
  }
  ```

### Request Personal Coaching
* **Route:** `POST /api/v1/accounts/users/coaching/`
* **Access:** `IsAuthenticated`
* **Request Body:**
  ```json
  {
      "name": "Sabbir Ahmed",
      "phone": "+1234567890",
      "email": "sabbir0087@gmail.com",
      "preferred_times": "Sundays 10am-2pm, Mon/Wed evenings",
      "coaching_type": "zoom" // Choice: "in_person", "zoom"
  }
  ```
* **Success Response (`201 Created`):** Saves request and sends confirmation email to the coaching team.

### Send Feedback
* **Route:** `POST /api/v1/accounts/users/feedback/`
* **Access:** `IsAuthenticated`
* **Request Body:**
  ```json
  {
      "message": "Great app! Love the speed control feature."
  }
  ```
* **Success Response (`201 Created`):** Saves the feedback.

---

## 2. Admin Dashboard & Metrics (`/api/v1/core/admin/`)

### Summary Stats
* **Route:** `GET /api/v1/core/admin/summary/`
* **Access:** `IsAdminUser` (Admin Bearer Token required)
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": {
          "total_users": 2847,
          "pro_subscribers": 1203,
          "audio_files": 384,
          "revenue": 6015.00,
          "recent_uploads": [
              {
                  "id": 1,
                  "title": "Bereishit - Aliya 1",
                  "category": "chumash",
                  "status": "published"
              }
          ]
      },
      "meta": {}
  }
  ```
* **Error Response (`401 Unauthorized`):**
  ```json
  {
      "success": false,
      "status_code": 401,
      "message": "Authentication credentials were not provided.",
      "errors": {
          "detail": "Authentication credentials were not provided."
      },
      "data": null
  }
  ```

### Analytics Charts
* **Route:** `GET /api/v1/core/admin/analytics/`
* **Access:** `IsAdminUser` (Admin Bearer Token required)
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": {
          "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
          "revenue": [420.00, 640.00, 580.00, 820.00, 1040.00, 1180.00],
          "users": [48, 74, 82, 112, 138, 164],
          "audio": {
              "Chumash": 46,
              "Mon-Thu": 24,
              "Haftoros": 18,
              "Megillos": 12,
              "Nusach": 0,
              "Yomim Tovim": 0
          },
          "payments": {
              "Paid": 42,
              "Pending": 5,
              "Failed": 3
          },
          "plays": [360, 440, 405, 590, 650, 720]
      },
      "meta": {}
  }
  ```

### Site Settings
* **Route:** `GET` / `POST` `/api/v1/core/admin/settings/`
* **Access:** `IsAdminUser` (Admin Bearer Token required)
* **POST Request Body:**
  ```json
  {
      "email_reports": true,
      "auto_publish_uploads": false,
      "payment_alerts": true,
      "default_upload_status": "published",
      "library_page_size": 24
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": {
          "email_reports": true,
          "auto_publish_uploads": false,
          "payment_alerts": true,
          "default_upload_status": "published",
          "library_page_size": 24
      },
      "meta": {}
  }
  ```

---

## 3. Audio Library & Content (`/api/v1/content/`)

### List Tracks (Admin View)
* **Route:** `GET /api/v1/content/admin-tracks/`
* **Access:** `IsAdminUser` (Admin Bearer Token required)
* **Query Parameters:** `category`, `status`, `search` (e.g. `?category=chumash&search=Bereishit`)
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": [
          {
              "id": 1,
              "title": "Bereishit - Aliya 1",
              "audio_file": "http://127.0.0.1:8000/media/audio/dummy1.mp3",
              "duration_seconds": 272,
              "file_size_bytes": 1024,
              "category": "chumash",
              "parsha": {
                  "id": 1,
                  "name": "Bereishit",
                  "sefer": "Bereishit"
              },
              "segment_type": "Aliya 1",
              "status": "published",
              "access_level": "pro",
              "created_at": "2026-07-07T14:44:14.281Z"
          }
      ],
      "meta": {}
  }
  ```

### Upload Track
* **Route:** `POST /api/v1/content/admin-tracks/`
* **Access:** `IsAdminUser` (Admin Bearer Token required)
* **Request Format:** `multipart/form-data`
* **Request Payload (Fields):**
  - `title` (String, required)
  - `audio_file` (File, required)
  - `category` (Choice: `chumash`, `mon_thu`, `haftoros`, `megillos`, `nusach`, `yomim_tovim`, required)
  - `parsha_id` (Integer, Optional ForeignKey ID of Parsha)
  - `segment_type` (String, e.g. "Aliya 1", optional)
  - `duration_seconds` (Integer, required)
  - `file_size_bytes` (Integer, required)
  - `status` (Choice: `published`, `draft`, `processing`, default: `draft`)
  - `access_level` (Choice: `free`, `pro`, default: `pro`)
* **Success Response (`201 Created`):** Returns the serialized track object wrapped in the success envelope.

### Edit Track
* **Route:** `PATCH /api/v1/content/admin-tracks/{id}/`
* **Access:** `IsAdminUser`
* **Request Format:** `multipart/form-data` (supports partial updates)
* **Success Response (`200 OK`):** Returns the updated track details.

### Delete Track
* **Route:** `DELETE /api/v1/content/admin-tracks/{id}/`
* **Access:** `IsAdminUser`
* **Success Response (`204 No Content` / `200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 204,
      "message": "Success",
      "data": null,
      "meta": {}
  }
  ```

### List Tracks (Public Student View)
* **Route:** `GET /api/v1/content/tracks/`
* **Access:** `IsAuthenticated`
* **Query Parameters:** `category` (Choice, optional), `parsha` (Integer ID, optional), `access_level` (Choice, optional)
* **Success Response (`200 OK`):**
  - Note: If `is_locked` is `true` (meaning the track requires Pro subscription and user is Free), the `audio_file` URL is masked as `null` for security.
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": [
          {
              "id": 1,
              "title": "Bereishit - Aliya 1",
              "audio_file": "http://127.0.0.1:8000/media/audio/dummy1.mp3", // null if locked
              "duration_seconds": 272,
              "file_size_bytes": 1024,
              "category": "chumash",
              "parsha": {
                  "id": 1,
                  "name": "Bereishit",
                  "sefer": "Bereishit"
              },
              "segment_type": "Aliya 1",
              "grouping": "Yamim Noraim", // String, e.g. Yamim Noraim, Shalosh Regalim (Optional)
              "status": "published",
              "access_level": "pro",
              "is_locked": false, // true if content is locked for the user
              "created_at": "2026-07-07T14:44:14.281Z"
          }
      ],
      "meta": {}
  }
  ```

### Get User Listening History (Seek Position)
* **Route:** `GET /api/v1/content/listening-history/`
* **Access:** `IsAuthenticated`
* **Query Parameters:** `track_id` (Integer, optional - returns progress for a specific track to resume audio playback)
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": [
          {
              "id": 1,
              "track": {
                  "id": 5,
                  "title": "Vayeira - Aliya 3",
                  "duration_seconds": 465,
                  "is_locked": false
              },
              "last_position_seconds": 192, // 3:12
              "completed": false,
              "updated_at": "2026-07-09T14:44:14Z"
          }
      ],
      "meta": {}
  }
  ```

### Update Listening Position (Save Progress)
* **Route:** `POST /api/v1/content/listening-history/`
* **Access:** `IsAuthenticated`
* **Request Body:**
  ```json
  {
      "track_id": 5,
      "last_position_seconds": 192,
      "completed": false
  }
  ```
* **Success Response (`200 OK` / `201 Created`):** Updates or creates a progress record.

---

## 4. Subscriptions & Payments (`/api/v1/payments/`)

### List User Subscriptions (Admin View)
* **Route:** `GET /api/v1/payments/admin/`
* **Access:** `IsAdminUser` (Admin Bearer Token required)
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": [
          {
              "id": 1,
              "user": 2,
              "user_email": "user@example.com",
              "plan_name": "Monthly Pro",
              "plan_price": "5.99",
              "status": "active",
              "current_period_end": "2026-08-08T00:00:00Z",
              "created_at": "2026-07-08T14:44:14Z"
          }
      ],
      "meta": {}
  }
  ```

### Sync Status (Mobile App Integration)
* **Route:** `POST /api/v1/payments/sync_status/`
* **Access:** `IsAuthenticated` (User Bearer Token required)
* **Request Body:**
  ```json
  {
      "rc_original_app_user_id": "RC_USER_ID_XYZ",
      "is_pro": true,
      "plan_name": "Monthly Pro", // Optional, defaults to "Monthly Pro"
      "price": 5.00 // Optional, defaults to 5.00
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": {
          "is_pro": true,
          "rc_original_app_user_id": "RC_USER_ID_XYZ"
      },
      "meta": {}
  }
  ```

### Create Stripe Checkout Session (Web Paywall)
* **Route:** `POST /api/v1/payments/create-checkout-session/`
* **Access:** `IsAuthenticated`
* **Request Body:**
  ```json
  {
      "plan_id": 1
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": {
          "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_..."
      },
      "meta": {}
  }
  ```

### Create Stripe Payment Intent (Native App Checkout SDK)
* **Route:** `POST /api/v1/payments/create-payment-intent/`
* **Access:** `IsAuthenticated`
* **Request Body:**
  ```json
  {
      "plan_id": 1
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": {
          "payment_intent": "pi_123456_secret_7890",
          "ephemeral_key": "ek_test_1234567890",
          "customer": "cus_1234567890",
          "publishable_key": "pk_test_..."
      },
      "meta": {}
  }
  ```

### Stripe Webhook Listener
* **Route:** `POST /api/v1/payments/stripe-webhook/`
* **Access:** `AllowAny` (Stripe signature verification optional but supported)
* **Success Response (`200 OK`):** Reconciles Stripe customer billing events (`checkout.session.completed`, `invoice.payment_succeeded`, `customer.subscription.deleted`) and locks/unlocks pro content access.

### RevenueCat Webhook Listener
* **Route:** `POST /api/v1/payments/webhook/`
* **Access:** `AllowAny` (RevenueCat Webhook Secret)
* **Request Body:**
  ```json
  {
      "event": {
          "type": "INITIAL_PURCHASE",
          "app_user_id": "RC_USER_ID_XYZ"
      }
  }
  ```
* **Success Response (`200 OK`):** Updates user `is_pro` status in the DB and returns standard HTTP `200 OK`.

---

## 5. Parshas & Reading Schedules (`/api/v1/parshas/`)

### List Parshas (Searchable)
* **Route:** `GET /api/v1/parshas/list/`
* **Access:** `IsAuthenticated`
* **Query Parameters:** `search` (Search by Parsha name, sefer, or Hebrew name)
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": [
          {
              "id": 1,
              "name": "Bereishit",
              "name_hebrew": "בְּרֵאשִׁית",
              "sefer": "Bereishit",
              "chapter_verse": "1:1-6:8",
              "haftorah_info": "Yeshayahu 42:5-43:10",
              "loaded_tracks_count": 7,
              "total_duration_seconds": 2520, // 42 min
              "is_loaded": true
          }
      ],
      "meta": {}
  }
  ```

### Get Monthly Shabbat Calendar
* **Route:** `GET /api/v1/parshas/calendar/`
* **Access:** `IsAuthenticated`
* **Query Parameters:** `month` (Integer 1-12, required), `year` (Integer YYYY, required)
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": [
          {
              "id": 4,
              "date": "2026-05-23",
              "hebrew_date": "6 Sivan 5786",
              "parsha": {
                  "id": 4,
                  "name": "Bechukotai",
                  "name_hebrew": "בְּחֻקֹּתַי",
                  "sefer": "Vayikra",
                  "chapter_verse": "26:3 - 27:34",
                  "haftorah_info": "Yirmiyahu 16:19 - 17:14"
              }
          }
      ],
      "meta": {}
  }
  ```

### Get Next Upcoming Shabbat & Countdown
* **Route:** `GET /api/v1/parshas/calendar/next/`
* **Access:** `IsAuthenticated`
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": {
          "id": 4,
          "date": "2026-05-23",
          "hebrew_date": "6 Sivan 5786",
          "parsha": {
              "id": 4,
              "name": "Bechukotai",
              "name_hebrew": "בְּחֻקֹּתַי",
              "sefer": "Vayikra",
              "chapter_verse": "26:3 - 27:34",
              "haftorah_info": "Yirmiyahu 16:19 - 17:14"
          },
          "weeks_until_bar_mitzvah": 47
      },
      "meta": {}
  }
  ```

---

## 6. Progress Dashboard & History (`/api/v1/progress/`)

### Get Child's Dashboard
* **Route:** `GET /api/v1/progress/dashboard/`
* **Access:** `IsAuthenticated` (Parent must be linked to Child)
* **Query Parameters:** `child_id` (Integer, required)
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": {
          "overall_progress": {
              "weeks_until_bar_mitzvah": 47,
              "total_aliyos_completed": 22,
              "total_haftorah_completed": 1,
              "haftorah_progress_percentage": 35,
              "total_aliyos_required": 63
          },
          "current_week": {
              "parsha": "Vayeira",
              "date": "2026-07-11",
              "grid": [
                  { "segment_type": "aliya_1", "label": "Aliya 1", "status": "completed" },
                  { "segment_type": "aliya_2", "label": "Aliya 2", "status": "completed" },
                  { "segment_type": "aliya_3", "label": "Aliya 3", "status": "completed" },
                  { "segment_type": "aliya_4", "label": "Aliya 4", "status": "completed" },
                  { "segment_type": "aliya_5", "label": "Aliya 5", "status": "in_progress" },
                  { "segment_type": "aliya_6", "label": "Aliya 6", "status": "not_started" },
                  { "segment_type": "aliya_7", "label": "Aliya 7", "status": "not_started" },
                  { "segment_type": "maftir", "label": "Maftir", "status": "not_started" },
                  { "segment_type": "haftorah", "label": "Haftorah", "status": "not_started" }
              ]
          }
      },
      "meta": {}
  }
  ```

### Get Child's Progress History
* **Route:** `GET /api/v1/progress/history/`
* **Access:** `IsAuthenticated` (Parent must be linked to Child)
* **Query Parameters:** `child_id` (Integer, required)
* **Success Response (`200 OK`):**
  ```json
  {
      "success": true,
      "status_code": 200,
      "message": "Success",
      "data": [
          {
              "parsha_name": "Vayeira",
              "date": "2026-07-11",
              "completed_segments": 4,
              "total_segments": 9,
              "grid": [
                  { "segment_type": "aliya_1", "label": "Aliya 1", "status": "completed" },
                  { "segment_type": "aliya_2", "label": "Aliya 2", "status": "completed" },
                  { "segment_type": "aliya_3", "label": "Aliya 3", "status": "completed" },
                  { "segment_type": "aliya_4", "label": "Aliya 4", "status": "completed" },
                  { "segment_type": "aliya_5", "label": "Aliya 5", "status": "in_progress" },
                  { "segment_type": "aliya_6", "label": "Aliya 6", "status": "not_started" },
                  { "segment_type": "aliya_7", "label": "Aliya 7", "status": "not_started" },
                  { "segment_type": "maftir", "label": "Maftir", "status": "not_started" },
                  { "segment_type": "haftorah", "label": "Haftorah", "status": "not_started" }
              ]
          }
      ],
      "meta": {}
  }
  ```

### Update Student Progress (Used by Son's App)
* **Route:** `POST /api/v1/progress/update_status/`
* **Access:** `IsAuthenticated` (Student token)
* **Request Body:**
  ```json
  {
      "parsha_id": 1,
      "segment_type": "aliya_1",
      "status": "completed" // or "in_progress", "not_started"
  }
  ```
* **Success Response (`200 OK`):** Returns the updated progress item details.

