"""Extra mock data for the India voice pilot: Hindi-speaking doctors across North Indian cities, cases that are
common in Indian clinics, and a Hindi-speaking demo patient. Additive and idempotent (keyed on e-mail)."""

import random
from datetime import date, time

from sqlalchemy.orm import Session

from .agents.specialties import SPECIALTIES
from .models import Availability, Patient, Provider, ProviderCase, User
from .security import hash_password

HINDI_PATIENT_EMAIL = "ramesh@demo.com"
HINDI_PATIENT_PASSWORD = "demo1234"

# (symptoms, diagnosis, outcome) — written in English so the doctor view and the case matcher stay consistent.
INDIA_CASES: dict[str, list[tuple[str, str, str]]] = {
    "General Physician": [
        ("High fever with chills every evening, severe body ache and pain behind the eyes for four days", "Dengue fever", "Fluids and platelet monitoring, recovered"),
        ("Fever rising in steps for a week with stomach pain, weakness and loss of appetite", "Typhoid (enteric fever)", "Antibiotic course, recovered"),
        ("Fever with shivering and sweating on alternate days after monsoon", "Malaria", "Antimalarial treatment"),
        ("Cough for more than three weeks with evening fever, weight loss and night sweats", "Pulmonary tuberculosis", "Started DOTS therapy"),
        ("Tiredness, pale skin, breathlessness on walking and dizziness in a young woman", "Iron deficiency anemia", "Iron tablets and diet advice"),
        ("Loose motions and vomiting after eating outside food, weakness and dry mouth", "Acute gastroenteritis", "ORS and zinc, recovered"),
        ("Joint pains and high fever during chikungunya outbreak", "Chikungunya", "Pain relief and rest"),
        ("Burning feet, tiredness and tingling, vegetarian diet", "Vitamin B12 deficiency", "B12 injections"),
        ("Yellow eyes and dark urine with fever after drinking unsafe water", "Hepatitis A", "Rest and supportive care"),
    ],
    "Cardiology": [
        ("Chest heaviness and sweating while walking uphill, diabetic for ten years", "Coronary artery disease", "Angioplasty with stent"),
        ("Breathlessness on exertion and palpitations in a woman with childhood joint pains", "Rheumatic heart disease (mitral stenosis)", "Balloon valvotomy"),
        ("Headache and giddiness with BP 170/110 found at a health camp", "Uncontrolled hypertension", "Two-drug therapy, low-salt diet"),
        ("Swelling in both feet and breathlessness at night needing extra pillows", "Congestive heart failure", "Diuretics and fluid restriction"),
        ("Sudden racing heartbeat with sweating and anxiety lasting ten minutes", "Supraventricular tachycardia", "Medication and ablation advised"),
    ],
    "Neurology": [
        ("One-sided throbbing headache with vomiting, worse in sunlight and on skipping meals", "Migraine", "Preventive tablets and trigger diary"),
        ("Burning and tingling in both feet at night in a long-standing diabetic", "Diabetic peripheral neuropathy", "Sugar control and nerve pain medicine"),
        ("Fits with frothing and loss of consciousness, tongue bite", "Epilepsy", "Regular antiseizure medicine"),
        ("Giddiness and spinning of the head on getting up from bed", "Positional vertigo", "Repositioning exercise"),
        ("Neck pain going down the arm with numb fingers in a tailor", "Cervical spondylosis with radiculopathy", "Physiotherapy and collar"),
        ("Sudden weakness of one arm and leg with slurred speech that recovered in an hour", "Transient ischemic attack", "Blood thinners and BP control"),
    ],
    "Dermatology": [
        ("Itchy ring-shaped red patches in the groin and waist, worse with sweating", "Fungal infection (tinea)", "Antifungal cream and tablets"),
        ("Severe itching at night between fingers, other family members also itching", "Scabies", "Permethrin for the whole family"),
        ("White patches on hands and around the lips slowly increasing", "Vitiligo", "Topical therapy and phototherapy"),
        ("Itchy rash with small blisters after using a new hair dye", "Allergic contact dermatitis", "Stopped dye, steroid cream"),
        ("Pimples and dark marks on the face in a teenager", "Acne vulgaris", "Topical retinoid"),
        ("Light coloured numb skin patch on the arm", "Leprosy work-up", "Referred for multidrug therapy"),
    ],
    "Gastroenterology": [
        ("Burning in the upper stomach and sour belching after spicy food and tea on empty stomach", "Acid peptic disease (gastritis)", "PPI and diet changes"),
        ("Gas, bloating and constipation for months with relief after passing stool", "Irritable bowel syndrome", "Fibre and diet plan"),
        ("Yellow eyes, swelling of the belly and feet in a long-term alcohol user", "Alcoholic liver disease", "Abstinence and liver care"),
        ("Pain on the right side of the stomach after oily food with vomiting", "Gallbladder stones", "Laparoscopic surgery"),
        ("Bleeding while passing stool with pain and hard stools", "Piles / anal fissure", "Stool softeners and sitz bath"),
        ("Loose motions with mucus and cramps for weeks, weight loss", "Amoebic colitis", "Metronidazole course"),
    ],
    "Pulmonology": [
        ("Wheezing and cough that gets worse in winter and with dust, since childhood", "Bronchial asthma", "Inhaler therapy"),
        ("Breathlessness and morning cough with phlegm in a woman cooking on a chulha for years", "COPD from biomass smoke", "Inhalers and clean cooking advice"),
        ("Cough with blood-streaked sputum, evening fever and weight loss", "Pulmonary tuberculosis", "Six-month anti-TB treatment"),
        ("Breathlessness and dry cough months after a bad chest infection", "Post-infective lung fibrosis", "Pulmonary rehabilitation"),
        ("Sneezing and breathlessness every Diwali season with smoke", "Allergic asthma", "Preventer inhaler"),
    ],
    "Orthopedics": [
        ("Pain in both knees while climbing stairs and squatting, age 60, difficulty sitting on the floor", "Knee osteoarthritis", "Physiotherapy, later knee replacement"),
        ("Lower back pain going down one leg after lifting a heavy sack", "Slipped disc (sciatica)", "Rest, physiotherapy"),
        ("Neck and shoulder pain in a person working long hours on a computer", "Cervical strain", "Posture correction and exercises"),
        ("Body pains and bone pain with difficulty getting up, little sun exposure", "Vitamin D deficiency (osteomalacia)", "Vitamin D and calcium"),
        ("Wrist pain and swelling after a fall from a motorcycle", "Distal radius fracture", "Plaster cast"),
        ("Frozen stiff shoulder in a diabetic, unable to comb hair", "Frozen shoulder", "Physiotherapy and injection"),
    ],
    "ENT": [
        ("Ear pain and pus discharge from the ear with reduced hearing since childhood", "Chronic suppurative otitis media", "Ear drops, tympanoplasty planned"),
        ("Blocked nose, sneezing and watery eyes every morning with dust", "Allergic rhinitis", "Nasal spray and antihistamine"),
        ("Throat pain and difficulty swallowing with fever in a child", "Acute tonsillitis", "Antibiotics"),
        ("Hoarse voice for two months in a tobacco chewer", "Laryngeal lesion work-up", "Laryngoscopy and biopsy"),
        ("Spinning head and ringing in the ear with vomiting", "Vestibular disorder", "Vestibular medicines"),
    ],
    "Endocrinology": [
        ("Sugar not coming under control with tablets, tingling feet and frequent urination", "Uncontrolled type 2 diabetes", "Insulin started with diet plan"),
        ("Weight gain, tiredness, feeling cold and irregular periods", "Hypothyroidism", "Thyroxine tablets"),
        ("Irregular periods, weight gain and facial hair in a young woman", "PCOS", "Lifestyle plan and metformin"),
        ("Sugar found high during pregnancy check-up", "Gestational diabetes", "Diet control and insulin"),
        ("Swelling in the front of the neck", "Goitre", "Thyroid tests and ultrasound"),
    ],
    "Psychiatry": [
        ("Nervousness, fast heartbeat and fear before exams, unable to sleep", "Anxiety disorder", "Counselling and short medication"),
        ("Feeling low, crying, no interest in work after losing a job", "Depression", "Antidepressant and therapy"),
        ("Drinking daily, shaking hands in the morning, family worried", "Alcohol dependence", "De-addiction programme"),
        ("Many body pains and gas with normal tests, a lot of tension at home", "Somatic symptom disorder", "Counselling"),
        ("Cannot sleep at night, mind keeps racing with worries", "Insomnia", "Sleep hygiene and CBT"),
    ],
    "Ophthalmology": [
        ("Slowly reducing vision in both eyes, white reflex, age 65", "Cataract", "Cataract surgery with lens implant"),
        ("Diabetic for fifteen years with blurred vision", "Diabetic retinopathy", "Laser treatment"),
        ("Red watery eyes with sticky discharge spreading in the family in monsoon", "Conjunctivitis (eye flu)", "Eye drops and hygiene"),
        ("Child unable to read the blackboard, squeezing eyes", "Refractive error (myopia)", "Spectacles"),
    ],
    "Urology": [
        ("Severe pain from the back to the lower stomach with burning urine and vomiting", "Kidney stone", "Laser stone removal"),
        ("Old man getting up many times at night to pass urine with weak stream", "Enlarged prostate", "Tablets, later TURP"),
        ("Burning urine and fever again and again in a diabetic woman", "Recurrent urinary infection", "Culture-based antibiotics"),
    ],
    "Obstetrics & Gynecology": [
        ("Heavy bleeding during periods with weakness and pale skin", "Fibroid uterus with anemia", "Iron therapy and surgery"),
        ("White discharge with itching and lower back pain", "Vaginal infection", "Treatment for both partners"),
        ("Two months of missed periods with morning vomiting", "Early pregnancy", "Antenatal registration"),
        ("Irregular periods and difficulty conceiving for two years", "PCOS with infertility", "Ovulation induction"),
        ("Hot flushes and irregular periods at age 48", "Menopause transition", "Counselling and supplements"),
    ],
}

