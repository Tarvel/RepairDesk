# RepairDesk

RepairDesk is a robust, web-based repair management system designed for device repair shops. It streamlines the entire repair lifecycle—from customer intake and initial diagnosis to parts management, quality control, and final collection.

Built using Django, Tailwind CSS, Alpine.js, and HTMX, RepairDesk provides a fast, modern, and reactive user interface without the complexity of a heavy JavaScript frontend framework.

## Features

- **Ticket Management Pipeline**: Track repairs through a defined lifecycle (Intake -> Diagnosing -> Awaiting Approval -> Repairing -> Pending QC -> Ready for Pickup -> Completed) using a robust finite-state machine (`django-fsm`).
- **Role-Based Access Control (RBAC)**: Specific actions and views are gated by user roles.
  - **Frontdesk**: Manages customers, intake, quotes, and collection.
  - **Technician**: Handles diagnosis, repair work, and requests parts/approval.
  - **Quality Analyst (QA)**: Reviews completed repairs and passes or fails them.
- **Real-Time Activity Timeline**: View all comments, system state changes, and updates in a scrolling timeline powered by HTMX polling.
- **In-App Notifications**: Real-time bell notifications alert staff to pending approvals, comments, and quality check requirements.
- **Customer & Device Management**: Track customer history and specific device details (brand, model, IMEI/Serial number, accessories received).
- **Inventory & Parts Management**: Track available stock, assign parts to tickets, and calculate total repair costs including labor.

## Tech Stack

- **Backend**: Python 3.13, [Django](https://www.djangoproject.com/) 5.0+
- **State Machine**: [django-fsm](https://github.com/viewflow/django-fsm)
- **Frontend / UI**:
  - HTML Templates
  - [Tailwind CSS](https://tailwindcss.com/) (via CDN for rapid development)
  - [Alpine.js](https://alpinejs.dev/) for lightweight client-side interactions (modals, dropdowns, tabs)
  - [HTMX](https://htmx.org/) for reactive async updates and polling
- **Authentication**: Built-in Django auth + custom Group-based roles and permissions.

## Setup & Installation

Follow these steps to run the project locally.

### Prerequisites
- Python 3.10 or higher
- `pip` and `venv` (or your preferred virtual environment tool)

### 1. Clone & Set Up Virtual Environment

```bash
# Navigate to your project folder
cd REPAIRDESK

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create a Superuser

You'll need an admin account to manage roles and start testing.

```bash
python manage.py createsuperuser
```

### 5. Start the Development Server

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`.

## Configuring Roles (Required)

To test the RBAC features properly, you must create Django Groups in the Admin panel (`/admin/`) exactly matching these names (case-sensitive):

1. `Frontdesk`
2. `Technician`
3. `Quality Analyst`

Create a few test users and assign them to these groups to see how the UI and ticket options change based on the logged-in user. Superusers bypass all role checks.

## Key Technical Decisions

- **Why HTMX & Alpine over React/Vue?** To keep the tech stack Python-focused and simple to maintain while still providing a modern "SPA-like" experience (real-time timeline polling, dynamic modals, async comment submission).
- **Why django-fsm?** Repair workflows heavily rely on strict state transitions (e.g., a ticket cannot jump from *Intake* straight to *Ready for Pickup* without passing *Diagnosis*, *Repair*, and *QC*). `django-fsm` enforces these rules at the model layer. *(Note: django-fsm is deprecated in favor of viewflow.fsm for future updates).*
- **In-App Notifications**: Uses HTMX polling (10-second interval) to hit a lightweight endpoint, retrieving a count and dropdown menu. This avoids the heavy infrastructure requirement of WebSockets/Django Channels.

## Future Roadmap

- Integration with messaging APIs (WhatsApp/SMS via Twilio) for automated customer updates.
- Export invoices and receipts as PDFs.
- Switch from HTMX polling to Django Channels/WebSockets if real-time scale requires it.
- Barcode generation and scanning for rapid device intake.
