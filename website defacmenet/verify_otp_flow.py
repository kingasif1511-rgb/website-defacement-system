from datetime import datetime, timedelta
from app import create_app
from database.models import db, User

def test_otp_verification_flow():
    print("=== Sentinel Guard OTP Flow Integration Test ===")
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF in tests for simplified mock requests
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_otp_verify.db'
    
    # Establish test client context
    client = app.test_client()
    
    with app.app_context():
        # Reset testing database
        db.drop_all()
        db.create_all()
        print("1. Testing database reset.")
        
        # 1. Register a user via POST
        reg_payload = {
            'username': 'tester',
            'email': 'tester@sentinel.local',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        }
        response = client.post('/register', data=reg_payload, follow_redirects=False)
        print("2. Registration request sent.")
        
        # Verify redirect occurred to the OTP verification page
        assert response.status_code == 302
        assert '/verify-otp' in response.headers['Location']
        print(f"   -> Redirected to: {response.headers['Location']}")
        
        # Query user in DB
        user = User.query.filter_by(email='tester@sentinel.local').first()
        assert user is not None
        assert user.is_verified is False
        assert user.otp is not None
        assert len(user.otp) == 6
        saved_otp = user.otp
        print(f"3. User stored in DB. Status: is_verified={user.is_verified}. Generated OTP: {saved_otp}")
        
        # 2. Try logging in immediately before verification (should be blocked)
        login_payload = {
            'username_or_email': 'tester@sentinel.local',
            'password': 'Password123!'
        }
        login_response = client.post('/login', data=login_payload, follow_redirects=False)
        assert login_response.status_code == 302
        assert '/verify-otp' in login_response.headers['Location']
        print("4. Checked login block. Unverified user rejected and redirected to OTP validation form.")
        
        # 3. Submit invalid OTP
        otp_bad_payload = {
            'email': 'tester@sentinel.local',
            'otp': '999999' # Incorrect OTP
        }
        bad_verify_response = client.post('/verify-otp', data=otp_bad_payload, follow_redirects=True)
        # Check that user remains unverified in DB
        user = User.query.filter_by(email='tester@sentinel.local').first()
        assert user.is_verified is False
        print("5. Attempted verify with bad OTP code. Correctly rejected; database state remains unverified.")
        
        # 4. Submit correct OTP
        otp_good_payload = {
            'email': 'tester@sentinel.local',
            'otp': saved_otp
        }
        good_verify_response = client.post('/verify-otp', data=otp_good_payload, follow_redirects=False)
        assert good_verify_response.status_code == 302
        assert '/login' in good_verify_response.headers['Location']
        
        # Verify user is now activated
        user = User.query.filter_by(email='tester@sentinel.local').first()
        assert user.is_verified is True
        assert user.otp is None
        print(f"6. Verified with correct OTP code. Redirected to login. Database state updated: is_verified={user.is_verified}")
        
        # 5. Log in after verification (should succeed)
        final_login_response = client.post('/login', data=login_payload, follow_redirects=False)
        assert final_login_response.status_code == 302
        assert '/dashboard' in final_login_response.headers['Location']
        print("7. Checked login success. Verified user successfully authenticated and redirected to dashboard.")
        
    print("\n=== OTP AUTH FLOW INTEGRATION TEST PASSED SUCCESSFUL ===")

if __name__ == '__main__':
    test_otp_verification_flow()
