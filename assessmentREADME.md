# Event Program Backend (Django)

## Project Overview

This project is a small, API-first Django backend for creating, managing, and sharing event programs (schedules/agendas).

Organizers can build programs incrementally, validate when a program is ready to be shared, and make programs publicly accessible while retaining the ability to edit them after sharing.

Programs can only be shared once they meet readiness criteria, including having at least one item and no conflicting item times.

**Quick Summary:**  
API-first Django backend for managing event programs.  
- Organizers can create programs, add/edit items, validate readiness, and share publicly.  
- Programs are shareable only when “ready” (at least one item, valid times, no conflicts).  
- Public users can view shared programs in read-only mode; authenticated users manage their own programs.  
- Includes a dashboard endpoint summarizing program readiness and item counts.


## System Architecture

### Data Model Overview

**Program**
- `title` (CharField, required) - Name of the event program
- `description` (TextField, optional) - Detailed description
- `date` (DateField, required) - Date of the event
- `capacity` (PositiveIntegerField, optional) - Expected or maximum attendee count
- `owner` (ForeignKey to User, required, indexed) - Creator of the program
- `share_token` (CharField, nullable, unique, indexed) - Non-guessable identifier for public sharing
- `shared_at` (DateTimeField, nullable) - Timestamp when program was first shared
- `created_at` / `updated_at` (DateTimeField, auto) - Audit timestamps

**ProgramItem**
- `program` (ForeignKey to Program, required, cascading delete) - Parent program
- `title` (CharField, required) - Name of the program item/session
- `description` (TextField, optional) - Details about the item
- `start_time` (DateTimeField, required) - When the item begins
- `end_time` (DateTimeField, required) - When the item ends
- `position` (PositiveIntegerField, required) - Order/sequence within the program
- `created_at` / `updated_at` (DateTimeField, auto) - Audit timestamps

**Relationships**
- One Program → Many ProgramItems (one-to-many, cascading delete)
- One User → Many Programs (one-to-many)

**Key Design Notes**
- Program readiness is **derived** (computed on-demand via a property method), not stored
- Share tokens are generated using `secrets.token_urlsafe()` only when sharing
- Database indexes on `owner`, `share_token`, and `program` foreign key for query performance
- `position` field ensures explicit ordering of items within a program

---

### API Endpoints

**Program Management** (Authenticated Users Only)
- `POST /api/programs/` - Create a new program
- `GET /api/programs/` - List all programs owned by the authenticated user
- `GET /api/programs/{id}/` - Retrieve detailed view of a specific program (owner/admin only)
- `PUT /api/programs/{id}/` - Update an existing program (owner/admin only)
- `PATCH /api/programs/{id}/` - Partially update a program (owner/admin only)
- `DELETE /api/programs/{id}/` - Delete a program and all its items (owner/admin only)
- `POST /api/programs/{id}/share/` - Share a program publicly (only if ready, generates share_token)

**Program Item Management** (Authenticated Users Only)
- `POST /api/programs/{program_id}/items/` - Add a new item to a program
- `PUT /api/programs/{program_id}/items/{item_id}/` - Update an existing item
- `PATCH /api/programs/{program_id}/items/{item_id}/` - Partially update an item
- `DELETE /api/programs/{program_id}/items/{item_id}/` - Remove an item from a program

**Public Access** (Unauthenticated Users)
- `GET /api/programs/shared/{share_token}/` - View a shared program in read-only mode

**Dashboard** (Authenticated Users Only)
- `GET /api/dashboard/` - Overview of all user's programs including:
  - Program title, date, and description
  - Item count per program
  - Readiness status (boolean)
  - Share status (whether shared, share URL if applicable)
  - Last updated timestamp

---

### Authentication & Authorization

**Authentication Implementation**
- Uses Django's built-in `User` model and authentication framework
- For development: Basic Authentication (username/password in request headers) when `DEBUG=True`
- For testing: Test users created in test cases, authenticated via DRF's `force_authenticate()`
- For production: Would use token-based authentication (JWT, OAuth) instead of Basic Auth
- Middleware ensures `request.user` is available and identifies the authenticated user
- This project **does not** implement login endpoints or credential management (assumes upstream auth)

