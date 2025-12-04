#!/bin/bash
# Quick Demo Setup Script
# Run from the Inouma folder: bash testing/setup_demo.sh

echo "=========================================="
echo "DEMO SETUP - Generating Test Data"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: manage.py not found. Please run this from the Inouma folder."
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "../env_site" ]; then
    source ../env_site/bin/activate
    echo "✓ Virtual environment activated"
fi

echo ""
echo "Step 0/8: Creating location..."
python manage.py shell < testing/generate_demo_location.py

echo ""
echo "Step 1/8: Creating machines..."
python manage.py shell < testing/generate_test_machines.py

echo ""
echo "Step 2/8: Creating 50 users for schedule generation..."
python manage.py shell < testing/generate_test_users.py

echo ""
echo "Step 3/9: Creating demo users (test1 and test2)..."
python manage.py shell < testing/generate_demo_users.py

echo ""
echo "Step 4/9: Creating schedule requirements..."
python manage.py shell < testing/generate_test_requirements.py

echo ""
echo "Step 5/9: Creating unavailabilities..."
python manage.py shell < testing/generate_test_unavailabilities.py

echo ""
echo "Step 6/9: Creating trainings..."
python manage.py shell < testing/generate_trainings.py

echo ""
echo "Step 7/9: Creating certifications..."
python manage.py shell < testing/generate_test_certifications.py

echo ""
echo "Step 8/9: Creating training sessions..."
python manage.py shell < testing/generate_demo_training_sessions.py

echo ""
echo "Step 9/9: Linking machines to trainings..."
python manage.py shell < testing/link_machines_to_trainings.py

echo ""
echo "=========================================="
echo "✅ DEMO SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Total users created: 52"
echo "  - 50 users for schedule generation (test3-test52@gmail.com)"
echo "  - 2 demo users:"
echo "    • test1@gmail.com / testpass123 (no certifications)"
echo "    • test2@gmail.com / testpass123 (Level 1 certifications)"
echo ""
echo "Optional: Make demo users trainers and update for shifts:"
echo "  python manage.py shell < testing/make_test_users_trainers.py"
echo "  python manage.py shell < testing/update_test_users_for_shifts.py"
echo ""
echo "Start server with: python manage.py runserver"
echo "Login at: http://127.0.0.1:8000/auth/login/email/"
echo ""

