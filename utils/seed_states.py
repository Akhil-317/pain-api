# import requests
# from sqlalchemy.orm import Session
# from database import sessionLocal
# from models.on_boarding_models import Country, State

# def seed_states():
#     db: Session = sessionLocal()

#     try:
#         response = requests.post("https://countriesnow.space/api/v0.1/countries/states")
#         data = response.json()["data"]

#         for country_entry in data:
#             country_name = country_entry["name"]
#             states = country_entry["states"]

#             country = db.query(Country).filter(Country.name == country_name).first()
#             if country:
#                 for state in states:
#                     exists = db.query(State).filter(
#                         State.name == state["name"],
#                         State.country_id == country.id
#                     ).first()
#                     if not exists:
#                         db.add(State(name=state["name"], country_id=country.id))

#         db.commit()
#         print("✅ States seeding complete.")
#     except Exception as e:
#         print("❌ Error seeding states:", e)
#     finally:
#         db.close()