**Authorization Model**
- **Program Owners**: Users who created a program can perform all CRUD operations on it and its items
- **Admins**: Users with `is_staff=True` or `is_superuser=True` can access and modify any program
- **Public (Unauthenticated)**: Can only view shared programs in read-only mode via share token

**Permission Implementation**
- Custom DRF permission classes:
  - `IsOwnerOrAdmin` - Allows access only to program owners or staff/superusers
  - `IsAuthenticatedOrReadOnlyShared` - Allows authenticated users full access, public users read-only access to shared programs
- View-level checks enforce that only ready programs can be shared
- Serializer validation ensures business rules are respected

---

## Core Features & Business Logic

### Program Readiness Criteria

A program is considered **ready to share** when **all** of the following conditions are met:

1. **Has at least one program item** - Empty programs cannot be shared
2. **All items have valid time ranges** - Each item's `end_time` must be after its `start_time`
3. **No time conflicts between items** - No two items can have overlapping time ranges
4. **All required program fields are filled** - Title and date must be present

**Conflict Detection Rules**
- Two items are considered conflicting if their time ranges overlap, defined as:
  start_a < end_b AND end_a > start_b.
  Adjacent items (where one ends exactly when another starts) are allowed and do not conflict.
- Items with identical `start_time` values are treated as conflicting
- Conflict detection happens:
  - When adding or updating program items (serializer validation)
  - When attempting to share a program (share action validation)
- Items are compared pairwise within the same program



**Readiness Implementation**
- Readiness is computed dynamically via a `@property` method on the Program model
- Result can be cached per-request to avoid redundant calculations
- No database field stores readiness state (ensures consistency)

---

### Program Sharing

**How Sharing Works**
- Programs can only be shared via `POST /api/programs/{id}/share/`
- Sharing is only permitted if the program passes all readiness checks
- On first share, a unique `share_token` is generated using `secrets.token_urlsafe(32)`
- The `shared_at` timestamp is recorded
- The share token never changes after initial generation (permanent link)


**Post-Share Behavior**
- Shared programs remain editable by their owners
- Changes to shared programs are immediately reflected in the public view
- If a shared program becomes "unready" (e.g., all items deleted), it remains shared but may show warnings or restricted content
- There is no "unshare" action—sharing is permanent once initiated

**Public Access**
- Public users access shared programs via `/api/programs/shared/{share_token}/`
- The endpoint returns full program details and all items in read-only format
- Invalid or non-existent tokens return `404 Not Found`
- Authentication is not required for this endpoint

---

### Program Item Validation

**Time Validation**
- `end_time` must be strictly after `start_time` (validated at serializer level)
- Both fields are required (no "start time only" items)
- Times are assumed to be in a consistent timezone (no cross-timezone handling)

**Conflict Detection**
- Implemented in the serializer's `validate()` method
- Fetches all sibling items (other items in the same program)
- Checks for overlapping ranges using interval comparison logic
- Raises `ValidationError` if conflicts are detected
- Works for both create and update operations (excludes self when updating)

**Item Ordering**
- Each item has a `position` field (positive integer)
- Position can be set manually by the client or auto-assigned (highest + 1)
- Items are returned ordered by `position` in API responses
- No automatic reordering occurs when items are deleted

**Required vs Optional Fields**
- Required: `title`, `start_time`, `end_time`, `position`
- Optional: `description`

---

## How to Run Locally

### Requirements
- Python 3.10+
- pip

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd <repository-directory>

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

#After running migrations, create a test user:
python manage.py createsuperuser

#Use these credentials to authenticate via the browsable API, Postman, or curl.

# Start the development server
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/`

### Running Tests

```bash
# Run the full test suite
python manage.py test

