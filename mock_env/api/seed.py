from mock_env.api.database import SessionLocal, Base, engine
from mock_env.api import models


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(models.Vendor).count() > 0:
        print("Already seeded.")
        return

    # Vendors — note Acme has aliases to test ambiguity
    db.add_all([
        models.Vendor(id="V001", name="Acme Corp",
                      aliases="Acme Corporation,ACME", email="ap@acme.com"),
        models.Vendor(id="V002", name="Beta LLC",
                      aliases="Beta Limited", email="billing@beta.com"),
        models.Vendor(id="V003", name="Acme Corporation",
                      aliases="", email="finance@acmecorp.com"),
    ])

    # Purchase orders
    db.add_all([
        models.PurchaseOrder(po_number="PO-1001", vendor_id="V001", amount=45000),
        models.PurchaseOrder(po_number="PO-1002", vendor_id="V002", amount=12000),
        models.PurchaseOrder(po_number="PO-1003", vendor_id="V001", amount=200000),
    ])

    # Employees
    db.add_all([
        models.Employee(id="E1042", name="Priya Sharma", department="Engineering"),
        models.Employee(id="E1043", name="Rahul Verma", department="Sales"),
    ])

    db.commit()
    db.close()
    print("Seeded successfully.")


if __name__ == "__main__":
    seed()