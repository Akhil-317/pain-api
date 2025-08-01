# import requests
# from sqlalchemy.orm import Session
# from database import sessionLocal
# from models.on_boarding_models import Country

# def seed_countries_if_needed():
#     db: Session = sessionLocal()
#     try:
#         countries_count = db.query(Country).count()
#         if countries_count == 0:
#             print("🌱 Seeding countries table...")

#             response = requests.get("https://restcountries.com/v3.1/all?fields=name,cca2,cca3,capital,region,flags")
#             if response.status_code != 200:
#                 print("❌ REST Countries API error:", response.text)
#                 return

#             countries = response.json()
#             print(f"Fetched {len(countries)} countries.")

#             for c in countries:
#                 try:
#                     # Safe handling of missing/optional fields
#                     name = c["name"]["common"]
#                     official_name = c["name"].get("official", name)
#                     iso2 = c.get("cca2", "")
#                     iso3 = c.get("cca3", "")
#                     capital_list = c.get("capital", [])
#                     capital = capital_list[0] if capital_list else None
#                     region = c.get("region", "")
#                     flag_url = c.get("flags", {}).get("png", "")

#                     # Skip entries without required ISO codes
#                     if not iso2 or not iso3:
#                         continue

#                     # Prevent duplicates
#                     existing = db.query(Country).filter(Country.iso2 == iso2).first()
#                     if not existing:
#                         db.add(Country(
#                             name=name,
#                             official_name=official_name,
#                             iso2=iso2,
#                             iso3=iso3,
#                             capital=capital,
#                             region=region,
#                             flag_url=flag_url
#                         ))
#                 except Exception as item_err:
#                     print(f"⚠️ Skipping {c.get('name', {}).get('common', 'Unknown')} - {item_err}")

#             db.commit()
#             print("✅ Country seeding complete.")
#         else:
#             print(f"✅ Countries already seeded ({countries_count} rows).")
#     except Exception as e:
#         print("❌ Error during seeding:", e)
#     finally:
#         db.close()
