import telebot
import io
from connection import *
from secret import *
from telebot import types
bot = telebot.TeleBot(api_key)
create_tables()

def is_admin(username):
    return username == "iamprogrammist"

def main_menu(username):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Add Product")
    btn2 = types.KeyboardButton("Delete Product")
    btn3 = types.KeyboardButton("View Products")
    btn4 = types.KeyboardButton("Add To Cart")
    btn5 = types.KeyboardButton("View Cart")
    btn6 = types.KeyboardButton("Update Cart")
    btn7 = types.KeyboardButton("Remove From Cart")
    btn8 = types.KeyboardButton("Checkout")
    btn9 = types.KeyboardButton("Order Status")
    if is_admin(username):
        markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9)
    else:
        markup.add(btn3, btn4, btn5, btn6, btn7, btn8, btn9)
    return markup

@bot.message_handler(commands=['start'])
def register_user(message):
    conn = open_connection()
    cur = conn.cursor()
    telegram_id = message.chat.id
    username = message.from_user.username
    cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cur.fetchone()
    if user:
        bot.send_message(message.chat.id, "You are already registered!", reply_markup=main_menu(username))
    else:
        cur.execute("INSERT INTO users (telegram_id, username) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING", (telegram_id, username))
        conn.commit()
        bot.send_message(message.chat.id, "You have successfully registered!", reply_markup=main_menu(username))
    close_connection(conn, cur)

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    if message.text == "Add Product":
        if is_admin(message.from_user.username):
            msg = bot.send_message(message.chat.id, "Enter product details in the format: name, description, price")
            bot.register_next_step_handler(msg, process_add_product)
        else:
            bot.send_message(message.chat.id, "You don't have permission to add products.")
    elif message.text == "Delete Product":
        if is_admin(message.from_user.username):
            msg = bot.send_message(message.chat.id, "Enter the product ID to delete")
            bot.register_next_step_handler(msg, process_delete_product)
        else:
            bot.send_message(message.chat.id, "You don't have permission to delete products.")
    elif message.text == "View Products":
        view_products(message)
    elif message.text == "View Cart":
        view_cart(message)
    elif message.text == "Checkout":
        checkout(message)
    elif message.text == "Order Status":
        order_status(message)
    elif message.text == "Add To Cart":
        msg = bot.send_message(message.chat.id, "Enter the product ID and quantity in the format: ID, quantity")
        bot.register_next_step_handler(msg, process_add_to_cart)
    elif message.text == "Update Cart":
        msg = bot.send_message(message.chat.id, "Enter the product ID and new quantity in the format: ID, new_quantity")
        bot.register_next_step_handler(msg, process_update_cart)
    elif message.text == "Remove From Cart":
        msg = bot.send_message(message.chat.id, "Enter the product ID to remove from cart")
        bot.register_next_step_handler(msg, process_remove_from_cart)

def process_add_product(message):
    bot.send_message(message.chat.id, "Now send the product image.")
    bot.register_next_step_handler(message, process_product_image, message.text)

def process_product_image(message, product_info):
    try:
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            image_bytes = io.BytesIO(downloaded_file)            
            name, description, price = product_info.split(',')
            conn = open_connection()
            cur = conn.cursor()            
            cur.execute(
                "INSERT INTO products (name, description, price, image) VALUES (%s, %s, %s, %s)",
                (name.strip(), description.strip(), float(price.strip()), image_bytes.getvalue())
            )
            conn.commit()
            bot.send_message(message.chat.id, "Product successfully added with image!")
        else:
            bot.send_message(message.chat.id, "Please send an image.")
    except Exception as e:
        bot.send_message(message.chat.id, "Error adding product. Please check the format.")
        print(e)
    finally:
        close_connection(conn, cur)

def process_delete_product(message):
    try:
        conn = open_connection()
        cur = conn.cursor()
        product_id = int(message.text)
        cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
        conn.commit()
        bot.send_message(message.chat.id, "Product successfully deleted!")
    except Exception as e:
        bot.send_message(message.chat.id, "Error deleting product. Please ensure the ID is correct.")
        print(e)
    finally:
        close_connection(conn, cur)

