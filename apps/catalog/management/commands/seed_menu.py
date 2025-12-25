"""
Management command to seed the database with sample menu categories and items.
"""
from django.core.management.base import BaseCommand
from apps.catalog.models import Category, MenuItem


class Command(BaseCommand):
    help = 'Seeds the database with sample menu data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding menu data...')

        # 1. Create Categories
        categories_data = [
            {'name': 'Main Dishes', 'ordering': 1, 'description': 'Filling main meals'},
            {'name': 'Sides', 'ordering': 2, 'description': 'Accompaniments and snacks'},
            {'name': 'Drinks', 'ordering': 3, 'description': 'Refreshing beverages'},
            {'name': 'Desserts', 'ordering': 4, 'description': 'Sweet treats'},
        ]

        categories = {}
        for data in categories_data:
            cat, created = Category.objects.get_or_create(
                name=data['name'],
                defaults={
                    'ordering': data['ordering'],
                    'description': data['description']
                }
            )
            categories[data['name']] = cat
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created category: {data['name']}"))

        # 2. Create Menu Items
        items_data = [
            # Main Dishes
            {'category': 'Main Dishes', 'name': 'Jollof Rice & Chicken', 'price': 2500, 'desc': 'Smoky party jollof with grilled chicken'},
            {'category': 'Main Dishes', 'name': 'Fried Rice Special', 'price': 2200, 'desc': 'Stir-fried rice with veggies and beef'},
            {'category': 'Main Dishes', 'name': 'Pounded Yam & Egusi', 'price': 3000, 'desc': 'Smooth pounded yam with rich egusi soup'},
            
            # Sides
            {'category': 'Sides', 'name': 'Plantain (Dodo)', 'price': 500, 'desc': 'Fried sweet ripe plantain'},
            {'category': 'Sides', 'name': 'Moin Moin', 'price': 700, 'desc': 'Steamed bean pudding'},
            {'category': 'Sides', 'name': 'French Fries', 'price': 1200, 'desc': 'Crispy golden potato chips'},
            
            # Drinks
            {'category': 'Drinks', 'name': 'Coca-Cola (50cl)', 'price': 400, 'desc': 'Chilled 50cl bottle'},
            {'category': 'Drinks', 'name': 'Fresh Orange Juice', 'price': 1500, 'desc': '100% freshly squeezed'},
            {'category': 'Drinks', 'name': 'Zobo Drink', 'price': 600, 'desc': 'Traditional hibiscus refreshing drink'},
            
            # Desserts
            {'category': 'Desserts', 'name': 'Chocolate Cake Slice', 'price': 1500, 'desc': 'Moist chocolate fudge cake'},
            {'category': 'Desserts', 'name': 'Vanilla Ice Cream', 'price': 1000, 'desc': 'Two scoops of creamy vanilla'},
        ]

        for data in items_data:
            cat = categories.get(data['category'])
            if cat:
                item, created = MenuItem.objects.get_or_create(
                    name=data['name'],
                    category=cat,
                    defaults={
                        'price_minor': data['price'] * 100,
                        'description': data['desc'],
                        'is_available': True,
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f"  - Created item: {data['name']}")

        self.stdout.write(self.style.SUCCESS('Successfully seeded menu data!'))
