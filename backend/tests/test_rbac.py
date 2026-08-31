from app.models.user import UserRole
from tests.conftest import auth_headers, make_user, make_warehouse


def test_sales_user_cannot_create_product(client, db):
    make_user(db, role=UserRole.SALES_USER, email="sales1@test.dev")
    headers = auth_headers(client, "sales1@test.dev")
    resp = client.post(
        "/api/products",
        json={"sku": "RBAC-1", "name": "Blocked Product", "unit_price": "10.00", "cost_price": "5.00"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_inventory_manager_can_create_product(client, db):
    make_user(db, role=UserRole.INVENTORY_MANAGER, email="invmgr1@test.dev")
    headers = auth_headers(client, "invmgr1@test.dev")
    resp = client.post(
        "/api/products",
        json={"sku": "RBAC-2", "name": "Allowed Product", "unit_price": "10.00", "cost_price": "5.00"},
        headers=headers,
    )
    assert resp.status_code == 201


def test_only_admin_can_create_warehouse(client, db):
    make_user(db, role=UserRole.INVENTORY_MANAGER, email="invmgr2@test.dev")
    headers = auth_headers(client, "invmgr2@test.dev")
    resp = client.post(
        "/api/warehouses",
        json={"name": "New WH", "code": "WH-RBAC"},
        headers=headers,
    )
    assert resp.status_code == 403

    make_user(db, role=UserRole.ADMIN, email="admin1@test.dev")
    admin_headers = auth_headers(client, "admin1@test.dev")
    resp = client.post(
        "/api/warehouses",
        json={"name": "New WH", "code": "WH-RBAC"},
        headers=admin_headers,
    )
    assert resp.status_code == 201


def test_sales_user_cannot_list_admin_users(client, db):
    make_user(db, role=UserRole.SALES_USER, email="sales-admin@test.dev")
    headers = auth_headers(client, "sales-admin@test.dev")
    resp = client.get("/api/admin/users", headers=headers)
    assert resp.status_code == 403


def test_sales_user_cannot_create_transfer(client, db):
    make_user(db, role=UserRole.SALES_USER, email="sales-trf@test.dev")
    headers = auth_headers(client, "sales-trf@test.dev")
    resp = client.post(
        "/api/transfers",
        json={
            "source_warehouse_id": "00000000-0000-0000-0000-000000000001",
            "destination_warehouse_id": "00000000-0000-0000-0000-000000000002",
            "items": [{"product_id": "00000000-0000-0000-0000-000000000003", "quantity": 1}],
        },
        headers=headers,
    )
    assert resp.status_code == 403


def test_unauthenticated_request_is_rejected(client):
    resp = client.post("/api/products", json={"sku": "X", "name": "X", "unit_price": "1", "cost_price": "1"})
    assert resp.status_code == 401


def test_unauthenticated_dashboard_is_rejected(client):
    resp = client.get("/api/dashboard/overview")
    assert resp.status_code == 401


def test_duplicate_sku_rejected(client, db):
    make_user(db, role=UserRole.ADMIN, email="admin2@test.dev")
    headers = auth_headers(client, "admin2@test.dev")
    payload = {"sku": "DUPE-SKU", "name": "First", "unit_price": "10.00", "cost_price": "5.00"}
    resp1 = client.post("/api/products", json=payload, headers=headers)
    assert resp1.status_code == 201
    resp2 = client.post("/api/products", json={**payload, "name": "Second"}, headers=headers)
    assert resp2.status_code == 409


def test_sales_user_cannot_list_transfers(client, db):
    make_user(db, role=UserRole.SALES_USER, email="sales-list-trf@test.dev")
    headers = auth_headers(client, "sales-list-trf@test.dev")
    resp = client.get("/api/transfers", headers=headers)
    assert resp.status_code == 403


def test_sales_user_cannot_fulfill_order(client, db):
    make_user(db, role=UserRole.SALES_USER, email="sales-fulfill@test.dev")
    headers = auth_headers(client, "sales-fulfill@test.dev")
    resp = client.post(
        "/api/orders/00000000-0000-0000-0000-000000000001/fulfill",
        headers=headers,
    )
    assert resp.status_code == 403


def test_warehouse_manager_cannot_list_suppliers(client, db):
    make_user(db, role=UserRole.WAREHOUSE_MANAGER, email="wh-suppliers@test.dev")
    headers = auth_headers(client, "wh-suppliers@test.dev")
    resp = client.get("/api/suppliers", headers=headers)
    assert resp.status_code == 403


def test_warehouse_manager_inventory_is_scoped(client, db):
    from app.models.stock_movement import MovementType
    from app.models.user import WarehouseUser
    from app.services.inventory_service import apply_stock_movement
    from tests.test_inventory import make_product

    admin = make_user(db, role=UserRole.ADMIN, email="scope-admin@test.dev")
    mgr = make_user(db, role=UserRole.WAREHOUSE_MANAGER, email="scope-wh@test.dev")
    wh_a = make_warehouse(db, code="SCA")
    wh_b = make_warehouse(db, code="SCB")
    db.add(WarehouseUser(user_id=mgr.id, warehouse_id=wh_a.id))
    db.commit()
    product = make_product(db)
    apply_stock_movement(
        db,
        product_id=product.id,
        warehouse_id=wh_a.id,
        movement_type=MovementType.ADJUSTMENT_IN,
        quantity=10,
        created_by_id=admin.id,
        reason="a",
    )
    apply_stock_movement(
        db,
        product_id=product.id,
        warehouse_id=wh_b.id,
        movement_type=MovementType.ADJUSTMENT_IN,
        quantity=20,
        created_by_id=admin.id,
        reason="b",
    )
    headers = auth_headers(client, "scope-wh@test.dev")
    resp = client.get("/api/inventory", headers=headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["warehouse_id"] == str(wh_a.id)


def test_unassigned_warehouse_manager_sees_no_inventory(client, db):
    make_user(db, role=UserRole.WAREHOUSE_MANAGER, email="wh-empty@test.dev")
    headers = auth_headers(client, "wh-empty@test.dev")
    resp = client.get("/api/inventory", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_admin_can_assign_warehouses(client, db):
    admin = make_user(db, role=UserRole.ADMIN, email="assign-admin@test.dev")
    mgr = make_user(db, role=UserRole.WAREHOUSE_MANAGER, email="assign-wh@test.dev")
    warehouse = make_warehouse(db, code="ASN")
    headers = auth_headers(client, "assign-admin@test.dev")
    resp = client.put(
        f"/api/admin/users/{mgr.id}/warehouses",
        json={"warehouse_ids": [str(warehouse.id)]},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["warehouse_ids"] == [str(warehouse.id)]
    assert body["warehouse_labels"] == ["ASN"]