def view_products(message):
    conn = open_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, image FROM products")
    products = cur.fetchall()
    if products:
        for product in products:
            product_id, name, price, image = product
            bot.send_message(message.chat.id, f"ID: {product_id}\nName: {name}\nPrice: {price}$")
            if image:
                image_bytes = io.BytesIO(image)
                bot.send_photo(message.chat.id, image_bytes)
    else:
        bot.send_message(message.chat.id, "No available products")
    close_connection(conn, cur)

def view_cart(message):
    conn = open_connection()
    cur = conn.cursor()
    user_id = message.chat.id
    cur.execute("""
        SELECT p.name, c.quantity, p.price
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
    """, (user_id,))
    cart_items = cur.fetchall()
    if cart_items:
        for item in cart_items:
            bot.send_message(message.chat.id, f"Product: {item[0]}, Quantity: {item[1]}, Price per unit: {item[2]}$")
    else:
        bot.send_message(message.chat.id, "Your cart is empty.")
    close_connection(conn, cur)

def process_add_to_cart(message):
    try:
        conn = open_connection()
        cur = conn.cursor()
        product_id, quantity = map(int, message.text.split(','))
        user_id = message.chat.id
        cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product = cur.fetchone()
        if not product:
            bot.send_message(message.chat.id, "Product not found.")
            return
        cur.execute("SELECT * FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product_id))
        existing_cart_item = cur.fetchone()
        if existing_cart_item:
            cur.execute("UPDATE cart SET quantity = quantity + %s WHERE user_id = %s AND product_id = %s",
                       (quantity, user_id, product_id))
        else:
            cur.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)",
                       (user_id, product_id, quantity))
        conn.commit()
        bot.send_message(message.chat.id, "Product successfully added to cart!")
    except Exception as e:
        bot.send_message(message.chat.id, "Error adding product to cart. Please check the input.")
        print(e)
    finally:
        close_connection(conn, cur)

def process_update_cart(message):
    try:
        conn = open_connection()
        cur = conn.cursor()
        product_id, new_quantity = map(int, message.text.split(','))
        user_id = message.chat.id
        cur.execute("UPDATE cart SET quantity = %s WHERE user_id = %s AND product_id = %s",
                   (new_quantity, user_id, product_id))
        conn.commit()
        bot.send_message(message.chat.id, "Cart updated successfully!")
    except Exception as e:
        bot.send_message(message.chat.id, "Error updating cart. Please check the input.")
        print(e)
    finally:
        close_connection(conn, cur)

def process_remove_from_cart(message):
    try:
        conn = open_connection()
        cur = conn.cursor()
        product_id = int(message.text)
        user_id = message.chat.id
        cur.execute("DELETE FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product_id))
        conn.commit()
        bot.send_message(message.chat.id, "Product successfully removed from cart!")
    except Exception as e:
        bot.send_message(message.chat.id, "Error removing product from cart. Please check the input.")
        print(e)
    finally:
        close_connection(conn, cur)

def checkout(message):
    try:
        conn = open_connection()
        cur = conn.cursor()
        user_id = message.chat.id
        cur.execute("""
            SELECT p.price, c.quantity
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = %s
        """, (user_id,))
        cart_items = cur.fetchall()
        if cart_items:
            total_amount = sum(item[0] * item[1] for item in cart_items)
            cur.execute(
                "INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, %s)",
                (user_id, total_amount, "processing")
            )
            conn.commit()
            cur.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
            conn.commit()
            bot.send_message(message.chat.id, f"Order successfully placed for {total_amount}$. Status: processing.")
        else:
            bot.send_message(message.chat.id, "Your cart is empty.")
    except Exception as e:
        bot.send_message(message.chat.id, "Error placing the order. Please try again.")
        print(e)
    finally:
        close_connection(conn, cur)

def order_status(message):
    conn = open_connection()
    cur = conn.cursor()
    user_id = message.chat.id
    cur.execute("SELECT id, total_amount, status FROM orders WHERE user_id = %s", (user_id,))
    orders = cur.fetchall()
    if orders:
        for order in orders:
            bot.send_message(message.chat.id, f"Order ID: {order[0]}, Total: {order[1]}$, Status: {order[2]}")
    else:
        bot.send_message(message.chat.id, "You have no orders.")
    close_connection(conn, cur)

bot.infinity_polling()