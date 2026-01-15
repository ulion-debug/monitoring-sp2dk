from monitoring_sp2dk.auth_api import hash_password, engine, users
from sqlalchemy import select

def create_user(username, password, role):
    with engine.begin() as conn:
        exists = conn.execute(
            select(users.c.id).where(users.c.username == username)
        ).first()

        if exists:
            print("Username already exists")
            return

        conn.execute(
            users.insert().values(
                username=username,
                password=hash_password(password),
                role=role
            )
        )

    print(f"User '{username}' with role '{role}' created")


if __name__ == "__main__":
    create_user("monitoring", "Monitoringsp2dK", "admin")
    create_user("monitoring-oc", "MonitoringOC", "oc")