# (name, sex, specialty, degrees, years, rating, reviews, location, languages)
INDIA_PROVIDERS = [
    ("Dr. Anjali Sharma", "F", "General Physician", "MBBS, MD (Medicine)", 16, 4.8, 812, "Sharma Clinic, Shamli", ["Hindi", "English"]),
    ("Dr. Mohammad Irfan Qureshi", "M", "General Physician", "MBBS, DNB (Family Medicine)", 11, 4.6, 540, "City Care Hospital, Muzaffarnagar", ["Hindi", "Urdu", "English"]),
    ("Dr. Sunita Yadav", "F", "General Physician", "MBBS", 22, 4.7, 1290, "Jan Seva Clinic, Meerut", ["Hindi", "English"]),
    ("Dr. Rajesh Kumar Gupta", "M", "Cardiology", "MD, DM (Cardiology)", 19, 4.9, 960, "Heartline Hospital, Meerut", ["Hindi", "English"]),
    ("Dr. Neha Agarwal", "F", "Cardiology", "MD, DNB (Cardiology)", 9, 4.6, 310, "Metro Heart Centre, Ghaziabad", ["Hindi", "English"]),
    ("Dr. Amit Tyagi", "M", "Neurology", "MD, DM (Neurology)", 14, 4.7, 455, "Neuro Care Centre, Meerut", ["Hindi", "English"]),
    ("Dr. Kavita Singh", "F", "Neurology", "MD, DM (Neurology)", 8, 4.5, 220, "Sanjeevani Hospital, Delhi", ["Hindi", "English", "Punjabi"]),
    ("Dr. Pooja Bansal", "F", "Dermatology", "MD (Dermatology)", 10, 4.8, 690, "Skin & Hair Clinic, Saharanpur", ["Hindi", "English"]),
    ("Dr. Vivek Chauhan", "M", "Dermatology", "MBBS, DDVL", 15, 4.5, 400, "Chauhan Skin Clinic, Muzaffarnagar", ["Hindi", "English"]),
    ("Dr. Sanjay Mittal", "M", "Gastroenterology", "MD, DM (Gastroenterology)", 17, 4.8, 730, "Mittal Gastro & Liver Centre, Meerut", ["Hindi", "English"]),
    ("Dr. Farah Naqvi", "F", "Gastroenterology", "MD, DNB (Gastroenterology)", 7, 4.6, 180, "Apex Hospital, Delhi", ["Hindi", "Urdu", "English"]),
    ("Dr. Harpreet Singh Sandhu", "M", "Pulmonology", "MD (Pulmonary Medicine)", 13, 4.7, 510, "Chest & TB Clinic, Karnal", ["Hindi", "Punjabi", "English"]),
    ("Dr. Rekha Verma", "F", "Pulmonology", "MD (Respiratory Medicine)", 20, 4.8, 880, "Verma Chest Hospital, Meerut", ["Hindi", "English"]),
    ("Dr. Manoj Rana", "M", "Orthopedics", "MS (Orthopaedics)", 18, 4.7, 1020, "Rana Bone & Joint Hospital, Shamli", ["Hindi", "English"]),
    ("Dr. Deepak Malik", "M", "Orthopedics", "MS, MCh (Orthopaedics)", 12, 4.6, 470, "Malik Ortho Centre, Panipat", ["Hindi", "Haryanvi", "English"]),
    ("Dr. Shalini Jain", "F", "ENT", "MS (ENT)", 14, 4.7, 560, "Jain ENT Clinic, Muzaffarnagar", ["Hindi", "English"]),
    ("Dr. Arvind Saxena", "M", "Endocrinology", "MD, DM (Endocrinology)", 16, 4.8, 640, "Diabetes & Thyroid Centre, Meerut", ["Hindi", "English"]),
    ("Dr. Ritu Chaudhary", "F", "Endocrinology", "MD (Medicine), Fellowship in Diabetology", 9, 4.6, 290, "Sugar Care Clinic, Shamli", ["Hindi", "English"]),
    ("Dr. Imran Khan", "M", "Psychiatry", "MD (Psychiatry)", 11, 4.7, 330, "Man Shanti Clinic, Saharanpur", ["Hindi", "Urdu", "English"]),
    ("Dr. Meenakshi Rawat", "F", "Psychiatry", "MD (Psychiatry)", 15, 4.8, 410, "Mind Wellness Centre, Dehradun", ["Hindi", "Garhwali", "English"]),
    ("Dr. Sandeep Goel", "M", "Ophthalmology", "MS (Ophthalmology)", 21, 4.9, 1500, "Goel Eye Hospital, Shamli", ["Hindi", "English"]),
    ("Dr. Nidhi Rastogi", "F", "Ophthalmology", "MS, DNB (Ophthalmology)", 8, 4.6, 260, "Drishti Eye Centre, Meerut", ["Hindi", "English"]),
    ("Dr. Pankaj Dhiman", "M", "Urology", "MS, MCh (Urology)", 13, 4.7, 380, "Stone & Kidney Clinic, Muzaffarnagar", ["Hindi", "English"]),
    ("Dr. Seema Tomar", "F", "Obstetrics & Gynecology", "MS (Obstetrics & Gynaecology)", 19, 4.8, 1180, "Tomar Maternity Home, Shamli", ["Hindi", "English"]),
    ("Dr. Ayesha Siddiqui", "F", "Obstetrics & Gynecology", "MD, DGO", 10, 4.7, 520, "Mother Care Hospital, Saharanpur", ["Hindi", "Urdu", "English"]),
]


