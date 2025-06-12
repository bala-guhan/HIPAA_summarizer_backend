from auth import auth_handler

def create_test_user(name, pwd, role="user"):
    try:
        # Create a test user with sample PHI data
        user_data = {
            "name": name,
            "email": f"{name.lower()}@example.com",
            "phone": "123-456-7890",
            "dob": "1990-01-01",
            "ssn": "123-45-6789"
        }
        
        # Create a test user
        res = auth_handler.register_user(
            username=name,
            password=pwd,
            user_data=user_data
        )
        if res:
            print("User created successfully!")
        else:
            print("Registration failed")
    except Exception as e:
        print(f"Error creating test user: {str(e)}")

if __name__ == "__main__":
    create_test_user('Saubhik Bhaumik', '12345678') 