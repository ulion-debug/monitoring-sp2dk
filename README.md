## DATABASE
CREATE DATABASE sp2dkdb;

CREATE USER sp2dkuser WITH PASSWORD 'passwordku';

ALTER ROLE sp2dkuser SET client_encoding TO 'utf8';

ALTER ROLE sp2dkuser SET default_transaction_isolation TO 'read committed';

ALTER ROLE sp2dkuser SET timezone TO 'Asia/Jakarta';

GRANT ALL PRIVILEGES ON DATABASE sp2dkdb TO sp2dkuser;

----------

CREATE TABLE sp2dk (

    id SERIAL PRIMARY KEY,

    unit VARCHAR(200),
    
    sp2dk INT,
    
    lhp2dk INT,
    
    outstanding INT,
    
    potensi NUMERIC,
    
    realisasi NUMERIC,
    
    kesimpulan_lhp2dk VARCHAR(200),
    
    tahun INT,
    
    bulan INT
);


ALTER SCHEMA public OWNER TO sp2dkuser;

GRANT ALL PRIVILEGES ON DATABASE sp2dkdb TO sp2dkuser;

GRANT ALL ON SCHEMA public TO sp2dkuser;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sp2dkuser;

GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sp2dkuser;

pip install "psycopg[binary]"

pip install uvicorn

pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt] sqlalchemy

## Python
#### jalanin untuk create user
python manage.py makemigrations

python manage.py migrate 

python -m monitoring_sp2dk.create_fastapi_user

-- username = monitoring

-- password = Monitoringsp2dK

### Run
python -m uvicorn monitoring_sp2dk.auth_api:app --reload --port 8001

python manage.py runserver