def _email(name: str) -> str:
    return name.replace("Dr. ", "").lower().replace(" ", ".") + "@yourhealthguide.in"


def seed_india(db: Session, doctor_password_hash: str | None = None) -> int:
    """Insert any India-pilot doctors that are missing. Returns the number added."""
    existing = {e for (e,) in db.query(User.email).filter(User.email.like("%@yourhealthguide.in")).all()}
    todo = [p for p in INDIA_PROVIDERS if _email(p[0]) not in existing]
    if todo:
        from .seed import DOCTOR_PASSWORD

        doctor_password_hash = doctor_password_hash or hash_password(DOCTOR_PASSWORD)
    rng = random.Random(2026)
    for idx, (name, sex, specialty, degrees, years, rating, reviews, location, languages) in enumerate(INDIA_PROVIDERS):
        # Draw the random numbers for every doctor so results do not depend on which ones already exist.
        base = rng.sample(SPECIALTIES[specialty]["cases"], k=min(4, len(SPECIALTIES[specialty]["cases"])))
        days = sorted(rng.sample(range(6), k=rng.randint(4, 6)))  # Mon–Sat OPD is the norm
        slot = rng.choice([15, 20, 20, 30])
        evening = [rng.random() < 0.7 for _ in days]
        if _email(name) in existing:
            continue
        user = User(email=_email(name), password_hash=doctor_password_hash, role="doctor", full_name=name)
        db.add(user)
        db.flush()
        focus = INDIA_CASES[specialty]
        provider = Provider(
            user_id=user.id,
            name=name,
            specialty=specialty,
            title=degrees,
            years_experience=years,
            rating=rating,
            reviews_count=reviews,
            bio=(
                f"{name} has {years} years of experience and consults in {', '.join(languages[:-1])} and {languages[-1]}. "
                f"Frequently treats {focus[0][1].lower()} and {focus[1][1].lower()}."
            ),
            location=location,
            languages=languages,
            photo_url=f"https://randomuser.me/api/portraits/{'women' if sex == 'F' else 'men'}/{30 + idx}.jpg",
            accepts_new=True,
        )
        db.add(provider)
        db.flush()
        for symptoms, diagnosis, outcome in [*focus, *base]:
            db.add(ProviderCase(provider_id=provider.id, symptoms=symptoms, diagnosis=diagnosis, outcome=outcome))
        for d, has_evening in zip(days, evening):
            db.add(Availability(provider_id=provider.id, weekday=d, start_time=time(10, 0), end_time=time(13, 30), slot_minutes=slot))
            if has_evening:
                db.add(Availability(provider_id=provider.id, weekday=d, start_time=time(17, 0), end_time=time(20, 0), slot_minutes=slot))

    if not db.query(User).filter(User.email == HINDI_PATIENT_EMAIL).first():
        user = User(email=HINDI_PATIENT_EMAIL, password_hash=hash_password(HINDI_PATIENT_PASSWORD), role="patient", full_name="Ramesh Kumar")
        db.add(user)
        db.flush()
        db.add(
            Patient(
                user_id=user.id,
                date_of_birth=date(1968, 8, 15),
                sex="Male",
                phone="+91 98765 43210",
                conditions=["Type 2 diabetes (since 2016)"],
                medications=["Metformin 500 mg twice daily"],
                allergies=[],
                surgeries=[],
                family_history=["Father: heart disease"],
                notes="Farmer. Speaks Hindi. Prefers voice.",
            )
        )
    db.commit()
    return len(todo)
