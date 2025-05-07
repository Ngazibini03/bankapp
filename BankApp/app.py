from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import random
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)

# File to store user data
users_file = "users.txt"
transactions_file = "transactions.txt"

# Helper function to read users from the text file
def read_users():
    users = {}
    if os.path.exists(users_file):
        with open(users_file, 'r') as file:
            for line in file:
                user_data = line.strip().split(",")
                if len(user_data) == 8:
                    users[user_data[4]] = {
                        "name": user_data[0],
                        "surname": user_data[1],
                        "phone": user_data[2],
                        "id_number": user_data[3],
                        "balance": float(user_data[5]),
                        "account_number": user_data[6],
                        "password": user_data[7]  # Add the password field
                    }
                else:
                    print(f"Skipping malformed line: {line.strip()}")
    return users

# Helper function to save user data to the text file
def save_users(users):
    with open(users_file, 'w') as file:
        for username, user in users.items():
            file.write(f"{user['name']},{user['surname']},{user['phone']},{user['id_number']},{username},{user['balance']},{user['account_number']},{user['password']}\n")

# Helper function to read transaction history
def read_transactions():
    transactions = []
    if os.path.exists(transactions_file):
        with open(transactions_file, 'r') as file:
            for line in file:
                transaction_data = line.strip().split(",")
                # Check if transaction_data has the expected number of fields
                if len(transaction_data) >= 6:  # Ensure we have enough fields
                    transactions.append({
                        'date': transaction_data[0],
                        'type': transaction_data[1],
                        'amount': transaction_data[2],
                        'details': transaction_data[5]  # Ensure this field contains account info
                    })
                else:
                    print(f"Skipping malformed transaction line: {line.strip()}")
    return transactions


# Helper function to log transactions
def log_transaction(transaction):
    with open(transactions_file, 'a') as file:
        file.write(transaction + "\n")

# Helper function to validate phone number (South African format)
def is_valid_phone(phone):
    return re.match(r"^\+27\d{9}$", phone) is not None

# Helper function to validate ID number (Example: simple check for digits and length)
def is_valid_id(id_number):
    return id_number.isdigit() and len(id_number) == 13

# Helper function to validate name and surname (letters only)
def is_valid_name(name):
    return re.match(r"^[A-Za-z]+$", name) is not None

# Helper function to validate username (not just numbers)
def is_valid_username(username):
    return re.match(r"^(?!\d+$)[A-Za-z09]+$", username) is not None

# Helper function to generate a 6-digit account number
def generate_account_number():
    return str(random.randint(100000, 999999))

# Route to homepage - always redirect to register page
@app.route('/')
def home():
    return redirect(url_for('login'))

# Route to register new users
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        id_number = request.form['id_number']
        username = request.form['username']
        password = request.form['password']

        # Validate name and surname (letters only)
        if not is_valid_name(name):
            flash('Name must contain only letters (no numbers or special characters).', 'danger')
            return render_template('register.html')

        if not is_valid_name(surname):
            flash('Surname must contain only letters (no numbers or special characters).', 'danger')
            return render_template('register.html')

        # Validate phone number (South African format)
        if not is_valid_phone(phone):
            flash('Invalid phone number! Please enter a valid South African phone number (e.g., +27638201155).', 'danger')
            return render_template('register.html')

        # Validate ID number
        if not is_valid_id(id_number):
            flash('Invalid ID number! Please enter a valid 13-digit ID number.', 'danger')
            return render_template('register.html')

        # Validate username (not just numbers)
        if not is_valid_username(username):
            flash('Username must contain at least one letter and cannot be just numbers.', 'danger')
            return render_template('register.html')

        # Read users from file
        users = read_users()

        # Check if username already exists
        if username in users:
            flash('Username already exists, please choose another.', 'danger')
            return render_template('register.html')

        # Check if ID number already exists
        for user in users.values():
            if user['id_number'] == id_number:
                flash('ID number already exists, please use a different one.', 'danger')
                return render_template('register.html')

        # Generate 6-digit account number
        account_number = generate_account_number()

        # Save new user
        users[username] = {
            'name': name,
            'surname': surname,
            'phone': phone,
            'id_number': id_number,
            'balance': 0.0,
            'account_number': account_number,
            'password': password
        }

        # Save users to file
        save_users(users)

        flash(f"Account created successfully! Your account number is {account_number}.", 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Route to login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = read_users()
        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))

        flash('Invalid username or password!', 'danger')
        return render_template('login.html')

    return render_template('login.html')