# Run tests with coverage report
coverage run --source='.' manage.py test
coverage report
```

---

## Testing Strategy

### Test Suite Overview

The test suite is organized into **five main test files**, containing classes focusing on a core aspects of the application. All tests use Django's `TestCase` and DRF's `APIClient` for API testing.

| Test Class                           | Purpose                                            | Key Scenarios Covered                                                                                                                                   |  Location               |
| ------------------------------------ | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| **ProgramCreationAndOwnershipTest**  | Validates program creation and ownership rules     | - Authenticated users can create programs <br> - Program creator is automatically owner <br> - Users cannot access or modify programs owned by others   | `test_programs.py`      |
| **ProgramItemTimeValidationTest**    | Enforces correct start/end times for program items | - End time before start time is rejected <br> - Updating to invalid time ranges fails                                                                   | `test_program_item.py`  |
| **ProgramItemConflictDetectionTest** | Prevents overlapping program items                 | - Creating items that overlap existing items fails <br> - Updating items to create conflicts is rejected <br> - Duplicate start times are rejected      | `test_program_item.py`  |
| **ProgramReadinessCalculationTest**  | Validates program readiness logic                  | - Programs with no items are not ready <br> - Programs with valid, non-overlapping items are ready <br> - Programs with conflicting items are not ready | `test_program_item.py`  |
| **ProgramSharingRulesTest**          | Tests program sharing logic                        | - Unready programs cannot be shared <br> - Sharing a ready program generates a token <br> - Re-sharing an already shared program is idempotent          | `test_sharing.py`       |
| **PublicAccessToSharedProgramsTest** | Validates safe public access                       | - Shared programs accessible without authentication <br> - Invalid share token returns 404 <br> - Public users cannot modify shared programs            | `test_public_access.py` |
| **DashboardOverviewEndpointTest**    | Ensures dashboard endpoint correctness             | - Returns only the authenticated user’s programs <br> - Includes readiness, share status, and item count for each program                               | `test_dashboard.py`     |

### Test Implementation Details

* **API testing** is done with `APIClient` and `force_authenticate()` for simulating authenticated requests.
* Tests use **isolated setup**; each test creates its own users, programs, and items.
* Tests are designed to be **modular**, making it easier to maintain and expand.
* **Edge cases** include:

  * Attempting to share unready or conflicting programs
  * Creating overlapping or duplicate items
  * Accessing programs with invalid share tokens

### How to Run the Tests

```bash
# Run all tests
python manage.py test

