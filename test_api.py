#!/usr/bin/env python3
"""
Simple API test script for ImagePod
Tests basic functionality without authentication
"""

import requests
import json
import time


def test_health_endpoint():
    """Test the health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Health endpoint working")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False


def test_root_endpoint():
    """Test the root endpoint"""
    print("🔍 Testing root endpoint...")
    try:
        response = requests.get("http://localhost:8000/")
        if response.status_code == 200:
            print("✅ Root endpoint working")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False


def test_docs_endpoint():
    """Test the API docs endpoint"""
    print("🔍 Testing API docs endpoint...")
    try:
        response = requests.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print("✅ API docs endpoint working")
            return True
        else:
            print(f"❌ API docs endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API docs endpoint error: {e}")
        return False


def test_register_endpoint():
    """Test user registration"""
    print("🔍 Testing user registration...")
    try:
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "password": "testpassword123"
        }
        
        response = requests.post("http://localhost:8000/auth/register", json=user_data)
        if response.status_code == 200:
            print("✅ User registration working")
            user = response.json()
            print(f"   Created user: {user['username']} ({user['email']})")
            return user
        else:
            print(f"❌ User registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ User registration error: {e}")
        return None


def test_login_endpoint():
    """Test user login"""
    print("🔍 Testing user login...")
    try:
        login_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        
        response = requests.post("http://localhost:8000/auth/login", json=login_data)
        if response.status_code == 200:
            print("✅ User login working")
            token_data = response.json()
            print(f"   Token type: {token_data['token_type']}")
            return token_data['access_token']
        else:
            print(f"❌ User login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ User login error: {e}")
        return None


def test_protected_endpoint(token):
    """Test a protected endpoint"""
    print("🔍 Testing protected endpoint...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get("http://localhost:8000/auth/me", headers=headers)
        if response.status_code == 200:
            print("✅ Protected endpoint working")
            user = response.json()
            print(f"   Authenticated as: {user['username']} ({user['email']})")
            return True
        else:
            print(f"❌ Protected endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Protected endpoint error: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Starting ImagePod API tests...")
    print("=" * 50)
    
    # Test basic endpoints
    health_ok = test_health_endpoint()
    root_ok = test_root_endpoint()
    docs_ok = test_docs_endpoint()
    
    if not all([health_ok, root_ok, docs_ok]):
        print("\n❌ Basic endpoints failed. Make sure the API is running.")
        print("   Start with: docker-compose up -d api")
        return
    
    print("\n" + "=" * 50)
    
    # Test authentication flow
    user = test_register_endpoint()
    if not user:
        print("\n❌ User registration failed. Check database connection.")
        return
    
    token = test_login_endpoint()
    if not token:
        print("\n❌ User login failed.")
        return
    
    protected_ok = test_protected_endpoint(token)
    
    print("\n" + "=" * 50)
    
    # Summary
    if all([health_ok, root_ok, docs_ok, user, token, protected_ok]):
        print("🎉 All tests passed!")
        print("\n📋 Your ImagePod API is working correctly!")
        print("   - API: http://localhost:8000")
        print("   - Docs: http://localhost:8000/docs")
        print("   - Test user created: test@example.com")
        print("   - Password: testpassword123")
    else:
        print("❌ Some tests failed. Check the logs above.")
    
    print("\n🔧 Next steps:")
    print("   1. Explore the API docs at http://localhost:8000/docs")
    print("   2. Create job templates")
    print("   3. Set up worker pools")
    print("   4. Configure billing accounts")


if __name__ == "__main__":
    main()
