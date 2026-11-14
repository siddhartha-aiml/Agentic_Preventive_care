"""Idempotent demo data seeder: providers (+ doctor logins), historical cases, schedules, demo patient."""

import random
from datetime import date, time

from sqlalchemy.orm import Session

from .agents.specialties import SPECIALTIES
from .models import Availability, Patient, Provider, ProviderCase, User
from .security import hash_password

DEMO_PATIENT_EMAIL = "patient@demo.com"
DEMO_PATIENT_PASSWORD = "demo1234"
DOCTOR_PASSWORD = "doctor123"

FIRST_F = ["Aisha", "Emily", "Sofia", "Priya", "Grace", "Olivia", "Maya", "Hannah", "Leila", "Chloe", "Nora", "Isabel", "Meera", "Rachel", "Yuki", "Zara"]
FIRST_M = ["James", "Arjun", "Daniel", "Omar", "Lucas", "Ethan", "Rahul", "Samuel", "Marcus", "Kenji", "David", "Carlos", "Noah", "Vikram", "Henry", "Adrian"]
LAST = ["Patel", "Johnson", "Nguyen", "Garcia", "Kim", "Okafor", "Sharma", "Williams", "Chen", "Rossi", "Haddad", "Martin", "Brooks", "Mehta", "Silva", "Reyes",
        "Anderson", "Kapoor", "Lopez", "Walker", "Tanaka", "Bennett", "Ali", "Foster", "Iyer", "Hughes", "Moreno", "Clarke", "Das", "Wright", "Evans", "Shah"]
LOCATIONS = ["Downtown Medical Center", "Greenfield Health Clinic", "Riverside Hospital", "Lakeview Family Practice",
             "Northside Specialty Center", "Maple Grove Clinic", "Harbor View Medical", "Sunrise Health Pavilion"]
LANGS = [["English"], ["English", "Spanish"], ["English", "Hindi"], ["English", "French"], ["English", "Arabic"], ["English", "Mandarin"]]
TITLES = {
    "General Physician": "MD, Family Medicine",
    "Cardiology": "MD, FACC — Cardiologist",
    "Neurology": "MD — Neurologist",
    "Dermatology": "MD, FAAD — Dermatologist",
    "Gastroenterology": "MD — Gastroenterologist",
    "Pulmonology": "MD — Pulmonologist",
    "Orthopedics": "MD — Orthopedic Surgeon",
    "ENT": "MD — Otolaryngologist",
    "Endocrinology": "MD — Endocrinologist",
    "Psychiatry": "MD — Psychiatrist",
    "Ophthalmology": "MD — Ophthalmologist",
    "Urology": "MD — Urologist",
    "Obstetrics & Gynecology": "MD, FACOG — OB/GYN",
}
PER_SPECIALTY = {"General Physician": 4, "Cardiology": 3, "Neurology": 3, "Orthopedics": 3, "Gastroenterology": 3, "Dermatology": 3, "Psychiatry": 3}


def seed(db: Session) -> None:
    """Base demo data (first start only), then the additive India voice-pilot data."""
    from .seed_india import seed_india

    if db.query(Provider).count() == 0:
        _seed_base(db)
    seed_india(db)


def _seed_base(db: Session) -> None:
    rng = random.Random(42)
    used_names: set[str] = set()
    doctor_hash = hash_password(DOCTOR_PASSWORD)  # hash once; bcrypt is deliberately slow
    portrait_idx = {"women": 10, "men": 10}

    for specialty, info in SPECIALTIES.items():
        n = PER_SPECIALTY.get(specialty, 2)
        for i in range(n):
            gender = "women" if rng.random() < 0.5 else "men"
            while True:
                first = rng.choice(FIRST_F if gender == "women" else FIRST_M)
                last = rng.choice(LAST)
                if f"{first} {last}" not in used_names:
                    used_names.add(f"{first} {last}")
                    break
            portrait_idx[gender] += rng.randint(1, 5)
            name = f"Dr. {first} {last}"
            years = rng.randint(4, 28)
            focus = rng.sample(info["cases"], k=min(3, len(info["cases"])))
            bio = (
                f"{name.split(' ', 1)[1]} is a board-certified {specialty.lower()} specialist with {years} years of experience, "
                f"known for a warm, evidence-based approach. Special interest in {focus[0][1].lower()} and {focus[1][1].lower()}."
            )
            email = f"{first.lower()}.{last.lower()}@yourhealthguide.dev"
            user = User(email=email, password_hash=doctor_hash, role="doctor", full_name=name)
            db.add(user)
            db.flush()
            provider = Provider(
                user_id=user.id,
                name=name,
                specialty=specialty,
                title=TITLES[specialty],
                years_experience=years,
                rating=round(rng.uniform(4.2, 5.0), 1),
                reviews_count=rng.randint(40, 620),
                bio=bio,
                location=rng.choice(LOCATIONS),
                languages=rng.choice(LANGS),
                photo_url=f"https://randomuser.me/api/portraits/{gender}/{portrait_idx[gender] % 99}.jpg",
                accepts_new=rng.random() > 0.1,
            )
            db.add(provider)
            db.flush()

            # Each provider has treated a different subset of cases (with variation) → differentiates matching.
            k = rng.randint(max(4, len(info["cases"]) - 4), len(info["cases"]))
            for symptoms, diagnosis, outcome in rng.sample(info["cases"], k=k):
                db.add(ProviderCase(provider_id=provider.id, symptoms=symptoms, diagnosis=diagnosis, outcome=outcome))
            # A couple of cross-over cases from General Physician for breadth.
            if specialty != "General Physician" and rng.random() < 0.5:
                s, d, o = rng.choice(SPECIALTIES["General Physician"]["cases"])
                db.add(ProviderCase(provider_id=provider.id, symptoms=s, diagnosis=d, outcome=o))

            days = sorted(rng.sample(range(5), k=rng.randint(3, 5)))
            if rng.random() < 0.3:
                days.append(5)  # Saturday clinic
            slot = rng.choice([20, 30, 30, 45])
            for d in days:
                if rng.random() < 0.8:
                    db.add(Availability(provider_id=provider.id, weekday=d, start_time=time(9, 0), end_time=time(12, 0), slot_minutes=slot))
                if d < 5 and rng.random() < 0.7:
                    db.add(Availability(provider_id=provider.id, weekday=d, start_time=time(14, 0), end_time=time(17, 0), slot_minutes=slot))

    if not db.query(User).filter(User.email == DEMO_PATIENT_EMAIL).first():
        user = User(email=DEMO_PATIENT_EMAIL, password_hash=hash_password(DEMO_PATIENT_PASSWORD), role="patient", full_name="Alex Morgan")
        db.add(user)
        db.flush()
        db.add(
            Patient(
                user_id=user.id,
                date_of_birth=date(1979, 6, 12),
                sex="Male",
                phone="+1 555 0134",
                conditions=["Hypertension (since 2018)", "Type 2 diabetes (since 2021)"],
                medications=["Lisinopril 10 mg daily", "Metformin 500 mg twice daily"],
                allergies=["Penicillin"],
                surgeries=["Appendectomy (2004)"],
                family_history=["Father: heart attack at 60", "Mother: hypothyroidism"],
                notes="Non-smoker. Walks 3x per week.",
            )
        )
    db.commit()