# Run a specific test class or method
python manage.py test programs.tests.ProgramItemTimeValidationTest
python manage.py test programs.tests.ProgramItemTimeValidationTest.test_creating_item_with_end_before_start_fails
```

* Tests run on a **temporary in-memory SQLite database** by default for speed.
* Results show which tests passed, failed, or encountered errors.

---


## Key Design Decisions

### Program Readiness is Derived
A program's readiness is dynamically computed based on its current state (presence of items, valid item times, no conflicts). There is no manually stored "ready" flag in the database. This ensures:
- Shared programs are always validated at share-time
- Changes to programs immediately affect readiness without manual updates
- No risk of stale or inconsistent readiness state
- Validation logic lives in one place (property method)

**Trade-off**: Readiness computation happens on every access. For programs with many items, this could be optimized with caching, but for the scope of this project, simplicity is prioritized.

---

### Sharing is Explicit and Permanent
Programs can only be shared through a dedicated backend action (`POST /api/programs/{id}/share/`) which generates a non-guessable share identifier (`share_token`). Key aspects:
- Sharing is only allowed if the program passes all readiness checks
- The share token is generated once and never changes (stable public URLs)
- Changes to shared programs are immediately reflected in the public view
- There is no "unshare" mechanism (sharing is permanent)

**Rationale**: Permanent share links avoid broken URLs and provide a consistent public-facing identifier. This aligns with typical event program use cases where organizers want stable links they can distribute.

**Trade-off**: If a program needs to be "unshared," the only option is deletion. This could be extended with a soft-delete or "unpublish" feature in the future.

---

### Public vs Authenticated Access
- **Public users (unauthenticated)**: Can only view shared programs via their share token in read-only mode. They cannot create, edit, delete, or share programs.
- **Authenticated organizers**: Can manage their own programs, access unpublished programs if they are the owner or an admin, and perform all CRUD actions.

This enforces clear authorization boundaries without implementing authentication logic (which is assumed to exist upstream).

**Rationale**: Simplifies the scope by focusing on authorization and business logic rather than authentication mechanisms.

---

### Validation Placement Strategy
- **Field-level validation**: Lives in models (e.g., `PositiveIntegerField`, `blank=False`)
- **Cross-field validation**: Lives in serializers (e.g., `end_time > start_time`)
- **Cross-record validation**: Lives in serializers (e.g., item conflict detection)
- **Access control and authorization**: Lives in views and permission classes

This separation ensures:
- Models remain reusable and database-focused
- Serializers handle API-specific validation logic
- Views handle request-level concerns
- Code is testable at each layer independently

---

### Program and Program Item Structure
- Programs are owned by a single user and contain ordered items
- Program items are validated relative to sibling items to prevent overlapping schedules
- Items have explicit `position` fields for ordering, giving clients control over sequence
- Cascading deletes ensure orphaned items don't remain when programs are deleted

This structure ensures:
- Structural integrity (no orphaned items)
- Clear ownership model (one owner per program)
- Flexibility for clients to control item ordering

---

### Dashboard Endpoint
A dedicated `/api/dashboard/` endpoint provides an overview of all programs for the authenticated user. It returns:
- List of programs with key metadata (title, date, item count)
- Readiness status for each program
- Share status (whether shared, share URL if applicable)
- Last updated timestamp

**Rationale**: The dashboard serves as a high-level summary for organizers to quickly assess their programs without fetching full details for each. This aligns with the task requirement for "an endpoint that returns a program overview suitable for a dashboard view."

---

### Minimal Scope for Simplicity
To keep the task intentionally small and focused, the following features are **intentionally omitted**:
- Program versioning or change history
- Fine-grained permissions (co-organizers, editors)
- Attendee tracking or ticketing management
- Edit limits or concurrency handling
- Timezone normalization

Trade-offs are documented in the next section and can be extended in the future if needed.

---

## Assumptions

- **Authentication System Exists Upstream**: An authentication system already exists and identifies users before requests reach the application (e.g., via middleware or gateway). This project focuses on authorization and business logic rather than login, registration, or credential management. Django's built-in `User` model and authentication framework are used, but no login endpoints are implemented.

- **Single Program Owner**: Each program has a single owner, represented by the authenticated user who created it. There are no co-owners or collaborators (this could be extended with role-based permissions in the future).

- **Public Access is Read-Only**: Public (unauthenticated) users can view shared programs via share tokens but cannot create, edit, delete, or share programs. All modification actions require authentication.

- **Authenticated Users Have Full Access to Their Own Programs**: Authenticated organizers and admins can perform all management actions (CRUD, sharing) on their own programs and can access unpublished programs if they are the owner or an admin.

- **Programs Can Be Edited After Sharing**: Programs can be edited at any time, including after being shared publicly. Changes are immediately reflected in the public view. There are no approval workflows or staged edits.

- **Single Timezone Assumption**: All program item times are assumed to be in a single consistent timezone. Cross-timezone scheduling, timezone conversion, and daylight saving time handling are not implemented.

- **Last-Write-Wins for Concurrent Edits**: No optimistic locking or concurrency control is implemented. If two users edit the same program simultaneously, the last write will overwrite the previous one. This is acceptable for the scope of this project but could lead to race conditions in high-concurrency scenarios.

These assumptions intentionally limit the scope of the system and allow the implementation to focus on program structure, validation, and sharing behavior.

---

## Trade-offs & Limitations

### No Program Versioning or History
Changes to programs overwrite previous states. Past versions cannot be restored, and there is no audit trail of what changed and when.

**Rationale**: Versioning adds significant complexity (storage, retrieval, UI for browsing versions). For a small-scope project, the cost outweighs the benefit. This can be added later with a change log or version table.

---

### No Fine-Grained Permissions
Only a simple owner/admin model is implemented. More complex roles (e.g., co-organizers, editors with limited permissions, viewers) are intentionally omitted.

**Rationale**: Role-based access control (RBAC) requires additional models, logic, and UI. The current design focuses on the common case: one organizer per program. Extending to multiple roles is straightforward but adds scope.

---

### No Attendee or Ticketing Management
While programs have a `capacity` field (expected or max attendee count), attendee tracking, registration, ticketing, and capacity enforcement are not included.

**Rationale**: These features are orthogonal to the core task of managing program structure and sharing. They would require additional models (Attendee, Ticket) and business logic (registration flow, payment). Keeping this out of scope maintains focus on the core requirements.

---

### No Edit Limits or Concurrency Handling
Shared programs can be edited freely without restrictions. Last-write-wins applies, avoiding additional complexity but potentially leading to race conditions in highly concurrent scenarios.

**Rationale**: Optimistic locking (version counters) or pessimistic locking (row-level locks) add complexity. For small-scale use, the risk is minimal. If needed, this can be addressed with timestamp-based conflict detection or ETags in the future.

---

### No Timezone Normalization
Program item times are assumed to be in a single consistent timezone. Cross-timezone scheduling, timezone conversion, and UTC normalization are not handled.

**Rationale**: Timezone handling is complex and error-prone (DST, regional differences). For a small-scope project focused on structure and validation, assuming a single timezone simplifies implementation. This can be extended by storing times in UTC and adding a timezone field to programs.

---

### No Soft Delete or Unshare Mechanism
Once a program is shared, the share token is permanent. There is no way to "unshare" a program or revoke access without deleting it entirely.

**Rationale**: Soft deletes and unpublish features add state management complexity. For simplicity, sharing is treated as a one-way action. This can be extended with a `is_published` flag or soft-delete mechanism if needed.

---

These trade-offs were consciously made to keep the implementation clear, maintainable, and focused on core functionality. They represent engineering judgment about what is essential for the task scope versus what can be deferred or extended.

---

## Future Improvements

### Program Versioning and Change History
Track previous states of programs to allow rollback, audit changes, and view historical versions. This would involve:
- A `ProgramVersion` model with snapshots of program state
- Endpoints to retrieve version history and restore previous versions
- UI to browse and compare versions

---

### Role-Based Permissions
Support multiple roles per program (e.g., co-organizers, editors, viewers) for finer-grained access control. This would involve:
- A `ProgramRole` model linking users to programs with role types
- Permission logic that checks roles in addition to ownership
- Invitation/collaboration workflows

---

### Attendee and Ticketing Management
Extend programs to handle attendee registration, ticketing, and capacity tracking. This would involve:
- `Attendee` and `Ticket` models
- Registration and check-in endpoints
- Capacity enforcement logic
- Payment integration (if needed)

---

### Dashboard Enhancements
Improve the dashboard endpoint with:
- Filtering (by date range, readiness status, shared status)
- Sorting (by date, last updated, item count)
- Pagination for users with many programs
- Visual summaries (upcoming vs past programs, statistics)

---

### Caching for Public Programs
Improve performance for high-traffic shared programs by caching read-only views. This would involve:
- Redis or Memcached for caching shared program data
- Cache invalidation on program updates
- HTTP caching headers (ETags, Cache-Control) for browser caching

---

### Timezone Support
Add timezone awareness to program item times:
- Store times in UTC in the database
- Add a `timezone` field to programs
- Convert times to the appropriate timezone in API responses
- Handle daylight saving time transitions

---

### Concurrency Control
Implement optimistic locking to prevent lost updates in concurrent editing scenarios:
- Add a `version` field to programs and items
- Check version on updates and reject stale updates
- Return conflict errors with current state for client-side resolution

---

### Notification System
Notify attendees or collaborators of program changes:
- Email or push notifications when a shared program is updated
- Subscription mechanism for public users to receive updates
- Webhook support for third-party integrations

---
These improvements represent natural extensions of the current design and could be prioritized based on user feedback and product requirements.