"""
Realistic seed data so the app looks populated immediately after setup.

Run with: python -m app.utils.seed
(the Docker entrypoint runs this automatically when SEED_ON_START=true)
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from app.core.security import hash_password
from app.database.base import Base
from app.database.connection import SessionLocal, engine
from app.models.category import Category
from app.models.customer_order import Customer, CustomerOrder, CustomerOrderItem, CustomerOrderStatus
from app.models.product import Product, ProductStatus
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.models.stock_movement import MovementType
from app.models.supplier import Supplier, SupplierProduct, SupplierStatus
from app.models.transfer import InventoryTransfer
from app.models.user import User, UserRole, WarehouseUser
from app.models.warehouse import Warehouse, WarehouseStatus
from app.services.inventory_service import apply_stock_movement
from app.services.purchase_order_service import receive_purchase_order
from app.services.transfer_service import create_transfer, receive_transfer

random.seed(42)

CATEGORY_TREE = {
    "Electronics": ["Computers", "Networking", "Accessories"],
    "Office Supplies": ["Furniture", "Stationery"],
    "Warehouse Equipment": ["Packaging", "Safety Gear"],
}

PRODUCT_NAMES = [
    "Laptop Pro 15", "Laptop Air 13", "Wireless Mouse", "Mechanical Keyboard", "27in Monitor",
    "USB-C Hub", "Gigabit Switch 8-Port", "Wi-Fi 6 Router", "Ethernet Cable 5m", "Webcam HD",
    "Office Chair Ergo", "Standing Desk", "Whiteboard 4x6", "Sticky Notes Pack", "Ballpoint Pens Box",
    "Printer Paper A4 Ream", "Stapler Heavy Duty", "Corrugated Boxes (50pk)", "Packing Tape Roll",
    "Bubble Wrap Roll", "Safety Helmet", "High-Vis Vest", "Steel Toe Boots", "Pallet Jack",
    "Forklift Battery", "Barcode Scanner", "Label Printer", "Shrink Wrap Roll", "Warehouse Shelving Unit",
    "Fire Extinguisher", "External SSD 1TB", "HDMI Cable 2m", "Power Strip 6-Outlet", "Laptop Stand",
    "Noise-Cancelling Headset", "Conference Speakerphone", "Projector Screen", "LED Desk Lamp",
    "Filing Cabinet 4-Drawer", "Recycled Paper Towels", "Hand Sanitizer Dispenser", "First Aid Kit",
    "Tool Box Set", "Cordless Drill", "Measuring Tape 5m", "Work Gloves (12 pairs)", "Extension Cord 10m",
    "Dolly Cart", "Industrial Scale", "Cable Ties (500pk)", "Anti-Static Wrist Strap", "Server Rack 12U",
]

SUPPLIERS = [
    ("TechSource Ltd", "Kampala", "Uganda"),
    ("Global Office Supplies", "Nairobi", "Kenya"),
    ("PackRight Industries", "Dar es Salaam", "Tanzania"),
    ("SafetyFirst Equipment Co", "Kigali", "Rwanda"),
    ("Nordic Electronics Wholesale", "Oslo", "Norway"),
]

WAREHOUSES = [
    ("Warehouse A - Kampala Central", "WH-A", "Kampala", "Uganda"),
    ("Warehouse B - Entebbe Logistics Park", "WH-B", "Entebbe", "Uganda"),
    ("Warehouse C - Jinja Depot", "WH-C", "Jinja", "Uganda"),
]

CUSTOMERS = [
    "Acme Retailers", "BrightMart Supermarkets", "Kampala Tech Hub", "Nile Logistics Co",
    "Savanna Electronics", "Pearl Office Solutions", "Rift Valley Traders", "Lakeview Wholesale",
]


DEMO_ACCOUNTS = [
    ("admin@supplychainx.dev", "System Administrator", UserRole.ADMIN, "Admin123!"),
    ("inventory.manager@supplychainx.dev", "Irene Manager", UserRole.INVENTORY_MANAGER, "Password123!"),
    ("warehouse.a@supplychainx.dev", "Wasswa Mukasa", UserRole.WAREHOUSE_MANAGER, "Password123!"),
    ("procurement@supplychainx.dev", "Peter Okello", UserRole.PROCUREMENT_MANAGER, "Password123!"),
    ("sales@supplychainx.dev", "Sarah Namutebi", UserRole.SALES_USER, "Password123!"),
]


def ensure_demo_users(db):
    """Create or reset the five demo logins so published credentials always work."""
    created = []
    for email, name, role, password in DEMO_ACCOUNTS:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=name,
                role=role,
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.hashed_password = hash_password(password)
            user.full_name = name
            user.role = role
            user.is_active = True
        created.append(user)
    return created


def get_or_create_admin(db):
    return ensure_demo_users(db)[0]


def seed_users(db):
    return ensure_demo_users(db)[1:]


def seed_categories(db):
    created = {}
    for parent_name, children in CATEGORY_TREE.items():
        parent = Category(name=parent_name)
        db.add(parent)
        db.flush()
        created[parent_name] = parent
        for child_name in children:
            child = Category(name=child_name, parent_id=parent.id)
            db.add(child)
            db.flush()
            created[child_name] = child
    return created


def seed_products(db, categories):
    all_categories = list(categories.values())
    products = []
    for i, name in enumerate(PRODUCT_NAMES):
        sku = f"SKU-{1000 + i}"
        cost = Decimal(random.randint(500, 50000)) / Decimal(100)
        price = cost * Decimal("1.4")
        product = Product(
            sku=sku,
            name=name,
            description=f"{name} — standard warehouse-managed item.",
            category_id=random.choice(all_categories).id,
            unit_price=price.quantize(Decimal("0.01")),
            cost_price=cost.quantize(Decimal("0.01")),
            reorder_level=random.choice([5, 10, 15, 20]),
            reorder_quantity=random.choice([50, 100, 150]),
            unit_of_measure="unit",
            status=ProductStatus.ACTIVE,
        )
        db.add(product)
        products.append(product)
    db.flush()
    return products


def seed_suppliers_and_links(db, products):
    suppliers = []
    for company, city, country in SUPPLIERS:
        supplier = Supplier(
            company_name=company,
            contact_person=f"{company.split()[0]} Contact",
            email=f"contact@{company.lower().replace(' ', '')}.com",
            phone="+256700000000",
            address=f"{city} Industrial Area",
            country=country,
            status=SupplierStatus.ACTIVE,
        )
        db.add(supplier)
        suppliers.append(supplier)
    db.flush()

    for product in products:
        chosen_suppliers = random.sample(suppliers, k=random.randint(1, 2))
        for supplier in chosen_suppliers:
            db.add(
                SupplierProduct(
                    supplier_id=supplier.id,
                    product_id=product.id,
                    unit_cost=product.cost_price,
                )
            )
    db.flush()
    return suppliers


def seed_warehouses(db):
    warehouses = []
    for name, code, city, country in WAREHOUSES:
        warehouse = Warehouse(name=name, code=code, city=city, country=country, status=WarehouseStatus.ACTIVE)
        db.add(warehouse)
        warehouses.append(warehouse)
    db.flush()
    return warehouses


def seed_warehouse_assignments(db, users, warehouses):
    scoped_users = [u for u in users if u.role in (UserRole.WAREHOUSE_MANAGER, UserRole.SALES_USER)]
    for user in scoped_users:
        exists = (
            db.query(WarehouseUser)
            .filter(WarehouseUser.user_id == user.id, WarehouseUser.warehouse_id == warehouses[0].id)
            .first()
        )
        if not exists:
            db.add(WarehouseUser(user_id=user.id, warehouse_id=warehouses[0].id))
    db.flush()


def seed_initial_stock(db, admin, products, warehouses):
    """Give every product an opening balance in Warehouse A via ADJUSTMENT_IN, some in B, little/none in C."""
    for product in products:
        qty_a = random.randint(20, 200)
        apply_stock_movement(
            db, product_id=product.id, warehouse_id=warehouses[0].id,
            movement_type=MovementType.ADJUSTMENT_IN, quantity=qty_a,
            created_by_id=admin.id, reason="Opening balance", commit=False,
        )
        if random.random() > 0.3:
            qty_b = random.randint(10, 80)
            apply_stock_movement(
                db, product_id=product.id, warehouse_id=warehouses[1].id,
                movement_type=MovementType.ADJUSTMENT_IN, quantity=qty_b,
                created_by_id=admin.id, reason="Opening balance", commit=False,
            )
        if random.random() > 0.7:
            qty_c = random.randint(5, 30)
            apply_stock_movement(
                db, product_id=product.id, warehouse_id=warehouses[2].id,
                movement_type=MovementType.ADJUSTMENT_IN, quantity=qty_c,
                created_by_id=admin.id, reason="Opening balance", commit=False,
            )
    db.commit()


def seed_purchase_orders(db, admin, suppliers, products, warehouses):
    for i in range(6):
        supplier = random.choice(suppliers)
        warehouse = random.choice(warehouses)
        chosen_products = random.sample(products, k=random.randint(2, 5))
        order = PurchaseOrder(
            order_number=f"PO-{2000 + i}",
            supplier_id=supplier.id,
            warehouse_id=warehouse.id,
            order_date=date.today() - timedelta(days=random.randint(1, 30)),
            expected_delivery_date=date.today() + timedelta(days=random.randint(1, 14)),
            status=PurchaseOrderStatus.SUBMITTED,
            created_by_id=admin.id,
            total_cost=0,
        )
        db.add(order)
        db.flush()
        total = Decimal("0")
        for product in chosen_products:
            qty = random.randint(20, 100)
            item = PurchaseOrderItem(
                purchase_order_id=order.id, product_id=product.id,
                quantity_ordered=qty, unit_cost=product.cost_price,
            )
            db.add(item)
            total += qty * product.cost_price
        order.total_cost = total
        db.commit()

        # Receive some of them fully, some partially, to show both PO statuses in the seed data.
        if i % 3 != 2:
            order_full = db.query(PurchaseOrder).filter(PurchaseOrder.id == order.id).first()
            receipts = [
                {"item_id": item.id, "quantity_received": item.quantity_ordered if i % 2 == 0 else item.quantity_ordered // 2}
                for item in order_full.items
            ]
            receive_purchase_order(db, purchase_order_id=order.id, receipts=receipts, received_by_id=admin.id)


def seed_transfers(db, admin, products, warehouses):
    for i in range(3):
        product_sample = random.sample(products, k=2)
        transfer = create_transfer(
            db,
            source_warehouse_id=warehouses[0].id,
            destination_warehouse_id=warehouses[1].id,
            items=[{"product_id": p.id, "quantity": random.randint(5, 15)} for p in product_sample],
            created_by_id=admin.id,
            notes="Routine restock transfer",
        )
        if i < 2:
            receive_transfer(db, transfer_id=transfer.id, received_by_id=admin.id)


def seed_customers_and_orders(db, admin, products, warehouses):
    customers = []
    for name in CUSTOMERS:
        customer = Customer(name=name, email=f"{name.lower().replace(' ', '.')}@example.com")
        db.add(customer)
        customers.append(customer)
    db.flush()

    for i in range(8):
        customer = random.choice(customers)
        warehouse = warehouses[0]
        chosen_products = random.sample(products, k=random.randint(1, 3))
        order = CustomerOrder(
            order_number=f"SO-{3000 + i}",
            customer_id=customer.id,
            warehouse_id=warehouse.id,
            order_date=date.today() - timedelta(days=random.randint(0, 10)),
            status=CustomerOrderStatus.PENDING,
            created_by_id=admin.id,
            total_amount=0,
        )
        db.add(order)
        db.flush()
        total = Decimal("0")
        for product in chosen_products:
            qty = random.randint(1, 5)
            db.add(CustomerOrderItem(order_id=order.id, product_id=product.id, quantity=qty, unit_price=product.unit_price))
            total += qty * product.unit_price
        order.total_amount = total
        db.commit()


def run():
    Base.metadata.create_all(bind=engine)  # safety net; migrations are the source of truth
    db = SessionLocal()
    try:
        demo_users = ensure_demo_users(db)
        admin = demo_users[0]
        users = demo_users[1:]
        db.commit()

        if db.query(Product).count() == 0:
            categories = seed_categories(db)
            db.commit()
            products = seed_products(db, categories)
            db.commit()
            suppliers = seed_suppliers_and_links(db, products)
            db.commit()
            warehouses = seed_warehouses(db)
            db.commit()
            seed_warehouse_assignments(db, users, warehouses)
            seed_initial_stock(db, admin, products, warehouses)
        else:
            products = db.query(Product).all()
            suppliers = db.query(Supplier).all()
            warehouses = db.query(Warehouse).all()

        if warehouses:
            seed_warehouse_assignments(db, users, warehouses)
            db.commit()

        if db.query(PurchaseOrder).count() == 0:
            seed_purchase_orders(db, admin, suppliers, products, warehouses)
        if db.query(InventoryTransfer).count() == 0:
            seed_transfers(db, admin, products, warehouses)
        if db.query(Customer).count() == 0:
            seed_customers_and_orders(db, admin, products, warehouses)

        print(f"Seeded {len(products)} products, {len(suppliers)} suppliers, {len(warehouses)} warehouses.")
        print("Admin login: admin@supplychainx.dev / Admin123!")
    finally:
        db.close()


if __name__ == "__main__":
    run()
