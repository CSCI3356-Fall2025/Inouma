"""
Reservations App URLs
"""

from django.urls import path
from . import views

app_name = "reservations"

urlpatterns = [
    # =========================================================================
    # PAGE VIEWS (Templates)
    # =========================================================================

    # Student pages
    path("my-reservations/", views.my_reservations, name="my_reservations"),
    path("training/", views.training_browser, name="training_browser"),
    path("my-progress/", views.my_training_progress, name="my_training_progress"),

    # Staff pages
    path("staff/", views.staff_reservations_hub, name="staff_reservations_hub"),
    path(
        "staff/reservations/",
        views.staff_reservations_dashboard,
        name="staff_reservations_dashboard",
    ),
    path(
        "staff/trainings/",
        views.staff_training_dashboard,
        name="staff_training_dashboard",
    ),
    path(
        "staff/maintenance/",
        views.maintenance_management,
        name="maintenance_management",
    ),
    path(
        "staff/blackouts/",
        views.blackout_management,
        name="blackout_management",
    ),

    # Team member pages
    path(
        "team/my-sessions/",
        views.team_my_training_sessions,
        name="team_my_training_sessions",
    ),

    # =========================================================================
    # MACHINE RESERVATION APIs
    # =========================================================================

    # Check availability for a machine
    path(
        "api/machines/<int:machine_id>/availability/",
        views.api_check_availability,
        name="api_check_availability",
    ),

    # Create reservation
    path(
        "api/machines/<int:machine_id>/reserve/",
        views.api_create_reservation,
        name="api_create_reservation",
    ),

    # Cancel reservation
    path(
        "api/reservations/<int:reservation_id>/cancel/",
        views.api_cancel_reservation,
        name="api_cancel_reservation",
    ),

    # My reservations (student)
    path(
        "api/my-reservations/",
        views.api_my_reservations,
        name="api_my_reservations",
    ),

    # =========================================================================
    # TRAINING BOOKING APIs
    # =========================================================================

    # Browse available training sessions
    path(
        "api/trainings/available/",
        views.api_available_trainings,
        name="api_available_trainings",
    ),

    # Book a training session
    path(
        "api/trainings/<int:session_id>/book/",
        views.api_book_training,
        name="api_book_training",
    ),

    # Cancel training booking
    path(
        "api/training-bookings/<int:booking_id>/cancel/",
        views.api_cancel_training_booking,
        name="api_cancel_training_booking",
    ),

    # Confirm waitlist notification
    path(
        "api/training-bookings/<int:booking_id>/confirm/",
        views.api_confirm_waitlist_booking,
        name="api_confirm_waitlist_booking",
    ),

    # My training bookings (student)
    path(
        "api/my-training-bookings/",
        views.api_my_training_bookings,
        name="api_my_training_bookings",
    ),

    # =========================================================================
    # TEAM MEMBER APIs
    # =========================================================================

    # My training sessions (as trainer)
    path(
        "api/my-training-sessions/",
        views.api_my_training_sessions,
        name="api_my_training_sessions",
    ),

    # Mark training complete
    path(
        "api/training-bookings/<int:booking_id>/complete/",
        views.api_mark_training_complete,
        name="api_mark_training_complete",
    ),

    # Mark training no-show
    path(
        "api/training-bookings/<int:booking_id>/no-show/",
        views.api_mark_training_no_show,
        name="api_mark_training_no_show",
    ),

    # =========================================================================
    # STAFF/ADMIN APIs
    # =========================================================================

    # All reservations (staff dashboard)
    path(
        "api/admin/reservations/",
        views.api_all_reservations,
        name="api_all_reservations",
    ),

    # All training sessions (staff dashboard)
    path(
        "api/admin/training-sessions/",
        views.api_all_training_sessions,
        name="api_all_training_sessions",
    ),

    # =========================================================================
    # MAINTENANCE APIs
    # =========================================================================

    # Report maintenance issue
    path(
        "api/machines/<int:machine_id>/report-maintenance/",
        views.api_report_maintenance,
        name="api_report_maintenance",
    ),

    # Maintenance queue (staff)
    path(
        "api/admin/maintenance/",
        views.api_maintenance_queue,
        name="api_maintenance_queue",
    ),

    # Take machine offline
    path(
        "api/admin/maintenance/<int:maintenance_id>/offline/",
        views.api_take_machine_offline,
        name="api_take_machine_offline",
    ),

    # Resolve maintenance
    path(
        "api/admin/maintenance/<int:maintenance_id>/resolve/",
        views.api_resolve_maintenance,
        name="api_resolve_maintenance",
    ),

    # =========================================================================
    # BLACKOUT PERIOD APIs
    # =========================================================================

    # List blackout periods
    path(
        "api/admin/blackouts/",
        views.api_blackout_periods,
        name="api_blackout_periods",
    ),

    # Create blackout period
    path(
        "api/admin/blackouts/create/",
        views.api_create_blackout,
        name="api_create_blackout",
    ),

    # Delete blackout period
    path(
        "api/admin/blackouts/<int:blackout_id>/delete/",
        views.api_delete_blackout,
        name="api_delete_blackout",
    ),
]
