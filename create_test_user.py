from auth import auth_handler

def create_test_user():
    try:
        # Create a test user
        auth_handler.register_user(
            username="johndoe",
            password="12345678",
            role="user"
        )
        print("Test user created successfully!")
        print(f"Username: johndoe")
        print("Password: 12345678")
    except Exception as e:
        print(f"Error creating test user: {str(e)}")

if __name__ == "__main__":
    create_test_user() 