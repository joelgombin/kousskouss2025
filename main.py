from models import Restaurant, Plat, Date, Service
import dspy
from dotenv import load_dotenv
import os



# read .env file
load_dotenv()

model = os.getenv("MODEL", "google/gemini-2.5-flash")

lm = dspy.LM("openrouter/"+ model, api_key=os.getenv("OPENROUTER_API_KEY"), cache=True)
dspy.configure(lm=lm, track_usage=True)

class ExtractPlats(dspy.Signature):
    """Extraie les plats et restuarants du programme du festival Kouss Kouss 2025"""

    context: str = dspy.InputField(desc="Le contexte de l'extraction")
    page: dspy.Image = dspy.InputField(desc="L'image du programme du festival Kouss Kouss 2025")

    restaurants: list[Restaurant] = dspy.OutputField(desc="La liste des restaurants participants au festival")

context = "Le festival Kouss Kouss 2025 est un festival culinaire marseillais consacré au couscous. Le programme de ce festival est disponible sous forme de PDF sur le site du festival : https://kousskouss.com/. Malheureusement, il s'agit d'un document PDF qui n'est pas pratique à utiliser pour trouver le couscous que l'on souhaite aller manger. L'image fournie est une page du programme du festival."

extract = dspy.Predict(ExtractPlats)

def main():
    # extract from an image
    image = dspy.Image.from_file("images/image1.jpg")
    restaurants = extract(context=context, page=image)
    
    def format_restaurants(restaurants_result):
        """Formate joliment la liste des restaurants"""
        if hasattr(restaurants_result, 'restaurants'):
            restaurants_list = restaurants_result.restaurants
        else:
            restaurants_list = restaurants_result
            
        print("🍽️  RESTAURANTS DU FESTIVAL KOUSS•KOUSS 2025 🍽️")
        print("=" * 60)
        
        for i, restaurant in enumerate(restaurants_list, 1):
            print(f"\n📍 {i}. {restaurant.nom}")
            print(f"   📍 Adresse: {restaurant.adresse}")
            print(f"   🏘️  Quartier: {restaurant.quartier.value}")
            
            if restaurant.chef:
                print(f"   👨‍🍳 Chef: {restaurant.chef}")
            
            if restaurant.telephone:
                print(f"   📞 Téléphone: {restaurant.telephone}")
            
            print(f"   🍽️  Plats ({len(restaurant.plats)}):")
            
            for j, plat in enumerate(restaurant.plats, 1):
                vegetarien_icon = "🌱" if plat.vegetarien else ""
                vegan_icon = "🌿" if plat.vegan else ""
                
                print(f"      {j}. {plat.nom} {vegetarien_icon}{vegan_icon}")
                print(f"         💰 {plat.prix}")
                print(f"         📝 {plat.description}")
                
                if plat.dates:
                    dates_str = ", ".join([f"{date.jour}/{date.mois}" for date in plat.dates])
                    print(f"         📅 Dates: {dates_str}")
                
                if plat.services:
                    services_str = ", ".join([service.value for service in plat.services])
                    print(f"         ⏰ Services: {services_str}")
                
                if j < len(restaurant.plats):
                    print()
            
            print("-" * 50)
    
    format_restaurants(restaurants)


if __name__ == "__main__":
    main()
