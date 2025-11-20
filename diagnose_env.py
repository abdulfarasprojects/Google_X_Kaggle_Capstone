#!/usr/bin/env python3
"""
ADK Environment Diagnostic and Startup Script

This script:
1. Verifies ADK is properly installed
2. Checks all dependencies
3. Initializes the agent runner
4. Outputs status and next steps
"""

import sys
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

def check_adk_availability():
    """Check if ADK is available without hanging"""
    logger.info("=" * 80)
    logger.info("ADK ENVIRONMENT DIAGNOSTIC")
    logger.info("=" * 80)
    logger.info("")
    
    # Step 1: Check google.adk import
    logger.info("[1] Checking google.adk module...")
    try:
        # Use importlib to check without full import
        import importlib.util
        spec = importlib.util.find_spec("google.adk")
        if spec:
            logger.info("    ✅ google-adk module found")
            return True
        else:
            logger.error("    ❌ google-adk module not found")
            return False
    except Exception as e:
        logger.error(f"    ❌ Error checking google-adk: {e}")
        return False

def check_dependencies():
    """Check critical dependencies"""
    logger.info("[2] Checking critical dependencies...")
    
    dependencies = [
        ('config.logging', 'Logger configuration'),
        ('config.gemini', 'Gemini model client'),
        ('database.meal_manager', 'Meal manager'),
        ('telegram', 'Telegram bot library'),
        ('sqlalchemy', 'Database ORM'),
    ]
    
    all_ok = True
    for module_name, description in dependencies:
        try:
            __import__(module_name)
            logger.info(f"    ✅ {description}")
        except ImportError as e:
            logger.error(f"    ❌ {description}: {e}")
            all_ok = False
    
    return all_ok

def check_database():
    """Check database availability"""
    logger.info("[3] Checking database...")
    
    db_path = Path("/Users/abdulfaras/Google_X_Kaggle_Capstone/weight_loss_app.db")
    if db_path.exists():
        logger.info(f"    ✅ Database file exists ({db_path})")
        return True
    else:
        logger.info(f"    ℹ️  Database will be created on first run ({db_path})")
        return True

def check_config_files():
    """Check required configuration files"""
    logger.info("[4] Checking configuration files...")
    
    config_files = [
        ("/Users/abdulfaras/Google_X_Kaggle_Capstone/config/settings.py", "Settings"),
        ("/Users/abdulfaras/Google_X_Kaggle_Capstone/config/logging.py", "Logging config"),
        ("/Users/abdulfaras/Google_X_Kaggle_Capstone/telegram_bot/bot.py", "Telegram bot"),
    ]
    
    all_ok = True
    for filepath, description in config_files:
        if Path(filepath).exists():
            logger.info(f"    ✅ {description}")
        else:
            logger.error(f"    ❌ {description} missing: {filepath}")
            all_ok = False
    
    return all_ok

def main():
    """Run all checks"""
    try:
        adk_ok = check_adk_availability()
        logger.info("")
        
        deps_ok = check_dependencies()
        logger.info("")
        
        db_ok = check_database()
        logger.info("")
        
        config_ok = check_config_files()
        logger.info("")
        
        logger.info("=" * 80)
        logger.info("STARTUP STATUS")
        logger.info("=" * 80)
        
        if adk_ok and deps_ok and db_ok and config_ok:
            logger.info("✅ All checks passed!")
            logger.info("")
            logger.info("To start the bot:")
            logger.info("  cd /Users/abdulfaras/Google_X_Kaggle_Capstone")
            logger.info("  python telegram_bot/bot.py")
            logger.info("")
            logger.info("✅ Environment is ready!")
            return 0
        else:
            logger.error("❌ Some checks failed. Please fix the issues above.")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Diagnostic failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
