'I believe this is run with:'

'python manage.py generate_training_sessions --days 30'

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from scheduling.models import Shift
from reservations.models import TrainingSession
from machines.models import Training


class Command(BaseCommand):
    help = "Generate TrainingSession records from training shifts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days ahead to generate sessions for",
        )

    def handle(self, *args, **options):
        days = options["days"]
        today = timezone.now().date()
        end_date = today + timedelta(days=days)

        self.stdout.write(
            f"Generating training sessions from {today} to {end_date}..."
        )

        shifts = (
            Shift.objects.filter(
                shift_type="training",
                date__gte=today,
                date__lte=end_date,
                status="scheduled",
            )
            .select_related("user", "location")
        )

        created = 0
        skipped = 0

        for s in shifts:
            training = Training.objects.filter(
                category=s.team_category,
                level=getattr(s, "training_level", 1),
            ).first()

            if not training:
                self.stdout.write(
                    f"  ! No Training match for shift {s.id} "
                    f"({s.team_category}, level={getattr(s, 'training_level', 1)})"
                )
                skipped += 1
                continue

            session, made = TrainingSession.objects.get_or_create(
                shift=s,
                training=training,
                defaults={
                    "trainer": s.user,
                    "date": s.date,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "location": s.location,
                    "max_participants": 8,
                    "status": "scheduled",
                },
            )
            if made:
                created += 1
                self.stdout.write(f"  ✓ Session {session.id} from shift {s.id}")
            else:
                skipped += 1

        self.stdout.write(
            f"Done. Created {created} sessions, skipped {skipped} existing."
        )
