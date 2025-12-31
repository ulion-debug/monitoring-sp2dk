from monitoring_sp2dk.auth_api import hash_password, engine, users

username = "monitoring"
password = "Monitoringsp2dK"

hashed = hash_password(password)

with engine.connect() as conn:
    conn.execute(users.insert().values(username=username, password=hashed))
    conn.commit()

print("User created")
