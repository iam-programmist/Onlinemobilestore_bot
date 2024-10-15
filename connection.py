import psycopg2
from secret import database_password
def open_connection():
    conn = psycopg2.connect(
        database = "Onlinemobilestore_db",
        user = "postgres",
        password = database_password,
        host="localhost",
        port = 5432
    )
    return conn

def close_connection(conn, cur):
    cur.close()
    conn.close()

def create_tables():
    conn = open_connection()
    cur = conn.cursor()
    cur.execute("""
                create table if not exists users(
                id serial primary key,
                username varchar(100) unique,
                telegram_id bigint unique,
                is_admin boolean default false,
                created_at timestamp default now());

                create table if not exists products(
                id serial primary key,
                name text not null,
                description text not null,
                price numeric(10, 2) not null,
                image bytea,
                created_at timestamp default now());

                create table if not exists cart(
                id serial primary key,
                user_id bigint references users(telegram_id),
                product_id int references products(id),
                quantity int,
                created_at timestamp default now());
        
                create table if not exists orders(
                id serial primary key,
                user_id bigint references users(telegram_id),
                total_amount numeric(10, 2),
                status varchar(50) default 'processing',
                created_at timestamp default now());
                """)
    conn.commit()
    close_connection(conn, cur)
