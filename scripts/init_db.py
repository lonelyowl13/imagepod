#!/usr/bin/env python3
"""
Database initialization script for ImagePod
Creates initial data and admin user
"""

import asyncio
import sys
import os
from sqlalchemy.orm import Session

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal, engine, Base
from app.services.user_service import UserService
from app.services.billing_service import BillingService
from app.schemas.user import UserCreate
from app.schemas.billing import BillingAccountCreate
from app.models import *  # Import all models


def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")


def create_admin_user():
    """Create an admin user"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        billing_service = BillingService(db)
        
        # Check if admin user already exists
        admin_user = user_service.get_user_by_email("admin@imagepod.com")
        if admin_user:
            print("✅ Admin user already exists")
            return admin_user
        
        # Create admin user
        admin_data = UserCreate(
            email="admin@imagepod.com",
            username="admin",
            full_name="ImagePod Administrator",
            password="admin123"  # Change this in production!
        )
        
        admin_user = user_service.create_user(admin_data)
        
        # Make user a superuser
        admin_user.is_superuser = True
        admin_user.is_verified = True
        db.commit()
        
        # Create default billing account
        billing_account_data = BillingAccountCreate(
            name="Admin Account",
            billing_email=admin_user.email,
            is_primary=True,
            auto_recharge=True,
            auto_recharge_threshold=10.0,
            auto_recharge_amount=100.0
        )
        
        billing_service.create_billing_account(admin_user.id, billing_account_data)
        
        print("✅ Admin user created:")
        print(f"   Email: {admin_user.email}")
        print(f"   Username: {admin_user.username}")
        print(f"   Password: admin123")
        print(f"   API Key: {admin_user.api_key}")
        print("⚠️  Please change the admin password after first login!")
        
        return admin_user
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return None
    finally:
        db.close()


def create_sample_templates():
    """Create sample job templates"""
    db = SessionLocal()
    try:
        from app.models.job import JobTemplate
        
        # Check if templates already exist
        existing_templates = db.query(JobTemplate).count()
        if existing_templates > 0:
            print("✅ Sample templates already exist")
            return
        
        # Create sample templates
        templates = [
            {
                "name": "Stable Diffusion Text-to-Image",
                "description": "Generate images from text prompts using Stable Diffusion",
                "docker_image": "runpod/stable-diffusion",
                "docker_tag": "latest",
                "template_config": {
                    "handler": "handler.py",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string"},
                            "negative_prompt": {"type": "string"},
                            "width": {"type": "integer", "default": 512},
                            "height": {"type": "integer", "default": 512},
                            "num_inference_steps": {"type": "integer", "default": 20}
                        },
                        "required": ["prompt"]
                    }
                },
                "min_gpu_memory": 4096,
                "max_gpu_memory": 8192,
                "min_cpu_cores": 2,
                "max_cpu_cores": 4,
                "min_ram": 8192,
                "max_ram": 16384,
                "base_price_per_second": 0.01,
                "is_public": True
            },
            {
                "name": "LLaMA Text Generation",
                "description": "Generate text using LLaMA language model",
                "docker_image": "runpod/llama",
                "docker_tag": "latest",
                "template_config": {
                    "handler": "handler.py",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string"},
                            "max_tokens": {"type": "integer", "default": 100},
                            "temperature": {"type": "number", "default": 0.7}
                        },
                        "required": ["prompt"]
                    }
                },
                "min_gpu_memory": 8192,
                "max_gpu_memory": 16384,
                "min_cpu_cores": 4,
                "max_cpu_cores": 8,
                "min_ram": 16384,
                "max_ram": 32768,
                "base_price_per_second": 0.02,
                "is_public": True
            }
        ]
        
        for template_data in templates:
            template = JobTemplate(**template_data)
            db.add(template)
        
        db.commit()
        print("✅ Sample job templates created")
        
    except Exception as e:
        print(f"❌ Error creating sample templates: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Main initialization function"""
    print("🚀 Initializing ImagePod database...")
    
    try:
        # Create tables
        create_tables()
        
        # Create admin user
        create_admin_user()
        
        # Create sample templates
        create_sample_templates()
        
        print("\n🎉 Database initialization complete!")
        print("\n📋 Next steps:")
        print("   1. Start the API: docker-compose up -d api")
        print("   2. Access API docs: http://localhost:8000/docs")
        print("   3. Login with admin credentials")
        print("   4. Create your first job template")
        print("   5. Set up worker pools")
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