# Route to dashboard
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    users = read_users()
    user = users[username]

    return render_template('dashboard.html', user=user)

# Route to deposit money
@app.route('/deposit', methods=['POST'])
def deposit():
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        amount = float(request.form['amount'])
    except ValueError:
        flash("Invalid amount. Please enter a numeric value.", "danger")
        return redirect(url_for('dashboard'))

    if amount <= 0:
        flash("Deposit amount must be positive!", "danger")
        return redirect(url_for('dashboard'))

    username = session['username']
    users = read_users()
    users[username]['balance'] += amount
    save_users(users)

    # Log the transaction in ZAR (South African Rands)
    log_transaction(f"{datetime.now()}, Deposit, {amount}, , , Account {users[username]['account_number']} deposited {amount} ZAR")
    flash(f"Deposited R{amount} successfully!", "success")
    return redirect(url_for('dashboard'))

# Route to withdraw money
@app.route('/withdraw', methods=['POST'])
def withdraw():
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        amount = float(request.form['amount'])
    except ValueError:
        flash("Invalid amount. Please enter a numeric value.", "danger")
        return redirect(url_for('dashboard'))

    if amount <= 0:
        flash("Withdrawal amount must be positive!", "danger")
        return redirect(url_for('dashboard'))

    username = session['username']
    users = read_users()
    if users[username]['balance'] < amount:
        flash("Insufficient balance!", "danger")
        return redirect(url_for('dashboard'))

    users[username]['balance'] -= amount
    save_users(users)

    # Log the transaction in ZAR (South African Rands)
    log_transaction(f"{datetime.now()}, Withdrawal, {amount}, , , Account {users[username]['account_number']} withdrew {amount} ZAR")
    flash(f"Withdrew R{amount} successfully!", "success")
    return redirect(url_for('dashboard'))

# Route to transfer money
@app.route('/transfer', methods=['POST'])
def transfer():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get the transfer amount
    try:
        amount = float(request.form.get('amount', 0))  # Default to 0 if the field is missing
    except ValueError:
        flash("Invalid amount. Please enter a numeric value.", "danger")
        return redirect(url_for('dashboard'))

    if amount <= 0:
        flash("Transfer amount must be positive!", "danger")
        return redirect(url_for('dashboard'))

    # Retrieve the recipient's account number
    recipient_account = request.form.get('recipient_account')  # Correct field name here
    if not recipient_account or recipient_account.strip() == "":
        flash("Recipient account number is required!", "danger")
        return redirect(url_for('dashboard'))

    username = session['username']
    users = read_users()

    # Check if the user has sufficient balance
    if users[username]['balance'] < amount:
        flash("Insufficient balance!", "danger")
        return redirect(url_for('dashboard'))

    # Find the recipient user by account number
    recipient_user = None
    for user_username, user_data in users.items():
        if user_data['account_number'] == recipient_account:
            recipient_user = user_data
            break

    if not recipient_user:
        flash("Recipient account not found!", "danger")
        return redirect(url_for('dashboard'))

    # Perform the transfer
    users[username]['balance'] -= amount
    recipient_user['balance'] += amount

    # Save updated users
    save_users(users)

    # Log the transaction
    log_transaction(
        f"{datetime.now()}, Transfer, {amount}, Account {users[username]['account_number']}, Account {recipient_account}, "
        f"Account {users[username]['account_number']} transferred {amount} ZAR to Account {recipient_account}"
    )

    flash(f"Transferred R{amount} successfully to Account {recipient_account}!", "success")
    return redirect(url_for('dashboard'))


@app.route('/view_history')
def view_history():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch logged-in user details
    username = session['username']
    users = read_users()
    user_account_number = users[username]['account_number']  # Get account number for the logged-in user

    # Get all transactions
    transactions = read_transactions()

    # Filter transactions for the logged-in user
    user_transactions = [transaction for transaction in transactions if user_account_number in transaction['details']]

    return render_template('view_history.html', transactions=user_transactions)


# Route to logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)